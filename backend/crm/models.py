from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import AuditModel, Organization


class Lead(AuditModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        LOST = "lost", "Lost"
        CONVERTED = "converted", "Converted"

    class Rating(models.TextChoices):
        COLD = "cold", "Cold"
        WARM = "warm", "Warm"
        HOT = "hot", "Hot"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="crm_leads"
    )
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="")
    industry = models.CharField(max_length=128, blank=True, default="")
    rating = models.CharField(
        max_length=10, choices=Rating.choices, default=Rating.WARM
    )
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    score = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    campaign = models.CharField(max_length=128, blank=True, default="")
    medium = models.CharField(max_length=64, blank=True, default="")
    next_follow_up = models.DateField(null=True, blank=True)
    lost_reason = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_leads_owned",
    )
    converted_customer = models.ForeignKey(
        "ops.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_from_leads",
    )
    converted_opportunity = models.ForeignKey(
        "crm.Opportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_from_leads",
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


RATING_SCORE = {
    Lead.Rating.COLD: 25,
    Lead.Rating.WARM: 50,
    Lead.Rating.HOT: 80,
}


class Opportunity(AuditModel):
    class Stage(models.TextChoices):
        PROSPECTING = "prospecting", "Prospecting"
        PROPOSAL = "proposal", "Proposal"
        NEGOTIATION = "negotiation", "Negotiation"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="crm_opportunities"
    )
    lead = models.ForeignKey(
        Lead,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities",
    )
    customer = models.ForeignKey(
        "ops.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_opportunities",
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.PROSPECTING
    )
    expected_close = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_opportunities_owned",
    )
    probability = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    priority = models.CharField(
        max_length=10, choices=Lead.Priority.choices, default=Lead.Priority.NORMAL
    )
    close_reason = models.CharField(max_length=255, blank=True, default="")
    won_on = models.DateField(null=True, blank=True)
    lost_on = models.DateField(null=True, blank=True)
    next_step = models.CharField(max_length=255, blank=True, default="")
    competitor = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "opportunities"

    def __str__(self):
        return self.name


STAGE_PROBABILITY = {
    Opportunity.Stage.PROSPECTING: 10,
    Opportunity.Stage.PROPOSAL: 40,
    Opportunity.Stage.NEGOTIATION: 70,
    Opportunity.Stage.WON: 100,
    Opportunity.Stage.LOST: 0,
}


class Activity(AuditModel):
    class Type(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        TASK = "task", "Task"
        NOTE = "note", "Note"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="crm_activities"
    )
    lead = models.ForeignKey(
        Lead,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    opportunity = models.ForeignKey(
        Opportunity,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.CALL)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    due_date = models.DateField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    done = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=255, blank=True, default="")
    external_events = models.JSONField(default=dict, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_activities_owned",
    )

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return self.subject
