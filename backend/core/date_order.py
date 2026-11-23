"""Reject a later date that falls before its start date."""

from datetime import date, datetime

from django.core.exceptions import ValidationError

# Later field, earlier field, message shown on the later field.
PAIRS = (
    ("end_date", "start_date", "End date cannot be before the start date."),
    ("maturity_date", "start_date", "Comes back on cannot be before the start date."),
    ("review_period_end", "review_period_start", "Period end cannot be before the start date."),
    ("due_date", "invoice_date", "Due date cannot be before the start date."),
    ("period_end", "period_start", "Period end cannot be before the start date."),
    ("valid_until", "valid_from", "Valid until cannot be before the start date."),
    ("valid_until", "quote_date", "Valid until cannot be before the start date."),
    ("valid_until", "rfq_date", "Valid until cannot be before the start date."),
    ("expected_date", "order_date", "Expected date cannot be before the start date."),
    ("required_date", "request_date", "Required by cannot be before the start date."),
    ("expires_on", "issued_on", "Expires on cannot be before the start date."),
    ("disposal_date", "purchase_date", "Disposal date cannot be before the start date."),
)


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def enforce_date_order(sender, instance, **kwargs):
    from core.numeric_bounds import OUR_APPS

    if instance is None:
        return
    meta = getattr(instance, "_meta", None)
    if meta is None or meta.app_label not in OUR_APPS:
        return
    errors = {}
    for later, earlier, message in PAIRS:
        if not hasattr(instance, later) or not hasattr(instance, earlier):
            continue
        end = _as_date(getattr(instance, later, None))
        start = _as_date(getattr(instance, earlier, None))
        if start and end and end < start:
            errors[later] = message
    if errors:
        raise ValidationError(errors)
