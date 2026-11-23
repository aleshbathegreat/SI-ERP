from django.conf import settings
from django.db import models

from accounts.models import Role
from core.models import AuditModel, Organization


class WorkTask(AuditModel):
    """Work a workflow assigns to a person or a role."""

    class Status(models.TextChoices):
        OPEN = "open", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        IN_REVIEW = "in_review", "In review"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="work_tasks"
    )
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True, default="")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_tasks",
    )
    role = models.ForeignKey(
        Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="work_tasks"
    )
    role_code = models.CharField(max_length=64, blank=True, default="")
    module = models.CharField(max_length=64, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    checklist = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-id"]
