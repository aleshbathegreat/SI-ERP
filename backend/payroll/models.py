from decimal import Decimal

from django.db import models

from core.models import AuditModel, Organization
from hr.models import Employee


class SalaryStructure(AuditModel):
    """Compensation template — earnings & statutory defaults (intl / PK practice)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="salary_structures"
    )
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    currency = models.CharField(max_length=3, default="PKR")
    basic = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    housing = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transport = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    medical = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    meal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Statutory defaults (% of basic) — used when generating slips
    income_tax_rate = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("5.000"))
    social_security_fixed = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("500"))
    provident_fund_rate = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("8.330"))
    employer_pf_rate = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("8.330"))
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]


class PayrollPeriod(AuditModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PROCESSING = "processing", "Processing"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="payroll_periods"
    )
    name = models.CharField(max_length=80)
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    pay_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="PKR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)
    gl_journal = models.ForeignKey(
        "finance.JournalEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payroll_periods",
    )

    class Meta:
        unique_together = ("organization", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return self.name


class Payslip(AuditModel):
    class PaymentMethod(models.TextChoices):
        BANK = "bank_transfer", "Bank transfer"
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"
        WALLET = "wallet", "Mobile wallet"

    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="payslips")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    currency = models.CharField(max_length=3, default="PKR")

    # Earnings (IAS 19 / register)
    basic = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    meal_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Legacy rollup kept for older clients
    allowances = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Employee statutory & other deductions
    income_tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)  # alias of income_tax
    social_security = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    eobi = models.DecimalField(max_digits=14, decimal_places=2, default=0)  # PK social security
    provident_fund = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pension = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    loan_repayment = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    advance_recovery = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Employer cost (not deducted from net)
    employer_provident_fund = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    employer_social_security = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    gross_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    employer_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    days_worked = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("30"))
    unpaid_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK
    )
    bank_account = models.CharField(max_length=64, blank=True)
    payment_reference = models.CharField(max_length=64, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ("period", "employee")
        ordering = ["-period_id", "employee_id"]

    def recompute(self):
        earn_parts = (
            self.basic,
            self.housing_allowance,
            self.transport_allowance,
            self.medical_allowance,
            self.meal_allowance,
            self.overtime,
            self.bonus,
            self.commission,
            self.other_earnings,
        )
        detail_allow = sum(earn_parts[1:], Decimal("0"))
        # Prefer detailed earnings; fall back to legacy allowances field
        if detail_allow or self.basic:
            self.allowances = detail_allow
            self.gross_pay = self.basic + detail_allow
        else:
            self.gross_pay = self.basic + (self.allowances or Decimal("0"))

        if self.income_tax and not self.tax:
            self.tax = self.income_tax
        elif self.tax and not self.income_tax:
            self.income_tax = self.tax
        else:
            self.tax = self.income_tax or self.tax or Decimal("0")
            self.income_tax = self.tax

        if self.eobi and not self.social_security:
            self.social_security = self.eobi
        elif self.social_security and not self.eobi:
            self.eobi = self.social_security
        else:
            self.eobi = self.social_security or self.eobi or Decimal("0")
            self.social_security = self.eobi

        statutory = (
            self.income_tax
            + self.social_security
            + self.provident_fund
            + self.pension
            + self.loan_repayment
            + self.advance_recovery
            + self.other_deductions
        )
        self.deductions = statutory
        self.total_deductions = statutory
        self.net_pay = self.gross_pay - statutory
        self.employer_cost = (
            self.gross_pay + self.employer_provident_fund + self.employer_social_security
        )
        return self

    def save(self, *args, **kwargs):
        self.recompute()
        super().save(*args, **kwargs)


class EmployeeLoan(AuditModel):
    class LoanType(models.TextChoices):
        PERSONAL = "personal", "Personal"
        HOUSING = "housing", "Housing / mortgage"
        VEHICLE = "vehicle", "Vehicle"
        SALARY_ADVANCE = "salary_advance", "Salary advance"
        EDUCATION = "education", "Education"
        MEDICAL = "medical", "Medical"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"
        WRITTEN_OFF = "written_off", "Written off"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employee_loans"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="loans")
    loan_number = models.CharField(max_length=40)
    loan_type = models.CharField(max_length=32, choices=LoanType.choices, default=LoanType.PERSONAL)
    currency = models.CharField(max_length=3, default="PKR")
    principal = models.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = models.DecimalField(
        max_digits=7, decimal_places=3, default=0, help_text="Annual interest %"
    )
    tenure_months = models.PositiveIntegerField(default=12)
    monthly_installment = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    disbursed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_repaid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    purpose = models.TextField(blank=True)
    guarantor = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="guaranteed_loans",
    )
    guarantor_name = models.CharField(max_length=120, blank=True)
    deduct_from_payroll = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "loan_number")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.loan_number} ({self.employee_id})"

    def compute_installment(self) -> Decimal:
        """Simple EMI: P * r*(1+r)^n / ((1+r)^n - 1); zero rate → principal/n."""
        p = Decimal(self.principal or 0)
        n = int(self.tenure_months or 1) or 1
        annual = Decimal(self.interest_rate or 0)
        if annual <= 0:
            return (p / n).quantize(Decimal("0.01"))
        r = (annual / Decimal("100")) / Decimal("12")
        factor = (1 + r) ** n
        emi = p * r * factor / (factor - 1)
        return emi.quantize(Decimal("0.01"))


class LoanRepayment(AuditModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    loan = models.ForeignKey(EmployeeLoan, on_delete=models.CASCADE, related_name="repayments")
    payslip = models.ForeignKey(
        Payslip, null=True, blank=True, on_delete=models.SET_NULL, related_name="loan_repayments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-due_date", "-id"]
