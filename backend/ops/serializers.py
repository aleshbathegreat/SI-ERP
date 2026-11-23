from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ops.models import (
    Customer,
    GoodsReceipt,
    GoodsReceiptLine,
    Item,
    ItemLot,
    UnitOfMeasure,
    ensure_default_units,
    LotBatch,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
    SalesQuotation,
    SalesQuotationLine,
    SerialNumber,
    StockLevel,
    StockMovement,
    Warehouse,
)
from ops.traceability import line_trace_map, post_tracked_movements

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = RO

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "code", org, kind="customer", model=Customer)
        return super().create(validated_data)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = RO

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "code", org, kind="warehouse", model=Warehouse)
            if not Warehouse.objects.filter(
                organization=org, is_deleted=False
            ).exists():
                validated_data["is_default"] = True
        return super().create(validated_data)


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = "__all__"
        read_only_fields = RO

    def validate_code(self, value):
        code = str(value or "").strip()
        if not code or len(code) > 32:
            raise serializers.ValidationError("Enter a short unit code such as kg or hr.")
        return code

    def validate_name(self, value):
        name = str(value or "").strip()
        if not name:
            raise serializers.ValidationError("Enter the unit name.")
        return name

    def validate(self, attrs):
        attrs = super().validate(attrs)
        code = attrs.get("code", getattr(self.instance, "code", ""))
        request = self.context.get("request")
        from core.access import user_organization

        org = user_organization(request.user) if request else None
        if org and code:
            clash = UnitOfMeasure.all_objects.filter(
                organization=org, code=code, is_deleted=False
            )
            if self.instance is not None and self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"code": f"Code {code} is already used. Choose a different code."}
                )
        return attrs


