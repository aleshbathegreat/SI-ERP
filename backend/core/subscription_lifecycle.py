"""Expire trials/subscriptions, dunning notices, overdue invoices."""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from core.access import effective_end_date, grace_deadline, subscription_open
from core.invoicing import mark_overdue_invoices
from core.models import Organization

# Warn N days before end, plus on the end day (required).
PREWARN_DAYS = (7, 3, 1)


def sync_org_plan_status(org: Organization, *, today: date | None = None) -> str:
    """Reconcile plan_status from dates. Returns action label."""
    today = today or date.today()
    if org.plan_status == Organization.PlanStatus.CANCELED:
        return "skipped_canceled"
    end = effective_end_date(org)
    if end is None:
        # No end date → hard-lock (trials/subscriptions must expire).
        if org.plan_status != Organization.PlanStatus.CANCELED:
            org.plan_status = Organization.PlanStatus.CANCELED
            org.save(update_fields=["plan_status", "updated_at"])
            return "canceled_no_end_date"
        return "no_end_date"
    if end >= today:
        if org.plan_status != Organization.PlanStatus.ACTIVE:
            org.plan_status = Organization.PlanStatus.ACTIVE
            org.save(update_fields=["plan_status", "updated_at"])
            return "reactivated"
        return "ok_active"
    deadline = grace_deadline(org)
    if deadline and deadline >= today:
        if org.plan_status != Organization.PlanStatus.PAST_DUE:
            org.plan_status = Organization.PlanStatus.PAST_DUE
            org.save(update_fields=["plan_status", "updated_at"])
            return "marked_past_due"
        return "ok_past_due"
    org.plan_status = Organization.PlanStatus.CANCELED
    org.save(update_fields=["plan_status", "updated_at"])
    return "canceled"


def _should_send_expiry_mail(org: Organization, today: date, cooldown_hours: int) -> bool:
    end = effective_end_date(org)
    if not end:
        return False
    # Always attempt on the exact end day (trial/subscription end warning required).
    if end == today:
        last = org.last_dunning_at
        if last and last.date() == today:
            return False
        return True
    # Pre-warn windows + through grace
    days_left = (end - today).days
    in_prewarn = days_left in PREWARN_DAYS
    in_grace = end < today and today <= (grace_deadline(org) or end)
    if not (in_prewarn or in_grace):
        return False
    last = org.last_dunning_at
    if not last:
        return True
    return (timezone.now() - last).total_seconds() >= cooldown_hours * 3600


def _send_dunning(org: Organization, *, today: date | None = None) -> bool:
    """Best-effort expiry reminder via platform SMTP (soft-fail if not configured)."""
    today = today or date.today()
    try:
        from core.mailer import send_platform_email
    except Exception:
        return False
    to = org.email or (org.owner.email if org.owner_id else "")
    if not to:
        return False
    end = effective_end_date(org)
    open_now = subscription_open(org)
    is_trial = org.plan == Organization.Plan.TRIAL
    kind = "trial" if is_trial else "subscription"
    days_left = (end - today).days if end else None

    if end and end == today:
        subject = f"SI-ERP {kind} ended today · {org.brand_name or org.name}"
        lead = (
            f"Your free trial for {org.name} ended today ({end.isoformat()})."
            if is_trial
            else f"Your subscription for {org.name} ended today ({end.isoformat()})."
        )
    elif end and days_left is not None and days_left > 0:
        subject = (
            f"SI-ERP {kind} ends in {days_left} day(s) · {org.brand_name or org.name}"
        )
        lead = (
            f"Your free trial for {org.name} ends on {end.isoformat()} "
            f"({days_left} day(s) remaining)."
            if is_trial
            else f"Your subscription for {org.name} ends on {end.isoformat()} "
            f"({days_left} day(s) remaining)."
        )
    else:
        subject = f"SI-ERP {kind} notice · {org.brand_name or org.name}"
        lead = (
            f"Your free trial for {org.name} has expired."
            if is_trial
            else f"Your subscription for {org.name} has expired."
        )

    body = (
        f"Hello,\n\n"
        f"{lead}\n\n"
        f"Tenant: {org.name} ({org.code})\n"
        f"Plan: {org.plan} · status: {org.plan_status}\n"
        f"Period end: {end}\n"
        f"Access open: {'yes' if open_now else 'no (renew on Billing)'}\n\n"
        f"Please renew at your SI-ERP Billing page to avoid interruption.\n"
    )
    try:
        ok = send_platform_email(subject, body, [to])
        if ok:
            org.last_dunning_at = timezone.now()
            org.save(update_fields=["last_dunning_at", "updated_at"])
        return bool(ok)
    except Exception:
        return False


def run_expiry_pass(*, send_mail: bool = True, dunning_cooldown_hours: int = 48) -> dict:
    """
    Daily job: mark past_due / canceled, overdue invoices, optional dunning emails.
    Soft-fails email when SMTP is not configured.
    """
    today = date.today()
    stats = {
        "checked": 0,
        "past_due": 0,
        "canceled": 0,
        "reactivated": 0,
        "dunning_sent": 0,
        "invoices_overdue": 0,
    }
    for org in Organization.objects.filter(is_active=True).exclude(
        plan_status=Organization.PlanStatus.CANCELED
    ):
        stats["checked"] += 1
        action = sync_org_plan_status(org, today=today)
        if action == "marked_past_due":
            stats["past_due"] += 1
        elif action in ("canceled", "canceled_no_end_date"):
            stats["canceled"] += 1
        elif action == "reactivated":
            stats["reactivated"] += 1

        if send_mail and _should_send_expiry_mail(org, today, dunning_cooldown_hours):
            if _send_dunning(org, today=today):
                stats["dunning_sent"] += 1

    stats["invoices_overdue"] = mark_overdue_invoices()
    return stats
