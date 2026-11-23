from django.conf import settings
from django.db import models

from core.softdelete import AllObjectsManager, SoftDeleteManager, soft_delete_instance


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_deleted",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        soft_delete_instance(self)
        return 1, {self._meta.label: 1}

    def save(self, *args, **kwargs):
        from core.uniqueness import reconcile_unique_on_create

        if reconcile_unique_on_create(self):
            return
        super().save(*args, **kwargs)


class SubscriptionPackage(models.Model):
    class Interval(models.TextChoices):
        TRIAL = "trial", "Trial"
        MONTH = "month", "Monthly"
        YEAR = "year", "Annual"

    name = models.CharField(max_length=128)
    code = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interval = models.CharField(max_length=16, choices=Interval.choices, default=Interval.MONTH)
    summary = models.CharField(max_length=255, blank=True)
    module_keys = models.JSONField(
        default=list,
        blank=True,
        help_text="Assignable product modules (finance.*/hr.*/payroll.*/billing)",
    )
    core_module_keys = models.JSONField(
        default=list,
        blank=True,
        help_text="Always-on shell modules; empty = platform default core set",
    )
    max_functional_users = models.PositiveIntegerField(default=10)
    max_ess_users = models.PositiveIntegerField(default=25)
    max_attendance_devices = models.PositiveIntegerField(
        default=0,
        help_text="Max attendance devices for tenants on this package (0 = none)",
    )
    attendance_connectors = models.JSONField(
        default=list,
        blank=True,
        help_text='Allowed connector keys from catalog; use ["*"] for all',
    )
    active = models.BooleanField(default=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "price", "name"]

    def __str__(self):
        return self.name


class Organization(TimeStampedModel):
    class Plan(models.TextChoices):
        TRIAL = "trial", "Trial"
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    class PlanStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=50, unique=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    ntn = models.CharField(max_length=32, blank=True)
    strn = models.CharField(max_length=32, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Karachi")
    currency = models.CharField(
        max_length=3,
        default="PKR",
        help_text="Default tenant currency for payroll and finance",
    )
    is_active = models.BooleanField(default=True)
    plan = models.CharField(max_length=16, choices=Plan.choices, default=Plan.TRIAL)
    plan_status = models.CharField(
        max_length=16, choices=PlanStatus.choices, default=PlanStatus.ACTIVE
    )
    trial_ends = models.DateField(null=True, blank=True)
    subscription_ends = models.DateField(null=True, blank=True)
    grace_days = models.PositiveIntegerField(
        default=7,
        help_text="Days after trial/subscription end before hard lock (past_due → canceled)",
    )
    last_dunning_at = models.DateTimeField(null=True, blank=True)
    package = models.ForeignKey(
        SubscriptionPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="organizations",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_organizations",
    )
    # SaaS multi-domain: {code}.{PLATFORM_ROOT_DOMAIN} always; optional custom host
    custom_domain = models.CharField(
        max_length=253,
        blank=True,
        default="",
        db_index=True,
        help_text="Custom hostname e.g. erp.client.com (verified before active)",
    )
    custom_domain_verified = models.BooleanField(default=False)
    domain_verify_token = models.CharField(max_length=64, blank=True, default="")
    domain_verified_at = models.DateTimeField(null=True, blank=True)
    brand_name = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Shown on login when visiting this tenant's domain",
    )
    brand_tagline = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text="Short line under brand name (login, shell)",
    )
    brand_primary_color = models.CharField(max_length=16, blank=True, default="#1B6A94")
    brand_secondary_color = models.CharField(max_length=16, blank=True, default="#C45C26")
    brand_logo = models.ImageField(
        upload_to="branding/logos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Primary logo (light backgrounds)",
    )
    brand_logo_dark = models.ImageField(
        upload_to="branding/logos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional logo for dark UI; falls back to brand_logo",
    )
    brand_favicon = models.ImageField(
        upload_to="branding/favicons/%Y/%m/",
        blank=True,
        null=True,
        help_text="Browser tab icon (PNG/ICO/SVG)",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.custom_domain:
            self.custom_domain = self.custom_domain.strip().lower().rstrip(".")
        super().save(*args, **kwargs)


class CompanyLink(models.Model):
    """User may belong to multiple tenant companies (desk-inspired)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_links"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="user_links"
    )

    class Meta:
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user} · {self.organization}"


class OrgRecord(AuditModel):
    """Abstract tenant-scoped record — all ERP data inherits organization FK."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="%(class)s_rows"
    )

    class Meta:
        abstract = True


