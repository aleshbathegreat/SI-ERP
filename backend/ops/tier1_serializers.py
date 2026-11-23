"""Tier-1 ops serializers: RFQ, returns, price lists, stocktake, landed cost."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ops.models import (
    Item,
    LandedCost,
    PriceList,
    PriceListItem,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReturn,
    PurchaseReturnLine,
    SalesReturn,
    SalesReturnLine,
    StockLevel,
    StockMovement,
    Stocktake,
    StocktakeLine,
    VendorRFQ,
    VendorRFQLine,
    VendorRFQQuote,
    VendorRFQQuoteLine,
    Warehouse,
)

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


# ── Vendor RFQ ──────────────────────────────────────────────────────────────


class VendorRFQLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = VendorRFQLine
        fields = ("id", "item", "item_sku", "item_name", "description", "qty")


class VendorRFQQuoteLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = VendorRFQQuoteLine
        fields = (
            "id",
            "rfq_line",
            "item",
            "item_sku",
            "item_name",
            "description",
            "qty",
            "unit_price",
            "line_total",
        )

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class VendorRFQQuoteSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    lines = VendorRFQQuoteLineSerializer(many=True, required=False)
    total = serializers.SerializerMethodField()

    class Meta:
        model = VendorRFQQuote
        fields = (
            "id",
            "rfq",
            "vendor",
            "vendor_name",
            "quote_date",
            "notes",
            "is_winning",
            "lines",
            "total",
        )
        read_only_fields = ("is_winning",)

    def get_total(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.line_total
        return str(total.quantize(Decimal("0.01")))

    def _sync_lines(self, quote, lines_data):
        quote.lines.all().delete()
        for line in lines_data:
            VendorRFQQuoteLine.objects.create(quote=quote, **line)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization

        lines_data = validated_data.pop("lines", [])
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            validated_data["organization"] = org
        rfq = validated_data.get("rfq")
        if rfq and rfq.status not in (
            VendorRFQ.Status.DRAFT,
            VendorRFQ.Status.SENT,
        ):
            raise serializers.ValidationError(
                {"rfq": f"Cannot add quotes to a {rfq.status} RFQ."}
            )
        quote = VendorRFQQuote.objects.create(**validated_data)
        self._sync_lines(quote, lines_data)
        return quote

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.rfq.status == VendorRFQ.Status.AWARDED:
            raise serializers.ValidationError(
                {"detail": "Cannot edit quotes on an awarded RFQ."}
            )
        lines_data = validated_data.pop("lines", None)
        validated_data.pop("is_winning", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            self._sync_lines(instance, lines_data)
        return instance


class VendorRFQSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    awarded_vendor_name = serializers.CharField(
        source="awarded_vendor.name", read_only=True, allow_null=True
    )
    po_no = serializers.CharField(
        source="purchase_order.po_no", read_only=True, allow_null=True
    )
    lines = VendorRFQLineSerializer(many=True, required=False)
    quotes = VendorRFQQuoteSerializer(many=True, read_only=True)

    class Meta:
        model = VendorRFQ
        fields = "__all__"
        read_only_fields = RO + (
            "status",
            "awarded_vendor",
            "purchase_order",
        )

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one RFQ line."}
                )
        return attrs

    def _sync_lines(self, rfq, lines_data):
        rfq.lines.all().delete()
        for line in lines_data:
            VendorRFQLine.objects.create(rfq=rfq, **line)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "rfq_no", org, kind="rfq", model=VendorRFQ)
        validated_data["status"] = VendorRFQ.Status.DRAFT
        rfq = VendorRFQ.objects.create(**validated_data)
        self._sync_lines(rfq, lines_data)
        return rfq

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status not in (VendorRFQ.Status.DRAFT, VendorRFQ.Status.SENT):
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} RFQ."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one RFQ line."}
                )
            self._sync_lines(instance, lines_data)
        return instance


@transaction.atomic
def award_rfq(rfq: VendorRFQ, quote_id: int, user=None) -> PurchaseOrder:
    from core.doc_numbers import ensure_doc_no

    if rfq.status == VendorRFQ.Status.AWARDED and rfq.purchase_order_id:
        return rfq.purchase_order
    if rfq.status == VendorRFQ.Status.CANCELLED:
        raise serializers.ValidationError("Cannot award a cancelled RFQ.")
    quote = (
        VendorRFQQuote.objects.filter(pk=quote_id, rfq=rfq, is_deleted=False)
        .prefetch_related("lines")
        .first()
    )
    if not quote:
        raise serializers.ValidationError({"quote_id": "Quote not found for this RFQ."})
    if not quote.lines.exists():
        raise serializers.ValidationError("Winning quote has no lines.")

    data = {"po_no": ""}
    ensure_doc_no(data, "po_no", rfq.organization, kind="po", model=PurchaseOrder)
    po = PurchaseOrder.objects.create(
        organization_id=rfq.organization_id,
        po_no=data["po_no"],
        vendor_id=quote.vendor_id,
        warehouse_id=rfq.warehouse_id,
        order_date=timezone.localdate(),
        currency=rfq.currency or "PKR",
        status=PurchaseOrder.Status.DRAFT,
        notes=f"Awarded from RFQ {rfq.rfq_no}"
        + (f"\n{rfq.notes}" if rfq.notes else ""),
        created_by=user,
        updated_by=user,
    )
    for ln in quote.lines.select_related("item"):
        PurchaseOrderLine.objects.create(
            purchase_order=po,
            item=ln.item,
            description=ln.description or "",
            qty=ln.qty,
            unit_price=ln.unit_price,
            warehouse_id=rfq.warehouse_id,
        )
    po.recompute_amount()
    rfq.quotes.update(is_winning=False)
    quote.is_winning = True
    quote.save(update_fields=["is_winning", "updated_at"])
    rfq.status = VendorRFQ.Status.AWARDED
    rfq.awarded_vendor_id = quote.vendor_id
    rfq.purchase_order = po
    rfq.save(
        update_fields=["status", "awarded_vendor", "purchase_order", "updated_at"]
    )
    return po


# ── Sales return / RMA ──────────────────────────────────────────────────────


class SalesReturnLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = SalesReturnLine
        fields = (
            "id",
            "sales_order_line",
            "item",
            "item_sku",
            "item_name",
            "description",
            "qty",
            "unit_price",
            "warehouse",
            "line_total",
        )

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class SalesReturnSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    order_no = serializers.CharField(
        source="sales_order.order_no", read_only=True, allow_null=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    lines = SalesReturnLineSerializer(many=True, required=False)
    total = serializers.SerializerMethodField()

    class Meta:
        model = SalesReturn
        fields = "__all__"
        read_only_fields = RO + ("status",)

    def get_total(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.line_total
        return str(total.quantize(Decimal("0.01")))

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one return line."}
                )
        return attrs

    def _sync_lines(self, doc, lines_data):
        doc.lines.all().delete()
        for line in lines_data:
            SalesReturnLine.objects.create(sales_return=doc, **line)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "rma_no", org, kind="rma", model=SalesReturn)
        validated_data["status"] = SalesReturn.Status.DRAFT
        doc = SalesReturn.objects.create(**validated_data)
        self._sync_lines(doc, lines_data)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status != SalesReturn.Status.DRAFT:
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} return."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one return line."}
                )
            self._sync_lines(instance, lines_data)
        return instance


@transaction.atomic
def post_sales_return(doc: SalesReturn, user=None) -> SalesReturn:
    if doc.status == SalesReturn.Status.POSTED:
        return doc
    if doc.status != SalesReturn.Status.DRAFT:
        raise serializers.ValidationError(
            f"Cannot post a return in status '{doc.status}'."
        )
    if not doc.lines.exists():
        raise serializers.ValidationError("Return has no lines.")
    default_wh = doc.warehouse
    for line in doc.lines.select_related("item", "warehouse"):
        if line.item.item_type == Item.ItemType.SERVICE:
            continue
        wh = line.warehouse or default_wh or line.item.default_warehouse
        if not wh:
            raise serializers.ValidationError(
                {"warehouse": f"No warehouse for {line.item.sku}."}
            )
        qty = line.qty or Decimal("0")
        if qty <= 0:
            continue
        mov = StockMovement(
            organization_id=doc.organization_id,
            item=line.item,
            warehouse=wh,
            sales_order_id=doc.sales_order_id,
            movement_date=doc.return_date,
            qty=qty,
            reason=StockMovement.Reason.RETURN,
            reference=doc.rma_no,
            notes=f"RMA {doc.rma_no}",
            created_by=user,
            updated_by=user,
        )
        mov.save()
        mov.apply_to_item()
        line.stock_movement = mov
        line.warehouse = wh
        line.save(update_fields=["stock_movement", "warehouse"])
    doc.status = SalesReturn.Status.POSTED
    doc.save(update_fields=["status", "updated_at"])
    return doc


# ── Purchase return ─────────────────────────────────────────────────────────


class PurchaseReturnLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReturnLine
        fields = (
            "id",
            "purchase_order_line",
            "item",
            "item_sku",
            "item_name",
            "description",
            "qty",
            "unit_price",
            "warehouse",
            "line_total",
        )

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class PurchaseReturnSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    po_no = serializers.CharField(
        source="purchase_order.po_no", read_only=True, allow_null=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    lines = PurchaseReturnLineSerializer(many=True, required=False)
    total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReturn
        fields = "__all__"
        read_only_fields = RO + ("status",)

    def get_total(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.line_total
        return str(total.quantize(Decimal("0.01")))

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one return line."}
                )
        return attrs

    def _sync_lines(self, doc, lines_data):
        doc.lines.all().delete()
        for line in lines_data:
            PurchaseReturnLine.objects.create(purchase_return=doc, **line)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(
                validated_data, "pret_no", org, kind="pret", model=PurchaseReturn
            )
        validated_data["status"] = PurchaseReturn.Status.DRAFT
        doc = PurchaseReturn.objects.create(**validated_data)
        self._sync_lines(doc, lines_data)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status != PurchaseReturn.Status.DRAFT:
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} return."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one return line."}
                )
            self._sync_lines(instance, lines_data)
        return instance


@transaction.atomic
def post_purchase_return(doc: PurchaseReturn, user=None) -> PurchaseReturn:
    if doc.status == PurchaseReturn.Status.POSTED:
        return doc
    if doc.status != PurchaseReturn.Status.DRAFT:
        raise serializers.ValidationError(
            f"Cannot post a return in status '{doc.status}'."
        )
    if not doc.lines.exists():
        raise serializers.ValidationError("Return has no lines.")
    default_wh = doc.warehouse
    for line in doc.lines.select_related("item", "warehouse"):
        if line.item.item_type == Item.ItemType.SERVICE:
            continue
        wh = line.warehouse or default_wh or line.item.default_warehouse
        if not wh:
            raise serializers.ValidationError(
                {"warehouse": f"No warehouse for {line.item.sku}."}
            )
        qty = line.qty or Decimal("0")
        if qty <= 0:
            continue
        mov = StockMovement(
            organization_id=doc.organization_id,
            item=line.item,
            warehouse=wh,
            purchase_order_id=doc.purchase_order_id,
            movement_date=doc.return_date,
            qty=-qty,
            reason=StockMovement.Reason.RETURN,
            reference=doc.pret_no,
            notes=f"Purchase return {doc.pret_no}",
            created_by=user,
            updated_by=user,
        )
        mov.save()
        mov.apply_to_item()
        line.stock_movement = mov
        line.warehouse = wh
        line.save(update_fields=["stock_movement", "warehouse"])
    doc.status = PurchaseReturn.Status.POSTED
    doc.save(update_fields=["status", "updated_at"])
    return doc


# ── Price list ──────────────────────────────────────────────────────────────


class PriceListItemSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = PriceListItem
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "unit_price",
            "valid_from",
            "valid_until",
        )


class PriceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, allow_null=True
    )
    items = PriceListItemSerializer(many=True, required=False)

    class Meta:
        model = PriceList
        fields = "__all__"
        read_only_fields = RO

    def _sync_items(self, pl, items_data):
        pl.items.all().delete()
        for row in items_data:
            PriceListItem.objects.create(price_list=pl, **row)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "code", org, kind="pl", model=PriceList)
        pl = PriceList.objects.create(**validated_data)
        self._sync_items(pl, items_data)
        return pl

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            self._sync_items(instance, items_data)
        return instance


# ── Stocktake ───────────────────────────────────────────────────────────────


class StocktakeLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    variance = serializers.SerializerMethodField()

    class Meta:
        model = StocktakeLine
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "system_qty",
            "counted_qty",
            "variance",
        )
        read_only_fields = ("system_qty",)

    def get_variance(self, obj):
        return str(obj.variance)


class StocktakeSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    lines = StocktakeLineSerializer(many=True, required=False)

    class Meta:
        model = Stocktake
        fields = "__all__"
        read_only_fields = RO + ("status",)

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one stocktake line."}
                )
        return attrs

    def _system_qty(self, warehouse_id, item_id):
        level = StockLevel.objects.filter(
            warehouse_id=warehouse_id, item_id=item_id, is_deleted=False
        ).first()
        return level.qty if level else Decimal("0")

    def _sync_lines(self, st, lines_data):
        st.lines.all().delete()
        for line in lines_data:
            item = line["item"]
            item_id = item.pk if hasattr(item, "pk") else item
            sys_qty = self._system_qty(st.warehouse_id, item_id)
            StocktakeLine.objects.create(
                stocktake=st,
                item_id=item_id,
                system_qty=sys_qty,
                counted_qty=line.get("counted_qty", Decimal("0")),
            )

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(validated_data, "st_no", org, kind="st", model=Stocktake)
        validated_data["status"] = Stocktake.Status.DRAFT
        st = Stocktake.objects.create(**validated_data)
        self._sync_lines(st, lines_data)
        return st

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status != Stocktake.Status.DRAFT:
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} stocktake."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one stocktake line."}
                )
            self._sync_lines(instance, lines_data)
        return instance


@transaction.atomic
def post_stocktake(st: Stocktake, user=None) -> Stocktake:
    if st.status == Stocktake.Status.POSTED:
        return st
    if st.status != Stocktake.Status.DRAFT:
        raise serializers.ValidationError(
            f"Cannot post a stocktake in status '{st.status}'."
        )
    for line in st.lines.select_related("item"):
        # refresh system qty at post time
        level = StockLevel.objects.filter(
            warehouse_id=st.warehouse_id, item_id=line.item_id, is_deleted=False
        ).first()
        sys_qty = level.qty if level else Decimal("0")
        line.system_qty = sys_qty
        variance = (line.counted_qty or Decimal("0")) - sys_qty
        if variance == 0:
            line.save(update_fields=["system_qty"])
            continue
        mov = StockMovement(
            organization_id=st.organization_id,
            item=line.item,
            warehouse=st.warehouse,
            movement_date=st.count_date,
            qty=variance,
            reason=StockMovement.Reason.ADJUSTMENT,
            reference=st.st_no,
            notes=f"Stocktake {st.st_no} variance",
            created_by=user,
            updated_by=user,
        )
        mov.save()
        mov.apply_to_item()
        line.stock_movement = mov
        line.save(update_fields=["system_qty", "stock_movement"])
    st.status = Stocktake.Status.POSTED
    st.save(update_fields=["status", "updated_at"])
    return st


# ── Landed cost ─────────────────────────────────────────────────────────────


class LandedCostSerializer(serializers.ModelSerializer):
    grn_no = serializers.CharField(source="goods_receipt.grn_no", read_only=True)
    total_charges = serializers.SerializerMethodField()

    class Meta:
        model = LandedCost
        fields = "__all__"
        read_only_fields = RO + ("status", "posted_at")

    def get_total_charges(self, obj):
        return str(obj.total_charges)

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization

        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            validated_data["organization"] = org
        validated_data["status"] = LandedCost.Status.DRAFT
        return LandedCost.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status != LandedCost.Status.DRAFT:
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} landed cost."}
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


@transaction.atomic
def post_landed_cost(lc: LandedCost, user=None) -> LandedCost:
    if lc.status == LandedCost.Status.POSTED:
        return lc
    if lc.status != LandedCost.Status.DRAFT:
        raise serializers.ValidationError(
            f"Cannot post landed cost in status '{lc.status}'."
        )
    charges = lc.total_charges
    if charges <= 0:
        raise serializers.ValidationError("Enter freight, duty, or other charges.")
    grn = lc.goods_receipt
    lines = list(grn.lines.select_related("item"))
    if not lines:
        raise serializers.ValidationError("GRN has no lines to allocate.")
    base_total = sum(
        (ln.qty or Decimal("0")) * (ln.unit_price or Decimal("0")) for ln in lines
    )
    if base_total <= 0:
        # equal split by qty
        qty_total = sum(ln.qty or Decimal("0") for ln in lines) or Decimal("1")
        for ln in lines:
            share = charges * ((ln.qty or Decimal("0")) / qty_total)
            qty = ln.qty or Decimal("1")
            add = (share / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
            ln.unit_price = (ln.unit_price or Decimal("0")) + add
            ln.save(update_fields=["unit_price"])
            item = Item.objects.select_for_update().get(pk=ln.item_id)
            item.unit_cost = ln.unit_price
            item.save(update_fields=["unit_cost", "updated_at"])
    else:
        for ln in lines:
            line_val = (ln.qty or Decimal("0")) * (ln.unit_price or Decimal("0"))
            share = charges * (line_val / base_total)
            qty = ln.qty or Decimal("1")
            add = (share / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
            ln.unit_price = (ln.unit_price or Decimal("0")) + add
            ln.save(update_fields=["unit_price"])
            item = Item.objects.select_for_update().get(pk=ln.item_id)
            item.unit_cost = ln.unit_price
            item.save(update_fields=["unit_cost", "updated_at"])
    lc.status = LandedCost.Status.POSTED
    lc.posted_at = timezone.now()
    lc.updated_by = user
    lc.save(update_fields=["status", "posted_at", "updated_by", "updated_at"])
    return lc
