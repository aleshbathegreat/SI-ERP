"""Enterprise leave day engine — working days, overlap, balance restore."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from hr.attendance_service import get_or_create_policy
from hr.models import AttendanceHoliday, LeaveBalance, LeaveRequest, LeaveType


def iter_dates(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _is_calendar_holiday(org, d: date) -> bool:
    return AttendanceHoliday.objects.filter(
        organization=org,
        holiday_date=d,
        is_deleted=False,
        is_optional=False,
    ).exists()


def count_leave_days(
    org,
    start: date,
    end: date,
    *,
    leave_type: LeaveType | None = None,
    half_day: bool = False,
) -> Decimal:
    """
    Count chargeable leave days excluding weekends + non-optional holidays
    (aligned with attendance reconcile), unless leave type opts out.
    """
    if end < start:
        return Decimal("0")
    if half_day:
        return Decimal("0.5")
    exclude_weekends = True
    exclude_holidays = True
    if leave_type is not None:
        exclude_weekends = bool(getattr(leave_type, "exclude_weekends", True))
        exclude_holidays = bool(getattr(leave_type, "exclude_holidays", True))
    policy = get_or_create_policy(org) if org else None
    weekend = set(policy.effective_weekend_days()) if policy else {5, 6}
    total = Decimal("0")
    for d in iter_dates(start, end):
        if exclude_weekends and d.weekday() in weekend:
            continue
        if exclude_holidays and org and _is_calendar_holiday(org, d):
            continue
        total += Decimal("1")
    return total


def overlapping_leave_exists(
    employee,
    start: date,
    end: date,
    *,
    exclude_id: int | None = None,
) -> LeaveRequest | None:
    qs = LeaveRequest.objects.filter(
        employee=employee,
        status__in=[
            LeaveRequest.Status.PENDING,
            LeaveRequest.Status.APPROVED,
        ],
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.select_related("leave_type").first()


def restore_leave_balance(leave: LeaveRequest) -> bool:
    """Decrement LeaveBalance.used after reject/cancel of an approved leave."""
    days = Decimal(str(leave.days or 0))
    if days <= 0:
        return False
    year = leave.start_date.year if leave.start_date else date.today().year
    bal = LeaveBalance.objects.filter(
        employee=leave.employee,
        leave_type=leave.leave_type,
        year=year,
    ).first()
    if not bal:
        return False
    bal.used = max(Decimal("0"), (bal.used or Decimal("0")) - days)
    bal.save(update_fields=["used", "updated_at"])
    return True


def seed_leave_balances_for_employee(employee, year: int | None = None, user=None) -> int:
    """Create year balances from leave-type quotas (pro-rata if joined mid-year)."""
    year = year or date.today().year
    org = employee.organization
    created = 0
    for lt in LeaveType.objects.filter(organization=org):
        quota = Decimal(str(lt.annual_quota or 0))
        accrued = quota
        method = getattr(lt, "accrual_method", "annual") or "annual"
        doj = employee.date_of_joining
        if method == "monthly" and quota > 0:
            # Seed YTD months; monthly top-up job can continue
            months = date.today().month if year == date.today().year else 12
            if doj and doj.year == year:
                months = max(0, date.today().month - doj.month + 1) if year == date.today().year else (12 - doj.month + 1)
            accrued = (quota / Decimal("12") * Decimal(str(months))).quantize(Decimal("0.01"))
        elif doj and doj.year == year and quota > 0:
            # Annual dump pro-rata from joining month
            months_left = 12 - doj.month + 1
            accrued = (quota * Decimal(str(months_left)) / Decimal("12")).quantize(
                Decimal("0.01")
            )
        _, was = LeaveBalance.objects.get_or_create(
            organization=org,
            employee=employee,
            leave_type=lt,
            year=year,
            defaults={
                "opening": Decimal("0"),
                "accrued": accrued,
                "created_by": user,
            },
        )
        if was:
            created += 1
    return created


def carry_forward_year(org, from_year: int, user=None) -> dict:
    """Year-end CF into next year opening+carried_forward for allow_carry_forward types."""
    to_year = from_year + 1
    moved = 0
    skipped = 0
    for bal in LeaveBalance.objects.filter(
        organization=org, year=from_year
    ).select_related("leave_type", "employee"):
        lt = bal.leave_type
        if not lt.allow_carry_forward:
            skipped += 1
            continue
        avail = Decimal(str(bal.available))
        if avail <= 0:
            skipped += 1
            continue
        cap = Decimal(str(getattr(lt, "max_carry_forward", 0) or 0))
        if cap > 0:
            avail = min(avail, cap)
        nxt, created = LeaveBalance.objects.get_or_create(
            organization=org,
            employee=bal.employee,
            leave_type=lt,
            year=to_year,
            defaults={
                "opening": Decimal("0"),
                "accrued": Decimal("0"),
                "carried_forward": avail,
                "created_by": user,
            },
        )
        if not created:
            nxt.carried_forward = (nxt.carried_forward or Decimal("0")) + avail
            nxt.save(update_fields=["carried_forward", "updated_at"])
        moved += 1
    return {"from_year": from_year, "to_year": to_year, "moved": moved, "skipped": skipped}


def payroll_day_factor(status: str, *, is_half_day: bool = False) -> Decimal:
    """Map attendance status → paid day factor for payroll."""
    s = (status or "").lower()
    if s in ("present", "late", "regularized", "wfh", "exempt"):
        return Decimal("1")
    if s in ("half_day",) or is_half_day:
        return Decimal("0.5")
    if s == "early_leave":
        return Decimal("1")
    if s == "holiday":
        return Decimal("1")  # paid holiday
    if s == "on_leave":
        return Decimal("0")  # paid vs unpaid handled by leave type at aggregate
    if s in ("absent", "exception"):
        return Decimal("0")
    return Decimal("0")
