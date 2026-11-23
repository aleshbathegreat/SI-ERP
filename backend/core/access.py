from datetime import date, timedelta
from decimal import Decimal

from core.models import Organization, SubscriptionPackage

MODULE_KEYS = [
    "dashboard",
    "finance",
    "hr",
    "payroll",
    "billing",
]

PACKAGE_SUMMARIES = {
    "trial": "14-day full ERP trial. Finance, HR and Payroll included.",
    "monthly": "Billed monthly. Full Finance, HR and Payroll SaaS access.",
    "annual": "Billed yearly (2 months included). Full ERP module access.",
}


def _full_assignable_modules():
    from accounts.rbac import ASSIGNABLE_MODULE_KEYS, CORE_MODULE_KEYS

    return list(ASSIGNABLE_MODULE_KEYS), list(CORE_MODULE_KEYS)


def ensure_default_packages():
    from accounts.rbac import ASSIGNABLE_MODULE_KEYS, CORE_MODULE_KEYS

    assignable = list(ASSIGNABLE_MODULE_KEYS)
    core = list(CORE_MODULE_KEYS)
    trial_connectors = [
        "zkteco_adms",
        "essl_biomax",
        "generic_webhook",
        "generic_csv",
    ]
    # name, code, price, interval, sort, max_fu, max_ess, max_devices, connectors
    defaults = [
        (
            "Trial",
            "trial",
            Decimal("0"),
            SubscriptionPackage.Interval.TRIAL,
            0,
            10,
            25,
            2,
            trial_connectors,
        ),
        (
            "Monthly",
            "monthly",
            Decimal("7500"),
            SubscriptionPackage.Interval.MONTH,
            1,
            10,
            50,
            10,
            ["*"],
        ),
        (
            "Annual",
            "annual",
            Decimal("75000"),
            SubscriptionPackage.Interval.YEAR,
            2,
            25,
            200,
            50,
            ["*"],
        ),
    ]
    for name, code, price, interval, sort, max_fu, max_ess, max_dev, connectors in defaults:
        SubscriptionPackage.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "price": price,
                "interval": interval,
                "summary": PACKAGE_SUMMARIES[code],
                "module_keys": assignable,
                "core_module_keys": core,
                "max_functional_users": max_fu,
                "max_ess_users": max_ess,
                "max_attendance_devices": max_dev,
                "attendance_connectors": connectors,
                "active": True,
                "sort": sort,
            },
        )


def sellable_packages():
    ensure_default_packages()
    return SubscriptionPackage.objects.filter(active=True).exclude(code="trial")


def effective_end_date(org: Organization | None) -> date | None:
    if org is None:
        return None
    if org.plan == Organization.Plan.TRIAL:
        return org.trial_ends
    return org.subscription_ends


def grace_deadline(org: Organization) -> date | None:
    end = effective_end_date(org)
    if not end:
        return None
    days = int(getattr(org, "grace_days", 7) or 0)
    return end + timedelta(days=days)


def subscription_open(org: Organization | None) -> bool:
    """True while paid/trial period or grace window remains (not canceled)."""
    if org is None:
        return False
    if org.plan_status == Organization.PlanStatus.CANCELED:
        return False
    if not org.is_active:
        return False
    today = date.today()
    end = effective_end_date(org)
    # Trials (and paid plans) require an end date — no open-ended access.
    if end is None:
        return False
    if end >= today:
        return True
    deadline = grace_deadline(org)
    return bool(deadline and deadline >= today)


def subscription_closed_message(org: Organization | None) -> str:
    """Clear user-facing reason when a tenant is locked."""
    if org is None:
        return "No organization is linked to this account."
    if not org.is_active:
        return "This organization has been deactivated. Contact platform support."
    if org.plan_status == Organization.PlanStatus.CANCELED:
        if org.plan == Organization.Plan.TRIAL:
            return "Your free trial has ended and access is locked. Renew on Billing or contact sales."
        return "Your subscription is canceled and access is locked. Renew on Billing to reopen the ERP."
    end = effective_end_date(org)
    if end is None:
        if org.plan == Organization.Plan.TRIAL:
            return "This trial has no end date configured and access is locked. Contact platform support."
        return "This subscription has no end date configured and access is locked. Contact platform support."
    if org.plan == Organization.Plan.TRIAL:
        return (
            f"Your free trial ended on {end.isoformat()}. "
            "Renew on Billing to reopen the ERP, or contact your administrator."
        )
    return (
        f"Your subscription ended on {end.isoformat()}. "
        "Renew on Billing to reopen the ERP."
    )


