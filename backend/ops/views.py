from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as SerValidationError

from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from core.workflow import WorkflowActionsMixin
from ops.commerce_serializers import (
    GoodsReceiptSerializer,
    SalesQuotationSerializer,
    convert_quotation_to_so,
)
from ops.pr_dn_serializers import (
    DeliveryNoteSerializer,
    PurchaseRequisitionSerializer,
    convert_requisition_to_po,
)
from ops.tier1_serializers import (
    LandedCostSerializer,
    PriceListSerializer,
    PurchaseReturnSerializer,
    SalesReturnSerializer,
    StocktakeSerializer,
    VendorRFQQuoteSerializer,
    VendorRFQSerializer,
    award_rfq,
    post_landed_cost,
    post_purchase_return,
    post_sales_return,
    post_stocktake,
)
from ops.models import (
    Customer,
    CustomerContract,
    DeliveryNote,
    GoodsReceipt,
    Item,
    ItemLot,
    UnitOfMeasure,
    ensure_default_units,
    LandedCost,
    LotBatch,
    PriceList,
    PurchaseOrder,
    PurchaseRequisition,
    PurchaseReturn,
    SalesOrder,
    SalesQuotation,
    SalesReturn,
    SerialNumber,
    StockLevel,
    StockMovement,
    Stocktake,
    VendorRFQ,
    VendorRFQQuote,
    Warehouse,
)
from ops.serializers import (
    CustomerSerializer,
    ItemLotSerializer,
    ItemSerializer,
    UnitOfMeasureSerializer,
    LotBatchSerializer,
    PurchaseOrderSerializer,
    SalesOrderSerializer,
    SerialNumberSerializer,
    StockLevelSerializer,
    StockMovementSerializer,
    WarehouseSerializer,
    deliver_sales_order,
    receive_purchase_order,
)
from ops.enterprise_serializers import (
    CustomerContractSerializer,
    generate_contract_invoice,
)


class CustomerViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ("code", "name", "email", "phone", "ntn", "contact_person", "city")
    filterset_fields = ("is_active", "currency")
    rbac_module = "sales.customers"


class SalesOrderViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = SalesOrder.objects.select_related("customer", "warehouse").prefetch_related(
        "lines__item", "lines__warehouse"
    )
    serializer_class = SalesOrderSerializer
    search_fields = ("order_no", "customer__name", "customer__code", "customer_po", "notes")
    filterset_fields = ("status", "customer", "currency", "warehouse")
    rbac_module = "sales.orders"
    # Submit from draft confirms the order (sales confirm, not LoA approve)
    workflow_submit_to = "confirmed"
    workflow_approve_to = "confirmed"
    workflow_reject_to = "cancelled"

    def perform_destroy(self, instance):
        if instance.status not in (SalesOrder.Status.DRAFT, SalesOrder.Status.CANCELLED):
            raise SerValidationError(
                "Only draft or cancelled sales orders can be deleted."
            )
        return super().perform_destroy(instance)

    def submit(self, request, pk=None):
        """Confirm SO with credit-limit check against open orders."""
        from django.db.models import Sum

        so = self.get_object()
        customer = so.customer
        limit = customer.credit_limit or Decimal("0")
        if limit > 0:
            open_amt = (
                SalesOrder.objects.filter(
                    organization_id=so.organization_id,
                    customer_id=customer.id,
                    is_deleted=False,
                    status__in=[
                        SalesOrder.Status.CONFIRMED,
                        SalesOrder.Status.DELIVERED,
                    ],
                )
                .exclude(pk=so.pk)
                .aggregate(s=Sum("amount"))["s"]
                or Decimal("0")
            )
            proposed = Decimal(str(open_amt)) + Decimal(str(so.amount or 0))
            if proposed > limit:
                return Response(
                    {
                        "detail": (
                            f"Credit limit exceeded for {customer.code}: "
                            f"exposure {proposed.quantize(Decimal('0.01'))} "
                            f"exceeds limit {limit.quantize(Decimal('0.01'))} "
                            f"{customer.currency or so.currency or ''}."
                        ),
                        "code": "credit_limit",
                        "exposure": str(proposed),
                        "credit_limit": str(limit),
                    },
                    status=400,
                )
        return super().submit(request, pk)

    @action(detail=True, methods=["post"], url_path="deliver")
    def deliver(self, request, pk=None):
        so = self.get_object()
        warehouse_id = request.data.get("warehouse")
        lines = request.data.get("lines")
        try:
            deliver_sales_order(
                so, warehouse_id=warehouse_id, user=request.user, lines=lines
            )
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        so.refresh_from_db()
        data = self.get_serializer(so).data
        dn = getattr(so, "_last_dn", None)
        if dn:
            data["dn_id"] = dn.id
            data["dn_no"] = dn.dn_no
            data["href"] = f"/sales/deliveries/{dn.id}"
        return Response(data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        so = self.get_object()
        if so.status in (SalesOrder.Status.DELIVERED, SalesOrder.Status.INVOICED):
            return Response(
                {"detail": "Cannot cancel a delivered/invoiced sales order."},
                status=400,
            )
        if so.lines.filter(qty_delivered__gt=0).exists():
            return Response(
                {"detail": "Cannot cancel after delivery has started."},
                status=400,
            )
        return self._set_status(so, SalesOrder.Status.CANCELLED, "cancel")

    @action(detail=True, methods=["post"], url_path="mark-invoiced")
    def mark_invoiced(self, request, pk=None):
        so = self.get_object()
        if so.status not in (SalesOrder.Status.DELIVERED, SalesOrder.Status.CONFIRMED):
            return Response(
                {"detail": "Confirm or deliver the order before marking invoiced."},
                status=400,
            )
        return self._set_status(so, SalesOrder.Status.INVOICED, "mark_invoiced")

    @action(detail=True, methods=["post"], url_path="create-invoice")
    def create_invoice(self, request, pk=None):
        """Create draft AR invoice linked to this sales order."""
        from core.doc_numbers import ensure_doc_no
        from finance.models import CustomerInvoice

        so = self.get_object()
        if so.status not in (
            SalesOrder.Status.CONFIRMED,
            SalesOrder.Status.DELIVERED,
            SalesOrder.Status.INVOICED,
        ):
            return Response(
                {"detail": "Confirm the sales order before creating an AR invoice."},
                status=400,
            )
        existing = CustomerInvoice.objects.filter(
            organization_id=so.organization_id,
            sales_order=so,
            is_deleted=False,
        ).exclude(status="rejected")
        if existing.exists():
            inv = existing.first()
            return Response(
                {
                    "detail": "An AR invoice already exists for this sales order.",
                    "invoice_id": inv.id,
                    "invoice_no": inv.invoice_no,
                },
                status=400,
            )
        terms = so.payment_terms_days or 30
        inv_date = timezone.localdate()
        data = {
            "invoice_no": "",
            "organization_id": so.organization_id,
            "customer_id": so.customer_id,
            "invoice_date": inv_date,
            "due_date": inv_date + timedelta(days=terms),
            "amount": so.amount or Decimal("0"),
            "tax_amount": so.tax_amount or Decimal("0"),
            "status": CustomerInvoice.Status.DRAFT,
            "currency": so.currency or "PKR",
            "description": f"AR from SO {so.order_no}",
            "created_by": request.user,
            "updated_by": request.user,
        }
        ensure_doc_no(
            data, "invoice_no", so.organization, kind="ar_invoice", model=CustomerInvoice
        )
        inv = CustomerInvoice.objects.create(sales_order=so, **data)
        return Response(
            {
                "id": inv.id,
                "invoice_no": inv.invoice_no,
                "amount": str(inv.amount),
                "status": inv.status,
                "href": f"/sales/invoices/{inv.id}",
            },
            status=status.HTTP_201_CREATED,
        )


class SalesQuotationViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SalesQuotation.objects.select_related(
        "customer", "sales_order"
    ).prefetch_related("lines__item")
    serializer_class = SalesQuotationSerializer
    search_fields = ("quote_no", "customer__name", "customer__code", "notes")
    filterset_fields = ("status", "customer", "currency")
    rbac_module = "sales.quotes"

    @action(detail=True, methods=["post"], url_path="send")
    def send_quote(self, request, pk=None):
        quote = self.get_object()
        if quote.status != SalesQuotation.Status.DRAFT:
            return Response({"detail": "Only draft quotes can be sent."}, status=400)
        quote.status = SalesQuotation.Status.SENT
        quote.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        quote = self.get_object()
        if quote.status not in (
            SalesQuotation.Status.DRAFT,
            SalesQuotation.Status.SENT,
        ):
            return Response({"detail": "Cannot accept this quotation."}, status=400)
        quote.status = SalesQuotation.Status.ACCEPTED
        quote.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        quote = self.get_object()
        try:
            so = convert_quotation_to_so(quote, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        return Response(
            {
                "quotation": self.get_serializer(quote).data,
                "sales_order_id": so.id,
                "order_no": so.order_no,
                "href": f"/sales/orders/{so.id}",
            }
        )


class GoodsReceiptViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.select_related(
        "vendor", "purchase_order", "warehouse", "received_by"
    ).prefetch_related("lines__item")
    serializer_class = GoodsReceiptSerializer
    search_fields = ("grn_no", "purchase_order__po_no", "vendor__name", "notes")
    filterset_fields = ("status", "qc_status", "vendor", "purchase_order", "warehouse")
    http_method_names = ["get", "patch", "head", "options", "delete"]
    rbac_module = "procurement.receipts"

    def partial_update(self, request, *args, **kwargs):
        """Allow QC status updates only."""
        grn = self.get_object()
        qc = request.data.get("qc_status")
        if qc not in (
            GoodsReceipt.QcStatus.PENDING,
            GoodsReceipt.QcStatus.PASSED,
            GoodsReceipt.QcStatus.FAILED,
        ):
            return Response(
                {"detail": "Provide qc_status: pending, passed, or failed."},
                status=400,
            )
        grn.qc_status = qc
        from ops.qc_hold import apply_grn_status

        apply_grn_status(grn, qc)
        grn.refresh_from_db()
        return Response(self.get_serializer(grn).data)

    @action(detail=True, methods=["post"], url_path="set-qc")
    def set_qc(self, request, pk=None):
        return self.partial_update(request, pk=pk)

    @action(detail=True, methods=["get", "patch"], url_path="put-away")
    def put_away(self, request, pk=None):
        from ops.wms import apply_grn_putaway, grn_putaway_plan

        grn = self.get_object()
        if request.method == "GET":
            return Response(grn_putaway_plan(grn))
        try:
            plan = apply_grn_putaway(
                grn, user=request.user, lines=request.data.get("lines")
            )
        except SerValidationError:
            raise
        return Response(plan)


class PurchaseRequisitionViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = PurchaseRequisition.objects.select_related(
        "preferred_vendor", "warehouse", "purchase_order"
    ).prefetch_related("lines__item")
    serializer_class = PurchaseRequisitionSerializer
    search_fields = ("pr_no", "department", "notes", "preferred_vendor__name")
    filterset_fields = ("status", "preferred_vendor", "warehouse", "currency")
    rbac_module = "procurement.requisitions"
    workflow_reject_to = "draft"

    def perform_destroy(self, instance):
        if instance.status not in (
            PurchaseRequisition.Status.DRAFT,
            PurchaseRequisition.Status.CANCELLED,
        ):
            raise SerValidationError(
                "Only draft or cancelled requisitions can be deleted."
            )
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        pr = self.get_object()
        if pr.status == PurchaseRequisition.Status.CONVERTED:
            return Response(
                {"detail": "Cannot cancel a converted requisition."},
                status=400,
            )
        return self._set_status(pr, PurchaseRequisition.Status.CANCELLED, "cancel")

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        pr = self.get_object()
        try:
            po = convert_requisition_to_po(pr, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        return Response(
            {
                "requisition": self.get_serializer(pr).data,
                "purchase_order_id": po.id,
                "po_no": po.po_no,
                "href": f"/procurement/orders/{po.id}",
            }
        )


class DeliveryNoteViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryNote.objects.select_related(
        "customer", "sales_order", "warehouse", "delivered_by"
    ).prefetch_related("lines__item")
    serializer_class = DeliveryNoteSerializer
    search_fields = ("dn_no", "sales_order__order_no", "customer__name", "notes")
    filterset_fields = ("status", "customer", "sales_order", "warehouse")
    rbac_module = "sales.deliveries"


class WarehouseViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    search_fields = ("code", "name", "address")
    filterset_fields = ("is_active", "is_default")
    rbac_module = "inventory.warehouses"


class UnitOfMeasureViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_active", "code")
    rbac_module = "inventory.items"

    def initial(self, request, *args, **kwargs):
        from accounts.rbac import can

        if request.method in ("GET", "HEAD", "OPTIONS"):
            self.rbac_module = ""
        else:
            action = {"POST": "add", "DELETE": "delete"}.get(request.method, "change")
            if can(request.user, "inventory.items", action):
                self.rbac_module = "inventory.items"
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        from core.access import user_organization

        org = user_organization(self.request.user)
        if org:
            ensure_default_units(org)
        return super().get_queryset()


class ItemViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Item.objects.select_related("default_warehouse").prefetch_related(
        "stock_levels__warehouse"
    )
    serializer_class = ItemSerializer
    search_fields = ("sku", "name", "barcode", "category")
    filterset_fields = ("is_active", "item_type", "category", "default_warehouse")
    rbac_module = "inventory.items"

    @action(detail=True, methods=["get"], url_path="label")
    def label(self, request, pk=None):
        """Printable label payload: barcode (falls back to SKU), name, sku."""
        item = self.get_object()
        return Response(
            {
                "id": item.id,
                "barcode": item.barcode or item.sku,
                "name": item.name,
                "sku": item.sku,
                "unit": item.unit,
                "sales_price": str(item.sales_price),
                "path": f"/inventory/items/{item.id}/label",
            }
        )


class StockLevelViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockLevel.objects.select_related("warehouse", "item")
    serializer_class = StockLevelSerializer
    search_fields = ("item__sku", "item__name", "warehouse__code", "warehouse__name")
    filterset_fields = ("warehouse", "item")
    rbac_module = "inventory.items"


class StockMovementViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related(
        "item", "warehouse", "to_warehouse", "purchase_order", "sales_order"
    )
    serializer_class = StockMovementSerializer
    search_fields = ("reference", "notes", "item__sku", "item__name")
    filterset_fields = (
        "reason",
        "item",
        "warehouse",
        "to_warehouse",
        "purchase_order",
        "sales_order",
        "lot",
        "serial",
        "batch_no",
    )
    http_method_names = ["get", "post", "head", "options", "delete"]
    rbac_module = "inventory.movements"


class PurchaseOrderViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = PurchaseOrder.objects.select_related("vendor", "warehouse").prefetch_related(
        "lines__item", "lines__warehouse"
    )
    serializer_class = PurchaseOrderSerializer
    search_fields = ("po_no", "vendor__name", "vendor_ref", "notes")
    filterset_fields = ("status", "vendor", "currency", "warehouse")
    rbac_module = "procurement.orders"
    workflow_reject_to = "draft"

    def perform_destroy(self, instance):
        if instance.status not in (
            PurchaseOrder.Status.DRAFT,
            PurchaseOrder.Status.CANCELLED,
        ):
            raise SerValidationError(
                "Only draft or cancelled purchase orders can be deleted."
            )
        return super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="three-way-match")
    def three_way_match_action(self, request, pk=None):
        from ops.match import three_way_match
        from finance.models import VendorInvoice

        po = self.get_object()
        inv = (
            VendorInvoice.objects.filter(
                organization_id=po.organization_id,
                purchase_order=po,
                is_deleted=False,
            )
            .exclude(status="rejected")
            .order_by("-id")
            .first()
        )
        amt = inv.amount if inv else None
        return Response(three_way_match(po, invoice_amount=amt))

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        from ops.match import three_way_match

        po = self.get_object()
        warehouse_id = request.data.get("warehouse")
        lines = request.data.get("lines")
        try:
            receive_purchase_order(
                po, warehouse_id=warehouse_id, user=request.user, lines=lines
            )
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        po.refresh_from_db()
        data = self.get_serializer(po).data
        grn = getattr(po, "_last_grn", None)
        if grn:
            from ops.wms import grn_putaway_plan

            data["grn_id"] = grn.id
            data["grn_no"] = grn.grn_no
            plan = grn_putaway_plan(grn)
            data["putaway_pending"] = sum(
                1 for row in plan["lines"] if Decimal(row["qty"]) > 0
            )
        data["three_way_match"] = three_way_match(po)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        po = self.get_object()
        if po.status == PurchaseOrder.Status.RECEIVED:
            return Response(
                {"detail": "Cannot cancel a fully received purchase order."},
                status=400,
            )
        if po.lines.filter(qty_received__gt=0).exists():
            return Response(
                {"detail": "Cannot cancel after goods receipt has started."},
                status=400,
            )
        return self._set_status(po, PurchaseOrder.Status.CANCELLED, "cancel")

    @action(detail=True, methods=["post"], url_path="create-invoice")
    def create_invoice(self, request, pk=None):
        """Create a draft AP vendor invoice linked to this PO (requires posted GRN)."""
        from finance.models import VendorInvoice
        from core.doc_numbers import ensure_doc_no
        from ops.match import three_way_match

        po = self.get_object()
        if po.status not in (
            PurchaseOrder.Status.APPROVED,
            PurchaseOrder.Status.RECEIVED,
        ):
            return Response(
                {"detail": "Approve or receive the PO before creating an AP invoice."},
                status=400,
            )
        failed_qc = po.goods_receipts.filter(
            is_deleted=False, status="posted", qc_status=GoodsReceipt.QcStatus.FAILED
        ).exists()
        if failed_qc:
            return Response(
                {
                    "detail": "QC failed on a goods receipt for this PO — cannot create AP invoice.",
                    "code": "qc_failed",
                },
                status=400,
            )
        match = three_way_match(po, invoice_amount=po.amount or Decimal("0"))
        if match.get("status") == "no_receipt":
            return Response(
                {
                    "detail": "No goods receipt posted for this PO — receive goods before billing.",
                    "three_way_match": match,
                },
                status=400,
            )
        existing = VendorInvoice.objects.filter(
            organization_id=po.organization_id,
            purchase_order=po,
            is_deleted=False,
        ).exclude(status="rejected")
        if existing.exists():
            inv = existing.first()
            return Response(
                {
                    "detail": "An AP invoice already exists for this PO.",
                    "invoice_id": inv.id,
                    "invoice_no": inv.invoice_no,
                },
                status=400,
            )

        terms = po.payment_terms_days or 30
        inv_date = timezone.localdate()
        data = {
            "invoice_no": "",
            "organization_id": po.organization_id,
            "vendor_id": po.vendor_id,
            "invoice_date": inv_date,
            "due_date": inv_date + timedelta(days=terms),
            "amount": po.amount or Decimal("0"),
            "wht_amount": Decimal("0"),
            "status": VendorInvoice.Status.DRAFT,
            "currency": po.currency or "PKR",
            "description": f"AP from PO {po.po_no}",
            "created_by": request.user,
            "updated_by": request.user,
        }
        ensure_doc_no(
            data,
            "invoice_no",
            po.organization,
            kind="invoice",
            model=VendorInvoice,
        )
        inv = VendorInvoice.objects.create(purchase_order=po, **data)
        return Response(
            {
                "id": inv.id,
                "invoice_no": inv.invoice_no,
                "amount": str(inv.amount),
                "status": inv.status,
                "href": f"/finance/invoices/{inv.id}",
                "three_way_match": match,
            },
            status=status.HTTP_201_CREATED,
        )


class VendorRFQViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = VendorRFQ.objects.select_related(
        "warehouse", "awarded_vendor", "purchase_order"
    ).prefetch_related("lines__item", "quotes__vendor", "quotes__lines__item")
    serializer_class = VendorRFQSerializer
    search_fields = ("rfq_no", "notes", "awarded_vendor__name")
    filterset_fields = ("status", "warehouse", "currency")
    rbac_module = "procurement.rfq"

    def perform_destroy(self, instance):
        if instance.status not in (
            VendorRFQ.Status.DRAFT,
            VendorRFQ.Status.CANCELLED,
        ):
            raise SerValidationError("Only draft or cancelled RFQs can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="send")
    def send_rfq(self, request, pk=None):
        rfq = self.get_object()
        if rfq.status != VendorRFQ.Status.DRAFT:
            return Response({"detail": "Only draft RFQs can be sent."}, status=400)
        rfq.status = VendorRFQ.Status.SENT
        rfq.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(rfq).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        rfq = self.get_object()
        if rfq.status == VendorRFQ.Status.AWARDED:
            return Response({"detail": "Cannot cancel an awarded RFQ."}, status=400)
        rfq.status = VendorRFQ.Status.CANCELLED
        rfq.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(rfq).data)

    @action(detail=True, methods=["post"], url_path="award")
    def award(self, request, pk=None):
        rfq = self.get_object()
        quote_id = request.data.get("quote_id") or request.data.get("quote")
        if not quote_id:
            return Response({"detail": "quote_id is required."}, status=400)
        try:
            po = award_rfq(rfq, int(quote_id), user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        rfq.refresh_from_db()
        return Response(
            {
                "rfq": self.get_serializer(rfq).data,
                "purchase_order_id": po.id,
                "po_no": po.po_no,
                "href": f"/procurement/orders/{po.id}",
            }
        )


class VendorRFQQuoteViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = VendorRFQQuote.objects.select_related("rfq", "vendor").prefetch_related(
        "lines__item"
    )
    serializer_class = VendorRFQQuoteSerializer
    search_fields = ("vendor__name", "notes", "rfq__rfq_no")
    filterset_fields = ("rfq", "vendor", "is_winning")
    rbac_module = "procurement.rfq"


class SalesReturnViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SalesReturn.objects.select_related(
        "customer", "sales_order", "warehouse", "ar_credit_invoice"
    ).prefetch_related("lines__item")
    serializer_class = SalesReturnSerializer
    search_fields = ("rma_no", "customer__name", "notes", "sales_order__order_no")
    filterset_fields = ("status", "customer", "sales_order", "warehouse")
    rbac_module = "sales.returns"

    def perform_destroy(self, instance):
        if instance.status != SalesReturn.Status.DRAFT:
            raise SerValidationError("Only draft returns can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="post")
    def post_return(self, request, pk=None):
        doc = self.get_object()
        try:
            post_sales_return(doc, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        doc.refresh_from_db()
        return Response(self.get_serializer(doc).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        doc = self.get_object()
        if doc.status == SalesReturn.Status.POSTED:
            return Response({"detail": "Cannot cancel a posted return."}, status=400)
        doc.status = SalesReturn.Status.CANCELLED
        doc.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(doc).data)


class PurchaseReturnViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PurchaseReturn.objects.select_related(
        "vendor", "purchase_order", "warehouse", "ap_credit_invoice"
    ).prefetch_related("lines__item")
    serializer_class = PurchaseReturnSerializer
    search_fields = ("pret_no", "vendor__name", "notes", "purchase_order__po_no")
    filterset_fields = ("status", "vendor", "purchase_order", "warehouse")
    rbac_module = "procurement.returns"

    def perform_destroy(self, instance):
        if instance.status != PurchaseReturn.Status.DRAFT:
            raise SerValidationError("Only draft returns can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="post")
    def post_return(self, request, pk=None):
        doc = self.get_object()
        try:
            post_purchase_return(doc, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        doc.refresh_from_db()
        return Response(self.get_serializer(doc).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        doc = self.get_object()
        if doc.status == PurchaseReturn.Status.POSTED:
            return Response({"detail": "Cannot cancel a posted return."}, status=400)
        doc.status = PurchaseReturn.Status.CANCELLED
        doc.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(doc).data)


class PriceListViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PriceList.objects.select_related("customer").prefetch_related(
        "items__item"
    )
    serializer_class = PriceListSerializer
    search_fields = ("code", "name", "customer__name", "notes")
    filterset_fields = ("is_active", "customer", "currency")
    rbac_module = "sales.pricing"


class StocktakeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Stocktake.objects.select_related("warehouse").prefetch_related(
        "lines__item"
    )
    serializer_class = StocktakeSerializer
    search_fields = ("st_no", "notes", "warehouse__code", "warehouse__name")
    filterset_fields = ("status", "warehouse")
    rbac_module = "inventory.stocktake"

    def perform_destroy(self, instance):
        if instance.status != Stocktake.Status.DRAFT:
            raise SerValidationError("Only draft stocktakes can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="post")
    def post_count(self, request, pk=None):
        st = self.get_object()
        try:
            post_stocktake(st, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        st.refresh_from_db()
        return Response(self.get_serializer(st).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        st = self.get_object()
        if st.status == Stocktake.Status.POSTED:
            return Response({"detail": "Cannot cancel a posted stocktake."}, status=400)
        st.status = Stocktake.Status.CANCELLED
        st.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(st).data)


class LandedCostViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LandedCost.objects.select_related("goods_receipt", "goods_receipt__vendor")
    serializer_class = LandedCostSerializer
    search_fields = ("notes", "goods_receipt__grn_no")
    filterset_fields = ("status", "goods_receipt")
    rbac_module = "procurement.landed_cost"

    def perform_destroy(self, instance):
        if instance.status != LandedCost.Status.DRAFT:
            raise SerValidationError("Only draft landed costs can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="post")
    def post_allocation(self, request, pk=None):
        lc = self.get_object()
        try:
            post_landed_cost(lc, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        lc.refresh_from_db()
        return Response(self.get_serializer(lc).data)


class LotBatchViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LotBatch.objects.select_related("item", "warehouse")
    serializer_class = LotBatchSerializer
    search_fields = ("batch_no", "item__sku", "item__name")
    filterset_fields = ("item", "warehouse")
    rbac_module = "inventory.batches"


class ItemLotViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ItemLot.objects.select_related("item")
    serializer_class = ItemLotSerializer
    search_fields = ("lot_no", "item__sku", "item__name")
    filterset_fields = ("item",)
    rbac_module = "inventory.lots"


class SerialNumberViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SerialNumber.objects.select_related("item", "warehouse")
    serializer_class = SerialNumberSerializer
    search_fields = ("serial_no", "item__sku", "item__name")
    filterset_fields = ("item", "status", "warehouse")
    rbac_module = "inventory.serials"


class CustomerContractViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = CustomerContract.objects.select_related("customer")
    serializer_class = CustomerContractSerializer
    search_fields = ("name", "customer__name", "customer__code", "notes")
    filterset_fields = ("status", "billing_frequency", "customer")
    rbac_module = "sales.contracts"

    @action(detail=True, methods=["post"], url_path="generate-invoice")
    def generate_invoice(self, request, pk=None):
        contract = self.get_object()
        try:
            inv = generate_contract_invoice(contract, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        contract.refresh_from_db()
        return Response(
            {
                "invoice_id": inv.id,
                "invoice_no": inv.invoice_no,
                "contract": self.get_serializer(contract).data,
            }
        )
