"""Platform owner / staff SaaS control APIs."""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import extend_subscription
from core.bulk import BulkDeleteMixin
from core.models import (
    Organization,
    PlatformSmtpSettings,
    SaaSInvoice,
    SubscriptionPackage,
    SupportTicket,
)
from core.platform_rbac import (
    has_platform_cap,
    is_platform_user,
    require_platform_cap,
)
from core.serializers import SubscriptionPackageSerializer


class IsPlatformStaff:
    def has_permission(self, request, view):
        return is_platform_user(request.user)


class PlatformOverviewView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        err = require_platform_cap(request.user, "overview")
        if err:
            return Response(err[0], status=err[1])

        orgs = Organization.objects.all()
        smtp = PlatformSmtpSettings.load()
        payfast_ready = False
        try:
            from core.models import PayFastSettings

            pf = PayFastSettings.load()
            if getattr(pf, "environment", "") == "live":
                payfast_ready = bool(pf.live_merchant_id and pf.live_secured_key)
            else:
                payfast_ready = bool(pf.sandbox_merchant_id and pf.sandbox_secured_key)
        except Exception:
            payfast_ready = False

        recent = list(
            orgs.order_by("-id")[:12].values(
                "id",
                "name",
                "code",
                "plan",
                "plan_status",
                "brand_name",
                "trial_ends",
                "subscription_ends",
            )
        )
        open_tickets = SupportTicket.objects.exclude(
            status__in=["resolved", "closed"]
        ).count()
        unpaid = SaaSInvoice.objects.filter(status__in=["sent", "overdue"]).count()

        from accounts.rbac import effective_package_modules
        from collections import Counter

        plan_mix = [
            {"label": k or "unset", "value": v}
            for k, v in Counter(orgs.values_list("plan", flat=True)).items()
        ]
        status_mix = [
            {"label": k or "unset", "value": v}
            for k, v in Counter(orgs.values_list("plan_status", flat=True)).items()
        ]
        pkg_rows = []
        for p in SubscriptionPackage.objects.filter(active=True).order_by("sort", "price"):
            eff = effective_package_modules(p)
            tenants_on = orgs.filter(package=p).count()
            pkg_rows.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "code": p.code,
                    "price": str(p.price),
                    "interval": p.interval,
                    "module_count": len(eff),
                    "core_count": len(p.core_module_keys or []),
                    "assignable_count": len(p.module_keys or []),
                    "tenants": tenants_on,
                    "max_functional_users": p.max_functional_users,
                    "max_ess_users": p.max_ess_users,
                }
            )

        sentiments = []
        past_due = orgs.filter(plan_status="past_due").count()
        if past_due:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Past-due tenants",
                    "detail": f"{past_due} org(s) need collection / grace handling.",
                }
            )
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Subscriptions healthy",
                    "detail": "No tenants currently marked past due.",
                }
            )
        if open_tickets:
            sentiments.append(
                {
                    "tone": "attention" if open_tickets > 5 else "neutral",
                    "title": "Support load",
                    "detail": f"{open_tickets} open ticket(s) in the queue.",
                }
            )
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Support clear",
                    "detail": "No open platform support tickets.",
                }
            )
        if unpaid:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Unpaid SaaS invoices",
                    "detail": f"{unpaid} invoice(s) sent/overdue.",
                }
            )
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Invoices settled",
                    "detail": "No sent/overdue SaaS invoices.",
                }
            )
        if not payfast_ready or not (smtp.is_active and smtp.host):
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Platform ops gaps",
                    "detail": "Configure SMTP and/or PayFast for full SaaS automation.",
                }
            )
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Platform rails ready",
                    "detail": "SMTP and PayFast are configured.",
                }
            )

        health = 100
        health -= min(40, past_due * 12)
        health -= min(25, open_tickets * 3)
        health -= min(20, unpaid * 4)
        if not payfast_ready:
            health -= 8
        if not (smtp.is_active and smtp.host):
            health -= 8
        health = max(0, min(100, health))

        return Response(
            {
                "tenants": orgs.count(),
                "tenants_active": orgs.filter(is_active=True).count(),
                "tenants_trial": orgs.filter(plan="trial").count(),
                "tenants_paid": orgs.exclude(plan="trial").count(),
                "tenants_past_due": past_due,
                "packages": SubscriptionPackage.objects.filter(active=True).count(),
                "platform_smtp_active": bool(
                    smtp.is_active and smtp.host and smtp.from_email
                ),
                "platform_payfast_ready": payfast_ready,
                "open_tickets": open_tickets,
                "unpaid_invoices": unpaid,
                "recent_tenants": recent,
                "plan_mix": plan_mix,
                "status_mix": status_mix,
                "package_stats": pkg_rows,
                "sentiments": sentiments,
                "health_score": health,
            }
        )


