from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class AccountType(AuditModel):
    """Tenant-defined GL account types (extendable beyond classic 5)."""

    class StatementClass(models.TextChoices):
        ASSET = "asset", "Asset (Balance sheet)"
        LIABILITY = "liability", "Liability (Balance sheet)"
        EQUITY = "equity", "Equity (Balance sheet)"
        INCOME = "income", "Income (P&L)"
        EXPENSE = "expense", "Expense (P&L)"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="account_types"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    statement_class = models.CharField(
        max_length=20,
        choices=StatementClass.choices,
        default=StatementClass.EXPENSE,
        help_text="Drives TB / P&L / BS bucketing",
    )
    is_system = models.BooleanField(
        default=False, help_text="Seeded classic types — code locked"
    )
    is_active = models.BooleanField(default=True)
    sort = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["sort", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


DEFAULT_ACCOUNT_TYPES = (
    ("asset", "Asset", "asset", 10),
    ("liability", "Liability", "liability", 20),
    ("equity", "Equity", "equity", 30),
    ("income", "Income", "income", 40),
    ("expense", "Expense", "expense", 50),
)


def ensure_default_account_types(organization) -> list[str]:
    created = []
    for code, name, stmt, sort in DEFAULT_ACCOUNT_TYPES:
        _, was = AccountType.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={
                "name": name,
                "statement_class": stmt,
                "is_system": True,
                "is_active": True,
                "sort": sort,
            },
        )
        if was:
            created.append(code)
    return created


class Account(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="accounts"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    # Stores AccountType.code (org-scoped catalog — dynamic / addable)
    account_type = models.CharField(max_length=32, default="expense")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def statement_class(self) -> str:
        at = AccountType.objects.filter(
            organization_id=self.organization_id, code=self.account_type
        ).first()
        if at:
            return at.statement_class
        if self.account_type in AccountType.StatementClass.values:
            return self.account_type
        return "expense"


class CostCenter(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="cost_centers"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.code} - {self.name}"


class Vendor(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vendors"
    )
    code = models.CharField(max_length=32, blank=True, default="")
    name = models.CharField(max_length=255)
    ntn = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    category = models.CharField(max_length=64, blank=True)
    contact_person = models.CharField(max_length=120, blank=True, default="")
    payment_terms_days = models.PositiveIntegerField(default=30)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=80, blank=True, default="Pakistan")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class JournalEntry(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        POSTED = "posted", "Posted"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="journals"
    )
    entry_date = models.DateField()
    reference = models.CharField(max_length=64, blank=True)
    narration = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journals_submitted",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journals_approved",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"JE-{self.pk} ({self.status})"


class JournalLine(models.Model):
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    cost_center = models.ForeignKey(
        CostCenter, null=True, blank=True, on_delete=models.SET_NULL
    )
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)


class Budget(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        LOCKED = "locked", "Locked"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="budgets"
    )
    name = models.CharField(max_length=128)
    fiscal_year = models.PositiveIntegerField()
    cost_center = models.ForeignKey(
        CostCenter, null=True, blank=True, on_delete=models.SET_NULL
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    utilized = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-fiscal_year", "name"]


class VendorInvoice(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vendor_invoices"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    purchase_order = models.ForeignKey(
        "ops.PurchaseOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendor_invoices",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendor_invoices",
    )
    invoice_no = models.CharField(max_length=64)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    wht_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="ap/invoices/%Y/%m/", blank=True, null=True
    )
    payment_ref = models.CharField(max_length=64, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Light FX: amounts stay in invoice currency; GL posts in org base currency using
    # fx_rate (looked up from FxRate at accrual). Full FX engine (revaluation) later.
    currency = models.CharField(max_length=8, default="PKR")
    fx_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)

    class Meta:
        unique_together = ("organization", "vendor", "invoice_no")
        ordering = ["-invoice_date"]


