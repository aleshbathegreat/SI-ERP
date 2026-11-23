from decimal import Decimal

from django.db import models

from core.models import AuditModel, Organization


class Bom(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="boms"
    )
    item = models.ForeignKey(
        "ops.Item",
        on_delete=models.PROTECT,
        related_name="boms",
        help_text="Finished good",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"


class BomLine(models.Model):
    bom = models.ForeignKey(Bom, on_delete=models.CASCADE, related_name="lines")
    component = models.ForeignKey(
        "ops.Item", on_delete=models.PROTECT, related_name="bom_component_lines"
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("1"))

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.bom_id}:{self.component_id} x {self.qty}"


class WorkOrder(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RELEASED = "released", "Released"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="work_orders"
    )
    wo_no = models.CharField(max_length=64)
    bom = models.ForeignKey(
        Bom,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="work_orders",
    )
    item = models.ForeignKey(
        "ops.Item",
        on_delete=models.PROTECT,
        related_name="work_orders",
        help_text="Finished good (defaults from BOM)",
    )
    qty_planned = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    qty_completed = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    warehouse = models.ForeignKey(
        "ops.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "wo_no")
        ordering = ["-id"]

    def __str__(self):
        return self.wo_no