def subscription_in_grace(org: Organization | None) -> bool:
    if org is None or not subscription_open(org):
        return False
    end = effective_end_date(org)
    today = date.today()
    return bool(end and end < today)


def days_until_lock(org: Organization | None) -> int | None:
    if org is None:
        return None
    deadline = grace_deadline(org) if effective_end_date(org) else None
    if not deadline:
        end = effective_end_date(org)
        if not end:
            return None
        return (end - date.today()).days
    return (deadline - date.today()).days


def is_owner(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    profile = getattr(user, "profile", None)
    org = getattr(profile, "organization", None) if profile else None
    return bool(org and org.owner_id == user.id)


def user_organization(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "organization", None) if profile else None


def start_trial(org: Organization, days: int = 14):
    ensure_default_packages()
    pkg = SubscriptionPackage.objects.filter(code="trial").first()
    org.plan = Organization.Plan.TRIAL
    org.plan_status = Organization.PlanStatus.ACTIVE
    org.trial_ends = date.today() + timedelta(days=days)
    org.package = pkg
    org.save(
        update_fields=["plan", "plan_status", "trial_ends", "package", "updated_at"]
    )


def extend_subscription(org: Organization, days: int, *, as_trial: bool | None = None):
    """Platform sales/owner: push trial or paid end date forward."""
    today = date.today()
    days = max(1, int(days))
    use_trial = as_trial if as_trial is not None else org.plan == Organization.Plan.TRIAL
    if use_trial:
        base = org.trial_ends if org.trial_ends and org.trial_ends > today else today
        org.trial_ends = base + timedelta(days=days)
        org.plan = Organization.Plan.TRIAL
        org.plan_status = Organization.PlanStatus.ACTIVE
        org.save(
            update_fields=["trial_ends", "plan", "plan_status", "updated_at"]
        )
    else:
        base = (
            org.subscription_ends
            if org.subscription_ends and org.subscription_ends > today
            else today
        )
        org.subscription_ends = base + timedelta(days=days)
        org.plan_status = Organization.PlanStatus.ACTIVE
        if org.plan == Organization.Plan.TRIAL:
            org.plan = Organization.Plan.MONTHLY
        org.save(
            update_fields=["subscription_ends", "plan", "plan_status", "updated_at"]
        )
    return org


def add_period(start: date, interval: str) -> date:
    if interval == SubscriptionPackage.Interval.YEAR:
        return start + timedelta(days=365)
    if interval == SubscriptionPackage.Interval.TRIAL:
        return start + timedelta(days=14)
    return start + timedelta(days=30)


def payment_kind(org: Organization, plan_code: str) -> str:
    from core.models import SubscriptionPayment

    if org.plan == Organization.Plan.TRIAL or not org.subscription_ends:
        return SubscriptionPayment.Kind.NEW
    if org.package_id and org.package and org.package.code != plan_code:
        return SubscriptionPayment.Kind.UPGRADE
    return SubscriptionPayment.Kind.RENEWAL


def cover_dates(org: Organization, plan_code: str, kind: str):
    ensure_default_packages()
    pkg = SubscriptionPackage.objects.filter(code=plan_code).first()
    today = date.today()
    interval = pkg.interval if pkg else SubscriptionPackage.Interval.MONTH
    if (
        kind == "renewal"
        and org.subscription_ends
        and org.subscription_ends >= today
    ):
        start = org.subscription_ends
    else:
        start = today
    return start, add_period(start, interval), pkg


def activate_paid_plan(org: Organization, plan_code: str, kind: str | None = None):
    ensure_default_packages()
    kind = kind or payment_kind(org, plan_code)
    start, ends, pkg = cover_dates(org, plan_code, kind)
    if not pkg:
        raise ValueError("Unknown plan")
    plan = (
        Organization.Plan.ANNUAL
        if pkg.interval == SubscriptionPackage.Interval.YEAR
        else Organization.Plan.MONTHLY
    )
    org.plan = plan
    org.plan_status = Organization.PlanStatus.ACTIVE
    org.subscription_ends = ends
    org.package = pkg
    org.save(
        update_fields=[
            "plan",
            "plan_status",
            "subscription_ends",
            "package",
            "updated_at",
        ]
    )
    return org, start, ends