class ItemSerializer(serializers.ModelSerializer):
    default_warehouse_name = serializers.CharField(
        source="default_warehouse.name", read_only=True, allow_null=True
    )
    stock_by_warehouse = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = RO + ("qty_on_hand",)

    def get_stock_by_warehouse(self, obj):
        levels = getattr(obj, "_prefetched_levels", None)
        qs = levels if levels is not None else obj.stock_levels.select_related("warehouse")
        return [
            {
                "warehouse_id": lv.warehouse_id,
                "warehouse_code": lv.warehouse.code,
                "warehouse_name": lv.warehouse.name,
                "qty": str(lv.qty),
            }
            for lv in qs
            if not lv.is_deleted
        ]

    def validate_default_warehouse(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Warehouse not in this organization.")
        return value

    def validate_unit(self, value):
        code = str(value or "ea").strip()
        if not code:
            raise serializers.ValidationError("Choose a unit.")
        return code[:32]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "unit" not in attrs and self.instance is not None:
            return attrs
        code = attrs.get("unit") or "ea"
        attrs["unit"] = code
        request = self.context.get("request")
        from core.access import user_organization

        org = user_organization(request.user) if request else None
        if org:
            ensure_default_units(org)
            active = UnitOfMeasure.objects.filter(
                organization=org, code=code, is_active=True
            ).exists()
            unchanged = self.instance is not None and str(self.instance.unit or "").strip() == code
            if not active and not unchanged:
                raise serializers.ValidationError(
                    {
                        "unit": (
                            f"{code} is not in the unit list. "
                            "Add it under Units of measure, then choose it here."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "sku", org, kind="item", model=Item)
            if not validated_data.get("default_warehouse"):
                wh = (
                    Warehouse.objects.filter(
                        organization=org, is_default=True, is_deleted=False
                    ).first()
                    or Warehouse.objects.filter(
                        organization=org, is_deleted=False
                    ).first()
                )
                if wh:
                    validated_data["default_warehouse"] = wh
        return super().create(validated_data)


class StockLevelSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = StockLevel
        fields = "__all__"
        read_only_fields = RO


class StockMovementSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    to_warehouse_name = serializers.CharField(
        source="to_warehouse.name", read_only=True, allow_null=True
    )
    lot_batch_no = serializers.CharField(
        source="lot.batch_no", read_only=True, default="", allow_null=True
    )
    serial_number = serializers.CharField(
        source="serial.serial_no", read_only=True, default="", allow_null=True
    )
    serial_no = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Serial number (required for track_serial items)",
    )
    item_track_batch = serializers.BooleanField(
        source="item.track_batch", read_only=True
    )
    item_track_serial = serializers.BooleanField(
        source="item.track_serial", read_only=True
    )

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = RO

    def _org_check(self, value, label):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError(f"{label} not in this organization.")
        return value

    def validate_item(self, value):
        return self._org_check(value, "Item")

    def validate_warehouse(self, value):
        return self._org_check(value, "Warehouse")

    def validate_to_warehouse(self, value):
        return self._org_check(value, "Destination warehouse")

    def validate_lot(self, value):
        return self._org_check(value, "Lot")

    def validate_serial(self, value):
        return self._org_check(value, "Serial")

    def validate_qty(self, value):
        if value is None or Decimal(str(value)) == 0:
            raise serializers.ValidationError("Quantity cannot be zero.")
        return value

    def validate(self, attrs):
        reason = attrs.get("reason") or getattr(self.instance, "reason", None)
        warehouse = attrs.get("warehouse", getattr(self.instance, "warehouse", None))
        to_wh = attrs.get("to_warehouse", getattr(self.instance, "to_warehouse", None))
        qty = attrs.get("qty", getattr(self.instance, "qty", None))
        item = attrs.get("item", getattr(self.instance, "item", None))

        if reason == StockMovement.Reason.TRANSFER:
            if not warehouse or not to_wh:
                raise serializers.ValidationError(
                    "Warehouse transfer requires source and destination warehouse."
                )
            if warehouse.pk == to_wh.pk:
                raise serializers.ValidationError(
                    "Source and destination warehouse must be different."
                )
            if qty is not None and Decimal(str(qty)) < 0:
                attrs["qty"] = abs(Decimal(str(qty)))
        elif item and getattr(item, "item_type", None) != Item.ItemType.SERVICE:
            if not warehouse:
                if item.default_warehouse_id:
                    attrs["warehouse"] = item.default_warehouse
                else:
                    raise serializers.ValidationError(
                        {"warehouse": "Warehouse is required for stockable items."}
                    )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from ops.traceability import prepare_direct_movement

        serial_no = validated_data.pop("serial_no", "")
        try:
            validated_data = prepare_direct_movement(validated_data, serial_no=serial_no)
            mov = super().create(validated_data)
            mov.apply_to_item()
            return mov
        except ValueError as e:
            raise serializers.ValidationError(str(e)) from e

    def update(self, instance, validated_data):
        raise serializers.ValidationError(
            "Stock movements are append-only. Create a reversing movement instead."
        )


class SalesOrderLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()
    item_track_batch = serializers.BooleanField(source="item.track_batch", read_only=True)
    item_track_serial = serializers.BooleanField(source="item.track_serial", read_only=True)

    class Meta:
        model = SalesOrderLine
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "item_track_batch",
            "item_track_serial",
            "description",
            "qty",
            "unit_price",
            "qty_delivered",
            "warehouse",
            "line_total",
        )
        read_only_fields = ("qty_delivered",)

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class SalesOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    subtotal = serializers.SerializerMethodField()
    lines = SalesOrderLineSerializer(many=True, required=False)
    fulfillment = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = "__all__"
        read_only_fields = RO + ("amount", "status", "submitted_by")

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_fulfillment(self, obj):
        ordered = Decimal("0")
        done = Decimal("0")
        for ln in obj.lines.all():
            ordered += ln.qty or Decimal("0")
            done += ln.qty_delivered or Decimal("0")
        pct = float((done / ordered * 100) if ordered else 0)
        return {
            "qty_ordered": str(ordered),
            "qty_delivered": str(done),
            "pct": round(pct, 1),
            "open": str(max(ordered - done, Decimal("0"))),
        }

    def validate_customer(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Customer not in this organization.")
        return value

    def validate_warehouse(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Warehouse not in this organization.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one sales order line."}
                )
        return attrs

    def _sync_lines(self, order, lines_data):
        order.lines.all().delete()
        for line in lines_data:
            SalesOrderLine.objects.create(sales_order=order, **line)
        order.recompute_amount()

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        if not lines_data:
            raise serializers.ValidationError(
                {"lines": "Add at least one sales order line."}
            )
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        customer = validated_data.get("customer")
        if customer:
            if not validated_data.get("payment_terms_days"):
                validated_data["payment_terms_days"] = customer.payment_terms_days or 30
            if not validated_data.get("currency"):
                validated_data["currency"] = customer.currency or "PKR"
            if not validated_data.get("shipping_address") and customer.address:
                validated_data["shipping_address"] = customer.address
        if org:
            ensure_doc_no(validated_data, "order_no", org, kind="so", model=SalesOrder)
        validated_data["status"] = SalesOrder.Status.DRAFT
        order = SalesOrder.objects.create(**validated_data)
        self._sync_lines(order, lines_data)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status not in (
            SalesOrder.Status.DRAFT,
            SalesOrder.Status.CANCELLED,
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot edit a {instance.status} sales order. "
                        "Use Confirm / Deliver / Cancel actions."
                    )
                }
            )
        lines_data = validated_data.pop("lines", None)
        if lines_data is not None and instance.lines.filter(qty_delivered__gt=0).exists():
            raise serializers.ValidationError(
                {"lines": "Cannot edit lines after delivery has started."}
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one sales order line."}
                )
            self._sync_lines(instance, lines_data)
        else:
            instance.recompute_amount()
        return instance


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()
    item_track_batch = serializers.BooleanField(source="item.track_batch", read_only=True)
    item_track_serial = serializers.BooleanField(source="item.track_serial", read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "item_track_batch",
            "item_track_serial",
            "description",
            "qty",
            "unit_price",
            "qty_received",
            "warehouse",
            "line_total",
        )
        read_only_fields = ("qty_received",)

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class PurchaseOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    subtotal = serializers.SerializerMethodField()
    lines = PurchaseOrderLineSerializer(many=True, required=False)
    fulfillment = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = RO + ("amount", "status", "submitted_by", "approved_by")

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_fulfillment(self, obj):
        ordered = Decimal("0")
        done = Decimal("0")
        for ln in obj.lines.all():
            ordered += ln.qty or Decimal("0")
            done += ln.qty_received or Decimal("0")
        pct = float((done / ordered * 100) if ordered else 0)
        return {
            "qty_ordered": str(ordered),
            "qty_received": str(done),
            "pct": round(pct, 1),
            "open": str(max(ordered - done, Decimal("0"))),
        }

    def validate_vendor(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Vendor not in this organization.")
        return value

    def validate_warehouse(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Warehouse not in this organization.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one purchase order line."}
                )
        return attrs

    def _sync_lines(self, order, lines_data):
        order.lines.all().delete()
        for line in lines_data:
            PurchaseOrderLine.objects.create(purchase_order=order, **line)
        order.recompute_amount()

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        if not lines_data:
            raise serializers.ValidationError(
                {"lines": "Add at least one purchase order line."}
            )
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        vendor = validated_data.get("vendor")
        if vendor:
            if not validated_data.get("payment_terms_days"):
                validated_data["payment_terms_days"] = (
                    getattr(vendor, "payment_terms_days", None) or 30
                )
            if not validated_data.get("currency"):
                validated_data["currency"] = getattr(vendor, "currency", None) or "PKR"
        if org:
            ensure_doc_no(validated_data, "po_no", org, kind="po", model=PurchaseOrder)
        validated_data["status"] = PurchaseOrder.Status.DRAFT
        order = PurchaseOrder.objects.create(**validated_data)
        self._sync_lines(order, lines_data)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status not in (
            PurchaseOrder.Status.DRAFT,
            PurchaseOrder.Status.CANCELLED,
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot edit a {instance.status} purchase order. "
                        "Use Submit / Approve / Receive / Cancel actions."
                    )
                }
            )
        lines_data = validated_data.pop("lines", None)
        if lines_data is not None and instance.lines.filter(qty_received__gt=0).exists():
            raise serializers.ValidationError(
                {"lines": "Cannot edit lines after goods receipt has started."}
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one purchase order line."}
                )
            self._sync_lines(instance, lines_data)
        else:
            instance.recompute_amount()
        return instance


