"""Subscription hard-gate inspired by desk SubscriptionGateMiddleware."""

from django.http import JsonResponse

from core.access import (
    is_owner,
    subscription_closed_message,
    subscription_open,
    user_organization,
)
from core.platform_rbac import is_platform_user

_OPEN_PREFIXES = (
    "/admin/",
    "/api/auth/",
    "/api/public/",
    "/api/saas/plans/",
    "/api/saas/signup/",
    "/api/schema/",
    "/api/docs/",
    "/api/health/",
    "/static/",
    "/media/",
)


class SubscriptionGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or "/"
        if any(path.startswith(p) for p in _OPEN_PREFIXES):
            return self.get_response(request)
        if not path.startswith("/api/"):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        if is_platform_user(user):
            return self.get_response(request)

        # Allow billing / invoices / support when closed (renew + escalate)
        if path.startswith("/api/saas/billing"):
            return self.get_response(request)
        if path.startswith("/api/saas/invoices"):
            return self.get_response(request)
        if path.startswith("/api/support/tickets"):
            return self.get_response(request)
        if path.startswith("/api/notifications"):
            return self.get_response(request)
        if path.startswith("/api/platform/"):
            return self.get_response(request)

        org = user_organization(user)
        if org is None:
            return self.get_response(request)

        try:
            from core.subscription_lifecycle import sync_org_plan_status

            sync_org_plan_status(org)
            org.refresh_from_db()
        except Exception:
            pass

        if subscription_open(org):
            return self.get_response(request)

        payload = {
            "detail": subscription_closed_message(org),
            "code": "subscription_closed",
            "is_owner": is_owner(user),
        }
        return JsonResponse(payload, status=402)

    def process_view(self, request, view_func, view_args, view_kwargs):
        return None
