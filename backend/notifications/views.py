from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import NotificationRead
from core.scoping import OrgScopedQuerysetMixin
from notifications.models import InboxMessage

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


class InboxMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxMessage
        fields = (
            "id",
            "organization",
            "recipient",
            "title",
            "body",
            "href",
            "module",
            "object_id",
            "kind",
            "read_at",
            "created_at",
        )
        read_only_fields = RO + ("recipient", "title", "body", "href", "module", "object_id", "kind", "read_at")


class InboxMessageViewSet(OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = InboxMessage.objects.select_related("recipient")
    serializer_class = InboxMessageSerializer
    rbac_exempt = True

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        message = self.get_object()
        if message.read_at is None:
            message.read_at = timezone.now()
            message.save(update_fields=["read_at", "updated_at"])
        NotificationRead.objects.update_or_create(
            user=request.user,
            key=f"inbox-{message.id}"[:64],
            defaults={"source_stamp": message.created_at.isoformat()[:64]},
        )
        return Response(self.get_serializer(message).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        message = self.get_object()
        message.delete()
        return Response(status=204)
