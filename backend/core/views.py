import uuid

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import allowed_modules, ensure_default_roles
from accounts.serializers import UserSerializer
from core.access import (
    activate_paid_plan,
    ensure_default_packages,
    sellable_packages,
    start_trial,
    subscription_open,
    user_organization,
)
from core.models import CompanyLink, Organization, SubscriptionPayment, SubscriptionPackage
from core.serializers import (
    OrganizationSerializer,
    SubscriptionPackageSerializer,
    SubscriptionPaymentSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken


class PlansView(APIView):
    permission_classes = [permissions.AllowAny]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        ensure_default_packages()
        pkgs = SubscriptionPackage.objects.filter(active=True).order_by("sort")
        return Response(SubscriptionPackageSerializer(pkgs, many=True).data)


class SignupView(APIView):
    """Create tenant organization + owner on a 14-day trial (desk-inspired)."""

    permission_classes = [permissions.AllowAny]
    rbac_exempt = True
    subscription_exempt = True

    @transaction.atomic
    def post(self, request):
        data = request.data
        required = ["company_name", "username", "email", "password"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response(
                {"detail": f"Missing fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=data["username"]).exists():
            return Response({"detail": "Username already taken"}, status=400)
        if User.objects.filter(email=data["email"]).exists():
            return Response({"detail": "Email already registered"}, status=400)

        base_slug = (
            "".join(c for c in data["company_name"].lower() if c.isalnum() or c == " ")
            .strip()
            .replace(" ", "-")[:40]
            or "company"
        )
        slug = base_slug
        i = 1
        while Organization.objects.filter(code=slug).exists():
            slug = f"{base_slug}-{i}"
            i += 1

        org = Organization.objects.create(
            name=data["company_name"],
            code=slug,
            email=data["email"],
            phone=data.get("phone", ""),
        )
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
        org.owner = user
        org.save(update_fields=["owner"])
        start_trial(org)
        ensure_default_roles(org)
        from core.email_defaults import ensure_default_email_templates

        ensure_default_email_templates(org)
        owner_role = Role.objects.filter(organization=org, code="owner").first()
        profile = UserProfile.objects.create(
            user=user,
            organization=org,
            role=UserProfile.RoleCode.OWNER,
            phone=data.get("phone", ""),
            designation="Owner",
            primary_role=owner_role,
        )
        if owner_role:
            UserRole.objects.get_or_create(user=user, role=owner_role)
        CompanyLink.objects.get_or_create(user=user, organization=org)

        if user.email:
            from core.notifications import notify_system

            notify_system(
                "Welcome to SI-ERP",
                f"Hello {user.first_name or user.username},\n\n"
                f"Your tenant '{org.name}' is ready on a trial plan.\n"
                f"Sign in with username: {user.username}\n"
                "To set a new password later, use Forgot password on the sign-in page.\n\n"
                "— SI-ERP",
                [user.email],
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "organization": OrganizationSerializer(org).data,
                "permissions": allowed_modules(user),
            },
            status=status.HTTP_201_CREATED,
        )


class BillingStatusView(APIView):
    subscription_exempt = True
    rbac_module = "billing"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        from core.billing_payfast import billing_gateway_status

        from core.access import days_until_lock, subscription_in_grace
        from core.models import SaaSInvoice
        from core.serializers import SaaSInvoiceSerializer

        payments = SubscriptionPayment.objects.filter(organization=org)[:10]
        invoices = SaaSInvoice.objects.filter(organization=org).order_by("-id")[:20]
        return Response(
            {
                "organization": OrganizationSerializer(org).data,
                "subscription_open": subscription_open(org),
                "subscription_in_grace": subscription_in_grace(org),
                "days_until_lock": days_until_lock(org),
                "plans": SubscriptionPackageSerializer(sellable_packages(), many=True).data,
                "payments": SubscriptionPaymentSerializer(payments, many=True).data,
                "invoices": SaaSInvoiceSerializer(invoices, many=True).data,
                **billing_gateway_status(),
            }
        )


class RenewSubscriptionView(APIView):
    """Demo renew when PayFast is not configured. Prefer /billing/checkout/ for live PayFast."""

    subscription_exempt = True
    rbac_module = "billing"
    rbac_action = "change"

    def post(self, request):
        from core.models import PayFastSettings

        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        plan_code = request.data.get("plan", "monthly")
        if plan_code not in ("monthly", "annual"):
            return Response({"detail": "plan must be monthly or annual"}, status=400)

        force_demo = bool(request.data.get("demo")) or request.user.is_superuser
        gateway = PayFastSettings.load()
        if gateway.ready and not force_demo:
            return Response(
                {
                    "detail": "PayFast is configured — use /api/saas/billing/checkout/",
                    "gateway_ready": True,
                    "use_checkout": True,
                },
                status=400,
            )

        pkg = SubscriptionPackage.objects.filter(code=plan_code).first()
        if not pkg:
            ensure_default_packages()
            pkg = SubscriptionPackage.objects.get(code=plan_code)

        from core.access import payment_kind

        kind = payment_kind(org, plan_code)
        org, start, end = activate_paid_plan(org, plan_code, kind)
        ref = f"DEMO-{uuid.uuid4().hex[:12].upper()}"
        payment = SubscriptionPayment.objects.create(
            organization=org,
            user=request.user,
            plan=plan_code,
            kind=kind,
            period_start=start,
            period_end=end,
            amount=pkg.price,
            reference=ref,
            basket_id=ref,
            environment="demo",
            status=SubscriptionPayment.Status.PAID,
            status_message="Demo renewal (PayFast not used)",
            notes="Demo renewal — PayFast gateway not configured or demo=true",
        )
        try:
            from core.invoicing import invoice_from_payment

            invoice_from_payment(payment, user=request.user)
        except Exception:
            pass
        return Response(
            {
                "organization": OrganizationSerializer(org).data,
                "payment": SubscriptionPaymentSerializer(payment).data,
                "demo": True,
            }
        )