class CustomerInvoice(AuditModel):
    """Accounts receivable invoice (order-to-cash)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="customer_invoices"
    )
    customer = models.ForeignKey(
        "ops.Customer", on_delete=models.PROTECT, related_name="ar_invoices"
    )
    sales_order = models.ForeignKey(
        "ops.SalesOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_invoices",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_invoices",
    )
    invoice_no = models.CharField(max_length=64)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    payment_ref = models.CharField(max_length=64, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    fx_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)

    class Meta:
        unique_together = ("organization", "invoice_no")
        ordering = ["-invoice_date"]


class BankAccount(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="bank_accounts"
    )
    name = models.CharField(max_length=128)
    bank_name = models.CharField(max_length=128)
    account_no = models.CharField(max_length=64)
    currency = models.CharField(max_length=8, default="PKR")
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_reconciled = models.DateField(null=True, blank=True)
    gl_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bank_accounts",
        help_text="Linked cash/bank GL account for payment auto-posting",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "account_no")

    def __str__(self):
        return f"{self.name} ({self.account_no})"


class BankReconciliation(AuditModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MATCHED = "matched", "Matched"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="bank_reconciliations"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="reconciliations"
    )
    statement_date = models.DateField()
    statement_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    book_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)


class Investment(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="investments"
    )
    name = models.CharField(max_length=128)
    instrument_type = models.CharField(max_length=64, default="TDR")
    principal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    rate_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    start_date = models.DateField()
    maturity_date = models.DateField()
    fund_tag = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, default="active")


class FixedAsset(AuditModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IN_REPAIR = "in_repair", "In repair"
        IDLE = "idle", "Idle"
        DISPOSED = "disposed", "Disposed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="fixed_assets"
    )
    asset_code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=64, blank=True)
    location = models.CharField(max_length=128, blank=True)
    custodian = models.CharField(max_length=128, blank=True)
    assigned_employee = models.ForeignKey(
        "hr.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_assets",
    )
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    depreciation_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    book_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    accumulated_depreciation = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.ACTIVE
    )
    disposed_on = models.DateField(null=True, blank=True)
    disposal_proceeds = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    disposal_date = models.DateField(null=True, blank=True)
    disposal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cip_flag = models.BooleanField(default=False, help_text="Capital work in progress")

    class Meta:
        unique_together = ("organization", "asset_code")
        ordering = ["asset_code"]

    def __str__(self):
        return f"{self.asset_code} — {self.name}"


class AssetDepreciationRun(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="asset_depreciation_runs"
    )
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organization", "period_year", "period_month")
        ordering = ["-period_year", "-period_month"]

    def __str__(self):
        return f"{self.period_year}-{self.period_month:02d}"


class EInvoiceSubmission(AuditModel):
    """Canonical FBR / PRAL e-invoice submission (FbrInvoiceSubmission is deprecated)."""

    class FbrStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="e_invoice_submissions"
    )
    ar_invoice = models.ForeignKey(
        CustomerInvoice,
        on_delete=models.CASCADE,
        related_name="e_invoice_submissions",
    )
    fbr_status = models.CharField(
        max_length=20, choices=FbrStatus.choices, default=FbrStatus.DRAFT
    )
    fbr_invoice_no = models.CharField(max_length=64, blank=True, default="")
    provider_ref = models.CharField(max_length=128, blank=True, default="")
    mode = models.CharField(
        max_length=16, blank=True, default="", help_text="sandbox | live"
    )
    error_message = models.TextField(blank=True, default="")
    payload_json = models.JSONField(default=dict, blank=True)
    response_json = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"FBR · {self.ar_invoice_id} · {self.fbr_status}"


class AssetRepair(AuditModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="asset_repairs"
    )
    asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE, related_name="repairs"
    )
    request_no = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.REQUESTED
    )
    requested_on = models.DateField(null=True, blank=True)
    completed_on = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vendor_name = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "request_no")
        ordering = ["-requested_on", "-id"]

    def __str__(self):
        return f"{self.request_no} — {self.title}"


class PmSchedule(AuditModel):
    """Preventive-maintenance schedule for a fixed asset (CMMS)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pm_schedules"
    )
    asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE, related_name="pm_schedules"
    )
    title = models.CharField(max_length=255)
    frequency_days = models.PositiveIntegerField(default=30)
    last_done = models.DateField(null=True, blank=True)
    next_due = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_due", "id"]

    def __str__(self):
        return f"{self.asset_id} — {self.title}"


