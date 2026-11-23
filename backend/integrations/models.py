from django.db import models

from core.models import AuditModel, Organization


class IntegrationConnection(AuditModel):
    class Status(models.TextChoices):
        DISCONNECTED = "disconnected", "Not configured"
        CONFIGURED = "configured", "Configured"
        ACTIVE = "active", "Active"
        ERROR = "error", "Error"
        DISABLED = "disabled", "Disabled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="integration_connections"
    )
    connector_key = models.CharField(max_length=64, db_index=True)
    display_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DISCONNECTED
    )
    is_enabled = models.BooleanField(default=False)
    # Non-secret settings (URLs, IDs, flags)
    config = models.JSONField(default=dict, blank=True)
    # Secret material — stored as JSON; treat as confidential at rest
    secrets = models.JSONField(default=dict, blank=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(null=True, blank=True)
    last_test_message = models.CharField(max_length=512, blank=True, default="")
    last_error = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "connector_key")
        ordering = ["connector_key"]

    def __str__(self):
        return f"{self.organization_id}:{self.connector_key}"

    @property
    def secrets_set_keys(self) -> list[str]:
        return [k for k, v in (self.secrets or {}).items() if v]
