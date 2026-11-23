from datetime import time

from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class Department(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self):
        return self.name


class Designation(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="designations"
    )
    title = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    grade = models.CharField(
        max_length=32, blank=True, default="", help_text="Band / grade (e.g. G5, M2)"
    )

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self):
        return self.title


class Shift(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="shifts"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=120)
    start_time = models.TimeField(default=time(9, 0))
    end_time = models.TimeField(default=time(18, 0))
    grace_minutes = models.PositiveIntegerField(default=15)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class OvertimePolicy(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="overtime_policies"
    )
    name = models.CharField(max_length=120)
    weekday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    weekend_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2)
    holiday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(AuditModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PROBATION = "probation", "Probation"
        ON_LEAVE = "on_leave", "On Leave"
        SUSPENDED = "suspended", "Suspended"
        SEPARATED = "separated", "Separated"

    class ContractType(models.TextChoices):
        PERMANENT = "permanent", "Permanent"
        CONTRACT = "contract", "Contract"
        INTERN = "intern", "Intern"
        CONSULTANT = "consultant", "Consultant"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employees"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employee",
    )
    employee_code = models.CharField(max_length=32)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL
    )
    designation = models.ForeignKey(
        Designation, null=True, blank=True, on_delete=models.SET_NULL
    )
    shift = models.ForeignKey(
        "Shift",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )
    reporting_manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="direct_reports"
    )
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, blank=True, default="")
    nationality = models.CharField(max_length=64, blank=True, default="")
    marital_status = models.CharField(max_length=32, blank=True, default="")
    national_id = models.CharField(
        max_length=32, blank=True, default="", help_text="CNIC / Emirates ID / Iqama"
    )
    ntn = models.CharField(max_length=32, blank=True, default="", help_text="Tax NTN")
    eobi_number = models.CharField(max_length=32, blank=True, default="")
    address = models.TextField(blank=True, default="")
    emergency_contact_name = models.CharField(max_length=128, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=32, blank=True, default="")
    bank_name = models.CharField(max_length=128, blank=True, default="")
    bank_iban = models.CharField(max_length=34, blank=True, default="")
    contract_type = models.CharField(
        max_length=20, choices=ContractType.choices, default=ContractType.PERMANENT
    )
    work_location = models.CharField(max_length=128, blank=True, default="")
    photo = models.ImageField(upload_to="employee-photos/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_tax_free = models.BooleanField(
        default=False,
        help_text="Skip income tax on payroll runs for this employee",
    )
    is_attendance_free = models.BooleanField(
        default=False,
        help_text=(
            "Attendance-exempt: no check-in/out required; payroll skips "
            "attendance/unpaid-leave proration (e.g. directors, field staff)"
        ),
    )

    class Meta:
        unique_together = ("organization", "employee_code")
        ordering = ["employee_code"]

    def __str__(self):
        return f"{self.employee_code} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class LeaveType(AuditModel):
    class AccrualMethod(models.TextChoices):
        ANNUAL = "annual", "Annual (full / pro-rata on join)"
        MONTHLY = "monthly", "Monthly accrual"
        NONE = "none", "Manual only"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="leave_types"
    )
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20)
    annual_quota = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=True)
    allow_carry_forward = models.BooleanField(default=False)
    allow_encashment = models.BooleanField(default=False)
    accrual_method = models.CharField(
        max_length=16, choices=AccrualMethod.choices, default=AccrualMethod.ANNUAL
    )
    max_carry_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Max days CF at year-end (0 = unlimited when CF allowed)",
    )
    exclude_weekends = models.BooleanField(default=True)
    exclude_holidays = models.BooleanField(default=True)
    gender_restriction = models.CharField(
        max_length=16,
        blank=True,
        default="",
        help_text="Optional: male / female — blank = all",
    )

    class Meta:
        unique_together = ("organization", "code")


