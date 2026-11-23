"""Tenant custom domain + public host branding APIs."""

from __future__ import annotations

from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import is_owner, user_organization
from core.tenancy import (
    branding_payload,
    is_valid_hostname,
    new_verify_token,
    platform_hosts,
    platform_root_domain,
    public_branding,
    subdomain_for,
    verify_custom_domain,
)


def _tenant_branding_response(org, request):
    root = platform_root_domain()
    data = branding_payload(org, request=request)
    data.update(
        {
            "organization": org.code,
            "subdomain": subdomain_for(org),
            "platform_root": root or None,
            "custom_domain": org.custom_domain or "",
            "custom_domain_verified": org.custom_domain_verified,
            "domain_verify_token": org.domain_verify_token,
            "domain_verified_at": org.domain_verified_at,
            "dns_instructions": {
                "cname": {
                    "host": org.custom_domain or "erp.yourcompany.com",
                    "target": subdomain_for(org) or root or "app.platform",
                },
                "txt": {
                    "host": f"_sigbl-challenge.{org.custom_domain or 'erp.yourcompany.com'}",
                    "value": org.domain_verify_token or "(save a domain to generate)",
                },
            },
        }
    )
    return data


class ResolveHostView(APIView):
    """Public — branding for current Host (or ?host=)."""

    authentication_classes = []
    permission_classes = [AllowAny]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        from core.tenancy import resolve_organization

        host = request.query_params.get("host") or getattr(
            request, "tenant_host", None
        )
        org = getattr(request, "tenant_organization", None)
        if request.query_params.get("host"):
            org = resolve_organization(host)
        data = public_branding(org, request=request)
        data["host"] = host
        data["platform_root"] = platform_root_domain() or None
        return Response(data)


class TenantDomainView(APIView):
    """Owner configures custom domain + brand assets for this tenant."""

    rbac_module = "settings.domain"
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        return Response(_tenant_branding_response(org, request))

    def put(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not (is_owner(request.user) or request.user.is_superuser):
            return Response({"detail": "Owner only"}, status=403)

        brand_name = request.data.get("brand_name")
        brand_tagline = request.data.get("brand_tagline")
        color = request.data.get("brand_primary_color")
        secondary = request.data.get("brand_secondary_color")
        domain = request.data.get("custom_domain")
        clear_logo = str(request.data.get("clear_brand_logo", "")).lower() in (
            "1",
            "true",
            "yes",
        )
        clear_logo_dark = str(request.data.get("clear_brand_logo_dark", "")).lower() in (
            "1",
            "true",
            "yes",
        )
        clear_favicon = str(request.data.get("clear_brand_favicon", "")).lower() in (
            "1",
            "true",
            "yes",
        )

        fields = []
        if brand_name is not None:
            org.brand_name = str(brand_name).strip()[:128]
            fields.append("brand_name")
        if brand_tagline is not None:
            org.brand_tagline = str(brand_tagline).strip()[:160]
            fields.append("brand_tagline")
        if color is not None:
            org.brand_primary_color = str(color).strip()[:16] or "#1B6A94"
            fields.append("brand_primary_color")
        if secondary is not None:
            org.brand_secondary_color = str(secondary).strip()[:16] or "#C45C26"
            fields.append("brand_secondary_color")

        for key, attr in (
            ("brand_logo", "brand_logo"),
            ("brand_logo_dark", "brand_logo_dark"),
            ("brand_favicon", "brand_favicon"),
        ):
            f = request.FILES.get(key)
            if f:
                setattr(org, attr, f)
                fields.append(attr)

        if clear_logo and org.brand_logo:
            org.brand_logo.delete(save=False)
            org.brand_logo = None
            fields.append("brand_logo")
        if clear_logo_dark and org.brand_logo_dark:
            org.brand_logo_dark.delete(save=False)
            org.brand_logo_dark = None
            fields.append("brand_logo_dark")
        if clear_favicon and org.brand_favicon:
            org.brand_favicon.delete(save=False)
            org.brand_favicon = None
            fields.append("brand_favicon")

        if domain is not None:
            domain = str(domain).strip().lower().rstrip(".")
            if domain:
                if not is_valid_hostname(domain):
                    return Response({"detail": "Invalid domain"}, status=400)
                if domain in platform_hosts():
                    return Response(
                        {"detail": "Cannot use platform hostname"}, status=400
                    )
                from core.models import Organization

                clash = (
                    Organization.objects.filter(custom_domain=domain)
                    .exclude(pk=org.pk)
                    .exists()
                )
                if clash:
                    return Response({"detail": "Domain already in use"}, status=400)
                if domain != org.custom_domain:
                    org.custom_domain = domain
                    org.custom_domain_verified = False
                    org.domain_verified_at = None
                    org.domain_verify_token = new_verify_token()
                    fields += [
                        "custom_domain",
                        "custom_domain_verified",
                        "domain_verified_at",
                        "domain_verify_token",
                    ]
            else:
                org.custom_domain = ""
                org.custom_domain_verified = False
                org.domain_verified_at = None
                org.domain_verify_token = ""
                fields += [
                    "custom_domain",
                    "custom_domain_verified",
                    "domain_verified_at",
                    "domain_verify_token",
                ]

        if not org.domain_verify_token and org.custom_domain:
            org.domain_verify_token = new_verify_token()
            fields.append("domain_verify_token")

        if fields:
            org.save(update_fields=list(set(fields)) + ["updated_at"])

        return self.get(request)


class TenantDomainVerifyView(APIView):
    rbac_module = "settings.domain"
    rbac_action = "change"

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not (is_owner(request.user) or request.user.is_superuser):
            return Response({"detail": "Owner only"}, status=403)
        if not org.custom_domain:
            return Response({"detail": "Set a custom domain first"}, status=400)
        if not org.domain_verify_token:
            org.domain_verify_token = new_verify_token()
            org.save(update_fields=["domain_verify_token", "updated_at"])

        force = bool(request.data.get("force")) and request.user.is_superuser
        if force:
            org.custom_domain_verified = True
            org.domain_verified_at = timezone.now()
            org.save(
                update_fields=[
                    "custom_domain_verified",
                    "domain_verified_at",
                    "updated_at",
                ]
            )
            return Response(
                {
                    "verified": True,
                    "detail": "Force-verified by platform owner",
                    "custom_domain": org.custom_domain,
                }
            )

        ok, detail = verify_custom_domain(org)
        if ok:
            org.custom_domain_verified = True
            org.domain_verified_at = timezone.now()
            org.save(
                update_fields=[
                    "custom_domain_verified",
                    "domain_verified_at",
                    "updated_at",
                ]
            )
        return Response(
            {
                "verified": ok,
                "detail": detail,
                "custom_domain": org.custom_domain,
                "custom_domain_verified": org.custom_domain_verified,
            },
            status=200 if ok else 400,
        )


class PlatformDomainConfigView(APIView):
    """Superuser — read platform root domain config."""

    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        from core.platform_rbac import has_platform_cap

        if not (
            request.user.is_authenticated and has_platform_cap(request.user, "domains")
        ):
            return Response({"detail": "Platform domains capability required"}, status=403)
        return Response(
            {
                "platform_root": platform_root_domain() or None,
                "platform_hosts": sorted(platform_hosts()),
                "notes": (
                    "Set PLATFORM_ROOT_DOMAIN and PLATFORM_HOSTS in server env. "
                    "Tenant subdomains are {code}.{root}. Custom domains are per-tenant."
                ),
            }
        )
