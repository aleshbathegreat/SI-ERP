"""Quotations and Goods Receipt serializers + convert-to-SO."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ops.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    SalesOrder,
    SalesOrderLine,
    SalesQuotation,
    SalesQuotationLine,
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


class SalesQuotationLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = SalesQuotationLine
        fields = (
            "id",
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


class SalesQuotationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    sales_order_no = serializers.CharField(
        source="sales_order.order_no", read_only=True, allow_null=True
    )
    lines = SalesQuotationLineSerializer(many=True, required=False)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = SalesQuotation
        fields = "__all__"
        read_only_fields = RO + ("amount", "status", "sales_order")

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one quotation line."}
                )
        return attrs

    def _sync_lines(self, quote, lines_data):
        quote.lines.all().delete()
        for line in lines_data:
            SalesQuotationLine.objects.create(quotation=quote, **line)
        quote.recompute_amount()

    @transaction.atomic
    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        customer = validated_data.get("customer")
        if customer and not validated_data.get("payment_terms_days"):
            validated_data["payment_terms_days"] = customer.payment_terms_days or 30
        if customer and not validated_data.get("currency"):
            validated_data["currency"] = customer.currency or "PKR"
        if org:
            ensure_doc_no(
                validated_data, "quote_no", org, kind="quote", model=SalesQuotation
            )
        validated_data["status"] = SalesQuotation.Status.DRAFT
        quote = SalesQuotation.objects.create(**validated_data)
        self._sync_lines(quote, lines_data)
        return quote

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status not in (
            SalesQuotation.Status.DRAFT,
            SalesQuotation.Status.SENT,
        ):
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} quotation."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one quotation line."}
                )
            self._sync_lines(instance, lines_data)
        else:
            instance.recompute_amount()
        return instance


@transaction.atomic
def convert_quotation_to_so(quote: SalesQuotation, user=None) -> SalesOrder:
    from core.doc_numbers import ensure_doc_no

    if quote.status == SalesQuotation.Status.CONVERTED and quote.sales_order_id:
        return quote.sales_order
    if quote.status in (
        SalesQuotation.Status.CANCELLED,
        SalesQuotation.Status.EXPIRED,
    ):
        raise serializers.ValidationError(
            f"Cannot convert a {quote.status} quotation."
        )
    if not quote.lines.exists():
        raise serializers.ValidationError("Quotation has no lines.")

    data = {"order_no": ""}
    ensure_doc_no(data, "order_no", quote.organization, kind="so", model=SalesOrder)
    so = SalesOrder.objects.create(
        organization_id=quote.organization_id,
        order_no=data["order_no"],
        customer_id=quote.customer_id,
        order_date=timezone.localdate(),
        payment_terms_days=quote.payment_terms_days or 30,
        discount_amount=quote.discount_amount or Decimal("0"),
        tax_amount=quote.tax_amount or Decimal("0"),
        currency=quote.currency or "PKR",
        status=SalesOrder.Status.DRAFT,
        notes=f"Converted from quote {quote.quote_no}",
        created_by=user,
        updated_by=user,
    )
    for ln in quote.lines.select_related("item"):
        SalesOrderLine.objects.create(
            sales_order=so,
            item=ln.item,
            description=ln.description or "",
            qty=ln.qty,
            unit_price=ln.unit_price,
        )
    so.recompute_amount()
    quote.status = SalesQuotation.Status.CONVERTED
    quote.sales_order = so
    quote.save(update_fields=["status", "sales_order", "updated_at"])
    return so


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = GoodsReceiptLine
        fields = (
            "id",
            "purchase_order_line",
            "item",
            "item_sku",
            "item_name",
            "description",
            "qty",
            "qty_on_hold",
            "unit_price",
            "warehouse",
            "line_total",
        )

    def get_line_total(self, obj):
        return str(obj.line_total.quantize(Decimal("0.01")))


class GoodsReceiptSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    po_no = serializers.CharField(source="purchase_order.po_no", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    hold_qty = serializers.SerializerMethodField()

    class Meta:
        model = GoodsReceipt
        fields = "__all__"
        read_only_fields = RO + ("status", "grn_no", "received_by")

    def get_total(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.line_total
        return str(total.quantize(Decimal("0.01")))

    def get_hold_qty(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.qty_on_hold or Decimal("0")
        return str(total)
