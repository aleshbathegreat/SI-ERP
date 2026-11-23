from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class RecordComment(AuditModel):
    """A note on any SIERP record, not only a document."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="record_comments"
    )
    module = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="record_comments",
    )

    class Meta:
        ordering = ["-id"]
