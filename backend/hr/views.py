from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from core.workflow import WorkflowActionsMixin
from hr.attendance_service import (
    apply_leave_to_attendance,
    clear_leave_attendance,
    evaluate_record,
    get_or_create_policy,
    punch_check_in,
    punch_check_out,
    reconcile_day,
    reconcile_range,
)
from hr.leave_service import (
    carry_forward_year,
    restore_leave_balance,
    seed_leave_balances_for_employee,
)
from hr.lifecycle_service import (
    document_compliance,
    ensure_default_document_types,
    record_job_event,
    sync_job_history_on_employee_update,
)
from hr.models import (
    AttendanceHoliday,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceRegularization,
    BenefitPlan,
    Department,
    Designation,
    DocumentTypeDefinition,
    Employee,
    EmployeeBenefit,
    EmployeeDocument,
    ExpenseClaim,
    FinalSettlement,
    JobHistory,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    OvertimePolicy,
    PerformanceReview,
    ProbationRecord,
    RecruitmentRequest,
    SeparationChecklistItem,
    SeparationRecord,
    Shift,
    TrainingCourse,
    TrainingRecord,
    seed_separation_checklist,
)
from hr.serializers import (
    AttendanceHolidaySerializer,
    AttendancePolicySerializer,
    AttendanceRecordSerializer,
    AttendanceRegularizationSerializer,
    BenefitPlanSerializer,
    DepartmentSerializer,
    DesignationSerializer,
    DocumentTypeDefinitionSerializer,
    EmployeeBenefitSerializer,
    EmployeeDocumentSerializer,
    EmployeeSerializer,
    ExpenseClaimSerializer,
    FinalSettlementSerializer,
    JobHistorySerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    OvertimePolicySerializer,
    PerformanceReviewSerializer,
    ProbationRecordSerializer,
    RecruitmentRequestSerializer,
    SeparationChecklistItemSerializer,
    SeparationRecordSerializer,
    ShiftSerializer,
    TrainingCourseSerializer,
    TrainingRecordSerializer,
)


class DepartmentViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ("name", "code")
    rbac_module = "hr.departments"


class DesignationViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    search_fields = ("title", "code")
    rbac_module = "hr.designations"


class ShiftViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    search_fields = ("code", "name")
    rbac_module = "hr.shifts"


class OvertimePolicyViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = OvertimePolicy.objects.all()
    serializer_class = OvertimePolicySerializer
    search_fields = ("name",)
    filterset_fields = ("is_active",)
    rbac_module = "hr.overtime"


class EmployeeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related(
        "department", "designation", "shift", "reporting_manager", "user"
    )
    serializer_class = EmployeeSerializer
    search_fields = (
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "national_id",
        "phone",
    )
    filterset_fields = ("status", "department", "contract_type")
    rbac_module = "hr.employees"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        emp = serializer.save(organization=org, created_by=self.request.user)
        record_job_event(
            emp,
            event_type=JobHistory.EventType.HIRE,
            effective_date=emp.date_of_joining or date.today(),
            reason="Initial hire / employee create",
            user=self.request.user,
            to_snapshot={
                "department": emp.department.name if emp.department_id else "",
                "designation": emp.designation.title if emp.designation_id else "",
                "basic_salary": str(emp.basic_salary or 0),
                "status": emp.status,
            },
        )
        seed_leave_balances_for_employee(emp, user=self.request.user)

    def perform_update(self, serializer):
        emp = self.get_object()
        old = {
            "department_id": emp.department_id,
            "designation_id": emp.designation_id,
            "reporting_manager_id": emp.reporting_manager_id,
            "basic_salary": emp.basic_salary,
            "status": emp.status,
            "contract_type": emp.contract_type,
            "work_location": emp.work_location,
            "department": emp.department.name if emp.department_id else "",
            "designation": (
                f"{emp.designation.code} — {emp.designation.title}"
                if emp.designation_id
                else ""
            ),
        }
        emp = serializer.save(updated_by=self.request.user)
        sync_job_history_on_employee_update(emp, old, user=self.request.user)

    @action(detail=True, methods=["get"], url_path="dossier")
    def dossier(self, request, pk=None):
        """Employee 360 — career, leave, attendance, docs, training, performance."""
        emp = self.get_object()
        today = date.today()
        year = today.year
        leave_balances = LeaveBalanceSerializer(
            LeaveBalance.objects.filter(employee=emp, year=year).select_related("leave_type"),
            many=True,
        ).data
        recent_leaves = LeaveRequestSerializer(
            LeaveRequest.objects.filter(employee=emp)
            .select_related("leave_type")
            .order_by("-start_date")[:12],
            many=True,
        ).data
        att_month = AttendanceRecord.objects.filter(
            employee=emp, work_date__year=today.year, work_date__month=today.month
        )
        att_summary = {
            "present": att_month.filter(
                status__in=["present", "late", "regularized", "wfh"]
            ).count(),
            "absent": att_month.filter(status="absent").count(),
            "on_leave": att_month.filter(status="on_leave").count(),
            "half_day": att_month.filter(status="half_day").count(),
            "ot_minutes": sum(att_month.values_list("overtime_minutes", flat=True)),
        }
        docs = EmployeeDocumentSerializer(
            EmployeeDocument.objects.filter(employee=emp).order_by("-expires_on")[:20],
            many=True,
            context={"request": request},
        ).data
        probation = ProbationRecordSerializer(
            ProbationRecord.objects.filter(employee=emp).order_by("-end_date")[:3],
            many=True,
        ).data
        benefits = EmployeeBenefitSerializer(
            EmployeeBenefit.objects.filter(employee=emp, status="active").select_related(
                "plan"
            ),
            many=True,
        ).data
        separations = SeparationRecordSerializer(
            SeparationRecord.objects.filter(employee=emp)
            .prefetch_related("checklist_items")
            .order_by("-last_working_day")[:3],
            many=True,
        ).data
        job_history = JobHistorySerializer(
            JobHistory.objects.filter(employee=emp).order_by("-effective_date", "-id")[:40],
            many=True,
        ).data
        trainings = TrainingRecordSerializer(
            TrainingRecord.objects.filter(employee=emp)
            .select_related("course")
            .order_by("-start_date", "-id")[:20],
            many=True,
        ).data
        performance = PerformanceReviewSerializer(
            PerformanceReview.objects.filter(employee=emp)
            .select_related("reviewer")
            .order_by("-id")[:10],
            many=True,
        ).data
        compliance = document_compliance(emp)
        return Response(
            {
                "employee": EmployeeSerializer(emp).data,
                "leave_balances": leave_balances,
                "recent_leaves": recent_leaves,
                "attendance_month": att_summary,
                "documents": docs,
                "document_compliance": compliance,
                "job_history": job_history,
                "trainings": trainings,
                "performance": performance,
                "probation": probation,
                "benefits": benefits,
                "separations": separations,
            }
        )

    @action(detail=True, methods=["get"], url_path="doc-compliance")
    def doc_compliance(self, request, pk=None):
        return Response(document_compliance(self.get_object()))


class LeaveTypeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    rbac_module = "hr.leave_types"


class LeaveBalanceViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.select_related("employee", "leave_type")
    serializer_class = LeaveBalanceSerializer
    filterset_fields = ("employee", "leave_type", "year")
    search_fields = ("employee__first_name", "employee__last_name", "leave_type__code")
    rbac_module = "hr.leaves"

    @action(detail=False, methods=["post"], url_path="accrue-year")
    def accrue_year(self, request):
        """Seed / top-up balances (pro-rata join + monthly method aware)."""
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        year = int(request.data.get("year") or date.today().year)
        created = 0
        for emp in Employee.objects.filter(
            organization=org, status__in=["active", "probation"]
        ):
            created += seed_leave_balances_for_employee(emp, year=year, user=request.user)
        return Response({"year": year, "created": created})

    @action(detail=False, methods=["post"], url_path="carry-forward")
    def carry_forward(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        from_year = int(request.data.get("from_year") or date.today().year - 1)
        result = carry_forward_year(org, from_year, user=request.user)
        return Response(result)

    @action(detail=True, methods=["post"])
    def encash(self, request, pk=None):
        bal = self.get_object()
        if not bal.leave_type.allow_encashment:
            return Response({"detail": "Leave type does not allow encashment"}, status=400)
        days = Decimal(str(request.data.get("days") or 0))
        if days <= 0:
            return Response({"detail": "days must be > 0"}, status=400)
        avail = Decimal(str(bal.available))
        if days > avail:
            return Response(
                {"detail": f"Insufficient balance ({avail} available)"}, status=400
            )
        bal.encashed = (bal.encashed or Decimal("0")) + days
        bal.save(update_fields=["encashed", "updated_at"])
        return Response(self.get_serializer(bal).data)


class LeaveRequestViewSet(WorkflowActionsMixin, BulkDeleteMixin, viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "leave_type")
    serializer_class = LeaveRequestSerializer
    filterset_fields = ("status", "employee", "leave_type")
    rbac_module = "hr.leaves"
    workflow_submit_to = "pending"
    workflow_approve_to = "approved"
    workflow_reject_to = "rejected"

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return self.queryset.none()
        return self.queryset.filter(employee__organization=org)

    def perform_create(self, serializer):
        employee = serializer.validated_data.get("employee")
        if employee is None:
            linked = getattr(self.request.user, "employee", None)
            if linked is None:
                raise ValidationError(
                    {"employee": "No employee profile linked to this user."}
                )
            serializer.save(created_by=self.request.user, employee=linked)
            return
        serializer.save(created_by=self.request.user)

    def approve(self, request, pk=None):
        obj = self.get_object()
        current = getattr(obj, self.workflow_status_field)
        if current in {self.workflow_submit_to, "pending"}:
            days = Decimal(str(obj.days or 0))
            year = obj.start_date.year if obj.start_date else date.today().year
            org = obj.employee.organization
            bal, _ = LeaveBalance.objects.get_or_create(
                organization=org,
                employee=obj.employee,
                leave_type=obj.leave_type,
                year=year,
                defaults={
                    "opening": Decimal("0"),
                    "accrued": obj.leave_type.annual_quota or Decimal("0"),
                    "created_by": request.user,
                },
            )
            avail = Decimal(str(bal.available))
            if days > avail:
                return Response(
                    {
                        "detail": f"Insufficient leave balance ({avail} available, {days} requested)",
                        "code": "leave_balance",
                    },
                    status=400,
                )
            resp = super().approve(request, pk=pk)
            if getattr(resp, "status_code", 200) < 400:
                bal.used = (bal.used or Decimal("0")) + days
                bal.save(update_fields=["used", "updated_at"])
                obj.refresh_from_db()
                apply_leave_to_attendance(obj)
            return resp
        return super().approve(request, pk=pk)

    def reject(self, request, pk=None):
        obj = self.get_object()
        was_approved = obj.status == LeaveRequest.Status.APPROVED
        resp = super().reject(request, pk=pk)
        if getattr(resp, "status_code", 200) < 400 and was_approved:
            restore_leave_balance(obj)
            clear_leave_attendance(obj)
        return resp

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        obj = self.get_object()
        if obj.status == LeaveRequest.Status.CANCELLED:
            return Response(self.get_serializer(obj).data)
        if obj.status == LeaveRequest.Status.APPROVED:
            restore_leave_balance(obj)
            clear_leave_attendance(obj)
        elif obj.status not in (
            LeaveRequest.Status.PENDING,
            LeaveRequest.Status.REJECTED,
        ):
            raise ValidationError({"status": "Cannot cancel in current status."})
        obj.status = LeaveRequest.Status.CANCELLED
        obj.updated_by = request.user
        obj.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(self.get_serializer(obj).data)


class RecruitmentRequestViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = RecruitmentRequest.objects.select_related("department", "designation")
    serializer_class = RecruitmentRequestSerializer
    search_fields = ("title", "candidate_name", "candidate_email")
    filterset_fields = ("status",)
    rbac_module = "hr.recruitment"
    workflow_submit_to = "interview"
    workflow_approve_to = "offer"
    workflow_reject_to = "closed"

    @action(detail=True, methods=["post"], url_path="hire")
    def hire(self, request, pk=None):
        """Create Employee + Probation + leave balances from an offer/hired req."""
        req = self.get_object()
        org = req.organization
        name = (req.candidate_name or "").strip() or req.title
        parts = name.split(None, 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else "."
        email = (req.candidate_email or "").strip() or f"hire-{req.pk}@example.com"
        code = str(request.data.get("employee_code") or "").strip()
        if not code:
            n = Employee.objects.filter(organization=org).count() + 1
            code = f"EMP-{n:04d}"
        if Employee.objects.filter(organization=org, employee_code=code).exists():
            raise ValidationError({"employee_code": "Already exists"})
        doj = request.data.get("date_of_joining") or date.today().isoformat()
        if isinstance(doj, str):
            doj = date.fromisoformat(doj)
        emp = Employee.objects.create(
            organization=org,
            employee_code=code,
            first_name=first[:100],
            last_name=last[:100],
            email=email,
            department=req.department,
            designation=req.designation,
            date_of_joining=doj,
            status=Employee.Status.PROBATION,
            basic_salary=Decimal(str(request.data.get("basic_salary") or 0)),
            created_by=request.user,
        )
        probation_days = int(request.data.get("probation_days") or 90)
        ProbationRecord.objects.create(
            organization=org,
            employee=emp,
            start_date=doj,
            end_date=doj + timedelta(days=probation_days),
            status=ProbationRecord.Status.ON_PROBATION,
            notes=f"Hired from recruitment #{req.pk}",
            created_by=request.user,
        )
        seed_leave_balances_for_employee(emp, year=doj.year, user=request.user)
        record_job_event(
            emp,
            event_type=JobHistory.EventType.HIRE,
            effective_date=doj,
            reason=f"Hired from recruitment #{req.pk}",
            user=request.user,
            to_snapshot={
                "department": emp.department.name if emp.department_id else "",
                "designation": emp.designation.title if emp.designation_id else "",
                "basic_salary": str(emp.basic_salary or 0),
                "status": emp.status,
            },
        )
        req.status = RecruitmentRequest.Status.HIRED
        req.updated_by = request.user
        req.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(
            {
                "recruitment": self.get_serializer(req).data,
                "employee": EmployeeSerializer(emp).data,
            }
        )


class BenefitPlanViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BenefitPlan.objects.all()
    serializer_class = BenefitPlanSerializer
    search_fields = ("name", "code")
    rbac_module = "hr.benefits"


class EmployeeBenefitViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = EmployeeBenefit.objects.select_related("employee", "plan")
    serializer_class = EmployeeBenefitSerializer
    filterset_fields = ("status", "employee", "plan")
    rbac_module = "hr.benefits"


class AttendancePolicyViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AttendancePolicy.objects.all()
    serializer_class = AttendancePolicySerializer
    rbac_module = "hr.attendance"
    http_method_names = ["get", "put", "patch", "head", "options"]

    def list(self, request, *args, **kwargs):
        org = user_organization(request.user)
        if not org:
            return Response([])
        policy = get_or_create_policy(org)
        return Response([self.get_serializer(policy).data])

    def retrieve(self, request, *args, **kwargs):
        org = user_organization(request.user)
        policy = get_or_create_policy(org)
        return Response(self.get_serializer(policy).data)


class AttendanceHolidayViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AttendanceHoliday.objects.all()
    serializer_class = AttendanceHolidaySerializer
    rbac_module = "hr.attendance"
    search_fields = ("name", "notes")
    filterset_fields = ("holiday_date", "is_optional")
    ordering = ["holiday_date"]


class AttendanceRecordViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related("employee", "device")
    serializer_class = AttendanceRecordSerializer
    search_fields = ("employee__employee_code", "employee__first_name", "notes")
    filterset_fields = ("status", "employee", "work_date", "work_type", "source")
    rbac_module = "hr.attendance"

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        org = user_organization(request.user)
        emp_id = request.data.get("employee")
        work_date = request.data.get("work_date") or date.today().isoformat()
        at = request.data.get("time")
        if not emp_id:
            raise ValidationError({"employee": "Required"})
        emp = Employee.objects.filter(organization=org, pk=emp_id).first()
        if not emp:
            raise ValidationError({"employee": "Not found"})
        from datetime import datetime as dt

        t = None
        if at:
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t = dt.strptime(str(at), fmt).time()
                    break
                except ValueError:
                    continue
        rec, action = punch_check_in(
            emp, work_date=date.fromisoformat(str(work_date)), at=t, source="manual"
        )
        return Response(
            {**self.get_serializer(rec).data, "punch_action": action}
        )

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        org = user_organization(request.user)
        emp_id = request.data.get("employee")
        work_date = request.data.get("work_date") or date.today().isoformat()
        at = request.data.get("time")
        if not emp_id:
            raise ValidationError({"employee": "Required"})
        emp = Employee.objects.filter(organization=org, pk=emp_id).first()
        if not emp:
            raise ValidationError({"employee": "Not found"})
        from datetime import datetime as dt

        t = None
        if at:
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t = dt.strptime(str(at), fmt).time()
                    break
                except ValueError:
                    continue
        rec, action = punch_check_out(
            emp, work_date=date.fromisoformat(str(work_date)), at=t, source="manual"
        )
        return Response(
            {**self.get_serializer(rec).data, "punch_action": action}
        )

    @action(detail=True, methods=["post"], url_path="regularize")
    def regularize(self, request, pk=None):
        rec = self.get_object()
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": "Regularization reason is required"})
        if "check_in" in request.data:
            rec.check_in = request.data.get("check_in") or None
        if "check_out" in request.data:
            rec.check_out = request.data.get("check_out") or None
        rec.regularize_reason = reason
        rec.status = AttendanceRecord.Status.REGULARIZED
        rec.notes = request.data.get("notes") or rec.notes
        evaluate_record(rec)
        # keep regularized sticky
        rec.status = AttendanceRecord.Status.REGULARIZED
        rec.save()
        return Response(self.get_serializer(rec).data)

    @action(detail=False, methods=["get"], url_path="today")
    def today_board(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        today = date.today()
        employees = Employee.objects.filter(
            organization=org,
            status__in=[Employee.Status.ACTIVE, Employee.Status.PROBATION],
        ).order_by("employee_code")
        records = {
            r.employee_id: r
            for r in AttendanceRecord.objects.filter(
                organization=org, work_date=today
            ).select_related("employee")
        }
        rows = []
        for emp in employees:
            rec = records.get(emp.pk)
            rows.append(
                {
                    "employee": emp.pk,
                    "employee_code": emp.employee_code,
                    "employee_name": emp.full_name,
                    "is_attendance_free": emp.is_attendance_free,
                    "record_id": rec.pk if rec else None,
                    "check_in": rec.check_in if rec else None,
                    "check_out": rec.check_out if rec else None,
                    "status": (
                        AttendanceRecord.Status.EXEMPT
                        if emp.is_attendance_free
                        else (rec.status if rec else "absent")
                    ),
                    "late_minutes": rec.late_minutes if rec else 0,
                    "worked_minutes": rec.worked_minutes if rec else 0,
                }
            )
        present = sum(
            1
            for r in rows
            if r["status"]
            in ("present", "late", "wfh", "half_day", "early_leave", "regularized")
        )
        absent = sum(1 for r in rows if r["status"] == "absent")
        exempt = sum(1 for r in rows if r["is_attendance_free"] or r["status"] == "exempt")
        on_leave = sum(1 for r in rows if r["status"] == "on_leave")
        holiday = sum(1 for r in rows if r["status"] == "holiday")
        return Response(
            {
                "work_date": today.isoformat(),
                "totals": {
                    "headcount": len(rows),
                    "present": present,
                    "absent": absent,
                    "exempt": exempt,
                    "on_leave": on_leave,
                    "holiday": holiday,
                },
                "rows": rows,
            }
        )

    @action(detail=False, methods=["post"], url_path="reconcile")
    def reconcile(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        work_date = request.data.get("work_date")
        start = request.data.get("start")
        end = request.data.get("end")
        if start and end:
            result = reconcile_range(
                org, date.fromisoformat(str(start)), date.fromisoformat(str(end))
            )
        else:
            d = date.fromisoformat(str(work_date)) if work_date else date.today()
            result = reconcile_day(org, d)
        return Response(result)

    @action(detail=False, methods=["get", "patch"], url_path="policy")
    def policy(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        policy = get_or_create_policy(org)
        if request.method == "GET":
            return Response(AttendancePolicySerializer(policy).data)
        ser = AttendancePolicySerializer(policy, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


def _parse_hhmm(value):
    from datetime import datetime as dt

    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.strptime(text[:8], fmt).time()
        except ValueError:
            continue
    raise ValidationError({"time": "Use HH:MM"})


class AttendanceRegularizationViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AttendanceRegularization.objects.select_related("employee")
    serializer_class = AttendanceRegularizationSerializer
    filterset_fields = ("status", "employee", "work_date")
    search_fields = ("employee__first_name", "employee__last_name", "employee__employee_code", "reason")
    rbac_module = "hr.attendance"
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        emp = serializer.validated_data["employee"]
        if emp.organization_id != org.id:
            raise ValidationError({"employee": "Not in this organization"})
        work_date = serializer.validated_data["work_date"]
        if AttendanceRegularization.objects.filter(
            employee=emp, work_date=work_date, status=AttendanceRegularization.Status.PENDING
        ).exists():
            raise ValidationError({"work_date": "A correction for this day is already waiting."})
        serializer.save(organization=org, created_by=self.request.user)

    def _apply(self, row: AttendanceRegularization):
        rec, _ = AttendanceRecord.objects.get_or_create(
            organization_id=row.organization_id,
            employee_id=row.employee_id,
            work_date=row.work_date,
            defaults={"source": AttendanceRecord.Source.ESS, "created_by": self.request.user},
        )
        if row.requested_check_in:
            rec.check_in = row.requested_check_in
        if row.requested_check_out:
            rec.check_out = row.requested_check_out
        rec.regularize_reason = row.reason
        rec.source = AttendanceRecord.Source.ESS
        rec.updated_by = self.request.user
        evaluate_record(rec)
        rec.status = AttendanceRecord.Status.REGULARIZED
        rec.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        row = self.get_object()
        if row.status != AttendanceRegularization.Status.PENDING:
            return Response({"detail": "Only a pending request can be approved."}, status=400)
        self._apply(row)
        row.status = AttendanceRegularization.Status.APPROVED
        row.review_note = str(request.data.get("review_note") or "")[:255]
        row.updated_by = request.user
        row.save(update_fields=["status", "review_note", "updated_by", "updated_at"])
        return Response(self.get_serializer(row).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        row = self.get_object()
        if row.status != AttendanceRegularization.Status.PENDING:
            return Response({"detail": "Only a pending request can be rejected."}, status=400)
        row.status = AttendanceRegularization.Status.REJECTED
        row.review_note = str(request.data.get("review_note") or "")[:255]
        row.updated_by = request.user
        row.save(update_fields=["status", "review_note", "updated_by", "updated_at"])
        return Response(self.get_serializer(row).data)


class ProbationRecordViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ProbationRecord.objects.select_related("employee")
    serializer_class = ProbationRecordSerializer
    filterset_fields = ("status", "employee")
    rbac_module = "hr.probation"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        emp = serializer.validated_data.get("employee")
        serializer.save(organization=org, created_by=self.request.user)
        if emp and emp.status == Employee.Status.ACTIVE:
            emp.status = Employee.Status.PROBATION
            emp.save(update_fields=["status", "updated_at"])

    def _set_outcome(self, request, status_value, employee_status=None, extend_days=None):
        rec = self.get_object()
        rec.status = status_value
        if extend_days:
            rec.end_date = rec.end_date + timedelta(days=int(extend_days))
            notes = (request.data.get("notes") or "").strip()
            if notes:
                rec.notes = ((rec.notes or "") + "\n" + notes).strip()
            rec.save(update_fields=["status", "end_date", "notes", "updated_at"])
        else:
            notes = (request.data.get("notes") or "").strip()
            if notes:
                rec.notes = ((rec.notes or "") + "\n" + notes).strip()
                rec.save(update_fields=["status", "notes", "updated_at"])
            else:
                rec.save(update_fields=["status", "updated_at"])
        emp = rec.employee
        if employee_status:
            emp.status = employee_status
            emp.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(rec).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._set_outcome(
            request, ProbationRecord.Status.CONFIRMED, Employee.Status.ACTIVE
        )

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        days = int(request.data.get("days") or 30)
        if days < 1:
            raise ValidationError({"days": "Must be >= 1"})
        return self._set_outcome(
            request,
            ProbationRecord.Status.EXTENDED,
            Employee.Status.PROBATION,
            extend_days=days,
        )

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        return self._set_outcome(
            request, ProbationRecord.Status.FAILED, Employee.Status.SEPARATED
        )

    @action(detail=False, methods=["get"], url_path="due-soon")
    def due_soon(self, request):
        org = user_organization(request.user)
        if not org:
            return Response([])
        days = int(request.query_params.get("days") or 30)
        cutoff = date.today() + timedelta(days=days)
        qs = self.get_queryset().filter(
            organization=org,
            status__in=[
                ProbationRecord.Status.ON_PROBATION,
                ProbationRecord.Status.EXTENDED,
            ],
            end_date__lte=cutoff,
            end_date__gte=date.today() - timedelta(days=7),
        ).order_by("end_date")
        return Response(self.get_serializer(qs, many=True).data)


class PerformanceReviewViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = PerformanceReview.objects.select_related("employee")
    serializer_class = PerformanceReviewSerializer
    filterset_fields = ("status", "employee")
    rbac_module = "hr.performance"
    workflow_submit_to = "submitted"
    workflow_approve_to = "approved"
    workflow_reject_to = "draft"


class TrainingCourseViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.all()
    serializer_class = TrainingCourseSerializer
    search_fields = ("code", "title", "provider", "category")
    filterset_fields = ("is_active", "is_mandatory", "category")
    rbac_module = "hr.training"


class TrainingRecordViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingRecord.objects.select_related("employee", "course")
    serializer_class = TrainingRecordSerializer
    search_fields = ("title", "provider", "certificate_no")
    filterset_fields = ("status", "employee", "course")
    rbac_module = "hr.training"

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        rec = self.get_object()
        rec.status = TrainingRecord.Status.COMPLETED
        if not rec.end_date:
            rec.end_date = date.today()
        cert_no = str(request.data.get("certificate_no") or "").strip()
        if cert_no:
            rec.certificate_no = cert_no
        if request.data.get("score") not in (None, ""):
            rec.score = Decimal(str(request.data.get("score")))
        if rec.course_id and rec.course.validity_months and not rec.certificate_expires_on:
            rec.certificate_expires_on = date.today() + timedelta(
                days=30 * int(rec.course.validity_months)
            )
        rec.save()
        return Response(self.get_serializer(rec).data)

    @action(detail=False, methods=["get"], url_path="expiring-certs")
    def expiring_certs(self, request):
        org = user_organization(request.user)
        if not org:
            return Response([])
        days = int(request.query_params.get("days") or 60)
        cutoff = date.today() + timedelta(days=days)
        qs = (
            self.get_queryset()
            .filter(
                organization=org,
                certificate_expires_on__isnull=False,
                certificate_expires_on__lte=cutoff,
                status=TrainingRecord.Status.COMPLETED,
            )
            .order_by("certificate_expires_on")
        )
        return Response(self.get_serializer(qs, many=True).data)


class SeparationRecordViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SeparationRecord.objects.select_related(
        "employee", "fnf_worksheet"
    ).prefetch_related("checklist_items")
    serializer_class = SeparationRecordSerializer
    filterset_fields = ("status", "employee")
    rbac_module = "hr.separation"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        sep = serializer.save(organization=org, created_by=self.request.user)
        seed_separation_checklist(sep, user=self.request.user)
        FinalSettlement.objects.get_or_create(
            organization=org,
            separation=sep,
            defaults={"created_by": self.request.user},
        )
        return sep

    @action(detail=True, methods=["post"], url_path="start-clearance")
    def start_clearance(self, request, pk=None):
        sep = self.get_object()
        seed_separation_checklist(sep, user=request.user)
        sep.status = SeparationRecord.Status.CLEARANCE
        sep.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(sep).data)

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        """Pragmatic F&F worksheet: leave encashment + notice + gratuity − deductions."""
        sep = self.get_object()
        emp = sep.employee
        basic = Decimal(str(emp.basic_salary or 0))
        daily = (basic / Decimal("30")).quantize(Decimal("0.01")) if basic else Decimal("0")

        year = (sep.last_working_day or date.today()).year
        leave_days = Decimal("0")
        for bal in LeaveBalance.objects.filter(
            employee=emp, year=year, leave_type__allow_encashment=True
        ).select_related("leave_type"):
            avail = Decimal(str(bal.available or 0))
            if avail > 0:
                leave_days += avail
        leave_encashment = (leave_days * daily).quantize(Decimal("0.01"))

        if "notice_pay" in request.data:
            notice_pay = Decimal(str(request.data.get("notice_pay") or 0))
        else:
            notice_pay = (daily * Decimal("30")).quantize(Decimal("0.01"))

        if "gratuity" in request.data:
            gratuity = Decimal(str(request.data.get("gratuity") or 0))
        else:
            years = Decimal("0")
            if emp.date_of_joining and sep.last_working_day:
                days = (sep.last_working_day - emp.date_of_joining).days
                years = (Decimal(days) / Decimal("365")).quantize(Decimal("0.01"))
            # Simple: 15 days basic per completed year
            gratuity = (years * daily * Decimal("15")).quantize(Decimal("0.01"))

        if "deductions" in request.data:
            deductions = Decimal(str(request.data.get("deductions") or 0))
        else:
            deductions = Decimal("0")
            try:
                from payroll.models import EmployeeLoan

                for loan in EmployeeLoan.objects.filter(
                    employee=emp, status__in=["active", "approved"]
                ):
                    deductions += Decimal(str(loan.outstanding_balance or 0))
            except Exception:
                pass

        net = (leave_encashment + notice_pay + gratuity - deductions).quantize(
            Decimal("0.01")
        )
        fnf, _ = FinalSettlement.objects.get_or_create(
            organization=sep.organization,
            separation=sep,
            defaults={"created_by": request.user},
        )
        fnf.leave_encashment = leave_encashment
        fnf.notice_pay = notice_pay
        fnf.gratuity = gratuity
        fnf.deductions = deductions
        fnf.net_payable = net
        fnf.status = FinalSettlement.Status.CALCULATED
        if "notes" in request.data:
            fnf.notes = str(request.data.get("notes") or "")
        fnf.updated_by = request.user
        fnf.save()
        sep.final_settlement = net
        sep.save(update_fields=["final_settlement", "updated_at"])
        return Response(self.get_serializer(sep).data)

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        sep = self.get_object()
        pending = sep.checklist_items.filter(is_done=False)
        force = bool(request.data.get("force"))
        if pending.exists() and not force:
            raise ValidationError(
                {
                    "checklist": f"{pending.count()} clearance item(s) still open. "
                    "Complete them or pass force=true."
                }
            )
        if "final_settlement" in request.data:
            sep.final_settlement = Decimal(str(request.data.get("final_settlement") or 0))
        else:
            fnf = getattr(sep, "fnf_worksheet", None)
            if fnf is not None:
                sep.final_settlement = fnf.net_payable
        sep.status = SeparationRecord.Status.SETTLED
        sep.save(update_fields=["status", "final_settlement", "updated_at"])
        emp = sep.employee
        emp.status = Employee.Status.SEPARATED
        # Unlink ESS login so portal access stops
        if emp.user_id and request.data.get("unlink_user", True):
            emp.user = None
        emp.save(update_fields=["status", "user", "updated_at"])
        return Response(self.get_serializer(sep).data)

    @action(detail=True, methods=["post"], url_path="toggle-checklist")
    def toggle_checklist(self, request, pk=None):
        sep = self.get_object()
        item_id = request.data.get("item_id")
        item = SeparationChecklistItem.objects.filter(
            separation=sep, pk=item_id
        ).first()
        if not item:
            raise ValidationError({"item_id": "Not found"})
        item.is_done = not item.is_done
        item.done_at = timezone.now() if item.is_done else None
        if "notes" in request.data:
            item.notes = str(request.data.get("notes") or "")
        item.save(update_fields=["is_done", "done_at", "notes", "updated_at"])
        return Response(SeparationChecklistItemSerializer(item).data)


class FinalSettlementViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = FinalSettlement.objects.select_related(
        "separation", "separation__employee"
    )
    serializer_class = FinalSettlementSerializer
    filterset_fields = ("status", "separation")
    rbac_module = "hr.separation"
    http_method_names = ["get", "head", "options", "patch", "put"]


class ExpenseClaimViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ExpenseClaim.objects.select_related("employee")
    serializer_class = ExpenseClaimSerializer
    search_fields = ("category", "notes", "employee__employee_code", "employee__first_name")
    filterset_fields = ("status", "employee", "category")
    rbac_module = "hr.claims"


class DocumentTypeDefinitionViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = DocumentTypeDefinition.objects.all()
    serializer_class = DocumentTypeDefinitionSerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_required", "is_active", "requires_expiry")
    rbac_module = "hr.documents"

    def get_queryset(self):
        from core.access import user_organization as uo

        qs = super().get_queryset()
        org = uo(self.request.user)
        if org:
            ensure_default_document_types(org)
        return qs

    @action(detail=False, methods=["post"], url_path="seed-defaults")
    def seed_defaults(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        created = ensure_default_document_types(org)
        return Response({"created": created, "count": len(created)})


class EmployeeDocumentViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = EmployeeDocument.objects.select_related("employee")
    serializer_class = EmployeeDocumentSerializer
    search_fields = ("title", "doc_type", "reference")
    filterset_fields = ("doc_type", "employee", "verification_status")
    rbac_module = "hr.documents"

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        org = user_organization(request.user)
        if not org:
            return Response([])
        days = int(request.query_params.get("days") or 30)
        today = date.today()
        cutoff = today + timedelta(days=days)
        qs = (
            self.get_queryset()
            .filter(
                organization=org,
                expires_on__isnull=False,
                expires_on__lte=cutoff,
            )
            .order_by("expires_on")
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        doc = self.get_object()
        decision = str(request.data.get("status") or "verified").lower()
        if decision not in ("verified", "rejected", "pending"):
            raise ValidationError({"status": "Use verified, rejected, or pending"})
        doc.verification_status = decision
        doc.verified_at = timezone.now() if decision == "verified" else None
        if request.data.get("notes"):
            doc.notes = ((doc.notes or "") + "\n" + str(request.data["notes"])).strip()
        doc.save(update_fields=["verification_status", "verified_at", "notes", "updated_at"])
        return Response(self.get_serializer(doc).data)


class JobHistoryViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = JobHistory.objects.select_related("employee", "from_manager", "to_manager")
    serializer_class = JobHistorySerializer
    search_fields = (
        "employee__employee_code",
        "employee__first_name",
        "employee__last_name",
        "reason",
        "to_designation",
        "to_department",
    )
    filterset_fields = ("event_type", "employee", "effective_date")
    rbac_module = "hr.employees"

    @action(detail=False, methods=["post"], url_path="apply-event")
    def apply_event(self, request):
        """Create history row and optionally apply to employee master."""
        org = user_organization(request.user)
        emp_id = request.data.get("employee")
        if not emp_id:
            raise ValidationError({"employee": "Required"})
        emp = Employee.objects.filter(organization=org, pk=emp_id).first()
        if not emp:
            raise ValidationError({"employee": "Not found"})
        event_type = str(request.data.get("event_type") or JobHistory.EventType.OTHER)
        eff = request.data.get("effective_date") or date.today().isoformat()
        if isinstance(eff, str):
            eff = date.fromisoformat(eff)
        to_snap = {
            "department_id": request.data.get("department_id")
            if "department_id" in request.data
            else emp.department_id,
            "designation_id": request.data.get("designation_id")
            if "designation_id" in request.data
            else emp.designation_id,
            "reporting_manager_id": request.data.get("reporting_manager_id")
            if "reporting_manager_id" in request.data
            else emp.reporting_manager_id,
            "basic_salary": request.data.get("basic_salary", emp.basic_salary),
            "status": request.data.get("status") or emp.status,
            "contract_type": request.data.get("contract_type") or emp.contract_type,
            "work_location": request.data.get("work_location", emp.work_location),
        }
        apply = bool(request.data.get("apply_to_employee", True))
        # Resolve labels after optional apply
        hist = record_job_event(
            emp,
            event_type=event_type,
            effective_date=eff,
            reason=str(request.data.get("reason") or ""),
            user=request.user,
            to_snapshot=to_snap,
            apply_to_employee=apply,
        )
        return Response(JobHistorySerializer(hist).data, status=201)