class MaintenanceWorkOrder(AuditModel):
    """CMMS work order (corrective or generated from a PM schedule)."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="maintenance_orders"
    )
    mwo_no = models.CharField(max_length=64)
    asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE, related_name="maintenance_orders"
    )
    pm_schedule = models.ForeignKey(
        PmSchedule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    scheduled_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_orders_assigned",
    )

    class Meta:
        unique_together = ("organization", "mwo_no")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.mwo_no} — {self.title}"


class MaintenancePart(models.Model):
    """Spare issued from stock against a maintenance work order."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="maintenance_parts"
    )
    work_order = models.ForeignKey(
        MaintenanceWorkOrder, on_delete=models.CASCADE, related_name="parts"
    )
    item = models.ForeignKey(
        "ops.Item", on_delete=models.PROTECT, related_name="maintenance_parts"
    )
    warehouse = models.ForeignKey(
        "ops.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_parts",
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    stock_movement = models.ForeignKey(
        "ops.StockMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_parts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.work_order_id} · {self.item_id} x {self.qty}"


class TaxCode(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tax_codes"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    tax_type = models.CharField(max_length=32, default="wht")
    rate_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")


class AccountingPeriod(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="accounting_periods"
    )
    name = models.CharField(max_length=64)
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    is_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "year", "month")
        ordering = ["-year", "-month"]


class TaxChallan(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tax_challans"
    )
    challan_no = models.CharField(max_length=64)
    tax_type = models.CharField(max_length=32, default="wht")
    period_label = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default="draft")
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "challan_no")


class BankStatementLine(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="bank_statement_lines"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="statement_lines"
    )
    txn_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reference = models.CharField(max_length=128, blank=True, default="")
    matched = models.BooleanField(default=False)
    reconciliation = models.ForeignKey(
        BankReconciliation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lines",
    )


class AssetDepreciationLine(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="asset_depreciation_lines"
    )
    asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE, related_name="depreciation_lines"
    )
    run_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-run_date", "-id"]

    def __str__(self):
        return f"{self.asset_id} @ {self.run_date}"


class FbrInvoiceSubmission(AuditModel):
    """DEPRECATED — use EInvoiceSubmission. Kept read-only for legacy rows."""

    class InvoiceType(models.TextChoices):
        AR = "ar", "AR"
        AP = "ap", "AP"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUEUED = "queued", "Queued"
        SUBMITTED = "submitted", "Submitted"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="fbr_submissions"
    )
    invoice_type = models.CharField(
        max_length=8, choices=InvoiceType.choices, default=InvoiceType.AR
    )
    local_invoice_id = models.CharField(max_length=64)
    fbr_invoice_no = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    payload_json = models.TextField(blank=True, default="")
    response_json = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.invoice_type}:{self.local_invoice_id}"


