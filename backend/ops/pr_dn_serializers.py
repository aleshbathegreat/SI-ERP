"""Purchase Requisition + Delivery Note serializers and convert helpers."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ops.models import (
    DeliveryNote,
    DeliveryNoteLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
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


class PurchaseRequisitionLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequisitionLine
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


class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    preferred_vendor_name = serializers.CharField(
        source="preferred_vendor.name", read_only=True, allow_null=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    po_no = serializers.CharField(
        source="purchase_order.po_no", read_only=True, allow_null=True
    )
    lines = PurchaseRequisitionLineSerializer(many=True, required=False)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequisition
        fields = "__all__"
        read_only_fields = RO + (
            "estimated_amount",
            "status",
            "purchase_order",
            "requested_by",
            "submitted_by",
            "approved_by",
        )

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least one requisition line."}
                )
        return attrs

    def _sync_lines(self, pr, lines_data):
        pr.lines.all().delete()
        for line in lines_data:
            PurchaseRequisitionLine.objects.create(requisition=pr, **line)
        pr.recompute_amount()

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
                validated_data, "pr_no", org, kind="pr", model=PurchaseRequisition
            )
        validated_data["status"] = PurchaseRequisition.Status.DRAFT
        if request and request.user and request.user.is_authenticated:
            validated_data.setdefault("requested_by", request.user)
        pr = PurchaseRequisition.objects.create(**validated_data)
        self._sync_lines(pr, lines_data)
        return pr

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status not in (
            PurchaseRequisition.Status.DRAFT,
            PurchaseRequisition.Status.SUBMITTED,
        ):
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {instance.status} requisition."}
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if not lines_data:
                raise serializers.ValidationError(
                    {"lines": "Keep at least one requisition line."}
                )
            self._sync_lines(instance, lines_data)
        else:
            instance.recompute_amount()
        return instance


@transaction.atomic
def convert_requisition_to_po(pr: PurchaseRequisition, user=None) -> PurchaseOrder:
    from core.doc_numbers import ensure_doc_no

    if pr.status == PurchaseRequisition.Status.CONVERTED and pr.purchase_order_id:
        return pr.purchase_order
    if pr.status != PurchaseRequisition.Status.APPROVED:
        raise serializers.ValidationError(
            "Approve the purchase requisition before converting to a PO."
        )
    if not pr.preferred_vendor_id:
        raise serializers.ValidationError(
            {"preferred_vendor": "Set a preferred vendor before converting to PO."}
        )
    if not pr.lines.exists():
        raise serializers.ValidationError("Requisition has no lines.")

    data = {"po_no": ""}
    ensure_doc_no(data, "po_no", pr.organization, kind="po", model=PurchaseOrder)
    po = PurchaseOrder.objects.create(
        organization_id=pr.organization_id,
        po_no=data["po_no"],
        vendor_id=pr.preferred_vendor_id,
        warehouse_id=pr.warehouse_id,
        order_date=timezone.localdate(),
        expected_date=pr.required_date,
        currency=pr.currency or "PKR",
        status=PurchaseOrder.Status.DRAFT,
        notes=f"Converted from PR {pr.pr_no}"
        + (f"\n{pr.notes}" if pr.notes else ""),
        created_by=user,
        updated_by=user,
    )
    for ln in pr.lines.select_related("item"):
        PurchaseOrderLine.objects.create(
            purchase_order=po,
            item=ln.item,
            description=ln.description or "",
            qty=ln.qty,
            unit_price=ln.unit_price,
            warehouse_id=pr.warehouse_id,
        )
    po.recompute_amount()
    pr.status = PurchaseRequisition.Status.CONVERTED
    pr.purchase_order = po
    pr.save(update_fields=["status", "purchase_order", "updated_at"])
    return po


class DeliveryNoteLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNoteLine
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


class DeliveryNoteSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    order_no = serializers.CharField(source="sales_order.order_no", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )
    lines = DeliveryNoteLineSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = "__all__"
        read_only_fields = RO + ("status", "dn_no", "delivered_by")

    def get_total(self, obj):
        total = Decimal("0")
        for ln in obj.lines.all():
            total += ln.line_total
        return str(total.quantize(Decimal("0.01")))
