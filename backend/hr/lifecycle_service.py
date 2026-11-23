"""Enterprise HR lifecycle helpers — job history, document compliance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from hr.models import (
    Department,
    Designation,
    DocumentTypeDefinition,
    Employee,
    EmployeeDocument,
    JobHistory,
)


def _label_dept(dept) -> str:
    if not dept:
        return ""
    return f"{dept.code} — {dept.name}" if getattr(dept, "code", None) else str(dept)


def _label_desig(desig) -> str:
    if not desig:
        return ""
    grade = getattr(desig, "grade", "") or ""
    title = desig.title if hasattr(desig, "title") else str(desig)
    code = getattr(desig, "code", "") or ""
    base = f"{code} — {title}" if code else title
    return f"{base} ({grade})" if grade else base


@transaction.atomic
def record_job_event(
    employee: Employee,
    *,
    event_type: str,
    effective_date: date | None = None,
    reason: str = "",
    user=None,
    from_snapshot: dict | None = None,
    to_snapshot: dict | None = None,
    apply_to_employee: bool = False,
) -> JobHistory:
    """
    Append a job-history row. When apply_to_employee=True and to_snapshot has
    department/designation/manager/salary/status/grade, update Employee master.
    """
    eff = effective_date or date.today()
    before = from_snapshot or {
        "department_id": employee.department_id,
        "department": _label_dept(employee.department),
        "designation_id": employee.designation_id,
        "designation": _label_desig(employee.designation),
        "reporting_manager_id": employee.reporting_manager_id,
        "basic_salary": str(employee.basic_salary or 0),
        "status": employee.status,
        "contract_type": employee.contract_type,
        "work_location": employee.work_location,
    }
    after = dict(to_snapshot or {})

    # Resolve human-readable labels from ids when missing
    if after.get("department_id") and not after.get("department"):
        after["department"] = _label_dept(
            Department.objects.filter(pk=after["department_id"]).first()
        )
    if after.get("designation_id") and not after.get("designation"):
        after["designation"] = _label_desig(
            Designation.objects.filter(pk=after["designation_id"]).first()
        )

    if apply_to_employee and after:
        if "department_id" in after:
            employee.department_id = after.get("department_id") or None
        if "designation_id" in after:
            employee.designation_id = after.get("designation_id") or None
        if "reporting_manager_id" in after:
            employee.reporting_manager_id = after.get("reporting_manager_id") or None
        if "basic_salary" in after and after["basic_salary"] is not None:
            employee.basic_salary = Decimal(str(after["basic_salary"]))
        if "status" in after and after["status"]:
            employee.status = after["status"]
        if "contract_type" in after and after["contract_type"]:
            employee.contract_type = after["contract_type"]
        if "work_location" in after:
            employee.work_location = after.get("work_location") or ""
        employee.save()
        employee.refresh_from_db()
        after["department"] = _label_dept(employee.department)
        after["designation"] = _label_desig(employee.designation)
        after["basic_salary"] = str(employee.basic_salary or 0)
        after["status"] = employee.status

    return JobHistory.objects.create(
        organization=employee.organization,
        employee=employee,
        event_type=event_type,
        effective_date=eff,
        from_department=before.get("department", ""),
        to_department=after.get("department", before.get("department", "")),
        from_designation=before.get("designation", ""),
        to_designation=after.get("designation", before.get("designation", "")),
        from_salary=Decimal(str(before.get("basic_salary") or 0)),
        to_salary=Decimal(str(after.get("basic_salary", before.get("basic_salary") or 0))),
        from_status=before.get("status", ""),
        to_status=after.get("status", before.get("status", "")),
        from_manager_id=before.get("reporting_manager_id") or None,
        to_manager_id=(
            after.get("reporting_manager_id", before.get("reporting_manager_id")) or None
        ),
        reason=reason or "",
        created_by=user,
    )


def sync_job_history_on_employee_update(employee: Employee, old: dict, user=None) -> JobHistory | None:
    """Compare previous values vs current; write promotion/transfer/salary/status events."""
    changes = []
    if old.get("department_id") != employee.department_id:
        changes.append("transfer")
    if old.get("designation_id") != employee.designation_id:
        changes.append("promotion" if employee.designation_id else "transfer")
    salary_changed = Decimal(str(old.get("basic_salary") or 0)) != Decimal(
        str(employee.basic_salary or 0)
    )
    if salary_changed:
        changes.append("salary_revision")
    if old.get("status") != employee.status:
        changes.append("status_change")
    if old.get("reporting_manager_id") != employee.reporting_manager_id:
        changes.append("manager_change")
    if not changes:
        return None
    # Prefer a single combined event when multiple fields change together
    if "promotion" in changes and salary_changed:
        etype = JobHistory.EventType.PROMOTION
    elif "transfer" in changes:
        etype = JobHistory.EventType.TRANSFER
    elif "salary_revision" in changes:
        etype = JobHistory.EventType.SALARY_REVISION
    elif "manager_change" in changes:
        etype = JobHistory.EventType.MANAGER_CHANGE
    else:
        etype = JobHistory.EventType.STATUS_CHANGE
    return record_job_event(
        employee,
        event_type=etype,
        from_snapshot=old,
        to_snapshot={
            "department_id": employee.department_id,
            "department": _label_dept(employee.department),
            "designation_id": employee.designation_id,
            "designation": _label_desig(employee.designation),
            "reporting_manager_id": employee.reporting_manager_id,
            "basic_salary": str(employee.basic_salary or 0),
            "status": employee.status,
            "contract_type": employee.contract_type,
            "work_location": employee.work_location,
        },
        reason="Auto-logged from employee master update",
        user=user,
    )


def ensure_default_document_types(organization) -> list[str]:
    defaults = (
        ("cnic", "National ID / CNIC", True, True, 30, True),
        ("photo", "Employee photograph", True, False, 0, False),
        ("contract", "Employment contract", True, False, 0, True),
        ("education", "Education certificate", False, False, 0, False),
        ("experience", "Experience letter", False, False, 0, False),
        ("bank", "Bank account proof", True, False, 0, False),
        ("visa", "Visa / work permit", False, True, 60, True),
        ("medical", "Medical fitness", False, True, 30, False),
        ("nda", "NDA / confidentiality", True, False, 0, False),
    )
    created = []
    for code, name, required, needs_exp, warn, block in defaults:
        _, was = DocumentTypeDefinition.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={
                "name": name,
                "is_required": required,
                "requires_expiry": needs_exp,
                "warn_days_before_expiry": warn,
                "blocks_payroll_if_missing": block,
                "is_active": True,
                "sort": 100,
            },
        )
        if was:
            created.append(code)
    return created


def document_compliance(employee: Employee) -> dict:
    """Required-doc matrix vs filed documents (latest per type)."""
    org = employee.organization
    ensure_default_document_types(org)
    required = list(
        DocumentTypeDefinition.objects.filter(
            organization=org, is_active=True, is_required=True
        ).order_by("sort", "code")
    )
    docs = {
        d.doc_type: d
        for d in EmployeeDocument.objects.filter(employee=employee).order_by(
            "-issued_on", "-id"
        )
    }
    today = date.today()
    rows = []
    missing = 0
    expired = 0
    expiring = 0
    for dt in required:
        doc = docs.get(dt.code)
        status = "missing"
        days_left = None
        if doc:
            if doc.expires_on and doc.expires_on < today:
                status = "expired"
                expired += 1
                days_left = (doc.expires_on - today).days
            elif doc.expires_on:
                days_left = (doc.expires_on - today).days
                if dt.warn_days_before_expiry and days_left <= dt.warn_days_before_expiry:
                    status = "expiring"
                    expiring += 1
                else:
                    status = "ok"
            else:
                if dt.requires_expiry:
                    status = "missing_expiry"
                    missing += 1
                else:
                    status = "ok"
        else:
            missing += 1
        rows.append(
            {
                "code": dt.code,
                "name": dt.name,
                "is_required": dt.is_required,
                "requires_expiry": dt.requires_expiry,
                "blocks_payroll_if_missing": dt.blocks_payroll_if_missing,
                "status": status,
                "document_id": doc.id if doc else None,
                "title": doc.title if doc else None,
                "expires_on": doc.expires_on.isoformat() if doc and doc.expires_on else None,
                "days_to_expiry": days_left,
            }
        )
    blocking = [
        r
        for r in rows
        if r["blocks_payroll_if_missing"]
        and r["status"] in ("missing", "expired", "missing_expiry")
    ]
    return {
        "employee_id": employee.id,
        "compliant": missing == 0 and expired == 0,
        "missing": missing,
        "expired": expired,
        "expiring": expiring,
        "blocking_count": len(blocking),
        "blocks_payroll": len(blocking) > 0,
        "items": rows,
    }
