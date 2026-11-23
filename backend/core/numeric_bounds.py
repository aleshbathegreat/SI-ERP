"""Reject out-of-range numbers on save. Signed fields stay signed."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models

OUR_APPS = {
    "accounts",
    "contracts",
    "core",
    "crm",
    "dms",
    "finance",
    "hr",
    "integrations",
    "mfg",
    "ops",
    "payroll",
    "projects",
    "qms",
    "service",
}

YEAR_FIELDS = {"fiscal_year", "year", "period_year"}
MONTH_FIELDS = {"month", "period_month"}
YEAR_MIN, YEAR_MAX = 2000, 2100
PERCENT_FIELDS = {
    "rate_percent",
    "income_tax_rate",
    "provident_fund_rate",
    "employer_pf_rate",
    "depreciation_rate",
    "probability",
}
# Balances and stock movements are signed on purpose.
ALLOW_NEGATIVE = {
    ("finance", "bankstatementline", "amount"),
    ("finance", "bankreconciliation", "statement_balance"),
    ("finance", "bankreconciliation", "book_balance"),
    ("finance", "bankaccount", "opening_balance"),
    ("finance", "bankaccount", "current_balance"),
    ("hr", "finalsettlement", "net_payable"),
    ("ops", "stockmovement", "qty"),
}
POSITIVE_RATE = {
    ("finance", "fxrate", "rate"),
    ("finance", "vendorinvoice", "fx_rate"),
    ("finance", "customerinvoice", "fx_rate"),
}


def bounds_for(app_label: str, model_name: str, field_name: str):
    """Return (minimum, maximum). None means no bound on that side."""
    key = (app_label, model_name, field_name)
    if field_name in YEAR_FIELDS:
        return YEAR_MIN, YEAR_MAX
    if field_name in MONTH_FIELDS:
        return 1, 12
    if field_name == "port":
        return 1, 65535
    if key in ALLOW_NEGATIVE:
        return None, None
    if field_name in PERCENT_FIELDS:
        return 0, 100
    if key in POSITIVE_RATE:
        return Decimal("0.00000001"), None
    return 0, None


def _number(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def collect_numeric_errors(instance) -> dict:
    opts = instance._meta
    if opts.app_label not in OUR_APPS:
        return {}
    errors = {}
    for field in opts.concrete_fields:
        if field.primary_key or getattr(field, "is_relation", False) or not field.editable:
            continue
        if not isinstance(field, (models.DecimalField, models.IntegerField, models.FloatField)):
            continue
        number = _number(getattr(instance, field.attname, None))
        if number is None:
            continue
        low, high = bounds_for(opts.app_label, opts.model_name, field.name)
        label = str(field.verbose_name or field.name).replace("_", " ")
        if low is not None and number < low:
            if field.name in YEAR_FIELDS:
                errors[field.name] = f"Must be between {YEAR_MIN} and {YEAR_MAX}."
            elif field.name in MONTH_FIELDS:
                errors[field.name] = "Must be between 1 and 12."
            elif low == 0:
                errors[field.name] = f"{label[:1].upper()}{label[1:]} cannot be negative."
            else:
                errors[field.name] = f"{label[:1].upper()}{label[1:]} must be at least {low}."
        elif high is not None and number > high:
            if field.name in YEAR_FIELDS:
                errors[field.name] = f"Must be between {YEAR_MIN} and {YEAR_MAX}."
            elif field.name in PERCENT_FIELDS:
                errors[field.name] = f"{label[:1].upper()}{label[1:]} cannot be more than 100."
            else:
                errors[field.name] = f"{label[:1].upper()}{label[1:]} cannot be more than {high}."
    return errors


def enforce_numeric_bounds(sender, instance, **kwargs):
    errors = collect_numeric_errors(instance)
    if errors:
        raise ValidationError(errors)
