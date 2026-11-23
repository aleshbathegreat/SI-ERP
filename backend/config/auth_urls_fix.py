"""Token refresh must stay open when subscription is closed."""

from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView


class OpenTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    subscription_exempt = True
    rbac_exempt = True
