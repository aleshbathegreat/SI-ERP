from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from mfg.models import Bom, BomLine, WorkOrder
from ops.models import Item, StockLevel, StockMovement

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


class BomLineSerializer(serializers.ModelSerializer):
    component_sku = serializers.CharField(source="component.sku", read_only=True)
    component_name = serializers.CharField(source="component.name", read_only=True)

    class Meta:
        model = BomLine
        fields = ("id", "component", "component_sku", "component_name", "qty")


class BomSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    lines = BomLineSerializer(many=True, required=False)

    class Meta:
        model = Bom
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "code",
            "name",
            "is_active",
            "lines",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO

    def validate(self, attrs):
        from core.access import user_organization

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        inst = self.instance
        code = attrs.get("code", inst.code if inst else None)
        if org and code:
            dup = Bom.objects.filter(organization=org, code=code)
            if inst:
                dup = dup.exclude(pk=inst.pk)
            if dup.exists():
                raise ValidationError({"code": "A BOM with this code already exists."})
        fg = attrs.get("item") or (inst.item if inst else None)
        for i, line in enumerate(attrs.get("lines") or []):
            comp = line.get("component")
            if comp is not None and fg is not None and comp.pk == fg.pk:
                raise ValidationError(
                    {"lines": f"Line {i + 1}: component cannot be the finished good."}
                )
            if org and comp is not None and comp.organization_id != org.id:
                raise ValidationError({"lines": f"Line {i + 1}: invalid component."})
            qty = line.get("qty")
            if qty is None or Decimal(str(qty)) <= 0:
                raise ValidationError(
                    {"lines": f"Line {i + 1}: quantity must be greater than zero."}
                )
        if org and fg is not None and fg.organization_id != org.id:
            raise ValidationError({"item": "Invalid finished good."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        bom = super().create(validated_data)
        for line in lines:
            BomLine.objects.create(bom=bom, **line)
        return bom

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        bom = super().update(instance, validated_data)
        if lines is not None:
            bom.lines.all().delete()
            for line in lines:
                BomLine.objects.create(bom=bom, **line)
        return bom


class WorkOrderSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    bom_code = serializers.CharField(source="bom.code", read_only=True, allow_null=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, allow_null=True
    )

    class Meta:
        model = WorkOrder
        fields = "__all__"
        read_only_fields = list(RO) + ["status", "qty_completed"]

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        validated_data.pop("status", None)
        validated_data.pop("qty_completed", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        bom = validated_data.get("bom")
        if bom and not validated_data.get("item"):
            validated_data["item"] = bom.item
        if org:
            ensure_doc_no(validated_data, "wo_no", org, kind="wo", model=WorkOrder)
        validated_data["status"] = WorkOrder.Status.DRAFT
        validated_data["qty_completed"] = Decimal("0")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        validated_data.pop("qty_completed", None)
        if instance.status not in (
            WorkOrder.Status.DRAFT,
            WorkOrder.Status.RELEASED,
        ):
            raise ValidationError(
                {"detail": f"Cannot edit a {instance.status} work order."}
            )
        return super().update(instance, validated_data)


@transaction.atomic
def release_work_order(wo: WorkOrder, *, user=None) -> WorkOrder:
    if wo.status != WorkOrder.Status.DRAFT:
        raise ValidationError("Only draft work orders can be released.")
    wo.status = WorkOrder.Status.RELEASED
    if user:
        wo.updated_by = user
    wo.save(update_fields=["status", "updated_by", "updated_at"])
    return wo


@transaction.atomic
def complete_work_order(
    wo: WorkOrder,
    *,
    qty=None,
    user=None,
    batch_no=None,
    serial_nos=None,
    expiry_date=None,
    lot=None,
) -> WorkOrder:
    """
    Complete WO: issue BOM components (lot/serial auto-allocated FIFO by expiry) and
    receipt FG. Tracked FG items require batch_no / serial_nos.
    """
    from ops.traceability import parse_trace, post_tracked_movements

    if wo.status == WorkOrder.Status.DRAFT:
        raise ValidationError("Release the work order before completing it.")
    if wo.status not in (
        WorkOrder.Status.RELEASED,
        WorkOrder.Status.IN_PROGRESS,
    ):
        raise ValidationError("Work order cannot be completed in its current status.")
    try:
        take = Decimal(str(qty if qty not in (None, "") else wo.qty_planned or 0))
    except Exception:
        raise ValidationError("Completion qty must be a number.")
    if take <= 0:
        raise ValidationError("Completion qty must be positive.")

    wh = wo.warehouse or (wo.item.default_warehouse if wo.item_id else None)
    bom = wo.bom
    if bom is None:
        raise ValidationError("Work order has no BOM; assign a BOM before completing.")
    bom_lines = list(bom.lines.select_related("component"))
    if not bom_lines:
        raise ValidationError(
            f"BOM {bom.code} has no component lines; add lines before completing."
        )

    # Component availability check (aggregated per component) before any issue.
    required: dict[int, tuple[Item, Decimal]] = {}
    for line in bom_lines:
        comp = line.component
        if comp.item_type != Item.ItemType.STOCKABLE:
            continue
        issue_qty = (Decimal(str(line.qty or 0)) * take).quantize(Decimal("0.001"))
        if issue_qty <= 0:
            continue
        prev = required.get(comp.pk, (comp, Decimal("0")))[1]
        required[comp.pk] = (comp, prev + issue_qty)
    shortages = []
    for comp, need in required.values():
        if wh is not None:
            level = (
                StockLevel.objects.select_for_update()
                .filter(organization_id=wo.organization_id, warehouse=wh, item=comp)
                .first()
            )
            from ops.qc_hold import available_qty

            free = available_qty(level) if level is not None else Decimal("0")
            held = Decimal(str(level.qty_qc_hold or 0)) if level is not None else Decimal("0")
            where = f" in {wh.code}"
            if free < need:
                hold_note = f", {held} on QC hold" if held > 0 else ""
                shortages.append(
                    f"{comp.sku}: need {need.normalize():f}, available {free.normalize():f}{hold_note}{where}"
                )
            continue
        else:
            have = Decimal(str(comp.qty_on_hand or 0))
            where = ""
        if have < need:
            shortages.append(
                f"{comp.sku}: need {need.normalize():f}, available {have.normalize():f}{where}"
            )
    if shortages:
        raise ValidationError(
            "Insufficient component stock — " + "; ".join(shortages)
        )

    if bom:
        for line in bom_lines:
            comp = line.component
            issue_qty = (Decimal(str(line.qty or 0)) * take).quantize(Decimal("0.001"))
            if issue_qty <= 0:
                continue
            if comp.item_type == Item.ItemType.STOCKABLE:
                post_tracked_movements(
                    item=comp,
                    qty=issue_qty,
                    outbound=True,
                    auto_allocate=True,
                    organization=wo.organization,
                    warehouse=wh,
                    movement_date=timezone.localdate(),
                    reason=StockMovement.Reason.ISSUE,
                    reference=wo.wo_no,
                    notes=f"WO issue · {wo.wo_no}",
                    created_by=user,
                    updated_by=user,
                )

    fg = wo.item
    if fg and fg.item_type == Item.ItemType.STOCKABLE:
        post_tracked_movements(
            item=fg,
            qty=take,
            outbound=False,
            trace=parse_trace(
                {
                    "batch_no": batch_no,
                    "serial_nos": serial_nos,
                    "expiry_date": expiry_date,
                    "lot": lot,
                }
            ),
            organization=wo.organization,
            warehouse=wh,
            movement_date=timezone.localdate(),
            reason=StockMovement.Reason.RECEIPT,
            reference=wo.wo_no,
            notes=f"WO receipt FG · {wo.wo_no}",
            created_by=user,
            updated_by=user,
        )

    wo.qty_completed = (Decimal(str(wo.qty_completed or 0)) + take).quantize(
        Decimal("0.001")
    )
    wo.status = WorkOrder.Status.DONE
    if user:
        wo.updated_by = user
    wo.save(update_fields=["qty_completed", "status", "updated_by", "updated_at"])
    return wo
