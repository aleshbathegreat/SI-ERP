from rest_framework import serializers

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
)

RO = ("organization", "created_at", "updated_at", "created_by", "updated_by")


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = RO


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = "__all__"
        read_only_fields = RO


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = RO


class OvertimePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimePolicy
        fields = "__all__"
        read_only_fields = RO


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    reporting_manager_name = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    docs_expiring_soon = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = RO

    def get_reporting_manager_name(self, obj):
        if obj.reporting_manager_id:
            return obj.reporting_manager.full_name
        return None

    def get_user_username(self, obj):
        if obj.user_id:
            return getattr(obj.user, "username", None)
        return None

    def get_docs_expiring_soon(self, obj):
        from datetime import date, timedelta

        cutoff = date.today() + timedelta(days=30)
        return obj.documents.filter(
            expires_on__isnull=False, expires_on__lte=cutoff, expires_on__gte=date.today()
        ).count()

    def validate_national_id(self, value):
        value = (value or "").strip()
        if not value:
            return value
        request = self.context.get("request")
        org = None
        if request:
            from core.access import user_organization

            org = user_organization(request.user)
        if self.instance is not None:
            org = org or self.instance.organization
        if org:
            qs = Employee.objects.filter(organization=org, national_id=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("National ID already used in this organization.")
        return value


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = RO


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    available = serializers.SerializerMethodField()
    allow_encashment = serializers.BooleanField(
        source="leave_type.allow_encashment", read_only=True
    )

    def get_available(self, obj):
        return str(obj.available)

    class Meta:
        model = LeaveBalance
        fields = "__all__"
        read_only_fields = RO


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.none(), required=False, allow_null=True
    )

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.access import user_organization

        request = self.context.get("request")
        org = user_organization(request.user) if request and request.user else None
        if org is not None:
            self.fields["employee"].queryset = Employee.objects.filter(
                organization=org, is_deleted=False
            )
        else:
            self.fields["employee"].queryset = Employee.objects.none()

    def validate(self, attrs):
        from hr.leave_service import count_leave_days, overlapping_leave_exists
        from core.access import user_organization

        instance = getattr(self, "instance", None)
        employee = attrs.get("employee") or (instance.employee if instance else None)
        leave_type = attrs.get("leave_type") or (instance.leave_type if instance else None)
        start = attrs.get("start_date") or (instance.start_date if instance else None)
        end = attrs.get("end_date") or (instance.end_date if instance else None)
        half = attrs.get("is_half_day")
        if half is None:
            half = bool(instance.is_half_day) if instance else False

        request = self.context.get("request")
        org = user_organization(request.user) if request and request.user else None
        if org is not None:
            if employee and employee.organization_id != org.id:
                raise serializers.ValidationError(
                    {"employee": "Employee is not in your organization."}
                )
            if leave_type and getattr(leave_type, "organization_id", None) not in (
                None,
                org.id,
            ):
                raise serializers.ValidationError(
                    {"leave_type": "Leave type is not in your organization."}
                )

        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date must be on or after start."})

        if employee and start and end:
            hit = overlapping_leave_exists(
                employee, start, end, exclude_id=instance.pk if instance else None
            )
            if hit:
                raise serializers.ValidationError(
                    {
                        "start_date": (
                            f"Overlaps existing {hit.status} leave "
                            f"({hit.start_date} → {hit.end_date})."
                        )
                    }
                )

        if leave_type and employee:
            restriction = (leave_type.gender_restriction or "").strip().lower()
            if restriction and (employee.gender or "").strip().lower() not in (
                "",
                restriction,
            ):
                raise serializers.ValidationError(
                    {"leave_type": f"This leave type is restricted to {restriction}."}
                )

        # Auto-compute working days unless explicitly provided and non-empty on create
        if employee and leave_type and start and end:
            org = employee.organization
            computed = count_leave_days(
                org, start, end, leave_type=leave_type, half_day=half
            )
            if half:
                attrs["end_date"] = start
            # Always recompute when half_day or days missing / zero
            if attrs.get("days") in (None, "", 0, "0") or half or not instance:
                attrs["days"] = computed
            elif instance and (
                "start_date" in attrs or "end_date" in attrs or "leave_type" in attrs
            ):
                attrs["days"] = computed
        return attrs


class RecruitmentRequestSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)

    class Meta:
        model = RecruitmentRequest
        fields = "__all__"
        read_only_fields = RO


class BenefitPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitPlan
        fields = "__all__"
        read_only_fields = RO


class EmployeeBenefitSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = EmployeeBenefit
        fields = "__all__"
        read_only_fields = RO


class AttendancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendancePolicy
        fields = "__all__"
        read_only_fields = RO


class AttendanceHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceHoliday
        fields = "__all__"
        read_only_fields = RO


class AttendanceRegularizationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)

    class Meta:
        model = AttendanceRegularization
        fields = "__all__"
        read_only_fields = RO + ("status", "review_note")


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    is_attendance_free = serializers.BooleanField(
        source="employee.is_attendance_free", read_only=True
    )
    worked_hours = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = "__all__"
        read_only_fields = RO + (
            "late_minutes",
            "early_leave_minutes",
            "overtime_minutes",
            "worked_minutes",
        )

    def get_worked_hours(self, obj):
        mins = obj.worked_minutes or 0
        return round(mins / 60, 2)

    def validate_employee(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Employee not in this organization.")
        return value

    def create(self, validated_data):
        from hr.attendance_service import ensure_exempt_or_block, evaluate_record

        emp = validated_data.get("employee")
        work_date = validated_data.get("work_date")
        if emp and emp.is_attendance_free and work_date:
            rec = ensure_exempt_or_block(emp, work_date)
            return rec
        rec = AttendanceRecord(**validated_data)
        evaluate_record(rec)
        rec.save()
        return rec

    def update(self, instance, validated_data):
        from hr.attendance_service import evaluate_record

        for k, v in validated_data.items():
            setattr(instance, k, v)
        if instance.employee_id and instance.employee.is_attendance_free:
            instance.status = AttendanceRecord.Status.EXEMPT
            instance.notes = instance.notes or "Attendance-exempt employee"
        else:
            evaluate_record(instance)
        instance.save()
        return instance


class ProbationRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = ProbationRecord
        fields = "__all__"
        read_only_fields = RO


class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceReview
        fields = "__all__"
        read_only_fields = RO

    def get_reviewer_name(self, obj):
        return obj.reviewer.full_name if obj.reviewer_id else None


class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = "__all__"
        read_only_fields = RO


class TrainingRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True, default=None)
    certificate_expired = serializers.SerializerMethodField()

    class Meta:
        model = TrainingRecord
        fields = "__all__"
        read_only_fields = RO

    def get_certificate_expired(self, obj):
        from datetime import date

        return bool(
            obj.certificate_expires_on and obj.certificate_expires_on < date.today()
        )

    def validate(self, attrs):
        course = attrs.get("course") or getattr(self.instance, "course", None)
        if course and not attrs.get("title"):
            attrs["title"] = course.title
        if course and not attrs.get("provider"):
            attrs["provider"] = course.provider or ""
        if course and attrs.get("hours") in (None, "", 0, "0"):
            attrs["hours"] = course.duration_hours
        return attrs


class SeparationChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeparationChecklistItem
        fields = "__all__"
        read_only_fields = RO


class FinalSettlementSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="separation.employee.full_name", read_only=True
    )
    last_working_day = serializers.DateField(
        source="separation.last_working_day", read_only=True
    )

    class Meta:
        model = FinalSettlement
        fields = "__all__"
        read_only_fields = RO


class SeparationRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    checklist_items = SeparationChecklistItemSerializer(many=True, read_only=True)
    checklist_done = serializers.SerializerMethodField()
    checklist_total = serializers.SerializerMethodField()
    fnf_worksheet = FinalSettlementSerializer(read_only=True)

    class Meta:
        model = SeparationRecord
        fields = "__all__"
        read_only_fields = RO

    def get_checklist_done(self, obj):
        return obj.checklist_items.filter(is_done=True).count()

    def get_checklist_total(self, obj):
        return obj.checklist_items.count()


class ExpenseClaimSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = ExpenseClaim
        fields = "__all__"
        read_only_fields = RO


class DocumentTypeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTypeDefinition
        fields = "__all__"
        read_only_fields = RO


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = "__all__"
        read_only_fields = RO

    def get_is_expired(self, obj):
        from datetime import date

        return bool(obj.expires_on and obj.expires_on < date.today())

    def get_days_to_expiry(self, obj):
        from datetime import date

        if not obj.expires_on:
            return None
        return (obj.expires_on - date.today()).days


class JobHistorySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)

    class Meta:
        model = JobHistory
        fields = "__all__"
        read_only_fields = RO