class PlatformModuleCatalogView(APIView):
    """Grouped module catalog for package assignment UI."""

    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        err = require_platform_cap(request.user, "packages")
        if err:
            return Response(err[0], status=err[1])
        from accounts.rbac import (
            ASSIGNABLE_MODULE_KEYS,
            CORE_MODULE_KEYS,
            package_module_catalog,
        )

        return Response(
            {
                "groups": package_module_catalog(),
                "core_keys": CORE_MODULE_KEYS,
                "assignable_keys": ASSIGNABLE_MODULE_KEYS,
            }
        )


class PlatformPackageViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    queryset = SubscriptionPackage.objects.all().order_by("sort", "price", "name")
    serializer_class = SubscriptionPackageSerializer
    permission_classes = [IsAuthenticated, IsPlatformStaff]
    rbac_exempt = True
    subscription_exempt = True
    pagination_class = None
    search_fields = ("name", "code", "summary")
    filterset_fields = ("active", "interval")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        err = require_platform_cap(request.user, "packages")
        if err:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(err[0]["detail"])


class PlatformTenantsView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        err = require_platform_cap(request.user, "tenants")
        if err:
            return Response(err[0], status=err[1])
        rows = []
        for o in Organization.objects.select_related("package", "owner").order_by("-id"):
            from core.access import days_until_lock, subscription_in_grace, subscription_open

            rows.append(
                {
                    "id": o.id,
                    "name": o.name,
                    "code": o.code,
                    "brand_name": o.brand_name or o.name,
                    "email": o.email,
                    "plan": o.plan,
                    "plan_status": o.plan_status,
                    "package_name": o.package.name if o.package_id else None,
                    "is_active": o.is_active,
                    "trial_ends": o.trial_ends,
                    "subscription_ends": o.subscription_ends,
                    "grace_days": o.grace_days,
                    "subscription_open": subscription_open(o),
                    "subscription_in_grace": subscription_in_grace(o),
                    "days_until_lock": days_until_lock(o),
                    "owner": o.owner.username if o.owner_id else None,
                    "custom_domain": o.custom_domain or "",
                    "custom_domain_verified": o.custom_domain_verified,
                }
            )
        return Response({"results": rows, "count": len(rows)})

    def patch(self, request):
        err = require_platform_cap(request.user, "tenants")
        if err:
            return Response(err[0], status=err[1])
        org_id = request.data.get("id")
        org = Organization.objects.filter(pk=org_id).first()
        if not org:
            return Response({"detail": "Tenant not found"}, status=404)
        for field in ("is_active", "plan_status", "plan", "grace_days"):
            if field in request.data:
                setattr(org, field, request.data[field])
        pkg_code = request.data.get("package_code")
        if pkg_code is not None:
            pkg = SubscriptionPackage.objects.filter(code=pkg_code).first()
            org.package = pkg
        # Extend convenience on same endpoint when staff has tenants.extend
        if "extend_days" in request.data:
            if not has_platform_cap(request.user, "tenants.extend"):
                return Response({"detail": "Requires tenants.extend"}, status=403)
            extend_subscription(
                org,
                int(request.data.get("extend_days") or 14),
                as_trial=request.data.get("as_trial"),
            )
            return Response(
                {
                    "ok": True,
                    "id": org.id,
                    "trial_ends": org.trial_ends,
                    "subscription_ends": org.subscription_ends,
                    "plan_status": org.plan_status,
                }
            )
        org.save()
        return Response({"ok": True, "id": org.id})
