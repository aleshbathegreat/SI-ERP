"""WMS lite: bins, put-away from goods receipts, pick lists.

Confirming a pick against an open sales order deducts the chosen bins and
posts the delivery note in the same transaction. A pick against a delivery
that already posted does not move stock again. Direct delivery (no pick)
draws bin qty down FIFO so bin totals cannot stay above what shipped.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ops.models import (
    DeliveryNote,
    Item,
    PickList,
    PickListLine,
    SalesOrder,
    StockLevel,
    StockLevelBin,
    Warehouse,
    WarehouseBin,
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

ZERO = Decimal("0")
RECEIVING_BIN_CODES = {"recv", "receiving", "inbound", "dock", "stage", "staging"}


def _org(serializer):
    from core.access import user_organization

    request = serializer.context.get("request")
    return user_organization(request.user) if request else None


class WarehouseBinSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    stock = serializers.SerializerMethodField()

    class Meta:
        model = WarehouseBin
        fields = "__all__"
        read_only_fields = RO

    def get_stock(self, obj):
        return [
            {
                "item": r.item_id,
                "item_sku": r.item.sku,
                "item_name": r.item.name,
                "qty": str(r.qty),
            }
            for r in obj.stock.select_related("item").filter(is_deleted=False)
            if r.qty
        ]

    def validate_warehouse(self, value):
        org = _org(self)
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Warehouse not in this organization.")
        return value

    def validate(self, attrs):
        wh = attrs.get("warehouse") or getattr(self.instance, "warehouse", None)
        code = (attrs.get("code") or getattr(self.instance, "code", "") or "").strip()
        if wh and code:
            qs = WarehouseBin.all_objects.filter(warehouse=wh, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": "A bin with this code already exists in the warehouse."}
                )
        return attrs


class PickListLineSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    bin_code = serializers.CharField(source="bin.code", read_only=True, default="")

    class Meta:
        model = PickListLine
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "sales_order_line",
            "qty",
            "bin",
            "bin_code",
            "picked_qty",
        )
        read_only_fields = ("picked_qty",)


class PickListSerializer(serializers.ModelSerializer):
    lines = PickListLineSerializer(many=True, required=False)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    sales_order_no = serializers.CharField(
        source="sales_order.order_no", read_only=True, default=""
    )
    delivery_note_no = serializers.CharField(
        source="delivery_note.dn_no", read_only=True, default=""
    )

    class Meta:
        model = PickList
        fields = "__all__"
        read_only_fields = RO + ("status", "picked_at", "picked_by")
        extra_kwargs = {"pick_no": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        org = _org(self)
        for key in ("warehouse", "sales_order", "delivery_note"):
            obj = attrs.get(key)
            if org and obj is not None and obj.organization_id != org.id:
                raise serializers.ValidationError({key: "Not in this organization."})
        return attrs

    def _check_lines(self, org, warehouse, lines):
        for ln in lines:
            b = ln.get("bin")
            if b and (b.organization_id != getattr(org, "id", None) or b.warehouse_id != warehouse.id):
                raise serializers.ValidationError(
                    {"lines": "Bin must belong to the pick list warehouse."}
                )

    @transaction.atomic
    def create(self, validated_data):
        from core.doc_numbers import ensure_doc_no

        org = _org(self)
        lines = validated_data.pop("lines", [])
        self._check_lines(org, validated_data["warehouse"], lines)
        if org:
            ensure_doc_no(validated_data, "pick_no", org, kind="pick", model=PickList)
        pl = PickList.objects.create(**validated_data)
        for ln in lines:
            PickListLine.objects.create(pick_list=pl, **ln)
        return pl

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.status == PickList.Status.DONE:
            raise serializers.ValidationError("A completed pick list cannot be edited.")
        lines = validated_data.pop("lines", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if lines is not None:
            self._check_lines(_org(self), instance.warehouse, lines)
            instance.lines.all().delete()
            for ln in lines:
                PickListLine.objects.create(pick_list=instance, **ln)
        return instance


def suggest_bin(org_id, warehouse_id, item_id, need):
    """Bin with the most stock of the item in the warehouse (prefer one covering `need`)."""
    rows = list(
        StockLevelBin.objects.filter(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            item_id=item_id,
            bin__isnull=False,
            bin__active=True,
            bin__is_deleted=False,
            is_deleted=False,
            qty__gt=0,
        )
        .select_related("bin")
        .order_by("-qty")
    )
    for r in rows:
        if r.qty >= need:
            return r.bin
    return rows[0].bin if rows else None


@transaction.atomic
def create_pick_list(*, org, user, sales_order=None, delivery_note=None, warehouse=None, notes=""):
    from core.doc_numbers import ensure_doc_no

    if not sales_order and not delivery_note:
        raise serializers.ValidationError(
            "Provide sales_order or delivery_note to create a pick list."
        )
    if delivery_note and not sales_order:
        sales_order = delivery_note.sales_order

    src = delivery_note or sales_order
    wh = warehouse or getattr(src, "warehouse", None) or getattr(sales_order, "warehouse", None)
    if wh is None and sales_order is not None:
        first = sales_order.lines.filter(warehouse__isnull=False).select_related("warehouse").first()
        wh = first.warehouse if first else None
    if wh is None:
        wh = Warehouse.objects.filter(
            organization=org, is_default=True, is_deleted=False
        ).first() or Warehouse.objects.filter(organization=org, is_deleted=False).first()
    if wh is None:
        raise serializers.ValidationError({"warehouse": "No warehouse available."})

    if delivery_note is not None:
        if DeliveryNote.objects.filter(pk=delivery_note.pk, organization=org).first() is None:
            raise serializers.ValidationError({"delivery_note": "Not found."})
        if PickList.objects.filter(
            organization=org, delivery_note=delivery_note, is_deleted=False
        ).exists():
            raise serializers.ValidationError(
                "A pick list already exists for this delivery note."
            )
        raw = [
            (l.item, l.qty, l.sales_order_line)
            for l in delivery_note.lines.select_related("item", "sales_order_line")
        ]
    else:
        if sales_order.status not in (
            SalesOrder.Status.CONFIRMED,
            SalesOrder.Status.INVOICED,
        ):
            raise serializers.ValidationError(
                "Confirm the sales order before creating a pick list."
            )
        raw = []
        for l in sales_order.lines.select_related("item"):
            open_qty = (l.qty or ZERO) - (l.qty_delivered or ZERO)
            raw.append((l.item, open_qty, l))

    rows = [
        (item, qty, sol)
        for item, qty, sol in raw
        if qty and qty > 0 and item.item_type != Item.ItemType.SERVICE
    ]
    if not rows:
        raise serializers.ValidationError("Nothing to pick: no open stockable lines.")

    data = {"pick_no": ""}
    ensure_doc_no(data, "pick_no", org, kind="pick", model=PickList)
    pl = PickList.objects.create(
        organization=org,
        pick_no=data["pick_no"],
        sales_order=sales_order,
        delivery_note=delivery_note,
        warehouse=wh,
        status=PickList.Status.DRAFT,
        notes=notes or f"Pick for {(delivery_note.dn_no if delivery_note else sales_order.order_no)}",
        created_by=user,
        updated_by=user,
    )
    for item, qty, sol in rows:
        PickListLine.objects.create(
            pick_list=pl,
            item=item,
            sales_order_line=sol,
            qty=qty,
            bin=suggest_bin(org.id, wh.id, item.id, qty),
        )
    return pl


def _pick_moves_stock(pl: PickList) -> bool:
    """True when this confirm is the shipment (no delivery posted yet)."""
    if pl.delivery_note_id or not pl.sales_order_id:
        return False
    so = SalesOrder.objects.select_for_update().get(pk=pl.sales_order_id)
    if so.status == SalesOrder.Status.CANCELLED:
        raise serializers.ValidationError("Sales order is cancelled.")
    if so.status == SalesOrder.Status.DELIVERED:
        return False
    return True


def _deduct_pick_bin(pl: PickList, ln: PickListLine, picked: Decimal) -> None:
    if ln.bin_id:
        sb = (
            StockLevelBin.objects.select_for_update()
            .filter(
                organization_id=pl.organization_id,
                warehouse_id=pl.warehouse_id,
                bin_id=ln.bin_id,
                item_id=ln.item_id,
                is_deleted=False,
            )
            .first()
        )
        have = sb.qty if sb else ZERO
        if have < picked:
            code = ln.bin.code if ln.bin_id else ""
            raise serializers.ValidationError(
                {
                    "lines": (
                        f"Insufficient stock in bin {code} for {ln.item.sku}: "
                        f"need {picked}, available {have}."
                    )
                }
            )
        sb.qty = have - picked
        sb.save(update_fields=["qty", "updated_at"])
        return
    consume_bins(
        org_id=pl.organization_id,
        warehouse_id=pl.warehouse_id,
        item_id=ln.item_id,
        qty=picked,
    )


def _post_pick_delivery(pl: PickList, user) -> None:
    """Post a delivery note for the picked qty. Bins are already deducted."""
    so = SalesOrder.objects.select_for_update().get(pk=pl.sales_order_id)
    wanted: dict[int, Decimal] = {}
    open_qty: dict[int, Decimal] = {}
    for ln in pl.lines.select_related("item", "sales_order_line"):
        picked = ln.picked_qty or ZERO
        if picked <= 0:
            continue
        if not ln.sales_order_line_id:
            raise serializers.ValidationError(
                {"lines": f"{ln.item.sku} is not linked to a sales order line."}
            )
        sol = ln.sales_order_line
        open_qty[sol.id] = (sol.qty or ZERO) - (sol.qty_delivered or ZERO)
        wanted[sol.id] = wanted.get(sol.id, ZERO) + picked
    payload = []
    for sol_id, qty in wanted.items():
        room = open_qty.get(sol_id, ZERO)
        if qty > room:
            raise serializers.ValidationError(
                {
                    "lines": (
                        f"Picked qty {qty} exceeds open quantity {room} on the sales order."
                    )
                }
            )
        if qty > 0:
            payload.append({"id": sol_id, "qty": str(qty)})
    if not payload:
        return
    from ops.serializers import deliver_sales_order

    deliver_sales_order(
        so,
        warehouse_id=pl.warehouse_id,
        user=user,
        lines=payload,
        deduct_bins=False,
        force_warehouse=True,
    )
    dn = getattr(so, "_last_dn", None)
    if dn is not None:
        pl.delivery_note = dn


@transaction.atomic
def confirm_pick(pick_list: PickList, *, user=None, lines=None, deduct_bin=True):
    """Record picked qty and, when the order is still open, post the delivery note."""
    pl = PickList.objects.select_for_update().get(pk=pick_list.pk)
    if pl.status == PickList.Status.DONE:
        raise serializers.ValidationError("Pick list is already confirmed.")

    post_delivery = _pick_moves_stock(pl)
    deduct_now = bool(deduct_bin) and post_delivery
    # Ad-hoc lists (no sales order) only move bins.
    if deduct_bin and not pl.sales_order_id and not pl.delivery_note_id:
        deduct_now = True

    overrides = {}
    for row in lines or []:
        if isinstance(row, dict) and row.get("id") is not None:
            overrides[int(row["id"])] = row

    for ln in pl.lines.select_related("item", "bin"):
        row = overrides.get(ln.id, {})
        picked = Decimal(str(row["picked_qty"])) if row.get("picked_qty") not in (None, "") else ln.qty
        if picked < 0 or picked > ln.qty:
            raise serializers.ValidationError(
                {"lines": f"Picked qty for {ln.item.sku} must be between 0 and {ln.qty}."}
            )
        if row.get("bin") not in (None, ""):
            b = WarehouseBin.objects.filter(
                pk=row["bin"],
                organization_id=pl.organization_id,
                warehouse_id=pl.warehouse_id,
                is_deleted=False,
            ).first()
            if not b:
                raise serializers.ValidationError(
                    {"lines": f"Invalid bin for {ln.item.sku}."}
                )
            ln.bin = b
        if deduct_now and picked > 0:
            _deduct_pick_bin(pl, ln, picked)
        ln.picked_qty = picked
        ln.save(update_fields=["picked_qty", "bin"])

    if post_delivery:
        _post_pick_delivery(pl, user)

    pl.status = PickList.Status.DONE
    pl.picked_at = timezone.now()
    pl.picked_by = user
    pl.updated_by = user
    pl.save(
        update_fields=[
            "status",
            "picked_at",
            "picked_by",
            "updated_by",
            "updated_at",
            "delivery_note",
        ]
    )
    return pl


@transaction.atomic
def put_away(*, org, bin_obj: WarehouseBin, item_id, qty, user=None):
    """Assign warehouse stock of an item to a bin (bin totals cannot exceed warehouse stock)."""
    qty = Decimal(str(qty))
    if qty <= 0:
        raise serializers.ValidationError({"qty": "Qty must be positive."})
    item = Item.objects.filter(pk=item_id, organization=org, is_deleted=False).first()
    if not item:
        raise serializers.ValidationError({"item": "Invalid item."})
    level = StockLevel.objects.filter(
        organization=org, warehouse_id=bin_obj.warehouse_id, item=item, is_deleted=False
    ).first()
    total = level.qty if level else ZERO
    assigned = sum(
        (
            r.qty
            for r in StockLevelBin.objects.select_for_update().filter(
                organization=org,
                warehouse_id=bin_obj.warehouse_id,
                item=item,
                is_deleted=False,
            )
        ),
        ZERO,
    )
    if assigned + qty > total:
        raise serializers.ValidationError(
            {
                "qty": (
                    f"Exceeds warehouse stock for {item.sku}: on hand {total}, "
                    f"already in bins {assigned}."
                )
            }
        )
    sb, _ = StockLevelBin.objects.select_for_update().get_or_create(
        organization=org,
        warehouse_id=bin_obj.warehouse_id,
        bin=bin_obj,
        item=item,
        defaults={"qty": ZERO, "created_by": user},
    )
    sb.qty = (sb.qty or ZERO) + qty
    sb.save(update_fields=["qty", "updated_at"])
    return sb


def _on_hand(org, warehouse_id, item_id) -> Decimal:
    level = StockLevel.objects.filter(
        organization=org,
        warehouse_id=warehouse_id,
        item_id=item_id,
        is_deleted=False,
    ).first()
    return level.qty if level else ZERO


def _binned_qty(org, warehouse_id, item_id) -> Decimal:
    total = ZERO
    rows = StockLevelBin.objects.filter(
        organization=org,
        warehouse_id=warehouse_id,
        item_id=item_id,
        is_deleted=False,
    )
    for row in rows:
        total += row.qty or ZERO
    return total


def consume_bins(*, org_id, warehouse_id, item_id, qty) -> Decimal:
    """Draw qty out of bins that hold the item. Short bins are left; warehouse stock is separate."""
    left = Decimal(str(qty or 0))
    if left <= 0:
        return ZERO
    rows = (
        StockLevelBin.objects.select_for_update()
        .filter(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            item_id=item_id,
            is_deleted=False,
            qty__gt=0,
            bin__isnull=False,
        )
        .order_by("id")
    )
    taken = ZERO
    for sb in rows:
        if left <= 0:
            break
        step = min(sb.qty or ZERO, left)
        if step <= 0:
            continue
        sb.qty = (sb.qty or ZERO) - step
        sb.save(update_fields=["qty", "updated_at"])
        left -= step
        taken += step
    return taken


def suggest_receiving_bin(org_id, warehouse_id, item_id, need):
    """Prefer a bin that already holds the item, then a receiving dock, then the only bin."""
    found = suggest_bin(org_id, warehouse_id, item_id, need)
    if found:
        return found
    bins = list(
        WarehouseBin.objects.filter(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            active=True,
            is_deleted=False,
        ).order_by("code")
    )
    for b in bins:
        if (b.code or "").strip().lower() in RECEIVING_BIN_CODES:
            return b
    if len(bins) == 1:
        return bins[0]
    return None


def grn_putaway_plan(grn) -> dict:
    """Unassigned receipt qty and a suggested bin for each stockable line."""
    remaining: dict[tuple[int, int], Decimal] = {}
    lines = []
    bin_rows: dict[int, dict] = {}
    tracking = False
    for ln in grn.lines.select_related("item", "warehouse"):
        wh = ln.warehouse or grn.warehouse
        if wh is None or ln.item.item_type == Item.ItemType.SERVICE:
            continue
        wh_bins = WarehouseBin.objects.filter(
            organization_id=grn.organization_id,
            warehouse_id=wh.id,
            active=True,
            is_deleted=False,
        ).order_by("code")
        if wh_bins.exists():
            tracking = True
        for b in wh_bins:
            bin_rows[b.id] = {"id": b.id, "code": b.code, "warehouse": wh.id}
        key = (wh.id, ln.item_id)
        if key not in remaining:
            remaining[key] = max(
                ZERO, _on_hand(grn.organization, wh.id, ln.item_id) - _binned_qty(grn.organization, wh.id, ln.item_id)
            )
        room = remaining[key]
        qty = min(ln.qty or ZERO, room)
        if qty < 0:
            qty = ZERO
        remaining[key] = room - qty
        suggested = (
            suggest_receiving_bin(grn.organization_id, wh.id, ln.item_id, qty)
            if qty > 0
            else None
        )
        lines.append(
            {
                "line_id": ln.id,
                "item": ln.item_id,
                "item_sku": ln.item.sku,
                "item_name": ln.item.name,
                "warehouse": wh.id,
                "qty": str(qty),
                "suggested_bin": suggested.id if suggested else None,
                "suggested_bin_code": suggested.code if suggested else "",
            }
        )
    return {
        "tracking": tracking,
        "lines": lines,
        "bins": list(bin_rows.values()),
    }


@transaction.atomic
def apply_grn_putaway(grn, *, user, lines=None):
    """Put unassigned GRN qty into bins. Omit lines to use the suggestion."""
    from ops.models import GoodsReceipt

    if grn.status != GoodsReceipt.Status.POSTED:
        raise serializers.ValidationError("Only a posted goods receipt can be put away.")
    plan = {row["line_id"]: row for row in grn_putaway_plan(grn)["lines"]}
    jobs = []
    if lines:
        for row in lines:
            if not isinstance(row, dict):
                continue
            raw_id = row.get("line_id", row.get("id"))
            if raw_id in (None, ""):
                continue
            spec = plan.get(int(raw_id))
            if spec is None:
                raise serializers.ValidationError({"lines": "Unknown goods receipt line."})
            qty = Decimal(str(row["qty"])) if row.get("qty") not in (None, "") else Decimal(spec["qty"])
            if qty <= 0:
                continue
            if qty > Decimal(spec["qty"]):
                raise serializers.ValidationError(
                    {
                        "lines": (
                            f"Put-away qty {qty} exceeds unassigned {spec['qty']} "
                            f"for {spec['item_sku']}."
                        )
                    }
                )
            bin_id = row.get("bin") or spec["suggested_bin"]
            if not bin_id:
                raise serializers.ValidationError(
                    {"lines": f"Choose a bin for {spec['item_sku']}."}
                )
            jobs.append((spec, qty, int(bin_id)))
    else:
        for spec in plan.values():
            qty = Decimal(spec["qty"])
            if qty > 0 and spec["suggested_bin"]:
                jobs.append((spec, qty, int(spec["suggested_bin"])))
    if not jobs:
        raise serializers.ValidationError(
            "Nothing to put away. Stock is already in bins, or no bin was suggested."
        )
    for spec, qty, bin_id in jobs:
        b = WarehouseBin.objects.filter(
            pk=bin_id,
            organization_id=grn.organization_id,
            warehouse_id=spec["warehouse"],
            active=True,
            is_deleted=False,
        ).first()
        if not b:
            raise serializers.ValidationError(
                {"lines": f"Invalid bin for {spec['item_sku']}."}
            )
        put_away(org=grn.organization, bin_obj=b, item_id=spec["item"], qty=qty, user=user)
    return grn_putaway_plan(grn)
