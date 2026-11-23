"""Three-way match: Purchase Order ↔ Goods Receipt ↔ AP Invoice."""

from __future__ import annotations

from decimal import Decimal


def _d(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


def three_way_match(po, invoice_amount=None, tolerance_pct: float = 2.0) -> dict:
    """
    Compare PO ordered value vs GRN received value vs optional AP invoice amount.
    Returns match status and variance details.
    """
    if po is None:
        return {
            "ok": False,
            "status": "no_po",
            "detail": "No purchase order linked.",
        }

    po_qty = Decimal("0")
    recv_qty = Decimal("0")
    po_value = Decimal("0")
    recv_value = Decimal("0")
    for ln in po.lines.all():
        q = ln.qty or Decimal("0")
        r = ln.qty_received or Decimal("0")
        p = ln.unit_price or Decimal("0")
        po_qty += q
        recv_qty += r
        po_value += q * p
        recv_value += r * p

    # Prefer GRN document totals when present
    grn_value = Decimal("0")
    grn_qty = Decimal("0")
    grn_count = 0
    for grn in po.goods_receipts.filter(is_deleted=False, status="posted"):
        grn_count += 1
        for gl in grn.lines.all():
            grn_qty += gl.qty or Decimal("0")
            grn_value += (gl.qty or Decimal("0")) * (gl.unit_price or Decimal("0"))

    if grn_count:
        matched_recv_value = grn_value
        matched_recv_qty = grn_qty
    else:
        matched_recv_value = recv_value
        matched_recv_qty = recv_qty

    inv_amt = _d(invoice_amount) if invoice_amount is not None else None
    tol = Decimal(str(tolerance_pct)) / Decimal("100")

    issues = []
    if matched_recv_qty + Decimal("0.001") < po_qty:
        issues.append("partial_receipt")
    if matched_recv_qty > po_qty + Decimal("0.001"):
        issues.append("over_receipt")

    status = "matched"
    if inv_amt is not None:
        base = matched_recv_value if matched_recv_value > 0 else po_value
        variance = abs(inv_amt - base)
        allowed = (base * tol).quantize(Decimal("0.01"))
        if variance > allowed and variance >= Decimal("0.01"):
            issues.append("amount_variance")
            status = "variance"
        elif "partial_receipt" in issues:
            status = "partial"
        else:
            status = "matched"
    else:
        if "over_receipt" in issues:
            status = "over_receipt"
        elif "partial_receipt" in issues:
            status = "partial"
        elif matched_recv_qty <= 0:
            status = "no_receipt"
            issues.append("no_receipt")
        else:
            status = "matched"

    return {
        "ok": status == "matched",
        "status": status,
        "issues": issues,
        "tolerance_pct": tolerance_pct,
        "po_qty": str(po_qty),
        "received_qty": str(matched_recv_qty),
        "po_value": str(_d(po_value)),
        "received_value": str(_d(matched_recv_value)),
        "invoice_amount": str(inv_amt) if inv_amt is not None else None,
        "grn_count": grn_count,
        "detail": (
            "Three-way match OK"
            if status == "matched"
            else f"Match status: {status} ({', '.join(issues) or 'check values'})"
        ),
    }
