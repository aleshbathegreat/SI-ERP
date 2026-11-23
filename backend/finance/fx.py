"""FX helpers (light): rate lookup + conversion using FxRate rows."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finance.models import FxRate


def get_rate(org, from_ccy: str, to_ccy: str, on_date: date | None = None) -> Decimal | None:
    """
    Latest FxRate on or before `on_date` for from→to. Falls back to the inverse of
    to→from. Returns Decimal(1) for same currency, None when no rate is known.
    """
    f = (from_ccy or "").strip().upper()
    t = (to_ccy or "").strip().upper()
    if not f or not t or f == t:
        return Decimal("1")
    on_date = on_date or date.today()
    base = FxRate.objects.filter(
        organization=org, is_deleted=False, rate_date__lte=on_date
    )
    direct = base.filter(currency_from=f, currency_to=t).order_by("-rate_date", "-id").first()
    if direct and Decimal(str(direct.rate)) > 0:
        return Decimal(str(direct.rate))
    inverse = base.filter(currency_from=t, currency_to=f).order_by("-rate_date", "-id").first()
    if inverse and Decimal(str(inverse.rate)) > 0:
        return (Decimal("1") / Decimal(str(inverse.rate))).quantize(Decimal("0.00000001"))
    return None


def convert(org, amount, from_ccy: str, to_ccy: str, on_date: date | None = None) -> Decimal:
    rate = get_rate(org, from_ccy, to_ccy, on_date)
    if rate is None:
        raise ValueError(f"No FX rate for {from_ccy}→{to_ccy} on or before {on_date or date.today()}")
    return (Decimal(str(amount or 0)) * rate).quantize(Decimal("0.01"))


def invoice_base_rate(invoice, org, *, refresh: bool = False) -> Decimal:
    """
    Rate to convert invoice-currency amounts into org base currency.
    Looks up FxRate on first accrual (or refresh) and stores it on the invoice.
    """
    base = (getattr(org, "currency", "") or "PKR").upper()
    ccy = (getattr(invoice, "currency", "") or base).upper()
    if ccy == base:
        return Decimal("1")
    stored = Decimal(str(getattr(invoice, "fx_rate", 1) or 1))
    if not refresh and stored > 0 and stored != Decimal("1"):
        return stored
    on = getattr(invoice, "invoice_date", None)
    rate = get_rate(org, ccy, base, on)
    if rate is None:
        raise ValueError(f"No FX rate for {ccy}→{base}; add one under Finance → FX rates.")
    invoice.fx_rate = rate
    invoice.save(update_fields=["fx_rate", "updated_at"])
    return rate
