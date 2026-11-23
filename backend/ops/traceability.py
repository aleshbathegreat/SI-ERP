"""Lot / batch / serial traceability helpers for stock posting paths (GRN, DN, WO, manual)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from ops.models import Item, LotBatch, SerialNumber, StockMovement


@dataclass
class Alloc:
    qty: Decimal
    lot: LotBatch | None = None
    serial: SerialNumber | None = None

    @property
    def batch_no(self) -> str:
        return self.lot.batch_no if self.lot else ""


def item_is_tracked(item: Item) -> bool:
    return item.item_type != Item.ItemType.SERVICE and bool(
        item.track_batch or item.track_serial
    )


def _serial_list(trace: dict) -> list[str]:
    raw = trace.get("serial_nos")
    if raw is None:
        raw = trace.get("serial_no") or trace.get("serials")
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[\n,;]+", raw)
    else:
        parts = list(raw)
    return [str(p).strip() for p in parts if str(p).strip()]


def parse_trace(row: dict | None) -> dict:
    """Normalise lot/serial keys from an API line payload."""
    if not isinstance(row, dict):
        return {}
    out = {}
    lot = row.get("lot") or row.get("lot_id")
    if lot not in (None, ""):
        out["lot"] = int(lot)
    batch_no = (row.get("batch_no") or "").strip() if row.get("batch_no") else ""
    if batch_no:
        out["batch_no"] = batch_no
    if row.get("expiry_date"):
        out["expiry_date"] = row["expiry_date"]
    serials = _serial_list(row)
    if serials:
        out["serial_nos"] = serials
    return out


def line_trace_map(raw_lines) -> dict[int, dict]:
    """Map line id → trace dict from optional [{id, qty, batch_no, serial_nos...}]."""
    out: dict[int, dict] = {}
    if not raw_lines:
        return out
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        lid = row.get("id") or row.get("line_id")
        if lid is None:
            continue
        tr = parse_trace(row)
        if tr:
            out[int(lid)] = tr
    return out


def _find_lot(org_id, item, warehouse, trace: dict) -> LotBatch | None:
    qs = LotBatch.objects.filter(organization_id=org_id, item=item, is_deleted=False)
    if trace.get("lot"):
        return qs.filter(pk=trace["lot"]).first()
    batch_no = trace.get("batch_no")
    if not batch_no:
        return None
    if warehouse is not None:
        lot = qs.filter(batch_no=batch_no, warehouse=warehouse).first()
        if lot:
            return lot
    return qs.filter(batch_no=batch_no, warehouse__isnull=True).first()


def _lot_fits_warehouse(lot: LotBatch, warehouse) -> bool:
    return warehouse is None or lot.warehouse_id in (None, warehouse.pk)


def plan_allocations(
    *,
    item: Item,
    org_id: int,
    warehouse,
    qty: Decimal,
    outbound: bool,
    trace: dict | None = None,
    auto_allocate: bool = False,
) -> list[Alloc]:
    """
    Validate lot/serial requirements and return allocations (one per movement).
    Inbound creates lot/serial rows when missing. Raises DRF ValidationError.
    """
    qty = abs(Decimal(str(qty)))
    trace = trace or {}
    sku = item.sku
    if not item_is_tracked(item):
        return [Alloc(qty=qty)]

    # ---- batch / lot parts ------------------------------------------------
    lot_parts: list[tuple[LotBatch | None, Decimal]] = [(None, qty)]
    if item.track_batch:
        if outbound:
            lot = _find_lot(org_id, item, warehouse, trace)
            if lot is None and (trace.get("lot") or trace.get("batch_no")):
                raise ValidationError({"lots": f"{sku}: lot/batch not found."})
            if lot is not None:
                if not _lot_fits_warehouse(lot, warehouse):
                    raise ValidationError(
                        {"lots": f"{sku}: batch {lot.batch_no} is not in this warehouse."}
                    )
                if (lot.qty or Decimal("0")) < qty:
                    raise ValidationError(
                        {
                            "lots": (
                                f"{sku}: batch {lot.batch_no} has {lot.qty}, need {qty}."
                            )
                        }
                    )
                lot_parts = [(lot, qty)]
            elif auto_allocate:
                lot_qs = LotBatch.objects.filter(
                    organization_id=org_id,
                    item=item,
                    is_deleted=False,
                    qty__gt=0,
                )
                if warehouse is not None:
                    lot_qs = lot_qs.filter(warehouse=warehouse)
                need = qty
                lot_parts = []
                for lot in lot_qs.order_by("expiry_date", "id"):
                    if need <= 0:
                        break
                    take = min(need, lot.qty or Decimal("0"))
                    if take > 0:
                        lot_parts.append((lot, take))
                        need -= take
                if need > 0:
                    raise ValidationError(
                        {"lots": f"{sku}: insufficient batch stock, short by {need}."}
                    )
            else:
                raise ValidationError(
                    {"lots": f"{sku}: batch/lot is required for issue (track_batch)."}
                )
        else:
            lot = _find_lot(org_id, item, warehouse, trace)
            if lot is None:
                batch_no = trace.get("batch_no")
                if not batch_no:
                    raise ValidationError(
                        {"lots": f"{sku}: batch/lot is required for receipt (track_batch)."}
                    )
                lot, _ = LotBatch.objects.get_or_create(
                    organization_id=org_id,
                    item=item,
                    batch_no=batch_no,
                    warehouse=warehouse,
                    defaults={
                        "expiry_date": trace.get("expiry_date") or None,
                        "qty": Decimal("0"),
                    },
                )
            elif not _lot_fits_warehouse(lot, warehouse):
                raise ValidationError(
                    {"lots": f"{sku}: batch {lot.batch_no} belongs to another warehouse."}
                )
            if trace.get("expiry_date") and not lot.expiry_date:
                lot.expiry_date = trace["expiry_date"]
                lot.save(update_fields=["expiry_date", "updated_at"])
            lot_parts = [(lot, qty)]

    # ---- serials ----------------------------------------------------------
    if not item.track_serial:
        return [Alloc(qty=q, lot=lot) for lot, q in lot_parts]

    if qty != qty.to_integral_value():
        raise ValidationError({"serials": f"{sku}: serial-tracked qty must be a whole number."})
    n = int(qty)
    serials = _serial_list(trace)
    if outbound and not serials and auto_allocate:
        sq = SerialNumber.objects.filter(
            organization_id=org_id,
            item=item,
            is_deleted=False,
            status=SerialNumber.Status.AVAILABLE,
        )
        if warehouse is not None:
            sq = sq.filter(warehouse=warehouse)
        serials = list(sq.order_by("id").values_list("serial_no", flat=True)[:n])
    if len(serials) != n:
        raise ValidationError(
            {"serials": f"{sku}: {n} serial number(s) required, {len(serials)} provided."}
        )
    if len(set(serials)) != len(serials):
        raise ValidationError({"serials": f"{sku}: duplicate serial numbers."})

    units: list[LotBatch | None] = []
    for lot, q in lot_parts:
        units.extend([lot] * int(q))
    while len(units) < n:
        units.append(None)

    allocs: list[Alloc] = []
    for sn_no, lot in zip(serials, units):
        existing = SerialNumber.objects.filter(
            organization_id=org_id, item=item, serial_no=sn_no
        ).first()
        if outbound:
            if not existing or existing.is_deleted:
                raise ValidationError({"serials": f"{sku}: serial {sn_no} not found."})
            if existing.status != SerialNumber.Status.AVAILABLE:
                raise ValidationError(
                    {"serials": f"{sku}: serial {sn_no} is {existing.status}, not available."}
                )
            if (
                warehouse is not None
                and existing.warehouse_id
                and existing.warehouse_id != warehouse.pk
            ):
                raise ValidationError(
                    {"serials": f"{sku}: serial {sn_no} is in another warehouse."}
                )
            sn = existing
        else:
            if existing and existing.status == SerialNumber.Status.AVAILABLE:
                raise ValidationError(
                    {"serials": f"{sku}: serial {sn_no} is already in stock."}
                )
            if existing and existing.status == SerialNumber.Status.SCRAPPED:
                raise ValidationError(
                    {"serials": f"{sku}: serial {sn_no} was scrapped and cannot be received."}
                )
            if existing:
                sn = existing
            else:
                sn = SerialNumber.objects.create(
                    organization_id=org_id,
                    item=item,
                    serial_no=sn_no,
                    status=SerialNumber.Status.AVAILABLE,
                    warehouse=warehouse,
                )
        allocs.append(Alloc(qty=Decimal("1"), lot=lot, serial=sn))
    return allocs


@transaction.atomic
def post_tracked_movements(
    *,
    item: Item,
    qty,
    outbound: bool,
    trace: dict | None = None,
    auto_allocate: bool = False,
    **mov_kwargs,
) -> list[StockMovement]:
    """
    Create + apply stock movement(s). `qty` is a positive magnitude; sign is derived
    from `outbound`. Serial-tracked items produce one movement per serial.
    """
    org_id = mov_kwargs.get("organization_id") or getattr(
        mov_kwargs.get("organization"), "id", None
    )
    allocs = plan_allocations(
        item=item,
        org_id=org_id,
        warehouse=mov_kwargs.get("warehouse"),
        qty=qty,
        outbound=outbound,
        trace=trace,
        auto_allocate=auto_allocate,
    )
    movements: list[StockMovement] = []
    for a in allocs:
        signed = -a.qty if outbound else a.qty
        mov = StockMovement(
            item=item,
            qty=signed,
            lot=a.lot,
            batch_no=a.batch_no,
            serial=a.serial,
            **mov_kwargs,
        )
        mov.save()
        try:
            mov.apply_to_item()
        except ValueError as e:
            raise ValidationError(str(e)) from e
        movements.append(mov)
    return movements


def prepare_direct_movement(data: dict, *, serial_no: str = "") -> dict:
    """
    Manual StockMovement create: resolve lot / serial for tracked items.
    Mutates and returns validated_data (adds lot, batch_no, serial).
    """
    item: Item = data["item"]
    if not item_is_tracked(item):
        return data
    qty = Decimal(str(data["qty"]))
    reason = data.get("reason")
    transfer = reason == StockMovement.Reason.TRANSFER
    outbound = transfer or qty < 0
    warehouse = data.get("warehouse")
    trace: dict = {}
    if data.get("lot"):
        trace["lot"] = data["lot"].pk
    if data.get("batch_no"):
        trace["batch_no"] = data["batch_no"]
    serial_val = (serial_no or "").strip()
    if not serial_val and data.get("serial"):
        serial_val = data["serial"].serial_no
    if serial_val:
        trace["serial_nos"] = [serial_val]
    if item.track_serial and abs(qty) != 1:
        raise ValidationError({"qty": "Serial-tracked items move one unit (±1) per movement."})
    allocs = plan_allocations(
        item=item,
        org_id=item.organization_id,
        warehouse=warehouse,
        qty=abs(qty),
        outbound=outbound,
        trace=trace,
    )
    if len(allocs) != 1:
        raise ValidationError({"detail": "Exactly one lot/serial per movement."})
    a = allocs[0]
    data["lot"] = a.lot
    data["batch_no"] = a.batch_no
    data["serial"] = a.serial
    return data
