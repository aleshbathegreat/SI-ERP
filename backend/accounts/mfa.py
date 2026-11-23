import pyotp
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserProfile
from accounts.rbac import allowed_modules, ensure_default_roles
from accounts.serializers import UserSerializer
from core.access import subscription_open, user_organization
from core.serializers import OrganizationSerializer


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class MfaSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.mfa_secret:
            profile.mfa_secret = pyotp.random_base32()
            profile.save(update_fields=["mfa_secret", "updated_at"])
        totp = pyotp.TOTP(profile.mfa_secret)
        uri = totp.provisioning_uri(
            name=request.user.email or request.user.username,
            issuer_name=getattr(settings, "MFA_ISSUER", "SIGBL ERP"),
        )
        return Response(
            {
                "secret": profile.mfa_secret,
                "otpauth_url": uri,
                "mfa_enabled": profile.mfa_enabled,
            }
        )

    def post(self, request):
        """Enable MFA after verifying a TOTP code."""
        code = str(request.data.get("code", "")).strip()
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.mfa_secret:
            return Response({"detail": "Call GET first to generate secret"}, status=400)
        if not pyotp.TOTP(profile.mfa_secret).verify(code, valid_window=1):
            return Response({"detail": "Invalid MFA code"}, status=400)
        profile.mfa_enabled = True
        profile.save(update_fields=["mfa_enabled", "updated_at"])
        return Response({"mfa_enabled": True})


class MfaDisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.mfa_enabled:
            return Response({"mfa_enabled": False})
        if not pyotp.TOTP(profile.mfa_secret).verify(code, valid_window=1):
            return Response({"detail": "Invalid MFA code"}, status=400)
        profile.mfa_enabled = False
        profile.save(update_fields=["mfa_enabled", "updated_at"])
        return Response({"mfa_enabled": False})


def issue_auth_payload(user, request=None):
    from accounts.models import Role, UserRole
    from core.access import ensure_default_packages

    refresh = RefreshToken.for_user(user)
    ensure_default_packages()
    org = user_organization(user)
    if org:
        ensure_default_roles(org)
        profile = getattr(user, "profile", None)
        if profile and profile.role and not UserRole.objects.filter(
            user=user, role__organization=org
        ).exists():
            role = Role.objects.filter(organization=org, code=profile.role).first()
            if role:
                UserRole.objects.get_or_create(user=user, role=role)
                if not profile.primary_role_id:
                    profile.primary_role = role
                    profile.save(update_fields=["primary_role", "updated_at"])
    ctx = {"request": request} if request is not None else {}
    from core.platform_rbac import (
        is_platform_user,
        platform_capabilities,
        platform_role,
    )

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user, context=ctx).data,
        "organization": OrganizationSerializer(org, context=ctx).data if org else None,
        "subscription_open": subscription_open(org) if org else False,
        "permissions": allowed_modules(user),
        "mfa_enabled": bool(getattr(getattr(user, "profile", None), "mfa_enabled", False)),
        "is_platform_user": is_platform_user(user),
        "platform_role": platform_role(user),
        "platform_capabilities": platform_capabilities(user),
    }
