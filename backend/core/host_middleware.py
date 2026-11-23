"""Resolve tenant from Host; reject unknown hosts when not using ALLOWED_HOSTS=*."""

from django.http import HttpResponseBadRequest, JsonResponse

from core.tenancy import host_allowed, normalize_host, resolve_organization


class TenantHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME") or ""
        host = normalize_host(raw)
        request.tenant_host = host
        request.tenant_organization = resolve_organization(host) if host else None

        # When Django ALLOWED_HOSTS includes *, still reject garbage hosts
        if host and not host_allowed(host):
            # Allow health without tenant binding
            path = request.path or "/"
            if path.startswith("/api/health"):
                return self.get_response(request)
            if path.startswith("/api/"):
                return JsonResponse(
                    {
                        "detail": "Unknown host. Use the platform domain or a configured tenant domain.",
                        "code": "unknown_host",
                        "host": host,
                    },
                    status=400,
                )
            return HttpResponseBadRequest("Unknown host")

        return self.get_response(request)
