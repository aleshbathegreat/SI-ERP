"""Employee Self-Service APIs — always scoped to the linked employee."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import can
from core.access import user_organization
from hr.attendance_service import punch_check_in, punch_check_out
from hr.leave_service import count_leave_days
from hr.models import (
    AttendanceHoliday,
    AttendanceRecord,
    Employee,
    EmployeeDocument,
    ExpenseClaim,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)
from hr.serializers import (
    AttendanceRecordSerializer,
    EmployeeDocumentSerializer,
    EmployeeSerializer,
    ExpenseClaimSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)
from payroll.models import EmployeeLoan, Payslip
from payroll.payslip_document import render_salary_slip_html
from payroll.serializers import PayslipSerializer


def _linked_employee(user) -> Employee | None:
    emp = getattr(user, "employee", None)
    if emp and not getattr(emp, "is_deleted", False):
        return emp
    return None


def _require_employee(request):
    emp = _linked_employee(request.user)
    if not emp:
        return None, Response(
            {
                "detail": "No employee profile linked to your account. Ask HR to link you.",
                "code": "no_employee",
            },
            status=400,
        )
    org = user_organization(request.user)
    if org and emp.organization_id != org.id:
        return None, Response({"detail": "Employee org mismatch"}, status=403)
    return emp, None


class EssGateMixin:
    """All ESS endpoints use the ess module; no cross-employee access."""

    rbac_module = "ess"
    rbac_exempt = False


class EssDashboardView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        today = date.today()
        emp = Employee.objects.select_related("department", "designation", "shift").get(pk=emp.pk)
        leave_qs = LeaveRequest.objects.filter(employee=emp).order_by("-start_date")
        pending_leaves = leave_qs.filter(status=LeaveRequest.Status.PENDING).count()
        att = AttendanceRecord.objects.filter(employee=emp, work_date=today).first()
        month_rows = AttendanceRecord.objects.filter(
            employee=emp, work_date__gte=today.replace(day=1), work_date__lte=today
        )
        present_states = [
            AttendanceRecord.Status.PRESENT,
            AttendanceRecord.Status.LATE,
            AttendanceRecord.Status.EARLY_LEAVE,
            AttendanceRecord.Status.HALF_DAY,
            AttendanceRecord.Status.WFH,
            AttendanceRecord.Status.REGULARIZED,
            AttendanceRecord.Status.EXEMPT,
        ]
        month = {
            "present": month_rows.filter(status__in=present_states).count(),
            "on_time": month_rows.filter(
                status__in=[
                    AttendanceRecord.Status.PRESENT,
                    AttendanceRecord.Status.WFH,
                    AttendanceRecord.Status.REGULARIZED,
                ],
                late_minutes=0,
            ).count(),
            "late": month_rows.filter(Q(status=AttendanceRecord.Status.LATE) | Q(late_minutes__gt=0)).count(),
            "absent": month_rows.filter(status=AttendanceRecord.Status.ABSENT).count(),
        }
        balances = []
        for row in LeaveBalance.objects.filter(employee=emp, year=today.year).select_related("leave_type"):
            quota = (row.opening or 0) + (row.accrued or 0) + (row.carried_forward or 0)
            if not quota:
                quota = row.leave_type.annual_quota or 0
            used = (row.used or 0) + (row.encashed or 0)
            balances.append(
                {
                    "name": row.leave_type.name,
                    "remaining": str(row.available),
                    "quota": str(quota),
                    "used": str(used),
                }
            )
        remaining_total = sum((Decimal(item["remaining"]) for item in balances), Decimal("0"))
        quota_total = sum((Decimal(item["quota"]) for item in balances), Decimal("0"))
        used_total = sum((Decimal(item["used"]) for item in balances), Decimal("0"))
        loans = EmployeeLoan.objects.filter(
            employee=emp,
            is_deleted=False,
            status__in=[EmployeeLoan.Status.APPROVED, EmployeeLoan.Status.ACTIVE],
        )
        outstanding = sum((loan.outstanding_balance or 0 for loan in loans), Decimal("0"))
        installment = sum((loan.monthly_installment or 0 for loan in loans), Decimal("0"))
        from tasks.models import WorkTask

        tasks = WorkTask.objects.filter(
            organization_id=emp.organization_id,
            assignee=request.user,
            status__in=[
                WorkTask.Status.OPEN,
                WorkTask.Status.IN_PROGRESS,
                WorkTask.Status.IN_REVIEW,
            ],
            is_deleted=False,
        )[:5]
        holidays = AttendanceHoliday.objects.filter(
            organization_id=emp.organization_id,
            holiday_date__gte=today,
            is_deleted=False,
        ).order_by("holiday_date")[:4]
        birthdays = []
        for person in (
            Employee.objects.filter(
                organization_id=emp.organization_id,
                date_of_birth__month=today.month,
                is_deleted=False,
                status=Employee.Status.ACTIVE,
            )
            .exclude(pk=emp.pk)
            .select_related("department")
            .order_by("date_of_birth__day", "first_name")[:8]
        ):
            birthdays.append(
                {
                    "name": person.full_name,
                    "department": person.department.name if person.department_id else "",
                    "day": person.date_of_birth.day,
                }
            )
        slips = Payslip.objects.filter(employee=emp).select_related("period").order_by(
            "-period_id", "-id"
        )[:3]
        docs = EmployeeDocument.objects.filter(employee=emp).order_by("-id")[:5]
        shift = None
        if emp.shift_id:
            shift = {
                "name": emp.shift.name,
                "start": emp.shift.start_time.strftime("%H:%M"),
                "end": emp.shift.end_time.strftime("%H:%M"),
            }
        return Response(
            {
                "employee": EmployeeSerializer(emp).data,
                "workplace": {
                    "department": emp.department.name if emp.department_id else "",
                    "designation": emp.designation.title if emp.designation_id else "",
                    "location": emp.work_location or "",
                    "shift": shift,
                },
                "today": {
                    "work_date": today.isoformat(),
                    "attendance": AttendanceRecordSerializer(att).data if att else None,
                    "is_attendance_free": emp.is_attendance_free,
                },
                "month_attendance": month,
                "leave_summary": {
                    "year": today.year,
                    "remaining": str(remaining_total),
                    "quota": str(quota_total),
                    "used": str(used_total),
                    "balances": balances,
                },
                "loan": {
                    "outstanding": str(outstanding),
                    "installment": str(installment),
                    "count": loans.count(),
                },
                "tasks": [{"id": task.id, "title": task.title, "body": task.body} for task in tasks],
                "holidays": [
                    {"name": row.name, "date": row.holiday_date.isoformat()} for row in holidays
                ],
                "birthdays": birthdays,
                "counts": {
                    "pending_leaves": pending_leaves,
                    "payslips": Payslip.objects.filter(employee=emp).count(),
                    "documents": EmployeeDocument.objects.filter(employee=emp).count(),
                },
                "recent_leaves": LeaveRequestSerializer(leave_qs[:5], many=True).data,
                "recent_payslips": PayslipSerializer(slips, many=True).data,
                "recent_documents": EmployeeDocumentSerializer(docs, many=True).data,
            }
        )


class EssProfileView(EssGateMixin, APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        emp = Employee.objects.select_related(
            "department", "designation", "shift", "reporting_manager"
        ).get(pk=emp.pk)
        return Response(EmployeeSerializer(emp, context={"request": request}).data)

    def patch(self, request):
        if not can(request.user, "ess", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        allowed = {
            "phone",
            "email",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "bank_name",
            "bank_iban",
        }
        photo = request.FILES.get("photo")
        if photo is not None:
            if photo.size > 2 * 1024 * 1024:
                return Response({"detail": "Photo must be 2 MB or smaller."}, status=400)
            if not str(photo.content_type or "").startswith("image/"):
                return Response({"detail": "Photo must be an image."}, status=400)
            emp.photo = photo
            emp.save(update_fields=["photo", "updated_at"])
        data = {k: v for k, v in request.data.items() if k in allowed}
        ser = EmployeeSerializer(emp, data=data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class EssLeaveTypesView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp = _linked_employee(request.user)
        org = user_organization(request.user)
        org_ids: list[int] = []
        if org:
            org_ids.append(org.id)
        if emp and emp.organization_id and emp.organization_id not in org_ids:
            org_ids.append(emp.organization_id)
        if not org_ids:
            return Response([])
        qs = LeaveType.objects.filter(organization_id__in=org_ids).order_by("code")
        return Response(LeaveTypeSerializer(qs, many=True).data)


class EssLeaveBalancesView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp = _linked_employee(request.user)
        if not emp:
            return Response([])
        year = int(request.query_params.get("year") or date.today().year)
        qs = LeaveBalance.objects.filter(employee=emp, year=year).select_related(
            "leave_type"
        )
        return Response(LeaveBalanceSerializer(qs, many=True).data)


class EssLeavesView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp = _linked_employee(request.user)
        if not emp:
            return Response([])
        qs = LeaveRequest.objects.filter(employee=emp).select_related("leave_type").order_by(
            "-start_date", "-id"
        )
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        payload = dict(request.data)
        payload["employee"] = emp.pk
        payload.setdefault("status", LeaveRequest.Status.PENDING)
        if payload.get("start_date") and payload.get("end_date"):
            try:
                a = date.fromisoformat(str(payload["start_date"]))
                b = date.fromisoformat(str(payload["end_date"]))
                lt = None
                if payload.get("leave_type"):
                    lt = LeaveType.objects.filter(
                        pk=payload["leave_type"], organization_id=emp.organization_id
                    ).first()
                half = bool(payload.get("is_half_day"))
                payload["days"] = str(
                    count_leave_days(
                        emp.organization, a, b, leave_type=lt, half_day=half
                    )
                )
                if half:
                    payload["end_date"] = payload["start_date"]
            except ValueError:
                pass
        ser = LeaveRequestSerializer(data=payload, context={"request": request})
        ser.is_valid(raise_exception=True)
        leave = ser.save(created_by=request.user, employee=emp)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class EssAttendanceView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        qs = AttendanceRecord.objects.filter(employee=emp)
        month = (request.query_params.get("month") or "").strip()
        if len(month) == 7 and month[4] == "-":
            try:
                year, mon = int(month[:4]), int(month[5:7])
                if not 1 <= mon <= 12:
                    raise ValueError
            except ValueError:
                return Response({"detail": "month must be YYYY-MM."}, status=400)
            qs = qs.filter(work_date__year=year, work_date__month=mon).order_by("work_date")
        else:
            qs = qs.order_by("-work_date")[:60]
        return Response(AttendanceRecordSerializer(qs, many=True).data)

    def post(self, request):
        """Log exception or create/update a day note."""
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        if emp.is_attendance_free:
            return Response(
                {"detail": "You are attendance-exempt — no punch or exception needed."},
                status=400,
            )
        work_date = request.data.get("work_date") or date.today().isoformat()
        status_val = request.data.get("status") or AttendanceRecord.Status.EXCEPTION
        notes = request.data.get("notes") or "ESS attendance exception"
        rec, _ = AttendanceRecord.objects.update_or_create(
            organization_id=emp.organization_id,
            employee=emp,
            work_date=work_date,
            defaults={
                "status": status_val,
                "notes": notes,
                "source": AttendanceRecord.Source.ESS,
            },
        )
        return Response(AttendanceRecordSerializer(rec).data, status=201)


class EssAttendanceRegularizeView(EssGateMixin, APIView):
    """Employee correction request. The attendance day changes only after HR approves."""

    def post(self, request):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        if emp.is_attendance_free:
            return Response({"detail": "You are attendance-exempt."}, status=400)
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            return Response({"detail": "A reason is required."}, status=400)
        work_date = request.data.get("work_date") or date.today().isoformat()
        try:
            wd = date.fromisoformat(str(work_date))
        except ValueError:
            return Response({"detail": "work_date must be YYYY-MM-DD."}, status=400)
        from hr.models import AttendanceRegularization
        from hr.views import _parse_hhmm

        if AttendanceRegularization.objects.filter(
            employee=emp, work_date=wd, status=AttendanceRegularization.Status.PENDING
        ).exists():
            return Response({"detail": "A correction for this day is already waiting."}, status=400)
        try:
            check_in = _parse_hhmm(request.data.get("check_in"))
            check_out = _parse_hhmm(request.data.get("check_out"))
        except Exception:
            return Response({"detail": "Times must be HH:MM."}, status=400)
        row = AttendanceRegularization.objects.create(
            organization_id=emp.organization_id,
            employee=emp,
            work_date=wd,
            requested_check_in=check_in,
            requested_check_out=check_out,
            reason=reason[:255],
            created_by=request.user,
        )
        return Response(
            {
                "id": row.id,
                "work_date": row.work_date.isoformat(),
                "status": row.status,
                "reason": row.reason,
            },
            status=201,
        )


class EssPunchView(EssGateMixin, APIView):
    def post(self, request, action=None):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        kind = action or request.data.get("action") or "check-in"
        work_date = request.data.get("work_date")
        wd = date.fromisoformat(str(work_date)) if work_date else date.today()
        if kind in ("check-out", "out"):
            rec, punch_action = punch_check_out(emp, work_date=wd, source="ess")
        else:
            rec, punch_action = punch_check_in(emp, work_date=wd, source="ess")
        return Response(
            {**AttendanceRecordSerializer(rec).data, "punch_action": punch_action}
        )


class EssPayslipsView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        qs = Payslip.objects.filter(employee=emp).select_related("period").order_by(
            "-period_id", "-id"
        )
        return Response(PayslipSerializer(qs, many=True).data)


class EssTaxCertificateView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        from payroll.pk_statutory import current_fiscal_year, tax_certificate

        label = request.query_params.get("fiscal_year") or current_fiscal_year(date.today())
        try:
            return Response(tax_certificate(emp, label))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)


class EssPayslipPrintView(EssGateMixin, APIView):
    """Printable HTML payslip (Save as PDF from browser)."""

    def get(self, request, pk):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        slip = (
            Payslip.objects.filter(pk=pk, employee=emp)
            .select_related(
                "period",
                "period__organization",
                "employee",
                "employee__department",
                "employee__designation",
                "employee__organization",
            )
            .first()
        )
        if not slip:
            return Response({"detail": "Payslip not found"}, status=404)
        html = render_salary_slip_html(slip)
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp["Pragma"] = "no-cache"
        return resp


class EssDocumentsView(EssGateMixin, APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        qs = EmployeeDocument.objects.filter(employee=emp).order_by("-id")
        return Response(EmployeeDocumentSerializer(qs, many=True).data)


class EssClaimsView(EssGateMixin, APIView):
    """ESS expense claims — own records only."""

    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        qs = ExpenseClaim.objects.filter(employee=emp).order_by("-claim_date", "-id")
        return Response(ExpenseClaimSerializer(qs, many=True).data)

    def post(self, request):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        payload = dict(request.data)
        payload["employee"] = emp.pk
        payload.setdefault("status", ExpenseClaim.Status.SUBMITTED)
        payload.setdefault("claim_date", date.today().isoformat())
        ser = ExpenseClaimSerializer(data=payload, context={"request": request})
        ser.is_valid(raise_exception=True)
        claim = ser.save(
            organization=emp.organization,
            employee=emp,
            created_by=request.user,
        )
        return Response(ExpenseClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class EssPerformanceView(EssGateMixin, APIView):
    """The signed-in employee's own reviews. Self notes stay editable until approval."""

    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        from hr.models import PerformanceReview

        rows = PerformanceReview.objects.filter(employee=emp).select_related("reviewer").order_by("-id")
        return Response(
            [
                {
                    "id": row.id,
                    "period_label": row.period_label,
                    "review_type": row.review_type,
                    "status": row.status,
                    "rating": str(row.rating),
                    "self_rating": "" if row.self_rating is None else str(row.self_rating),
                    "goals": row.goals,
                    "achievements": row.achievements,
                    "feedback": row.feedback,
                    "development_plan": row.development_plan,
                    "reviewer_name": row.reviewer.full_name if row.reviewer_id else "",
                }
                for row in rows
            ]
        )

    def patch(self, request):
        if not can(request.user, "ess", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        from hr.models import PerformanceReview

        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return Response({"detail": "Review id is required."}, status=400)
        row = PerformanceReview.objects.filter(employee=emp, pk=pk).first()
        if not row:
            return Response({"detail": "Review not found"}, status=404)
        if row.status == PerformanceReview.Status.APPROVED:
            return Response({"detail": "An approved review is closed."}, status=400)
        if "self_rating" in request.data and request.data.get("self_rating") not in (None, ""):
            try:
                row.self_rating = Decimal(str(request.data.get("self_rating")))
            except Exception:
                return Response({"detail": "Self rating must be a number."}, status=400)
        if "achievements" in request.data:
            row.achievements = str(request.data.get("achievements") or "")[:8000]
        row.save(update_fields=["self_rating", "achievements", "updated_at"])
        return self.get(request)


class EssActivityView(EssGateMixin, APIView):
    """Plain-language trail of the signed-in user's own actions."""

    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        from core.audit_text import noise_filter, present
        from core.models import AuditLog

        logs = (
            AuditLog.objects.filter(organization_id=emp.organization_id, user=request.user)
            .exclude(noise_filter())
            .order_by("-id")[:40]
        )
        payload = []
        for log in logs:
            row = present(log)
            payload.append(
                {
                    "id": log.id,
                    "created_at": log.created_at,
                    "event": row["event"],
                    "area": row["area"],
                    "outcome": row["outcome"],
                }
            )
        return Response(payload)


_TASK_STATUSES = {"open", "in_progress", "in_review", "done"}
_TASK_PRIORITIES = {"low", "medium", "high", "urgent"}


def _clean_checklist(raw):
    if not isinstance(raw, list):
        return []
    items = []
    for item in raw[:20]:
        if isinstance(item, str):
            text, done = item, False
        elif isinstance(item, dict):
            text, done = item.get("text"), bool(item.get("done"))
        else:
            continue
        text = str(text or "").strip()[:120]
        if text:
            items.append({"text": text, "done": done})
    return items


def _task_payload(task, user):
    assignee = task.assignee
    return {
        "id": task.id,
        "title": task.title,
        "body": task.body,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else "",
        "checklist": task.checklist or [],
        "assignee": assignee.id if assignee else None,
        "assignee_name": (
            assignee.get_full_name() or assignee.username if assignee else ""
        ),
        "created_by": task.created_by_id,
        "can_remind": bool(
            task.created_by_id == getattr(user, "id", None)
            and task.assignee_id
            and task.assignee_id != user.id
        ),
    }


def _my_tasks(user, emp):
    from tasks.models import WorkTask

    return WorkTask.objects.filter(
        organization_id=emp.organization_id, is_deleted=False
    ).filter(Q(assignee=user) | Q(created_by=user)).select_related("assignee")


class EssTasksView(EssGateMixin, APIView):
    def get(self, request):
        if not can(request.user, "ess", "view"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        rows = _my_tasks(request.user, emp).order_by("due_date", "-id")
        return Response([_task_payload(row, request.user) for row in rows])

    def post(self, request):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        from django.contrib.auth import get_user_model
        from tasks.models import WorkTask

        title = str(request.data.get("title") or "").strip()
        if not title:
            return Response({"detail": "A title is required."}, status=400)
        priority = str(request.data.get("priority") or "medium")
        if priority not in _TASK_PRIORITIES:
            return Response({"detail": "Priority is not valid."}, status=400)
        due = None
        if request.data.get("due_date"):
            try:
                due = date.fromisoformat(str(request.data.get("due_date")))
            except ValueError:
                return Response({"detail": "due_date must be YYYY-MM-DD."}, status=400)
        assignee = request.user
        raw_assignee = request.data.get("assignee")
        if raw_assignee not in (None, "", request.user.id):
            try:
                assignee_id = int(raw_assignee)
            except (TypeError, ValueError):
                return Response({"detail": "Assignee is not valid."}, status=400)
            assignee = (
                get_user_model()
                .objects.filter(
                    pk=assignee_id,
                    is_active=True,
                    profile__organization_id=emp.organization_id,
                )
                .first()
            )
            if assignee is None:
                return Response({"detail": "Assignee must be in your organization."}, status=400)
        task = WorkTask.objects.create(
            organization_id=emp.organization_id,
            title=title[:180],
            body=str(request.data.get("body") or "")[:4000],
            assignee=assignee,
            priority=priority,
            due_date=due,
            checklist=_clean_checklist(request.data.get("checklist")),
            created_by=request.user,
        )
        if assignee.id != request.user.id:
            from notifications.services import push_inbox

            push_inbox(
                emp.organization,
                [assignee],
                title[:180],
                "A task was assigned to you.",
                href="/ess/tasks",
                kind="task",
            )
        return Response(_task_payload(task, request.user), status=201)

    def patch(self, request):
        if not can(request.user, "ess", "change"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return Response({"detail": "Task id is required."}, status=400)
        task = _my_tasks(request.user, emp).filter(pk=pk).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=404)
        status_val = request.data.get("status")
        if status_val is not None:
            if status_val not in _TASK_STATUSES:
                return Response({"detail": "Status is not valid."}, status=400)
            task.status = status_val
        if "title" in request.data:
            title = str(request.data.get("title") or "").strip()
            if not title:
                return Response({"detail": "A title is required."}, status=400)
            task.title = title[:180]
        if "body" in request.data:
            task.body = str(request.data.get("body") or "")[:4000]
        if "priority" in request.data:
            priority = str(request.data.get("priority") or "")
            if priority not in _TASK_PRIORITIES:
                return Response({"detail": "Priority is not valid."}, status=400)
            task.priority = priority
        if "due_date" in request.data:
            raw_due = request.data.get("due_date")
            if not raw_due:
                task.due_date = None
            else:
                try:
                    task.due_date = date.fromisoformat(str(raw_due))
                except ValueError:
                    return Response({"detail": "due_date must be YYYY-MM-DD."}, status=400)
        if "checklist" in request.data:
            task.checklist = _clean_checklist(request.data.get("checklist"))
        task.updated_by = request.user
        task.save()
        return Response(_task_payload(task, request.user))


class EssTaskRemindView(EssGateMixin, APIView):
    def post(self, request, pk):
        if not can(request.user, "ess", "add"):
            return Response({"detail": "Permission denied"}, status=403)
        emp, err = _require_employee(request)
        if err:
            return err
        task = _my_tasks(request.user, emp).filter(pk=pk, created_by=request.user).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=404)
        if not task.assignee_id or task.assignee_id == request.user.id:
            return Response({"detail": "There is nobody else to remind."}, status=400)
        from notifications.services import push_inbox

        push_inbox(
            emp.organization,
            [task.assignee],
            task.title,
            "Reminder: this task is still open.",
            href="/ess/tasks",
            kind="task",
        )
        return Response({"detail": "Reminder sent."})