class SubscriptionPayment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        NEW = "new", "New"
        RENEWAL = "renewal", "Renewal"
        UPGRADE = "upgrade", "Upgrade"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="payments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="subscription_payments",
    )
    plan = models.CharField(max_length=16)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.NEW)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="PKR")
    reference = models.CharField(max_length=64, unique=True)
    environment = models.CharField(max_length=16, default="sandbox", blank=True)
    basket_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    transaction_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    status_code = models.CharField(max_length=16, blank=True, default="")
    status_message = models.CharField(max_length=255, blank=True, default="")
    instrument_alias = models.CharField(max_length=64, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class AuditLog(TimeStampedModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=64)
    module = models.CharField(max_length=64, blank=True)
    object_type = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class _PayFastCredentialMixin:
    """Shared Premier PayFast sandbox/live credential helpers."""

    class Environment(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        LIVE = "live", "Live"

    @property
    def is_live(self):
        return self.environment == self.Environment.LIVE

    @property
    def api_base(self):
        base = self.live_api_base if self.is_live else self.sandbox_api_base
        return (base or "").rstrip("/")

    @property
    def merchant_id(self):
        return self.live_merchant_id if self.is_live else self.sandbox_merchant_id

    @property
    def secured_key(self):
        return self.live_secured_key if self.is_live else self.sandbox_secured_key

    @property
    def hash_key(self):
        chosen = self.live_hash_key if self.is_live else self.sandbox_hash_key
        return chosen or self.secured_key

    @property
    def ready(self):
        return bool(self.api_base and self.merchant_id and self.secured_key and self.hash_key)

    def get_environment_display(self):
        return dict(self.Environment.choices).get(self.environment, self.environment)


class PayFastSettings(_PayFastCredentialMixin, models.Model):
    """Singleton — platform Premier PayFast for SaaS subscription billing."""

    environment = models.CharField(
        max_length=16,
        choices=_PayFastCredentialMixin.Environment.choices,
        default=_PayFastCredentialMixin.Environment.SANDBOX,
    )
    sandbox_api_base = models.URLField(default="https://ipguat.apps.net.pk/Ecommerce/api")
    sandbox_merchant_id = models.CharField(max_length=128, blank=True, default="")
    sandbox_secured_key = models.CharField(max_length=255, blank=True, default="")
    sandbox_hash_key = models.CharField(max_length=255, blank=True, default="")
    live_api_base = models.URLField(default="https://ipg1.apps.net.pk/Ecommerce/api")
    live_merchant_id = models.CharField(max_length=128, blank=True, default="")
    live_secured_key = models.CharField(max_length=255, blank=True, default="")
    live_hash_key = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform PayFast gateway"
        verbose_name_plural = "Platform PayFast gateway"

    def __str__(self):
        return f"Premier PayFast · {self.get_environment_display()}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TenantPayGateway(_PayFastCredentialMixin, models.Model):
    """Optional per-tenant Premier PayFast (tenant-owned payments, not SaaS billing)."""

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="pay_gateway"
    )
    environment = models.CharField(
        max_length=16,
        choices=_PayFastCredentialMixin.Environment.choices,
        default=_PayFastCredentialMixin.Environment.SANDBOX,
    )
    sandbox_api_base = models.URLField(default="https://ipguat.apps.net.pk/Ecommerce/api")
    sandbox_merchant_id = models.CharField(max_length=128, blank=True, default="")
    sandbox_secured_key = models.CharField(max_length=255, blank=True, default="")
    sandbox_hash_key = models.CharField(max_length=255, blank=True, default="")
    live_api_base = models.URLField(default="https://ipg1.apps.net.pk/Ecommerce/api")
    live_merchant_id = models.CharField(max_length=128, blank=True, default="")
    live_secured_key = models.CharField(max_length=255, blank=True, default="")
    live_hash_key = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PayFast · {self.organization.code}"


class PlatformSmtpSettings(TimeStampedModel):
    """Singleton — platform owner SMTP for system emails (signup, billing, alerts)."""

    host = models.CharField(max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(blank=True, default="")
    from_name = models.CharField(max_length=128, blank=True, default="SIGBL ERP")
    reply_to = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Platform SMTP settings"
        verbose_name_plural = "Platform SMTP settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TenantSmtpSettings(TimeStampedModel):
    """Per-tenant SMTP for workflow / HR / finance emails."""

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="smtp_settings"
    )
    host = models.CharField(max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(blank=True, default="")
    from_name = models.CharField(max_length=128, blank=True, default="")
    reply_to = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"SMTP · {self.organization.code}"


class TenantEmailProfile(AuditModel):
    """A mailbox identity. A tenant may keep several: shared, per user, or per employee."""

    class Purpose(models.TextChoices):
        GENERAL = "general", "General"
        WORKFLOW = "workflow", "Workflow / Approvals"
        HR = "hr", "HR / ESS"
        FINANCE = "finance", "Finance"
        PAYROLL = "payroll", "Payroll"
        BILLING = "billing", "Billing"
        CRM = "crm", "CRM"

    class OwnerType(models.TextChoices):
        SHARED = "shared", "Shared mailbox"
        USER = "user", "Full user"
        EMPLOYEE = "employee", "Employee"

    class Inbound(models.TextChoices):
        NONE = "none", "Send only"
        GRAPH = "graph", "Microsoft 365 inbox"
        IMAP = "imap", "IMAP inbox"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="email_profiles"
    )
    name = models.CharField(max_length=128)
    email = models.EmailField()
    purpose = models.CharField(
        max_length=32, choices=Purpose.choices, default=Purpose.GENERAL
    )
    reply_to = models.EmailField(blank=True, default="")
    signature = models.TextField(blank=True, default="")
    owner_type = models.CharField(
        max_length=16, choices=OwnerType.choices, default=OwnerType.SHARED
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_profiles",
    )
    employee = models.ForeignKey(
        "hr.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_profiles",
    )
    inbound = models.CharField(
        max_length=16, choices=Inbound.choices, default=Inbound.NONE
    )
    imap_host = models.CharField(max_length=255, blank=True, default="")
    imap_port = models.PositiveIntegerField(default=993)
    imap_username = models.CharField(max_length=255, blank=True, default="")
    imap_password = models.CharField(max_length=255, blank=True, default="")
    imap_use_ssl = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "email")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            TenantEmailProfile.objects.filter(organization=self.organization).exclude(
                pk=self.pk
            ).update(is_default=False)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class MailMessage(AuditModel):
    """Tracked copy of mail sent or received through a tenant mailbox."""

    class Direction(models.TextChoices):
        OUT = "out", "Sent"
        IN = "in", "Received"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        RECEIVED = "received", "Received"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="mail_messages"
    )
    profile = models.ForeignKey(
        TenantEmailProfile, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=8, choices=Direction.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    from_email = models.EmailField(blank=True, default="")
    to_emails = models.CharField(max_length=500, blank=True, default="")
    message_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    error = models.TextField(blank=True, default="")
    lead = models.ForeignKey(
        "crm.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mail_messages",
    )
    opportunity = models.ForeignKey(
        "crm.Opportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mail_messages",
    )
    occurred_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "message_id"],
                condition=~models.Q(message_id=""),
                name="uniq_org_mail_message_id",
            )
        ]

    def __str__(self):
        return self.subject or self.message_id or f"Mail {self.pk}"


