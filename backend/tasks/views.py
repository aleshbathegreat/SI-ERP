from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import UserRole
from core.access import is_owner
from core.scoping import OrgScopedQuerysetMixin
from tasks.models import WorkTask

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)


class WorkTaskSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True, default="")

    class Meta:
        model = WorkTask
        fields = (
            "id",
            "organization",
            "title",
            "body",
            "assignee",
            "role",
            "role_name",
            "role_code",
            "module",
            "object_id",
            "status",
            "priority",
            "due_date",
            "checklist",
            "created_at",
        )
        read_only_fields = RO + ("role_name",)


class WorkTaskViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkTask.objects.select_related("role", "assignee")
    serializer_class = WorkTaskSerializer
    filterset_fields = ("status", "module", "object_id")
    search_fields = ("title", "body")
    rbac_exempt = True
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_owner(user):
            return qs
        role_ids = list(UserRole.objects.filter(user=user).values_list("role_id", flat=True))
        profile = getattr(user, "profile", None)
        code = profile.role if profile else ""
        query = Q(assignee=user) | Q(role_id__in=role_ids)
        if code:
            query |= Q(role_code=code) | Q(role__code=code)
        return qs.filter(query)

    def perform_create(self, serializer):
        from core.access import user_organization

        serializer.save(
            organization=user_organization(self.request.user),
            created_by=self.request.user,
            assignee=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = WorkTask.Status.DONE
        task.updated_by = request.user
        task.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(self.get_serializer(task).data)
