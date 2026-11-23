"""Premier PayFast SaaS billing — checkout, callback, platform/tenant gateway settings."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import activate_paid_plan, is_owner, payment_kind, user_organization
from core.models import (
    PayFastSettings,
    SubscriptionPackage,
    SubscriptionPayment,
    TenantPayGateway,
)
from core.payfast import (
    SUCCESS_CODES,
    PayFastError,
    callback_valid,
    gateway_for,
    hosted_access_token,
    hosted_fields,
    post_transaction_url,
)
from core.serializers import SubscriptionPaymentSerializer


PAID_CODES = SUCCESS_CODES


class IsPlatformOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        from core.platform_rbac import has_platform_cap

        return bool(
            request.user
            and request.user.is_authenticated
            and has_platform_cap(request.user, "payfast")
        )


def _mask_secret(value: str) -> bool:
    return bool(value)


class PayFastSettingsSerializer(serializers.ModelSerializer):
    sandbox_secured_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    sandbox_hash_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    live_secured_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    live_hash_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    sandbox_secured_key_set = serializers.SerializerMethodField()
    sandbox_hash_key_set = serializers.SerializerMethodField()
    live_secured_key_set = serializers.SerializerMethodField()
    live_hash_key_set = serializers.SerializerMethodField()
    ready = serializers.SerializerMethodField()
    environment_display = serializers.SerializerMethodField()

    class Meta:
        model = PayFastSettings
        fields = (
            "environment",
            "environment_display",
            "sandbox_api_base",
            "sandbox_merchant_id",
            "sandbox_secured_key",
            "sandbox_secured_key_set",
            "sandbox_hash_key",
            "sandbox_hash_key_set",
            "live_api_base",
            "live_merchant_id",
            "live_secured_key",
            "live_secured_key_set",
            "live_hash_key",
            "live_hash_key_set",
            "ready",
            "updated_at",
        )
        read_only_fields = ("updated_at", "ready", "environment_display")

    def get_sandbox_secured_key_set(self, obj):
        return _mask_secret(obj.sandbox_secured_key)

    def get_sandbox_hash_key_set(self, obj):
        return _mask_secret(obj.sandbox_hash_key)

    def get_live_secured_key_set(self, obj):
        return _mask_secret(obj.live_secured_key)

    def get_live_hash_key_set(self, obj):
        return _mask_secret(obj.live_hash_key)

    def get_ready(self, obj):
        return obj.ready

    def get_environment_display(self, obj):
        return obj.get_environment_display()

    def update(self, instance, validated_data):
        secret_fields = (
            "sandbox_secured_key",
            "sandbox_hash_key",
            "live_secured_key",
            "live_hash_key",
        )
        secrets = {k: validated_data.pop(k) for k in secret_fields if k in validated_data}
        for k, v in validated_data.items():
            setattr(instance, k, v)
        for k, v in secrets.items():
            if v:
                setattr(instance, k, v)
        instance.save()
        return instance


class TenantPayGatewaySerializer(PayFastSettingsSerializer):
    class Meta(PayFastSettingsSerializer.Meta):
        model = TenantPayGateway


class PlatformPayFastView(APIView):
    """Platform owner configures Premier PayFast for SaaS subscription billing."""

    permission_classes = [IsPlatformOwner]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        return Response(PayFastSettingsSerializer(PayFastSettings.load()).data)

    def put(self, request):
        cfg = PayFastSettings.load()
        ser = PayFastSettingsSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(PayFastSettingsSerializer(cfg).data)


class TenantPayGatewayView(APIView):
    """Tenant owner configures their own PayFast (optional; not used for SaaS bills)."""

    rbac_module = "billing"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        cfg, _ = TenantPayGateway.objects.get_or_create(organization=org)
        return Response(TenantPayGatewaySerializer(cfg).data)

    def put(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not (is_owner(request.user) or request.user.is_superuser):
            return Response({"detail": "Owner only"}, status=403)
        cfg, _ = TenantPayGateway.objects.get_or_create(organization=org)
        ser = TenantPayGatewaySerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(TenantPayGatewaySerializer(cfg).data)


def _frontend_billing_url(payment_id=None):
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    if payment_id:
        return f"{base}/billing?payment={payment_id}"
    return f"{base}/billing"


def _apply_paid(payment, payload):
    payment.status = SubscriptionPayment.Status.PAID
    payment.status_code = str(
        payload.get("err_code")
        or payload.get("status_code")
        or payload.get("code")
        or ""
    )
    payment.status_message = str(
        payload.get("err_msg")
        or payload.get("status_msg")
        or payload.get("message")
        or "Paid"
    )[:255]
    payment.transaction_id = str(
        payload.get("transaction_id") or payment.transaction_id
    )
    payment.instrument_alias = str(
        payload.get("instrument_alias") or payload.get("paymentname") or ""
    )[:64]
    org, start, end = activate_paid_plan(payment.organization, payment.plan, payment.kind)
    payment.period_start = start
    payment.period_end = end
    payment.organization = org
    payment.save()
    try:
        from core.invoicing import invoice_from_payment

        invoice_from_payment(payment, user=payment.user)
    except Exception:
        pass


def _fail(payment, payload):
    payment.status = SubscriptionPayment.Status.FAILED
    payment.status_code = str(
        payload.get("err_code")
        or payload.get("status_code")
        or payload.get("code")
        or ""
    )
    payment.status_message = str(
        payload.get("err_msg")
        or payload.get("status_msg")
        or payload.get("message")
        or "PayFast could not complete the payment."
    )[:255]
    payment.transaction_id = str(
        payload.get("transaction_id") or payment.transaction_id
    )
    payment.save()


class BillingCheckoutView(APIView):
    """Start hosted PayFast checkout for a SaaS plan (platform gateway)."""

    subscription_exempt = True
    rbac_module = "billing"
    rbac_action = "change"

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not (is_owner(request.user) or request.user.is_superuser):
            return Response({"detail": "Only the company owner can pay"}, status=403)

        plan_code = request.data.get("plan", "monthly")
        pkg = SubscriptionPackage.objects.filter(code=plan_code, active=True).exclude(
            code="trial"
        ).first()
        if not pkg:
            return Response({"detail": "Unknown plan"}, status=400)

        gateway = PayFastSettings.load()
        if not gateway.ready:
            return Response(
                {
                    "detail": (
                        f"Premier PayFast {gateway.get_environment_display()} is not configured. "
                        "Platform owner must set sandbox/live credentials."
                    ),
                    "gateway_ready": False,
                    "environment": gateway.environment,
                },
                status=400,
            )

        mobile = (
            request.data.get("mobile")
            or getattr(getattr(request.user, "profile", None), "phone", "")
            or "03000000000"
        )
        email = request.data.get("email") or request.user.email or org.email or ""
        if not email:
            return Response({"detail": "email required"}, status=400)

        kind = payment_kind(org, plan_code)
        basket_id = f"SIERP{timezone.now():%y%m%d%H%M%S}{request.user.pk}{uuid.uuid4().hex[:4]}"
        payment = SubscriptionPayment.objects.create(
            organization=org,
            user=request.user,
            plan=plan_code,
            kind=kind,
            amount=pkg.price,
            environment=gateway.environment,
            basket_id=basket_id,
            reference=basket_id,
            status=SubscriptionPayment.Status.PENDING,
            notes="PayFast hosted checkout",
        )
        amount = f"{payment.amount:.2f}"
        return_url = request.build_absolute_uri("/api/saas/billing/payfast/return/")
        try:
            token_payload = hosted_access_token(payment.basket_id, amount, gateway=gateway)
        except PayFastError as exc:
            _fail(payment, exc.payload)
            return Response(
                {"detail": str(exc), "payment": SubscriptionPaymentSerializer(payment).data},
                status=400,
            )

        fields = hosted_fields(
            token=token_payload.get("ACCESS_TOKEN") or token_payload.get("access_token"),
            merchant_name=str(token_payload.get("NAME") or "SIGBL ERP"),
            basket_id=payment.basket_id,
            amount=amount,
            mobile=mobile,
            email=email,
            description=f"SIGBL ERP {pkg.name}",
            success_url=return_url,
            failure_url=return_url,
            checkout_url=return_url,
            order_date=timezone.localdate().isoformat(),
            gateway=gateway,
        )
        return Response(
            {
                "payment": SubscriptionPaymentSerializer(payment).data,
                "action": post_transaction_url(gateway),
                "fields": fields,
                "environment": gateway.environment,
                "gateway_ready": True,
            }
        )


class BillingStatusPayFastMixin:
    """Augment billing status with gateway readiness."""

    pass


def billing_gateway_status():
    gw = PayFastSettings.load()
    return {
        "gateway_ready": gw.ready,
        "environment": gw.environment,
        "environment_display": gw.get_environment_display(),
    }


class PayFastReturnView(APIView):
    """PayFast success/failure callback (POST or GET) — csrf exempt, no auth."""

    authentication_classes = []
    permission_classes = [AllowAny]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        source = request.POST if request.method == "POST" and request.POST else request.GET
        data = {str(k).lower(): v for k, v in source.items()}
        basket_id = data.get("basket_id", "")
        err_code = str(data.get("err_code") or "")
        payment = SubscriptionPayment.objects.filter(basket_id=basket_id).first()
        gateway = PayFastSettings.load()
        if payment:
            # Prefer platform; if payment somehow used tenant (future), resolve via org
            gateway = gateway_for(None)

        confirmed = payment is not None and callback_valid(
            basket_id, err_code, data.get("validation_hash", ""), gateway=gateway
        )
        if not confirmed:
            return HttpResponseRedirect(_frontend_billing_url())

        payload = {
            "err_code": err_code,
            "err_msg": data.get("err_msg", ""),
            "transaction_id": data.get("transaction_id", ""),
            "instrument_alias": data.get("paymentname", ""),
        }
        if err_code in PAID_CODES:
            if payment.status != SubscriptionPayment.Status.PAID:
                _apply_paid(payment, payload)
        elif payment.status == SubscriptionPayment.Status.PENDING:
            _fail(payment, payload)

        return HttpResponseRedirect(_frontend_billing_url(payment.pk))


# Wrap for csrf_exempt at URL level
payfast_return = csrf_exempt(PayFastReturnView.as_view())
