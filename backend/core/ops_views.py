import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import is_owner, user_organization


class HealthView(APIView):
    permission_classes = [AllowAny]
    rbac_exempt = True
    subscription_exempt = True
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False
        return Response(
            {
                "status": "ok" if db_ok else "degraded",
                "database": "up" if db_ok else "down",
                "time": datetime.utcnow().isoformat() + "Z",
                "version": "1.1.0",
            },
            status=200 if db_ok else 503,
        )


class BackupView(APIView):
    """Create a DB file backup (SQLite) or dump marker for Postgres."""

    permission_classes = [IsAuthenticated]
    rbac_module = "settings.roles"

    def post(self, request):
        if not (is_owner(request.user) or request.user.is_superuser):
            return Response({"detail": "Owner/superuser only"}, status=403)
        backup_root = Path(settings.BACKUP_ROOT)
        backup_root.mkdir(exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        engine = settings.DATABASES["default"]["ENGINE"]
        if "sqlite" in engine:
            src = Path(settings.DATABASES["default"]["NAME"])
            dest = backup_root / f"db_{stamp}.sqlite3"
            shutil.copy2(src, dest)
            return Response({"backup": str(dest), "size": dest.stat().st_size})
        dest = backup_root / f"pg_backup_{stamp}.txt"
        dest.write_text(
            f"Postgres backup requested at {stamp}. Use pg_dump in CI/ops pipeline.\n",
            encoding="utf-8",
        )
        return Response({"backup": str(dest), "note": "Use pg_dump for Postgres"})


class OpsStatusView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_module = "dashboard"

    def get(self, request):
        org = user_organization(request.user)
        return Response(
            {
                "organization": org.code if org else None,
                "debug": settings.DEBUG,
                "email_backend": settings.EMAIL_BACKEND,
                "sod_enforce": getattr(settings, "SOD_ENFORCE", True),
                "mfa_issuer": getattr(settings, "MFA_ISSUER", "SIGBL ERP"),
                "timezone": settings.TIME_ZONE,
            }
        )
