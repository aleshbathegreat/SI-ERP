from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import AuditModel, Organization


class QualityInspection(AuditModel):
    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        CONDITIONAL = "conditional", "Conditional"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="quality_inspections"
    )
    inspection_no = models.CharField(max_length=64)
    grn = models.ForeignKey(
        "ops.GoodsReceipt",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_inspections",
    )
    item = models.ForeignKey(
        "ops.Item", on_delete=models.PROTECT, related_name="quality_inspections"
    )
    warehouse = models.ForeignKey(
        "ops.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_inspections",
    )
    result = models.CharField(
        max_length=20, choices=Result.choices, default=Result.PASS
    )
    qty_inspected = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_rejected = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_released = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        help_text="Quantity this inspection has released from QC hold.",
    )
    notes = models.TextField(blank=True, default="")
    inspected_at = models.DateTimeField(default=timezone.now)
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_inspections_done",
    )

    class Meta:
        unique_together = ("organization", "inspection_no")
        ordering = ["-inspected_at", "-id"]

    def __str__(self):
        return self.inspection_no


class Ncr(AuditModel):
    """Non-conformance report."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        CLOSED = "closed", "Closed"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Disposition(models.TextChoices):
        REWORK = "rework", "Rework"
        SCRAP = "scrap", "Scrap"
        USE_AS_IS = "use_as_is", "Use as is"
        RETURN_VENDOR = "return_vendor", "Return to vendor"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="ncrs"
    )
    ncr_no = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    source_inspection = models.ForeignKey(
        QualityInspection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ncrs",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.MEDIUM
    )
    description = models.TextField(blank=True, default="")
    disposition = models.CharField(
        max_length=20, choices=Disposition.choices, blank=True, default=""
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organization", "ncr_no")
        ordering = ["-id"]
        verbose_name = "NCR"

    def __str__(self):
        return f"{self.ncr_no} — {self.title}"


class Capa(AuditModel):
    """Corrective / preventive action tied to an NCR."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="capas"
    )
    ncr = models.ForeignKey(Ncr, on_delete=models.CASCADE, related_name="capas")
    action = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="capas_owned",
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "CAPA"

    def __str__(self):
        return f"CAPA {self.pk} · NCR {self.ncr_id}"
