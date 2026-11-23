from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class InboxMessage(AuditModel):
    """In-app notice for one person. Workflows write these alongside email."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="inbox_messages"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inbox_messages",
    )
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True, default="")
    href = models.CharField(max_length=255, blank=True, default="")
    module = models.CharField(max_length=64, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    kind = models.CharField(max_length=20, default="workflow")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