class EmailTemplate(AuditModel):
    """Reusable subject/body templates for tenant outbound mail."""

    class Purpose(models.TextChoices):
        GENERAL = "general", "General"
        WORKFLOW = "workflow", "Workflow / Approvals"
        HR = "hr", "HR / ESS"
        FINANCE = "finance", "Finance"
        PAYROLL = "payroll", "Payroll"
        BILLING = "billing", "Billing"
        SALES = "sales", "Sales"
        PROCUREMENT = "procurement", "Procurement"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="email_templates"
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    purpose = models.CharField(
        max_length=32, choices=Purpose.choices, default=Purpose.GENERAL
    )
    subject = models.CharField(max_length=255)
    body_text = models.TextField(help_text="Plain text body. Use {{var}} placeholders.")
    body_html = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["purpose", "code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def render(self, context: dict | None = None) -> tuple[str, str, str]:
        """Simple {{key}} substitution. Returns subject, text, html."""
        ctx = {str(k): str(v) for k, v in (context or {}).items()}

        def _sub(template: str) -> str:
            out = template or ""
            for k, v in ctx.items():
                out = out.replace("{{" + k + "}}", v)
            return out

        return _sub(self.subject), _sub(self.body_text), _sub(self.body_html)


class SaaSInvoice(TimeStampedModel):
    """Platform → tenant subscription invoice (not tenant AP VendorInvoice)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="saas_invoices"
    )
    invoice_no = models.CharField(max_length=32, unique=True)
    package = models.ForeignKey(
        SubscriptionPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    plan_code = models.CharField(max_length=32, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="PKR")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment = models.ForeignKey(
        SubscriptionPayment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="saas_invoices_created",
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.invoice_no

    def recompute_total(self):
        self.total = (self.amount or 0) + (self.tax_amount or 0)


class SupportTicket(TimeStampedModel):
    """Support channel between tenant users and platform staff."""

    class Category(models.TextChoices):
        BILLING = "billing", "Billing"
        TECHNICAL = "technical", "Technical"
        SALES = "sales", "Sales"
        GENERAL = "general", "General"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING = "waiting", "Waiting on tenant"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="support_tickets"
    )
    ticket_no = models.CharField(max_length=32, unique=True)
    subject = models.CharField(max_length=200)
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.GENERAL
    )
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_created",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_assigned",
    )
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.ticket_no


class SupportTicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name="messages"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_messages",
    )
    body = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal platform note — hidden from tenant users",
    )
    is_from_platform = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]


class PlatformStaff(TimeStampedModel):
    """Non-tenant platform operators with scoped SaaS capabilities."""

    class Role(models.TextChoices):
        OWNER = "owner", "Platform owner"
        FINANCE = "finance", "Finance team"
        SALES = "sales", "Sales team"
        SUPPORT = "support", "Support team"
        TECHNICAL = "technical", "Technical team"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_staff",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.SUPPORT)
    is_active = models.BooleanField(default=True)
    title = models.CharField(max_length=128, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["role", "user__username"]

    def __str__(self):
        return f"{self.user.username} · {self.role}"


class NotificationRead(TimeStampedModel):
    """Per-user read receipts for inbox items (re-opens when source_stamp changes)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_reads",
    )
    key = models.CharField(max_length=64, db_index=True)
    source_stamp = models.CharField(
        max_length=64,
        help_text="Item version when marked read — newer stamp = unread again",
    )
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "key")
        ordering = ["-read_at"]

    def __str__(self):
        return f"{self.user_id}:{self.key}"


class DocNumberSeries(AuditModel):
    """Configurable document number series per org/kind (preferred by ensure_doc_no)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="doc_number_series"
    )
    kind = models.CharField(max_length=32, help_text="e.g. po, invoice, so, grn")
    prefix = models.CharField(max_length=32, default="")
    next_number = models.PositiveIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=5)
    reset_yearly = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "kind")
        ordering = ["kind"]
        verbose_name_plural = "Doc number series"

    def __str__(self):
        return f"{self.kind} · {self.prefix}"


class ApprovalMatrixRule(AuditModel):
    """Amount-band approval matrix (configuration master; LoA runtime unchanged)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="approval_matrix_rules"
    )
    module_key = models.CharField(max_length=64)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Blank = no upper bound",
    )
    role_code = models.CharField(max_length=64)

    class Meta:
        ordering = ["module_key", "min_amount", "id"]

    def __str__(self):
        return f"{self.module_key} · {self.role_code}"
