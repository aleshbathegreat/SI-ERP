"""Platform staff roles and capability checks (enterprise SaaS ops)."""

from __future__ import annotations

PLATFORM_CAPS = {
    "overview": "Control center",
    "packages": "Subscription packages",
    "tenants": "Tenants",
    "tenants.extend": "Extend trial / subscription",
    "invoices": "SaaS invoices",
    "invoices.mark_paid": "Mark invoices paid",
    "smtp": "Platform SMTP",
    "payfast": "Platform PayFast",
    "domains": "Platform domains",
    "tickets": "Support tickets",
    "tickets.assign": "Assign tickets",
    "staff": "Manage platform staff",
}

ALL_CAPS = list(PLATFORM_CAPS.keys())

ROLE_CAPS: dict[str, list[str]] = {
    "owner": ALL_CAPS,
    "finance": [
        "overview",
        "packages",
        "tenants",
        "invoices",
        "invoices.mark_paid",
    ],
    "sales": [
        "overview",
        "packages",
        "tenants",
        "tenants.extend",
        "invoices",
    ],
    "support": [
        "overview",
        "tenants",
        "tickets",
        "tickets.assign",
    ],
    "technical": [
        "overview",
        "domains",
        "smtp",
        "payfast",
        "tickets",
    ],
}


def staff_record(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "platform_staff", None)


def platform_role(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return "owner"
    rec = staff_record(user)
    if rec and rec.is_active:
        return rec.role
    return None


def is_platform_user(user) -> bool:
    return platform_role(user) is not None


def platform_capabilities(user) -> list[str]:
    role = platform_role(user)
    if not role:
        return []
    return list(ROLE_CAPS.get(role, []))


def has_platform_cap(user, cap: str) -> bool:
    return cap in platform_capabilities(user)


class HasPlatformCap:
    """DRF permission — require a platform capability (or list, any-of)."""

    def __init__(self, *caps: str):
        self.caps = caps

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not self.caps:
            return is_platform_user(request.user)
        return any(has_platform_cap(request.user, c) for c in self.caps)


def require_platform_cap(user, *caps: str):
    """Return None if OK, else a Response-ready dict + status."""
    if not user or not user.is_authenticated:
        return {"detail": "Authentication required"}, 401
    if not caps:
        if not is_platform_user(user):
            return {"detail": "Platform staff only"}, 403
        return None
    if any(has_platform_cap(user, c) for c in caps):
        return None
    return {"detail": f"Requires platform capability: {', '.join(caps)}"}, 403