class LeaveBalance(AuditModel):
    """Per-employee leave balance for a calendar year."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="leave_balances"
    )
    employee = models.ForeignKey(
        "Employee", on_delete=models.CASCADE, related_name="leave_balances"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="balances"
    )
    year = models.PositiveIntegerField()
    opening = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    accrued = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    encashed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employee", "leave_type", "year")
        ordering = ["-year", "leave_type__code"]

    @property
    def available(self):
        return (
            (self.opening or 0)
            + (self.accrued or 0)
            + (self.carried_forward or 0)
            - (self.used or 0)
            - (self.encashed or 0)
        )


class LeaveRequest(AuditModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=6, decimal_places=2)
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)


class RecruitmentRequest(AuditModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="recruitment_requests"
    )
    title = models.CharField(max_length=128)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL
    )
    designation = models.ForeignKey(
        Designation, null=True, blank=True, on_delete=models.SET_NULL
    )
    openings = models.PositiveIntegerField(default=1)
    candidate_name = models.CharField(max_length=128, blank=True)
    candidate_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)


class BenefitPlan(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="benefit_plans"
    )
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    benefit_type = models.CharField(max_length=64, default="medical")
    employer_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employee_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")


class EmployeeBenefit(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employee_benefits"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="benefits")
    plan = models.ForeignKey(BenefitPlan, on_delete=models.PROTECT, related_name="enrollments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, default="active")


class AttendancePolicy(AuditModel):
    """Org-level shift / grace rules for attendance evaluation."""

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="attendance_policy"
    )
    work_start = models.TimeField(default=time(9, 0))
    work_end = models.TimeField(default=time(18, 0))
    late_grace_minutes = models.PositiveIntegerField(default=15)
    early_leave_grace_minutes = models.PositiveIntegerField(default=15)
    half_day_minutes = models.PositiveIntegerField(
        default=240, help_text="Minimum worked minutes to count as half day"
    )
    full_day_minutes = models.PositiveIntegerField(
        default=480, help_text="Expected full-day worked minutes"
    )
    overtime_after_minutes = models.PositiveIntegerField(
        default=480, help_text="OT starts after this many worked minutes"
    )
    require_checkout = models.BooleanField(default=True)
    allow_wfh = models.BooleanField(default=True)
    allow_manual_punch = models.BooleanField(default=True)
    auto_apply_leave = models.BooleanField(
        default=True, help_text="Mark attendance on_leave when leave is approved"
    )
    auto_apply_holiday = models.BooleanField(
        default=True, help_text="Mark attendance holiday from calendar / weekends"
    )
    auto_mark_absent = models.BooleanField(
        default=True,
        help_text="On reconcile, mark missing punches as absent for non-exempt staff",
    )
    weekend_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Weekday numbers treated as weekend (0=Mon … 6=Sun). Default Sat+Sun.",
    )

    def __str__(self):
        return f"Attendance policy · {self.organization_id}"

    def effective_weekend_days(self) -> list[int]:
        raw = self.weekend_days
        if isinstance(raw, list) and raw:
            return [int(x) for x in raw]
        return [5, 6]  # Sat, Sun


class AttendanceHoliday(AuditModel):
    """Org holiday calendar — used by attendance reconcile."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="attendance_holidays"
    )
    name = models.CharField(max_length=128)
    holiday_date = models.DateField()
    is_optional = models.BooleanField(
        default=False, help_text="Optional holiday — does not auto-mark unless opted"
    )
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("organization", "holiday_date", "name")
        ordering = ["holiday_date"]

    def __str__(self):
        return f"{self.holiday_date} · {self.name}"


