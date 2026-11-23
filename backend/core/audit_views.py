from rest_framework import serializers, viewsets
from django.db.models import Q

from core.access import user_organization
from core.audit_text import AREA_PREFIX, denied_filter, kind_filter, noise_filter, parse_day, present
from core.models import AuditLog


class AuditLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    who = serializers.CharField()
    event = serializers.CharField()
    area = serializers.CharField()
    record = serializers.CharField()
    href = serializers.CharField()
    role = serializers.CharField()
    outcome = serializers.CharField()
    change = serializers.CharField()

    def to_representation(self, instance):
        row = present(instance)
        return {
            "id": instance.id,
            "created_at": instance.created_at,
            "who": row["who"],
            "role": row["role"],
            "event": row["event"],
            "area": row["area"],
            "record": row["record"],
            "href": row["href"],
            "outcome": row["outcome"],
            "change": row["change"],
        }


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Immutable audit trail — business events only, in plain language."""

    serializer_class = AuditLogSerializer
    rbac_module = "settings.audit"
    search_fields = (
        "action",
        "module",
        "object_type",
        "object_id",
        "detail",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return AuditLog.objects.none()
        qs = (
            AuditLog.objects.filter(organization=org)
            .select_related("user", "user__profile", "user__profile__primary_role")
            .exclude(noise_filter())
        )
        params = self.request.query_params
        area = AREA_PREFIX.get((params.get("area") or "").strip().lower())
        if area:
            qs = qs.filter(
                Q(module__startswith=area)
                | Q(detail__icontains=f"/api/{area}/")
                | Q(detail__icontains=f"/{area}/")
            )
        kind = kind_filter(params.get("kind") or "")
        if kind is not None:
            qs = qs.filter(kind)
        if (params.get("outcome") or "").strip().lower() == "denied":
            qs = qs.filter(denied_filter())
        start = parse_day(params.get("from") or "")
        end = parse_day(params.get("to") or "")
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)
        return qs

    def list(self, request, *args, **kwargs):
        denied = self.filter_queryset(self.get_queryset()).filter(denied_filter()).count()
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict):
            response.data["denied"] = denied
        return response
