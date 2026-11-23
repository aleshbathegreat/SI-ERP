from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class Project(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pm_projects"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    customer = models.ForeignKey(
        "ops.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pm_projects",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProjectTask(AuditModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pm_tasks"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    hours_est = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hours_logged = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class ProjectCost(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pm_costs"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="costs"
    )
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_center = models.ForeignKey(
        "finance.CostCenter",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_costs",
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.description


class TimeEntry(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pm_time_entries"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="time_entries"
    )
    task = models.ForeignKey(
        ProjectTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )
    employee = models.ForeignKey(
        "hr.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    billable = models.BooleanField(default=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pm_time_entries_submitted",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pm_time_entries_approved",
    )
    customer_invoice = models.ForeignKey(
        "finance.CustomerInvoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "time entries"

    def __str__(self):
        return f"{self.project_id}:{self.date} {self.hours}h"
