"""Build TaxReturn lines/totals from AR/AP invoices and tax challans."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from finance.models import (
    CustomerInvoice,
    TaxChallan,
    TaxCode,
    TaxReturn,
    TaxReturnLine,
    VendorInvoice,
)

_ST_TYPES = ("sales_tax", "st", "gst", "vat")
_CHALLAN_TYPES = {
    TaxReturn.ReturnType.SALES_TAX: ("sales_tax", "st", "gst", "vat"),
    TaxReturn.ReturnType.WHT: ("wht",),
}


def _d(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


def _default_code(org, return_type: str) -> str:
    types = _ST_TYPES if return_type == TaxReturn.ReturnType.SALES_TAX else ("wht",)
    tc = (
        TaxCode.objects.filter(organization=org, is_active=True, tax_type__in=types)
        .order_by("code")
        .first()
    )
    if tc:
        return tc.code
    return "ST" if return_type == TaxReturn.ReturnType.SALES_TAX else "WHT"


def _period_label_in_range(label: str, start: date, end: date) -> bool:
    try:
        y, m = int(label[:4]), int(label[5:7])
        first = date(y, m, 1)
    except (ValueError, TypeError, IndexError):
        return False
    return start <= first <= end or (start.year == y and start.month == m)


@transaction.atomic
def rebuild_tax_return(tr: TaxReturn) -> TaxReturn:
    """Replace lines + totals from source documents for the return's period."""
    if tr.status == TaxReturn.Status.FILED:
        raise ValueError("Filed returns cannot be regenerated.")
    org = tr.organization
    tr.lines.all().delete()
    code = _default_code(org, tr.return_type)
    lines: list[TaxReturnLine] = []
    notes: list[str] = []

    if tr.return_type == TaxReturn.ReturnType.SALES_TAX:
        qs = CustomerInvoice.objects.filter(
            organization=org,
            is_deleted=False,
            invoice_date__gte=tr.period_start,
            invoice_date__lte=tr.period_end,
            status__in=["approved", "paid"],
            tax_amount__gt=0,
        ).select_related("customer")
        for inv in qs.order_by("invoice_date", "id"):
            rate = Decimal(str(getattr(inv, "fx_rate", 1) or 1))
            lines.append(
                TaxReturnLine(
                    tax_return=tr,
                    line_type=TaxReturnLine.LineType.CHARGE,
                    description=f"Output tax · {inv.invoice_no} · {inv.customer.name}",
                    tax_code=code,
                    taxable_amount=_d(Decimal(str(inv.amount or 0)) * rate),
                    tax_amount=_d(Decimal(str(inv.tax_amount or 0)) * rate),
                    source_type="customer_invoice",
                    source_id=inv.id,
                    source_ref=inv.invoice_no,
                )
            )
        notes.append("Input tax is not captured on AP invoices; output tax only.")
    else:
        qs = VendorInvoice.objects.filter(
            organization=org,
            is_deleted=False,
            invoice_date__gte=tr.period_start,
            invoice_date__lte=tr.period_end,
            status__in=["approved", "paid", "submitted"],
            wht_amount__gt=0,
        ).select_related("vendor")
        for inv in qs.order_by("invoice_date", "id"):
            rate = Decimal(str(getattr(inv, "fx_rate", 1) or 1))
            lines.append(
                TaxReturnLine(
                    tax_return=tr,
                    line_type=TaxReturnLine.LineType.CHARGE,
                    description=f"WHT · {inv.invoice_no} · {inv.vendor.name}",
                    tax_code=code,
                    taxable_amount=_d(Decimal(str(inv.amount or 0)) * rate),
                    tax_amount=_d(Decimal(str(inv.wht_amount or 0)) * rate),
                    source_type="vendor_invoice",
                    source_id=inv.id,
                    source_ref=inv.invoice_no,
                )
            )

    for ch in TaxChallan.objects.filter(
        organization=org,
        is_deleted=False,
        tax_type__in=_CHALLAN_TYPES[tr.return_type],
    ).order_by("challan_no"):
        if not _period_label_in_range(ch.period_label or "", tr.period_start, tr.period_end):
            continue
        lines.append(
            TaxReturnLine(
                tax_return=tr,
                line_type=TaxReturnLine.LineType.DEPOSIT,
                description=f"Challan {ch.challan_no} ({ch.status})",
                tax_code=code,
                taxable_amount=0,
                tax_amount=_d(ch.amount),
                source_type="tax_challan",
                source_id=ch.id,
                source_ref=ch.challan_no,
            )
        )

    TaxReturnLine.objects.bulk_create(lines)
    charge = sum(
        (l.tax_amount for l in lines if l.line_type == TaxReturnLine.LineType.CHARGE),
        Decimal("0"),
    )
    deposit = sum(
        (l.tax_amount for l in lines if l.line_type == TaxReturnLine.LineType.DEPOSIT),
        Decimal("0"),
    )
    taxable = sum(
        (l.taxable_amount for l in lines if l.line_type == TaxReturnLine.LineType.CHARGE),
        Decimal("0"),
    )
    tr.totals = {
        "taxable_total": str(taxable),
        "tax_total": str(charge),
        "deposited": str(deposit),
        "net_payable": str(charge - deposit),
        "document_count": sum(
            1 for l in lines if l.line_type == TaxReturnLine.LineType.CHARGE
        ),
        "challan_count": sum(
            1 for l in lines if l.line_type == TaxReturnLine.LineType.DEPOSIT
        ),
        "notes": notes,
    }
    tr.save(update_fields=["totals", "updated_at"])
    return tr
