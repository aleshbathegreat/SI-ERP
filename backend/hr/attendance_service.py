"""Enterprise attendance evaluation helpers."""

from __future__ import annotations

from datetime import date, datetime, time

from hr.models import (
    AttendanceHoliday,
    AttendancePolicy,
    AttendanceRecord,
    Employee,
    LeaveRequest,
)


def get_or_create_policy(org) -> AttendancePolicy:
    policy, _ = AttendancePolicy.objects.get_or_create(
        organization=org,
        defaults={},
    )
    return policy


def _as_time(value):
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _minutes_between(a: time | None, b: time | None) -> int:
    if not a or not b:
        return 0
    da = datetime.combine(date.today(), a)
    db = datetime.combine(date.today(), b)
    return int((db - da).total_seconds() // 60)


def evaluate_record(record: AttendanceRecord, policy: AttendancePolicy | None = None) -> AttendanceRecord:
    """Recompute status, late/early/OT/worked minutes from check-in/out + policy."""
    emp = record.employee
    if emp and emp.is_attendance_free:
        record.status = AttendanceRecord.Status.EXEMPT
        record.late_minutes = 0
        record.early_leave_minutes = 0
        record.overtime_minutes = 0
        record.worked_minutes = 0
        return record

    policy = policy or get_or_create_policy(record.organization)
    cin = _as_time(record.check_in)
    cout = _as_time(record.check_out)
    record.check_in = cin
    record.check_out = cout

    # Explicit statuses that should not be overwritten by clock logic
    sticky = {
        AttendanceRecord.Status.ON_LEAVE,
        AttendanceRecord.Status.HOLIDAY,
        AttendanceRecord.Status.EXEMPT,
        AttendanceRecord.Status.REGULARIZED,
    }
    work_type = record.work_type or AttendanceRecord.WorkType.OFFICE

    if not cin and not cout:
        if record.status not in sticky and record.status != AttendanceRecord.Status.EXCEPTION:
            record.status = AttendanceRecord.Status.ABSENT
        record.late_minutes = 0
        record.early_leave_minutes = 0
        record.overtime_minutes = 0
        record.worked_minutes = 0
        return record

    worked = max(0, _minutes_between(cin, cout)) if cin and cout else 0
    record.worked_minutes = worked

    late = 0
    if cin and policy.work_start:
        delta = _minutes_between(policy.work_start, cin)
        grace = int(policy.late_grace_minutes or 0)
        late = max(0, delta - grace) if delta > 0 else 0
    record.late_minutes = late

    early = 0
    if cout and policy.work_end:
        delta = _minutes_between(cout, policy.work_end)
        grace = int(policy.early_leave_grace_minutes or 0)
        early = max(0, delta - grace) if delta > 0 else 0
    record.early_leave_minutes = early

    ot = 0
    if worked and policy.full_day_minutes:
        after = int(policy.overtime_after_minutes or policy.full_day_minutes)
        ot = max(0, worked - after)
    record.overtime_minutes = ot

    half_threshold = int(policy.half_day_minutes or 240)
    full_threshold = int(policy.full_day_minutes or 480)

    if record.status in sticky:
        return record

    if work_type == AttendanceRecord.WorkType.HALF_DAY or (
        worked and worked < full_threshold and worked >= half_threshold
    ):
        record.is_half_day = True
        record.status = AttendanceRecord.Status.HALF_DAY
    elif work_type == AttendanceRecord.WorkType.WFH:
        record.status = AttendanceRecord.Status.WFH
        if late:
            record.status = AttendanceRecord.Status.LATE
    elif late and early:
        record.status = AttendanceRecord.Status.LATE
    elif late:
        record.status = AttendanceRecord.Status.LATE
    elif early:
        record.status = AttendanceRecord.Status.EARLY_LEAVE
    elif cin and not cout:
        record.status = AttendanceRecord.Status.PRESENT
    else:
        record.status = AttendanceRecord.Status.PRESENT

    if record.is_half_day and record.status == AttendanceRecord.Status.PRESENT:
        record.status = AttendanceRecord.Status.HALF_DAY

    return record


def ensure_exempt_or_block(employee: Employee, work_date: date) -> AttendanceRecord | None:
    """If employee is attendance-exempt, upsert EXEMPT day and return it."""
    if not employee.is_attendance_free:
        return None
    rec, _ = AttendanceRecord.objects.update_or_create(
        organization_id=employee.organization_id,
        employee=employee,
        work_date=work_date,
        defaults={
            "status": AttendanceRecord.Status.EXEMPT,
            "source": AttendanceRecord.Source.MANUAL,
            "notes": "Attendance-exempt employee",
            "late_minutes": 0,
            "early_leave_minutes": 0,
            "overtime_minutes": 0,
            "worked_minutes": 0,
        },
    )
    return rec


def punch_check_in(employee: Employee, work_date: date | None = None, at: time | None = None, source="manual"):
    if employee.is_attendance_free:
        return ensure_exempt_or_block(employee, work_date or date.today()), "exempt"
    work_date = work_date or date.today()
    at = at or datetime.now().time().replace(microsecond=0)
    rec, created = AttendanceRecord.objects.get_or_create(
        organization_id=employee.organization_id,
        employee=employee,
        work_date=work_date,
        defaults={"source": source},
    )
    if rec.check_in and not created:
        # already checked in — keep earliest
        existing = _as_time(rec.check_in)
        if existing and at > existing:
            at = existing
    rec.check_in = at
    rec.source = source
    evaluate_record(rec)
    rec.save()
    return rec, "checked_in"


def punch_check_out(employee: Employee, work_date: date | None = None, at: time | None = None, source="manual"):
    if employee.is_attendance_free:
        return ensure_exempt_or_block(employee, work_date or date.today()), "exempt"
    work_date = work_date or date.today()
    at = at or datetime.now().time().replace(microsecond=0)
    rec, _ = AttendanceRecord.objects.get_or_create(
        organization_id=employee.organization_id,
        employee=employee,
        work_date=work_date,
        defaults={"source": source},
    )
    if not rec.check_in:
        # allow checkout-only by setting check_in = work_start if policy has one
        policy = get_or_create_policy(employee.organization)
        rec.check_in = policy.work_start
    rec.check_out = at
    rec.source = source
    evaluate_record(rec)
    rec.save()
    return rec, "checked_out"


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        from datetime import timedelta

        cur = cur + timedelta(days=1)


def is_holiday(org, work_date: date, policy: AttendancePolicy | None = None) -> tuple[bool, str]:
    """Return (is_holiday, label). Includes weekends from policy."""
    policy = policy or get_or_create_policy(org)
    weekday = work_date.weekday()  # 0=Mon
    if weekday in policy.effective_weekend_days():
        return True, "Weekend"
    hit = (
        AttendanceHoliday.objects.filter(
            organization=org,
            holiday_date=work_date,
            is_deleted=False,
            is_optional=False,
        )
        .order_by("id")
        .first()
    )
    if hit:
        return True, hit.name
    return False, ""


def employee_on_approved_leave(employee: Employee, work_date: date) -> LeaveRequest | None:
    return (
        LeaveRequest.objects.filter(
            employee=employee,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=work_date,
            end_date__gte=work_date,
            is_deleted=False,
        )
        .select_related("leave_type")
        .first()
    )


def _can_system_overwrite(rec: AttendanceRecord | None) -> bool:
    """Don't clobber punched / regularized / exception days."""
    if rec is None:
        return True
    if rec.check_in or rec.check_out:
        return False
    if rec.status in (
        AttendanceRecord.Status.REGULARIZED,
        AttendanceRecord.Status.EXCEPTION,
        AttendanceRecord.Status.PRESENT,
        AttendanceRecord.Status.LATE,
        AttendanceRecord.Status.EARLY_LEAVE,
        AttendanceRecord.Status.HALF_DAY,
        AttendanceRecord.Status.WFH,
    ):
        return False
    return True


def apply_leave_to_attendance(leave: LeaveRequest) -> dict:
    """Mark each day in an approved leave as on_leave (no overwrite of punches)."""
    if leave.status != LeaveRequest.Status.APPROVED:
        return {"updated": 0, "skipped": 0}
    emp = leave.employee
    org = emp.organization
    policy = get_or_create_policy(org)
    if not policy.auto_apply_leave:
        return {"updated": 0, "skipped": 0, "disabled": True}
    updated = 0
    skipped = 0
    for d in _daterange(leave.start_date, leave.end_date):
        if emp.is_attendance_free:
            ensure_exempt_or_block(emp, d)
            skipped += 1
            continue
        # Skip holidays — leave on a holiday is usually not consumed for attendance
        hol, _ = is_holiday(org, d, policy)
        if hol and policy.auto_apply_holiday:
            skipped += 1
            continue
        rec = AttendanceRecord.objects.filter(
            organization=org, employee=emp, work_date=d
        ).first()
        if not _can_system_overwrite(rec):
            skipped += 1
            continue
        lt = getattr(leave.leave_type, "name", None) or "Leave"
        AttendanceRecord.objects.update_or_create(
            organization=org,
            employee=emp,
            work_date=d,
            defaults={
                "status": AttendanceRecord.Status.ON_LEAVE,
                "source": AttendanceRecord.Source.SYSTEM,
                "notes": f"Approved leave: {lt}",
                "check_in": None,
                "check_out": None,
                "late_minutes": 0,
                "early_leave_minutes": 0,
                "overtime_minutes": 0,
                "worked_minutes": 0,
            },
        )
        updated += 1
    return {"updated": updated, "skipped": skipped}


def clear_leave_attendance(leave: LeaveRequest) -> int:
    """Remove system on_leave rows for a cancelled/rejected leave (no punches)."""
    cleared = 0
    for d in _daterange(leave.start_date, leave.end_date):
        qs = AttendanceRecord.objects.filter(
            organization_id=leave.employee.organization_id,
            employee=leave.employee,
            work_date=d,
            status=AttendanceRecord.Status.ON_LEAVE,
            source=AttendanceRecord.Source.SYSTEM,
            check_in__isnull=True,
            check_out__isnull=True,
        )
        cleared += qs.count()
        qs.delete()
    return cleared


def reconcile_day(org, work_date: date | None = None) -> dict:
    """
    Best-practice daily board reconcile for all active employees:

    1. Exempt → EXEMPT
    2. Holiday / weekend → HOLIDAY (if no punches)
    3. Approved leave → ON_LEAVE (if no punches)
    4. Else missing record → ABSENT (if auto_mark_absent)
    """
    work_date = work_date or date.today()
    policy = get_or_create_policy(org)
    hol, hol_name = is_holiday(org, work_date, policy)
    employees = Employee.objects.filter(
        organization=org,
        status__in=[Employee.Status.ACTIVE, Employee.Status.PROBATION],
        is_deleted=False,
    )
    stats = {
        "work_date": work_date.isoformat(),
        "exempt": 0,
        "holiday": 0,
        "on_leave": 0,
        "absent": 0,
        "unchanged": 0,
        "total": 0,
    }
    for emp in employees:
        stats["total"] += 1
        rec = AttendanceRecord.objects.filter(
            organization=org, employee=emp, work_date=work_date
        ).first()

        if emp.is_attendance_free:
            ensure_exempt_or_block(emp, work_date)
            stats["exempt"] += 1
            continue

        if policy.auto_apply_holiday and hol and _can_system_overwrite(rec):
            AttendanceRecord.objects.update_or_create(
                organization=org,
                employee=emp,
                work_date=work_date,
                defaults={
                    "status": AttendanceRecord.Status.HOLIDAY,
                    "source": AttendanceRecord.Source.SYSTEM,
                    "notes": f"Holiday: {hol_name}",
                    "check_in": None,
                    "check_out": None,
                    "late_minutes": 0,
                    "early_leave_minutes": 0,
                    "overtime_minutes": 0,
                    "worked_minutes": 0,
                },
            )
            stats["holiday"] += 1
            continue

        leave = None
        if policy.auto_apply_leave:
            leave = employee_on_approved_leave(emp, work_date)
        if leave and _can_system_overwrite(rec):
            lt = getattr(leave.leave_type, "name", None) or "Leave"
            AttendanceRecord.objects.update_or_create(
                organization=org,
                employee=emp,
                work_date=work_date,
                defaults={
                    "status": AttendanceRecord.Status.ON_LEAVE,
                    "source": AttendanceRecord.Source.SYSTEM,
                    "notes": f"Approved leave: {lt}",
                    "check_in": None,
                    "check_out": None,
                    "late_minutes": 0,
                    "early_leave_minutes": 0,
                    "overtime_minutes": 0,
                    "worked_minutes": 0,
                },
            )
            stats["on_leave"] += 1
            continue

        if policy.auto_mark_absent and rec is None and not hol:
            AttendanceRecord.objects.create(
                organization=org,
                employee=emp,
                work_date=work_date,
                status=AttendanceRecord.Status.ABSENT,
                source=AttendanceRecord.Source.SYSTEM,
                notes="Auto-marked absent (no punch)",
            )
            stats["absent"] += 1
            continue

        stats["unchanged"] += 1
    return stats


def reconcile_range(org, start: date, end: date) -> dict:
    totals = {
        "days": 0,
        "exempt": 0,
        "holiday": 0,
        "on_leave": 0,
        "absent": 0,
        "unchanged": 0,
        "total": 0,
    }
    for d in _daterange(start, end):
        day = reconcile_day(org, d)
        totals["days"] += 1
        for k in ("exempt", "holiday", "on_leave", "absent", "unchanged", "total"):
            totals[k] += day.get(k, 0)
    return totals