class AttendanceRecord(AuditModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EARLY_LEAVE = "early_leave", "Early leave"
        HALF_DAY = "half_day", "Half day"
        WFH = "wfh", "Work from home"
        ON_LEAVE = "on_leave", "On leave"
        HOLIDAY = "holiday", "Holiday"
        EXEMPT = "exempt", "Exempt"
        EXCEPTION = "exception", "Exception"
        REGULARIZED = "regularized", "Regularized"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        DEVICE = "device", "Device sync"
        CSV = "csv", "CSV import"
        ESS = "ess", "ESS"
        SYSTEM = "system", "System"

    class WorkType(models.TextChoices):
        OFFICE = "office", "Office"
        WFH = "wfh", "Work from home"
        FIELD = "field", "Field / on-site"
        HALF_DAY = "half_day", "Half day"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="attendance_records"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_records"
    )
    work_date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    work_type = models.CharField(
        max_length=16, choices=WorkType.choices, default=WorkType.OFFICE
    )
    is_half_day = models.BooleanField(default=False)
    late_minutes = models.PositiveIntegerField(default=0)
    early_leave_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    worked_minutes = models.PositiveIntegerField(default=0)
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.MANUAL
    )
    device = models.ForeignKey(
        "AttendanceDevice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_records",
    )
    regularize_reason = models.CharField(max_length=255, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("organization", "employee", "work_date")
        ordering = ["-work_date"]


class AttendanceRegularization(AuditModel):
    """Employee asks HR to correct a day's punches. The day changes only after approval."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="attendance_regularizations"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_regularizations"
    )
    work_date = models.DateField()
    requested_check_in = models.TimeField(null=True, blank=True)
    requested_check_out = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-work_date", "-id"]

    def __str__(self):
        return f"{self.employee_id} {self.work_date} {self.status}"


class ProbationRecord(AuditModel):
    class Status(models.TextChoices):
        ON_PROBATION = "on_probation", "On Probation"
        CONFIRMED = "confirmed", "Confirmed"
        EXTENDED = "extended", "Extended"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="probation_records"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="probations")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ON_PROBATION)
    notes = models.TextField(blank=True)


class PerformanceReview(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"

    class ReviewType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        MID_YEAR = "mid_year", "Mid-year"
        PROBATION = "probation", "Probation"
        PIP = "pip", "PIP"
        PROJECT = "project", "Project"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="performance_reviews"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="performance_reviews"
    )
    period_label = models.CharField(max_length=64)
    review_type = models.CharField(
        max_length=20, choices=ReviewType.choices, default=ReviewType.ANNUAL
    )
    review_period_start = models.DateField(null=True, blank=True)
    review_period_end = models.DateField(null=True, blank=True)
    rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    self_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    goals = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    development_plan = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews_given",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)


class TrainingCourse(AuditModel):
    """Org training catalog — enrollments point at courses."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="training_courses"
    )
    code = models.CharField(max_length=32)
    title = models.CharField(max_length=128)
    provider = models.CharField(max_length=128, blank=True, default="")
    category = models.CharField(max_length=64, blank=True, default="general")
    duration_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    is_mandatory = models.BooleanField(default=False)
    validity_months = models.PositiveIntegerField(
        default=0, help_text="0 = no expiry; else certificate validity"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.title}"


class TrainingRecord(AuditModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="training_records"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trainings")
    course = models.ForeignKey(
        TrainingCourse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrollments",
    )
    title = models.CharField(max_length=128)
    provider = models.CharField(max_length=128, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    certificate_no = models.CharField(max_length=64, blank=True, default="")
    certificate_expires_on = models.DateField(null=True, blank=True)
    certificate_file = models.FileField(
        upload_to="hr/training/%Y/%m/", blank=True, null=True
    )
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)


class SeparationRecord(AuditModel):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        CLEARANCE = "clearance", "Clearance"
        SETTLED = "settled", "Settled"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="separations"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="separations")
    last_working_day = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    final_settlement = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    notes = models.TextField(blank=True)