def _line_qty_map(raw_lines):
    """Parse optional [{id|line_id, qty}] for partial receive/deliver."""
    if not raw_lines:
        return None
    out = {}
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        lid = row.get("id") or row.get("line_id")
        if lid is None:
            continue
        qty = row.get("qty")
        if qty is None:
            continue
        out[int(lid)] = Decimal(str(qty))
    return out or None


def receive_purchase_order(po: PurchaseOrder, warehouse_id=None, user=None, lines=None):
    """Post PO qty into stock and create a formal GoodsReceipt (GRN) document."""
    from core.doc_numbers import ensure_doc_no

    if po.status in (PurchaseOrder.Status.CANCELLED, PurchaseOrder.Status.RECEIVED):
        raise serializers.ValidationError(
            f"Cannot receive a purchase order in status '{po.status}'."
        )
    if po.status != PurchaseOrder.Status.APPROVED:
        raise serializers.ValidationError(
            "Approve the purchase order before receiving goods."
        )

    qty_map = _line_qty_map(lines)
    trace_map = line_trace_map(lines)
    default_wh = None
    if warehouse_id:
        default_wh = Warehouse.objects.filter(
            pk=warehouse_id, organization_id=po.organization_id, is_deleted=False
        ).first()
        if not default_wh:
            raise serializers.ValidationError({"warehouse": "Invalid warehouse."})
    elif po.warehouse_id:
        default_wh = po.warehouse

    moved = 0
    grn = None
    with transaction.atomic():
        grn_data = {"grn_no": ""}
        ensure_doc_no(grn_data, "grn_no", po.organization, kind="grn", model=GoodsReceipt)
        grn = GoodsReceipt.objects.create(
            organization_id=po.organization_id,
            grn_no=grn_data["grn_no"],
            purchase_order=po,
            vendor_id=po.vendor_id,
            warehouse=default_wh,
            receipt_date=timezone.localdate(),
            status=GoodsReceipt.Status.POSTED,
            notes=f"Receipt against PO {po.po_no}",
            received_by=user,
            created_by=user,
            updated_by=user,
        )

        for line in po.lines.select_related("item", "warehouse").select_for_update():
            remaining = (line.qty or Decimal("0")) - (line.qty_received or Decimal("0"))
            if remaining <= 0:
                continue
            take = remaining
            if qty_map is not None:
                if line.id not in qty_map:
                    continue
                take = qty_map[line.id]
                if take <= 0:
                    continue
                if take > remaining:
                    raise serializers.ValidationError(
                        {
                            "lines": (
                                f"Receive qty {take} exceeds open {remaining} "
                                f"for {line.item.sku}."
                            )
                        }
                    )

            wh = line.warehouse or default_wh or line.item.default_warehouse
            mov = None
            if line.item.item_type == Item.ItemType.SERVICE:
                line.qty_received = (line.qty_received or Decimal("0")) + take
                line.save(update_fields=["qty_received"])
            else:
                if not wh:
                    raise serializers.ValidationError(
                        {
                            "warehouse": (
                                f"No warehouse for line item {line.item.sku}. "
                                "Set PO warehouse or line warehouse."
                            )
                        }
                    )
                movs = post_tracked_movements(
                    item=line.item,
                    qty=take,
                    outbound=False,
                    trace=trace_map.get(line.id),
                    organization_id=po.organization_id,
                    warehouse=wh,
                    purchase_order=po,
                    movement_date=timezone.localdate(),
                    reason=StockMovement.Reason.RECEIPT,
                    reference=grn.grn_no,
                    notes=f"GRN {grn.grn_no} / PO {po.po_no}",
                    created_by=user,
                    updated_by=user,
                )
                mov = movs[0]
                if take > 0 and (line.unit_price or 0) > 0:
                    item = Item.objects.select_for_update().get(pk=line.item_id)
                    if item.item_type != Item.ItemType.SERVICE:
                        on_hand = item.qty_on_hand or Decimal("0")
                        prev = on_hand - take
                        if prev < 0:
                            prev = Decimal("0")
                        old_cost = item.unit_cost or Decimal("0")
                        new_cost = (
                            (old_cost * prev + (line.unit_price or 0) * take) / on_hand
                            if on_hand > 0
                            else (line.unit_price or 0)
                        )
                        item.unit_cost = Decimal(new_cost).quantize(Decimal("0.01"))
                        item.save(update_fields=["unit_cost", "updated_at"])
                line.qty_received = (line.qty_received or Decimal("0")) + take
                line.save(update_fields=["qty_received"])

            GoodsReceiptLine.objects.create(
                goods_receipt=grn,
                purchase_order_line=line,
                item=line.item,
                description=line.description or "",
                qty=take,
                unit_price=line.unit_price or Decimal("0"),
                warehouse=wh,
                stock_movement=mov,
            )
            moved += 1

        if moved == 0:
            raise serializers.ValidationError("Nothing left to receive on this PO.")

        fully = all(
            (ln.qty_received or Decimal("0")) >= (ln.qty or Decimal("0"))
            for ln in po.lines.all()
        )
        if fully:
            po.status = PurchaseOrder.Status.RECEIVED
            po.save(update_fields=["status", "updated_at"])
        from ops.qc_hold import hold_receipt

        hold_receipt(grn)
    po._last_grn = grn
    return po


