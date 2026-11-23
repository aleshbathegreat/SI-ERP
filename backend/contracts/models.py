from django.db import models

from core.models import AuditModel, Organization


class Contract(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="contracts"
    )
    contract_no = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    party_name = models.CharField(max_length=255, blank=True, default="")
    customer = models.ForeignKey(
        "ops.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commercial_contracts",
    )
    vendor = models.ForeignKey(
        "finance.Vendor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contracts",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contracts",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "contract_no")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.contract_no} — {self.title}"
