from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class ServiceCase(AuditModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING = "waiting", "Waiting on customer"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="service_cases"
    )
    case_no = models.CharField(max_length=64)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    customer = models.ForeignKey(
        "ops.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_cases",
    )
    sales_order = models.ForeignKey(
        "ops.SalesOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_cases",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_cases_assigned",
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    customer_invoice = models.ForeignKey(
        "finance.CustomerInvoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_cases",
    )

    class Meta:
        unique_together = ("organization", "case_no")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.case_no} — {self.subject}"


class ServiceNote(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="service_notes"
    )
    case = models.ForeignKey(
        ServiceCase, on_delete=models.CASCADE, related_name="notes"
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Note on {self.case_id}"


class ServicePart(models.Model):
    """Spare issued from stock against a service case."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="service_parts"
    )
    case = models.ForeignKey(
        ServiceCase, on_delete=models.CASCADE, related_name="parts"
    )
    item = models.ForeignKey(
        "ops.Item", on_delete=models.PROTECT, related_name="service_parts"
    )
    warehouse = models.ForeignKey(
        "ops.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_parts",
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    stock_movement = models.ForeignKey(
        "ops.StockMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_parts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.case_id} · {self.item_id} x {self.qty}"