class Currency(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="currencies"
    )
    code = models.CharField(max_length=8)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    sort = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["sort", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


DEFAULT_CURRENCIES = (
    ("PKR", "Pakistani Rupee", 10),
    ("USD", "US Dollar", 20),
    ("EUR", "Euro", 30),
    ("GBP", "British Pound", 40),
    ("AED", "UAE Dirham", 50),
    ("SAR", "Saudi Riyal", 60),
    ("CNY", "Chinese Yuan", 70),
    ("INR", "Indian Rupee", 80),
)


def ensure_default_currencies(organization) -> list[str]:
    created = []
    for code, name, sort in DEFAULT_CURRENCIES:
        if Currency.all_objects.filter(organization=organization, code=code).exists():
            continue
        Currency.objects.create(
            organization=organization,
            code=code,
            name=name,
            is_active=True,
            sort=sort,
        )
        created.append(code)
    return created


class FxRate(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="fx_rates"
    )
    currency_from = models.CharField(max_length=8)
    currency_to = models.CharField(max_length=8)
    rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    rate_date = models.DateField()

    class Meta:
        unique_together = ("organization", "currency_from", "currency_to", "rate_date")
        ordering = ["-rate_date", "currency_from", "currency_to"]

    def __str__(self):
        return f"{self.currency_from}/{self.currency_to} @ {self.rate_date}"


class ChequeRegister(AuditModel):
    class Status(models.TextChoices):
        ISSUED = "issued", "Issued"
        CLEARED = "cleared", "Cleared"
        BOUNCED = "bounced", "Bounced"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="cheques"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, related_name="cheques"
    )
    cheque_no = models.CharField(max_length=64)
    payee = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cheque_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ISSUED
    )
    is_pdc = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    cleared_date = models.DateField(null=True, blank=True)
    bounced_date = models.DateField(null=True, blank=True)
    bounce_reason = models.CharField(max_length=255, blank=True, default="")
    gl_journal = models.ForeignKey(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cheques",
    )

    class Meta:
        ordering = ["-cheque_date", "-id"]

    def __str__(self):
        return f"{self.cheque_no} — {self.payee}"


class IntercompanyPartner(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="ic_partners"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=8, default="PKR")
    receivable_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ic_receivable_partners",
    )
    payable_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ic_payable_partners",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class IntercompanyTxn(AuditModel):
    class Direction(models.TextChoices):
        RECEIVABLE = "receivable", "Receivable"
        PAYABLE = "payable", "Payable"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="ic_txns"
    )
    partner = models.ForeignKey(
        IntercompanyPartner, on_delete=models.PROTECT, related_name="txns"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    direction = models.CharField(
        max_length=20, choices=Direction.choices, default=Direction.RECEIVABLE
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    reference = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    gl_journal = models.ForeignKey(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ic_txns",
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.partner_id} {self.direction} {self.amount}"


class TaxReturn(AuditModel):
    class ReturnType(models.TextChoices):
        SALES_TAX = "sales_tax", "Sales tax"
        WHT = "wht", "Withholding tax"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FILED = "filed", "Filed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tax_returns"
    )
    return_type = models.CharField(
        max_length=20, choices=ReturnType.choices, default=ReturnType.SALES_TAX
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    totals = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")
    filed_at = models.DateTimeField(null=True, blank=True)
    filing_ref = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-period_end", "-id"]

    def __str__(self):
        return f"{self.return_type} {self.period_start}..{self.period_end}"


class TaxReturnLine(models.Model):
    class LineType(models.TextChoices):
        CHARGE = "charge", "Tax charge"
        DEPOSIT = "deposit", "Deposit / challan"

    tax_return = models.ForeignKey(
        TaxReturn, on_delete=models.CASCADE, related_name="lines"
    )
    line_type = models.CharField(
        max_length=16, choices=LineType.choices, default=LineType.CHARGE
    )
    description = models.CharField(max_length=255, blank=True, default="")
    tax_code = models.CharField(max_length=32, blank=True, default="")
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    source_type = models.CharField(max_length=32, blank=True, default="")
    source_id = models.PositiveIntegerField(null=True, blank=True)
    source_ref = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["id"]


class SavedReport(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="saved_reports"
    )
    name = models.CharField(max_length=128)
    report_key = models.CharField(max_length=64)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name", "-id"]

    def __str__(self):
        return f"{self.name} ({self.report_key})"
