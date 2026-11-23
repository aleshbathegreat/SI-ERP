"""FBR / PRAL e-invoice payload builder + submit (sandbox when FBR_API_URL is unset)."""

from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal
from urllib import error as urlerror
from urllib import request as urlrequest

from django.conf import settings
from django.utils import timezone

from finance.models import CustomerInvoice, EInvoiceSubmission

log = logging.getLogger(__name__)

SUBMITTABLE = {
    EInvoiceSubmission.FbrStatus.DRAFT,
    EInvoiceSubmission.FbrStatus.PENDING,
    EInvoiceSubmission.FbrStatus.REJECTED,
}


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def _q(v: Decimal) -> str:
    return str(_d(v).quantize(Decimal("0.01")))


def build_payload(inv: CustomerInvoice) -> dict:
    """PK-style (PRAL DI) invoice payload with NTN/STRN placeholders from org settings."""
    org = inv.organization
    cust = inv.customer
    amount = _d(inv.amount)
    tax = _d(inv.tax_amount)
    rate_pct = (tax / amount * Decimal("100")) if amount > 0 else Decimal("0")

    items: list[dict] = []
    so = inv.sales_order
    so_lines = list(so.lines.select_related("item")) if so else []
    if so_lines:
        sub = sum((_d(ln.qty) * _d(ln.unit_price) for ln in so_lines), Decimal("0"))
        for ln in so_lines:
            value = _d(ln.qty) * _d(ln.unit_price)
            # Pro-rate invoice tax over lines by value when line-level tax is unknown
            line_tax = (tax * value / sub) if sub > 0 else Decimal("0")
            items.append(
                {
                    "hsCode": getattr(ln.item, "hs_code", "") or "",
                    "productDescription": (ln.description or ln.item.name)[:255],
                    "sku": ln.item.sku,
                    "quantity": str(ln.qty),
                    "uoM": ln.item.unit or "ea",
                    "rate": f"{rate_pct.quantize(Decimal('0.01'))}%",
                    "valueSalesExcludingST": _q(value),
                    "salesTaxApplicable": _q(line_tax),
                    "totalValues": _q(value + line_tax),
                }
            )
    else:
        items.append(
            {
                "hsCode": "",
                "productDescription": (inv.description or f"Invoice {inv.invoice_no}")[:255],
                "quantity": "1",
                "uoM": "ea",
                "rate": f"{rate_pct.quantize(Decimal('0.01'))}%",
                "valueSalesExcludingST": _q(amount),
                "salesTaxApplicable": _q(tax),
                "totalValues": _q(amount + tax),
            }
        )

    warnings = []
    if not (org.ntn or "").strip():
        warnings.append("Seller NTN missing in organization settings")
    if not (org.strn or "").strip():
        warnings.append("Seller STRN missing in organization settings")
    if not (cust.ntn or "").strip():
        warnings.append("Buyer NTN missing (will be sent as Unregistered)")

    return {
        "invoiceType": "Sale Invoice",
        "invoiceDate": inv.invoice_date.isoformat() if inv.invoice_date else "",
        "invoiceRefNo": inv.invoice_no,
        "currency": getattr(inv, "currency", "PKR") or "PKR",
        "seller": {
            "ntn": (org.ntn or "").strip() or "NTN-NOT-SET",
            "strn": (org.strn or "").strip() or "STRN-NOT-SET",
            "businessName": org.name,
            "address": org.address or "",
        },
        "buyer": {
            "ntn": (cust.ntn or "").strip(),
            "businessName": cust.name,
            "address": cust.address or "",
            "registrationType": "Registered" if (cust.ntn or "").strip() else "Unregistered",
        },
        "items": items,
        "summary": {
            "lineCount": len(items),
            "valueExcludingST": _q(amount),
            "salesTax": _q(tax),
            "grandTotal": _q(amount + tax),
        },
        "warnings": warnings,
    }


def ensure_draft_submission(inv: CustomerInvoice) -> EInvoiceSubmission | None:
    """Create a draft EInvoiceSubmission for a posted/approved AR invoice (idempotent)."""
    existing = EInvoiceSubmission.objects.filter(
        organization_id=inv.organization_id, ar_invoice=inv, is_deleted=False
    ).first()
    if existing:
        return existing
    try:
        payload = build_payload(inv)
    except Exception:  # never block invoice approval
        log.exception("e-invoice payload build failed for invoice %s", inv.pk)
        payload = {}
    return EInvoiceSubmission.objects.create(
        organization_id=inv.organization_id,
        ar_invoice=inv,
        fbr_status=EInvoiceSubmission.FbrStatus.DRAFT,
        payload_json=payload,
        mode="sandbox" if not getattr(settings, "FBR_API_URL", "") else "live",
        created_by=getattr(inv, "approved_by", None) or inv.updated_by or inv.created_by,
    )


def submit_einvoice(sub: EInvoiceSubmission, *, user=None) -> EInvoiceSubmission:
    """
    Rebuild payload and submit. With FBR_API_URL set → POST to the provider.
    Otherwise sandbox: nothing leaves the system; status=submitted with
    provider_ref=sandbox:{uuid} and payload/response stored.
    """
    if sub.fbr_status not in SUBMITTABLE:
        raise ValueError(f"Cannot submit from status '{sub.fbr_status}'.")
    payload = build_payload(sub.ar_invoice)
    sub.payload_json = payload
    now = timezone.now()
    url = (getattr(settings, "FBR_API_URL", "") or "").strip()

    if not url:
        ref = f"sandbox:{uuid.uuid4()}"
        sub.mode = "sandbox"
        sub.provider_ref = ref
        sub.fbr_status = EInvoiceSubmission.FbrStatus.SUBMITTED
        sub.error_message = ""
        sub.submitted_at = now
        sub.response_json = {
            "mode": "sandbox",
            "transmitted": False,
            "provider_ref": ref,
            "message": "FBR_API_URL not configured; payload stored locally only.",
            "received_at": now.isoformat(),
        }
    else:
        sub.mode = "live"
        token = (getattr(settings, "FBR_API_TOKEN", "") or "").strip()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urlrequest.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        timeout = int(getattr(settings, "FBR_TIMEOUT", 20))
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", errors="replace")
                status_code = resp.status
            try:
                body = json.loads(raw) if raw else {}
            except ValueError:
                body = {"raw": raw[:2000]}
            sub.response_json = {"http_status": status_code, "body": body}
            sub.fbr_invoice_no = str(
                body.get("invoiceNumber") or body.get("fbr_invoice_no") or ""
            )[:64]
            sub.provider_ref = str(
                body.get("reference") or body.get("id") or sub.fbr_invoice_no or ""
            )[:128]
            sub.fbr_status = (
                EInvoiceSubmission.FbrStatus.ACCEPTED
                if sub.fbr_invoice_no
                else EInvoiceSubmission.FbrStatus.SUBMITTED
            )
            sub.error_message = ""
            sub.submitted_at = now
        except urlerror.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:2000]
            sub.fbr_status = EInvoiceSubmission.FbrStatus.REJECTED
            sub.error_message = f"HTTP {e.code}: {detail}"
            sub.response_json = {"http_status": e.code, "body": detail}
        except Exception as e:  # network / timeout
            sub.fbr_status = EInvoiceSubmission.FbrStatus.REJECTED
            sub.error_message = str(e)[:2000]
            sub.response_json = {"error": str(e)}
    if user:
        sub.updated_by = user
    sub.save()
    return sub