class FinalSettlement(AuditModel):
    """Full & final (F&F) settlement worksheet for a separation."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CALCULATED = "calculated", "Calculated"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="final_settlements"
    )
    separation = models.OneToOneField(
        SeparationRecord, on_delete=models.CASCADE, related_name="fnf_worksheet"
    )
    leave_encashment = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notice_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gratuity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")


class ExpenseClaim(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="expense_claims"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="expense_claims"
    )
    claim_date = models.DateField()
    category = models.CharField(max_length=64, default="general")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-claim_date", "-id"]


DEFAULT_SEPARATION_CHECKLIST = (
    ("it_assets", "IT assets returned (laptop, phone, access card)"),
    ("email_access", "Email / SSO access revoked"),
    ("finance_clearance", "Finance / advances / loans cleared"),
    ("hr_docs", "Exit interview & HR documentation"),
    ("leave_encash", "Leave encashment / recovery calculated"),
    ("id_card", "Company ID / badges returned"),
)


class SeparationChecklistItem(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="separation_checklist_items"
    )
    separation = models.ForeignKey(
        SeparationRecord, on_delete=models.CASCADE, related_name="checklist_items"
    )
    item_key = models.CharField(max_length=64)
    label = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    sort = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = ("separation", "item_key")
        ordering = ["sort", "id"]

    def __str__(self):
        return self.label


def seed_separation_checklist(separation, user=None) -> int:
    created = 0
    for i, (key, label) in enumerate(DEFAULT_SEPARATION_CHECKLIST):
        _, was = SeparationChecklistItem.objects.get_or_create(
            organization=separation.organization,
            separation=separation,
            item_key=key,
            defaults={
                "label": label,
                "sort": (i + 1) * 10,
                "created_by": user,
            },
        )
        if was:
            created += 1
    return created


class DocumentTypeDefinition(AuditModel):
    """Required / optional document matrix for the tenant."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="document_types"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    is_required = models.BooleanField(default=False)
    requires_expiry = models.BooleanField(default=False)
    warn_days_before_expiry = models.PositiveIntegerField(default=30)
    blocks_payroll_if_missing = models.BooleanField(
        default=False,
        help_text="If required and missing/expired, flag employee for payroll hold",
    )
    is_active = models.BooleanField(default=True)
    sort = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["sort", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class EmployeeDocument(AuditModel):
    class Verification(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employee_documents"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=128)
    doc_type = models.CharField(max_length=64, default="general")
    reference = models.CharField(max_length=128, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    verification_status = models.CharField(
        max_length=16, choices=Verification.choices, default=Verification.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to="hr/documents/%Y/%m/", blank=True, null=True)


class JobHistory(AuditModel):
    """Career / job history timeline — promotions, transfers, salary, status."""

    class EventType(models.TextChoices):
        HIRE = "hire", "Hire / joining"
        PROMOTION = "promotion", "Promotion"
        TRANSFER = "transfer", "Transfer"
        SALARY_REVISION = "salary_revision", "Salary revision"
        MANAGER_CHANGE = "manager_change", "Manager change"
        STATUS_CHANGE = "status_change", "Status change"
        CONTRACT_CHANGE = "contract_change", "Contract change"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="job_history"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="job_history"
    )
    event_type = models.CharField(
        max_length=32, choices=EventType.choices, default=EventType.OTHER
    )
    effective_date = models.DateField()
    from_department = models.CharField(max_length=160, blank=True, default="")
    to_department = models.CharField(max_length=160, blank=True, default="")
    from_designation = models.CharField(max_length=160, blank=True, default="")
    to_designation = models.CharField(max_length=160, blank=True, default="")
    from_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    to_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32, blank=True, default="")
    from_manager = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_manager = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-effective_date", "-id"]

    def __str__(self):
        return f"{self.employee_id} · {self.event_type} · {self.effective_date}"


class AttendanceDevice(AuditModel):
    class ConnMode(models.TextChoices):
        PUSH = "push_webhook", "Push / webhook"
        PULL = "pull_tcp", "Pull / TCP"
        CLOUD = "cloud_api", "Cloud / REST API"
        CSV = "csv_import", "CSV import"

    class SyncStatus(models.TextChoices):
        IDLE = "idle", "Idle"
        OK = "ok", "Last sync OK"
        ERROR = "error", "Last sync error"
        TESTING = "testing", "Testing"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="attendance_devices"
    )
    device_id = models.CharField(max_length=64)
    connector_key = models.CharField(
        max_length=64,
        default="generic_webhook",
        help_text="Key from hr.connectors.CONNECTOR_CATALOG",
    )
    make = models.CharField(max_length=64, blank=True)
    model_name = models.CharField(max_length=64, blank=True)
    location = models.CharField(max_length=128, blank=True)
    connection_mode = models.CharField(
        max_length=20, choices=ConnMode.choices, default=ConnMode.PUSH
    )
    host = models.CharField(max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(null=True, blank=True)
    username = models.CharField(max_length=128, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    api_token = models.CharField(max_length=512, blank=True, default="")
    webhook_secret = models.CharField(max_length=128, blank=True, default="")
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=16, choices=SyncStatus.choices, default=SyncStatus.IDLE
    )
    last_sync_message = models.CharField(max_length=255, blank=True, default="")
    last_error_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organization", "device_id")
        ordering = ["device_id"]

    def __str__(self):
        return f"{self.device_id} ({self.connector_key})"

