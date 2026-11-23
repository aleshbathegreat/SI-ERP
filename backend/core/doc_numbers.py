"""Org-scoped sequential document numbers (PO, invoice, SO, loan, etc.)."""

from __future__ import annotations

from datetime import date

from django.db import transaction


KIND_PREFIX = {
    "invoice": "AP",
    "ar_invoice": "AR",
    "po": "PO",
    "so": "SO",
    "quote": "QT",
    "grn": "GRN",
    "loan": "LN",
    "challan": "CH",
    "asset": "FA",
    "journal": "JE",
    "item": "SKU",
    "customer": "CUS",
    "vendor": "VEN",
    "warehouse": "WH",
    "wo": "WO",
    "contract": "CT",
    "rfq": "RFQ",
    "rma": "RMA",
    "dn": "DN",
    "pr": "PR",
    "pick": "PICK",
    "case": "CS",
    "mwo": "MWO",
    "ncr": "NCR",
    "qi": "QI",
    "gl": "GL",
    "at": "AT",
    "cc": "CC",
    "dep": "DEP",
    "des": "DES",
    "sh": "SH",
    "lt": "LT",
    "ben": "BEN",
    "trn": "TRN",
    "doc": "DOC",
    "ss": "SS",
    "tax": "TAX",
    "prj": "PRJ",
    "ic": "IC",
    "bom": "BOM",
    "bin": "BIN",
    "pl": "PL",
}


def _next_from_series(org, *, kind: str) -> str | None:
    """Allocate next number from DocNumberSeries if configured; else None."""
    if org is None:
        return None
    try:
        from core.models import DocNumberSeries
    except Exception:
        return None

    kind_key = (kind or "").lower().strip()
    if not kind_key:
        return None

    with transaction.atomic():
        series = (
            DocNumberSeries.objects.select_for_update()
            .filter(organization=org, kind=kind_key)
            .first()
        )
        if series is None:
            return None
        seq = int(series.next_number or 1)
        pad = max(1, int(series.padding or 5))
        prefix = (series.prefix or "").strip() or KIND_PREFIX.get(
            kind_key, kind_key.upper()[:6]
        )
        if series.reset_yearly:
            year = date.today().year
            doc = f"{prefix}-{year}-{seq:0{pad}d}"
        else:
            doc = f"{prefix}-{seq:0{pad}d}"
        series.next_number = seq + 1
        series.save(update_fields=["next_number", "updated_at"])
        return doc


def next_doc_no(org, *, kind: str, model=None, field: str = "", width: int = 5) -> str:
    """
    Return next number like PO-2026-00042 for the organization.
    Prefers DocNumberSeries when present; otherwise scans existing values.
    """
    from_series = _next_from_series(org, kind=kind)
    if from_series:
        return from_series

    prefix_code = KIND_PREFIX.get((kind or "").lower(), (kind or "DOC").upper()[:6])
    year = date.today().year
    prefix = f"{prefix_code}-{year}-"
    seq = 1
    if model is not None and field and org is not None:
        lookup = {f"{field}__istartswith": prefix}
        qs = model.objects.filter(organization=org, **lookup)
        # Soft-deleted rows may still hold numbers — use all_objects when present
        manager = getattr(model, "all_objects", None)
        if manager is not None:
            qs = manager.filter(organization=org, **lookup)
        last = qs.order_by(f"-{field}").values_list(field, flat=True).first()
        if last:
            try:
                seq = int(str(last).split("-")[-1]) + 1
            except ValueError:
                seq = (qs.count() or 0) + 1
    return f"{prefix}{seq:0{width}d}"


def ensure_doc_no(validated_data: dict, field: str, org, *, kind: str, model) -> None:
    """Fill blank document number in serializer validated_data."""
    current = (validated_data.get(field) or "").strip()
    if current:
        return
    validated_data[field] = next_doc_no(org, kind=kind, model=model, field=field)