def deliver_sales_order(
    so: SalesOrder,
    warehouse_id=None,
    user=None,
    lines=None,
    *,
    deduct_bins=True,
    force_warehouse=False,
):
    """Issue SO qty from stock and create a formal DeliveryNote (DN).

    deduct_bins: also draw the issued qty out of bin stock (FIFO). Pick confirm
    passes False because it already deducted the bins the picker chose.
    force_warehouse: issue from warehouse_id even when a line names another.
    """
    from core.doc_numbers import ensure_doc_no
    from ops.models import DeliveryNote, DeliveryNoteLine

    if so.status in (SalesOrder.Status.CANCELLED, SalesOrder.Status.DELIVERED):
        raise serializers.ValidationError(
            f"Cannot deliver a sales order in status '{so.status}'."
        )
    if so.status not in (SalesOrder.Status.CONFIRMED, SalesOrder.Status.INVOICED):
        raise serializers.ValidationError(
            "Confirm the sales order before delivering."
        )

    qty_map = _line_qty_map(lines)
    trace_map = line_trace_map(lines)
    default_wh = None
    if warehouse_id:
        default_wh = Warehouse.objects.filter(
            pk=warehouse_id, organization_id=so.organization_id, is_deleted=False
        ).first()
        if not default_wh:
            raise serializers.ValidationError({"warehouse": "Invalid warehouse."})
    elif so.warehouse_id:
        default_wh = so.warehouse

    moved = 0
    dn = None
    with transaction.atomic():
        dn_data = {"dn_no": ""}
        ensure_doc_no(dn_data, "dn_no", so.organization, kind="dn", model=DeliveryNote)
        dn = DeliveryNote.objects.create(
            organization_id=so.organization_id,
            dn_no=dn_data["dn_no"],
            sales_order=so,
            customer_id=so.customer_id,
            warehouse=default_wh,
            delivery_date=timezone.localdate(),
            status=DeliveryNote.Status.POSTED,
            notes=f"Delivery against SO {so.order_no}",
            delivered_by=user,
            created_by=user,
            updated_by=user,
        )

        for line in so.lines.select_related("item", "warehouse").select_for_update():
            remaining = (line.qty or Decimal("0")) - (line.qty_delivered or Decimal("0"))
            if remaining <= 0:
                continue
            take = remaining
            if qty_map is not None:
                if line.id not in qty_map:
                    continue
                take = qty_map[line.id]
                if take <= 0:
                    continue
                if take > remaining:
                    raise serializers.ValidationError(
                        {
                            "lines": (
                                f"Deliver qty {take} exceeds open {remaining} "
                                f"for {line.item.sku}."
                            )
                        }
                    )
            mov = None
            wh = line.warehouse or default_wh or line.item.default_warehouse
            if force_warehouse and default_wh is not None:
                wh = default_wh
            if line.item.item_type == Item.ItemType.SERVICE:
                line.qty_delivered = (line.qty_delivered or Decimal("0")) + take
                line.save(update_fields=["qty_delivered"])
            else:
                if not wh:
                    raise serializers.ValidationError(
                        {
                            "warehouse": (
                                f"No warehouse for line item {line.item.sku}. "
                                "Set SO warehouse or line warehouse."
                            )
                        }
                    )

                level = (
                    StockLevel.objects.select_for_update()
                    .filter(
                        organization_id=so.organization_id,
                        warehouse_id=wh.id,
                        item_id=line.item_id,
                        is_deleted=False,
                    )
                    .first()
                )
                from ops.qc_hold import available_qty

                on_hand = level.qty if level else Decimal("0")
                held = level.qty_qc_hold if level else Decimal("0")
                available = available_qty(level)
                if available < take:
                    hold_note = (
                        f" ({held} on QC hold)" if held and held > 0 else ""
                    )
                    raise serializers.ValidationError(
                        {
                            "lines": (
                                f"Insufficient stock for {line.item.sku} in {wh.code}: "
                                f"need {take}, available {available}{hold_note}."
                            )
                        }
                    )

                movs = post_tracked_movements(
                    item=line.item,
                    qty=take,
                    outbound=True,
                    trace=trace_map.get(line.id),
                    organization_id=so.organization_id,
                    warehouse=wh,
                    sales_order=so,
                    movement_date=timezone.localdate(),
                    reason=StockMovement.Reason.ISSUE,
                    reference=dn.dn_no,
                    notes=f"DN {dn.dn_no} / SO {so.order_no}",
                    created_by=user,
                    updated_by=user,
                )
                mov = movs[0]
                if deduct_bins:
                    from ops.wms import consume_bins

                    consume_bins(
                        org_id=so.organization_id,
                        warehouse_id=wh.id,
                        item_id=line.item_id,
                        qty=take,
                    )
                line.qty_delivered = (line.qty_delivered or Decimal("0")) + take
                line.save(update_fields=["qty_delivered"])

            DeliveryNoteLine.objects.create(
                delivery_note=dn,
                sales_order_line=line,
                item=line.item,
                description=line.description or "",
                qty=take,
                unit_price=line.unit_price or Decimal("0"),
                warehouse=wh,
                stock_movement=mov,
            )
            moved += 1

        if moved == 0:
            raise serializers.ValidationError("Nothing left to deliver on this SO.")

        fully = all(
            (ln.qty_delivered or Decimal("0")) >= (ln.qty or Decimal("0"))
            for ln in so.lines.all()
        )
        if fully:
            so.status = SalesOrder.Status.DELIVERED
            so.save(update_fields=["status", "updated_at"])
    so._last_dn = dn
    return so


class LotBatchSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default="", allow_null=True
    )

    class Meta:
        model = LotBatch
        fields = "__all__"
        read_only_fields = RO


class ItemLotSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    item_name = serializers.CharField(source="item.name", read_only=True, default="")

    class Meta:
        model = ItemLot
        fields = "__all__"
        read_only_fields = RO


class SerialNumberSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default="", allow_null=True
    )

    class Meta:
        model = SerialNumber
        fields = "__all__"
        read_only_fields = RO
