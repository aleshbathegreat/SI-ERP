"""QC quarantine: received stock stays unavailable until it is released."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from ops.models import GoodsReceipt, Item, StockLevel

ZERO = Decimal("0")


def available_qty(level) -> Decimal:
    if level is None:
        return ZERO
    free = (level.qty or ZERO) - (level.qty_qc_hold or ZERO)
    return free if free > 0 else ZERO


def _warehouse_id(grn, line):
    return line.warehouse_id or grn.warehouse_id


def _stock_lines(grn, item_id=None):
    qs = grn.lines.select_related("item", "warehouse")
    if item_id:
        qs = qs.filter(item_id=item_id)
    rows = []
    for ln in qs:
        if ln.item.item_type == Item.ItemType.SERVICE:
            continue
        if not _warehouse_id(grn, ln):
            continue
        rows.append(ln)
    return rows


def _level(org_id, warehouse_id, item_id):
    return (
        StockLevel.objects.select_for_update()
        .filter(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            item_id=item_id,
            is_deleted=False,
        )
        .first()
    )


def _set_line_hold(grn, line, target: Decimal) -> None:
    wh_id = _warehouse_id(grn, line)
    level = _level(grn.organization_id, wh_id, line.item_id)
    if level is None:
        return
    target = Decimal(target or 0)
    if target < 0:
        target = ZERO
    cap = line.qty or ZERO
    if target > cap:
        target = cap
    current = line.qty_on_hold or ZERO
    delta = target - current
    free = available_qty(level)
    if delta > free:
        delta = free
        target = current + delta
    new_hold = (level.qty_qc_hold or ZERO) + delta
    on_hand = level.qty or ZERO
    if new_hold < 0:
        new_hold = ZERO
    if new_hold > on_hand:
        new_hold = on_hand
    level.qty_qc_hold = new_hold
    level.save(update_fields=["qty_qc_hold", "updated_at"])
    line.qty_on_hold = target
    line.save(update_fields=["qty_on_hold"])


def hold_receipt(grn: GoodsReceipt) -> None:
    """Reserve every stockable line on a new goods receipt."""
    for ln in _stock_lines(grn):
        _set_line_hold(grn, ln, ln.qty or ZERO)


def apply_grn_status(grn: GoodsReceipt, status: str) -> GoodsReceipt:
    """QC pass releases the receipt. Fail or pending quarantines what is still on hand."""
    for ln in _stock_lines(grn):
        if status == GoodsReceipt.QcStatus.PASSED:
            _set_line_hold(grn, ln, ZERO)
        else:
            _set_line_hold(grn, ln, ln.qty or ZERO)
    grn.qc_status = status
    grn.save(update_fields=["qc_status", "updated_at"])
    return grn


def _held(grn, item_id) -> Decimal:
    return sum((ln.qty_on_hold or ZERO) for ln in _stock_lines(grn, item_id)) or ZERO


def release_item(grn, item_id, qty: Decimal) -> Decimal:
    left = Decimal(qty or 0)
    if left <= 0:
        return ZERO
    for ln in _stock_lines(grn, item_id):
        if left <= 0:
            break
        held = ln.qty_on_hold or ZERO
        step = held if held < left else left
        if step <= 0:
            continue
        _set_line_hold(grn, ln, held - step)
        left -= step
    return left


def ensure_hold_item(grn, item_id, qty: Decimal) -> None:
    target = Decimal(qty or 0)
    if target < 0:
        target = ZERO
    need = target - _held(grn, item_id)
    if need <= 0:
        return
    for ln in _stock_lines(grn, item_id):
        if need <= 0:
            break
        room = (ln.qty or ZERO) - (ln.qty_on_hold or ZERO)
        if room <= 0:
            continue
        step = room if room < need else need
        _set_line_hold(grn, ln, (ln.qty_on_hold or ZERO) + step)
        need -= step


def _mark_grn(grn, insp) -> None:
    from qms.models import QualityInspection

    lines = _stock_lines(grn)
    clear = bool(lines) and all((ln.qty_on_hold or ZERO) <= 0 for ln in lines)
    rejected = insp.qty_rejected or ZERO
    if insp.result == QualityInspection.Result.FAIL or (
        insp.result == QualityInspection.Result.CONDITIONAL and rejected > 0
    ):
        grn.qc_status = GoodsReceipt.QcStatus.FAILED
    elif clear:
        grn.qc_status = GoodsReceipt.QcStatus.PASSED
    grn.save(update_fields=["qc_status", "updated_at"])


@transaction.atomic
def sync_inspection(insp):
    """Move QC hold to match this inspection. No goods receipt means no stock effect."""
    from qms.models import QualityInspection

    if not insp.grn_id:
        return insp
    grn = (
        GoodsReceipt.objects.select_for_update()
        .filter(pk=insp.grn_id)
        .first()
    )
    if grn is None:
        return insp
    if insp.result == QualityInspection.Result.FAIL:
        desired = ZERO
    elif insp.result == QualityInspection.Result.CONDITIONAL:
        desired = (insp.qty_inspected or ZERO) - (insp.qty_rejected or ZERO)
    else:
        desired = insp.qty_inspected or ZERO
    if desired < 0:
        desired = ZERO
    delta = desired - (insp.qty_released or ZERO)
    if delta > 0:
        release_item(grn, insp.item_id, delta)
    elif delta < 0:
        ensure_hold_item(grn, insp.item_id, _held(grn, insp.item_id) + (-delta))
    if insp.result == QualityInspection.Result.FAIL:
        ensure_hold_item(
            grn, insp.item_id, insp.qty_inspected or insp.qty_rejected or ZERO
        )
    _mark_grn(grn, insp)
    insp.qty_released = desired
    insp.save(update_fields=["qty_released"])
    return insp


@transaction.atomic
def apply_ncr_disposition(ncr, *, user=None) -> None:
    """Close-out of a GRN-linked NCR: use-as-is releases, scrap and return leave the warehouse."""
    from qms.models import Ncr

    insp = ncr.source_inspection
    if insp is None or not insp.grn_id:
        return
    grn = GoodsReceipt.objects.select_for_update().filter(pk=insp.grn_id).first()
    if grn is None:
        return
    held = _held(grn, insp.item_id)
    rejected = insp.qty_rejected or ZERO
    qty = rejected if rejected > 0 else held
    if qty <= 0 or held <= 0:
        return
    if qty > held:
        qty = held
    if ncr.disposition == Ncr.Disposition.USE_AS_IS:
        release_item(grn, insp.item_id, qty)
        if _stock_lines(grn) and all(
            (ln.qty_on_hold or ZERO) <= 0 for ln in _stock_lines(grn)
        ):
            grn.qc_status = GoodsReceipt.QcStatus.PASSED
            grn.save(update_fields=["qc_status", "updated_at"])
        return
    if ncr.disposition not in (
        Ncr.Disposition.SCRAP,
        Ncr.Disposition.RETURN_VENDOR,
    ):
        return
    lines = _stock_lines(grn, insp.item_id)
    if not lines:
        return
    wh_id = _warehouse_id(grn, lines[0])
    level = _level(grn.organization_id, wh_id, insp.item_id)
    on_hand = level.qty if level else ZERO
    if qty > on_hand:
        qty = on_hand
    if qty <= 0:
        return
    release_item(grn, insp.item_id, qty)
    from ops.models import StockMovement, Warehouse
    from ops.traceability import post_tracked_movements

    wh = Warehouse.objects.filter(pk=wh_id).first()
    post_tracked_movements(
        item=insp.item,
        qty=qty,
        outbound=True,
        organization_id=grn.organization_id,
        warehouse=wh,
        movement_date=grn.receipt_date,
        reason=StockMovement.Reason.ISSUE,
        reference=ncr.ncr_no,
        notes=f"QC {ncr.disposition} · {ncr.ncr_no}",
        created_by=user,
        updated_by=user,
    )
