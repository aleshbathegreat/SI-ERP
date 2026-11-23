"""Authenticate JWT on request.user for subscription middleware (desk-style gates)."""

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.authenticator = JWTAuthentication()

    def __call__(self, request):
        header = self.authenticator.get_header(request)
        if header is not None:
            try:
                raw_token = self.authenticator.get_raw_token(header)
                validated = self.authenticator.get_validated_token(raw_token)
                request.user = self.authenticator.get_user(validated)
            except Exception:
                request.user = getattr(request, "user", None) or AnonymousUser()
        return self.get_response(request)
