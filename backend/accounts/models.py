from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization, TimeStampedModel


class Role(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=64)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.organization.code}:{self.name}"


class UserRole(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_links"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_links")

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user} · {self.role}"


class UserProfile(TimeStampedModel):
    class RoleCode(models.TextChoices):
        OWNER = "owner", "Organizational Super User"
        ADMIN = "admin", "Organizational Super User (Admin)"
        FINANCE = "finance", "Department Super User · Finance"
        HR = "hr", "Department Super User · HR"
        PAYROLL = "payroll", "Department Super User · Payroll"
        INITIATOR = "initiator", "Department Initiator"
        APPROVER = "approver", "Department Reviewer / Approver"
        EMPLOYEE = "employee", "Employee Self-Service User"
        VIEWER = "viewer", "Auditor"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="profiles",
        null=True,
        blank=True,
    )
    # Legacy single-role code used as default when UserRole rows are empty
    role = models.CharField(max_length=32, choices=RoleCode.choices, default=RoleCode.EMPLOYEE)
    primary_role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_members",
    )
    phone = models.CharField(max_length=32, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    is_active_member = models.BooleanField(default=True)
    mfa_secret = models.CharField(max_length=64, blank=True)
    mfa_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
