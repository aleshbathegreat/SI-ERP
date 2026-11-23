"""Append-only mutation audit. Plumbing calls are not recorded."""

from core.access import user_organization
from core.audit_text import classify_http
from core.models import AuditLog


def _message(response) -> str:
    data = getattr(response, "data", None)
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, list):
            return " ".join(str(item) for item in detail)[:300]
        if detail:
            return str(detail)[:300]
    return ""


class MutationAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        track = bool(
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            and user
            and getattr(user, "is_authenticated", False)
        )
        before = None
        if track:
            before = (
                AuditLog.objects.filter(user=user).order_by("-id").values_list("id", flat=True).first()
            )
        response = self.get_response(request)
        if not track:
            return response
        try:
            after = (
                AuditLog.objects.filter(user=user).order_by("-id").values_list("id", flat=True).first()
            )
            if after != before:
                return response
            info = classify_http(
                request.method,
                request.path or "",
                getattr(response, "status_code", 0),
                _message(response),
            )
            if not info:
                return response
            AuditLog.objects.create(
                organization=user_organization(user),
                user=user,
                action=info["stored_action"][:64],
                module=(info.get("module") or "")[:64],
                object_type=(info.get("noun") or "")[:64],
                object_id=(info.get("record_id") or "")[:64],
                detail=(info.get("stored_detail") or "")[:500],
            )
        except Exception:
            pass
        return response
