"""Platform-mail password reset. The reply never says whether the email exists."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.mfa import LoginRateThrottle


def reset_link(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/reset-password?uid={uid}&token={token}"


def send_password_reset(user) -> bool:
    from core.notifications import notify_system

    if not user.email:
        return False
    link = reset_link(user)
    body = (
        f"Hello {user.first_name or user.username},\n\n"
        f"A password reset was requested for username {user.username}.\n\n"
        f"Choose a new password:\n{link}\n\n"
        "If you did not ask for this, ignore this message. The link stops working after the password changes.\n\n"
        "— SI-ERP"
    )
    return notify_system("Reset your password", body, [user.email])


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    rbac_exempt = True
    subscription_exempt = True
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        for user in User.objects.filter(email__iexact=email, is_active=True):
            send_password_reset(user)
        return Response(
            {"detail": "If an account exists for that email, a reset link has been sent."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    rbac_exempt = True
    subscription_exempt = True
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        uid = str(request.data.get("uid") or "").strip()
        token = str(request.data.get("token") or "").strip()
        password = str(request.data.get("password") or "")
        if not uid or not token or not password:
            return Response({"detail": "Reset link and a new password are required."}, status=400)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except Exception:
            return Response({"detail": "This reset link is not valid."}, status=400)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "This reset link is not valid."}, status=400)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated. You can sign in."})
