from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import can
from core.access import user_organization
from core.scoping import OrgScopedQuerysetMixin
from integrations.catalog import public_catalog
from integrations.models import IntegrationConnection
from integrations.serializers import IntegrationConnectionSerializer
from integrations.services import test_connector


class IntegrationCatalogView(APIView):
    rbac_module = "settings.integrations"

    def get(self, request):
        if not can(request.user, "settings.integrations", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        connections = {}
        if org:
            for c in IntegrationConnection.objects.filter(organization=org):
                connections[c.connector_key] = {
                    "id": c.id,
                    "status": c.status,
                    "is_enabled": c.is_enabled,
                    "last_test_ok": c.last_test_ok,
                    "last_tested_at": c.last_tested_at,
                }
        items = public_catalog()
        for item in items:
            item["connection"] = connections.get(item["key"])
        recommended = [i for i in items if i.get("recommended")]
        return Response(
            {
                "connectors": items,
                "recommended_count": len(recommended),
                "connected_count": sum(1 for v in connections.values() if v.get("is_enabled")),
            }
        )


class IntegrationConnectionViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = IntegrationConnection.objects.all()
    serializer_class = IntegrationConnectionSerializer
    rbac_module = "settings.integrations"
    filterset_fields = ("connector_key", "status", "is_enabled")
    search_fields = ("connector_key", "display_name")

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        obj = serializer.save(organization=org, created_by=self.request.user)
        if obj.config or obj.secrets:
            obj.status = IntegrationConnection.Status.CONFIGURED
            obj.save(update_fields=["status"])

    def perform_update(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        if obj.is_enabled and obj.status != IntegrationConnection.Status.ERROR:
            obj.status = IntegrationConnection.Status.ACTIVE
            obj.save(update_fields=["status"])
        elif not obj.is_enabled and obj.status == IntegrationConnection.Status.ACTIVE:
            obj.status = IntegrationConnection.Status.CONFIGURED
            obj.save(update_fields=["status"])

    def create(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        key = request.data.get("connector_key")
        existing = IntegrationConnection.objects.filter(
            organization=org, connector_key=key
        ).first()
        if existing:
            ser = self.get_serializer(existing, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            self.perform_update(ser)
            return Response(ser.data)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "delete"):
            return Response({"detail": "Permission denied"}, status=403)
        return super().destroy(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not can(request.user, "settings.integrations", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        return super().retrieve(request, *args, **kwargs)


class IntegrationTestView(APIView):
    rbac_module = "settings.integrations"

    def post(self, request, pk):
        if not can(request.user, "settings.integrations", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        conn = IntegrationConnection.objects.filter(pk=pk, organization=org).first()
        if not conn:
            return Response({"detail": "Not found"}, status=404)
        conn = test_connector(conn)
        return Response(IntegrationConnectionSerializer(conn).data)


class IntegrationEnsureDefaultsView(APIView):
    """Seed recommended connector rows for the tenant."""

    rbac_module = "settings.integrations"

    def post(self, request):
        if not can(request.user, "settings.integrations", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        from integrations.catalog import INTEGRATION_CATALOG

        created = 0
        for item in INTEGRATION_CATALOG:
            if not item.get("recommended") and item["key"] not in (
                "microsoft365_mail",
                "attendance_biometric",
                "smtp_generic",
                "rest_openapi",
                "bank_salary_file",
            ):
                continue
            _, was_created = IntegrationConnection.objects.get_or_create(
                organization=org,
                connector_key=item["key"],
                defaults={
                    "display_name": item["name"],
                    "status": IntegrationConnection.Status.DISCONNECTED,
                    "created_by": request.user,
                },
            )
            if was_created:
                created += 1
        return Response({"created": created, "total": IntegrationConnection.objects.filter(organization=org).count()})
