"""Issue a stockable spare and respect QC hold."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ops.models import Item, StockLevel, StockMovement, Warehouse
from ops.qc_hold import available_qty
from ops.traceability import post_tracked_movements

ZERO = Decimal("0")


@transaction.atomic
def issue_spare(*, org, item_id, qty, user, reference, notes, warehouse_id=None):
    try:
        qty = Decimal(str(qty))
    except Exception as exc:
        raise ValidationError({"qty": "Qty must be a number."}) from exc
    if qty <= 0:
        raise ValidationError({"qty": "Qty must be positive."})
    item = Item.objects.filter(pk=item_id, organization=org, is_deleted=False).first()
    if item is None:
        raise ValidationError({"item": "Invalid item."})
    if item.item_type == Item.ItemType.SERVICE:
        raise ValidationError({"item": "Service items are not issued from stock."})
    if warehouse_id:
        wh = Warehouse.objects.filter(
            pk=warehouse_id, organization=org, is_deleted=False
        ).first()
        if wh is None:
            raise ValidationError({"warehouse": "Invalid warehouse."})
    else:
        wh = item.default_warehouse or Warehouse.objects.filter(
            organization=org, is_default=True, is_deleted=False
        ).first() or Warehouse.objects.filter(organization=org, is_deleted=False).first()
    if wh is None:
        raise ValidationError({"warehouse": "No warehouse available."})
    level = (
        StockLevel.objects.select_for_update()
        .filter(
            organization=org, warehouse=wh, item=item, is_deleted=False
        )
        .first()
    )
    free = available_qty(level)
    held = level.qty_qc_hold if level is not None else ZERO
    if free < qty:
        hold_note = f" ({held} on QC hold)" if held and held > 0 else ""
        raise ValidationError(
            {
                "qty": (
                    f"Insufficient stock for {item.sku} in {wh.code}: "
                    f"need {qty}, available {free}{hold_note}."
                )
            }
        )
    movs = post_tracked_movements(
        item=item,
        qty=qty,
        outbound=True,
        organization_id=org.id,
        warehouse=wh,
        movement_date=timezone.localdate(),
        reason=StockMovement.Reason.ISSUE,
        reference=reference,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    return {
        "item": item,
        "warehouse": wh,
        "movement": movs[0],
        "unit_cost": item.unit_cost or ZERO,
        "unit_price": item.sales_price or item.unit_cost or ZERO,
    }
