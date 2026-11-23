from decimal import Decimal

from rest_framework import serializers

from projects.models import Project, ProjectCost, ProjectTask, TimeEntry

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)


class ProjectSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=""
    )

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = RO


class ProjectTaskSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.code", read_only=True, default="")
    project_name = serializers.CharField(source="project.name", read_only=True, default="")

    class Meta:
        model = ProjectTask
        fields = "__all__"
        read_only_fields = RO


class ProjectCostSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.code", read_only=True, default="")
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    cost_center_name = serializers.CharField(
        source="cost_center.name", read_only=True, default=""
    )

    class Meta:
        model = ProjectCost
        fields = "__all__"
        read_only_fields = RO


class TimeEntrySerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.code", read_only=True, default="")
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    task_name = serializers.CharField(source="task.name", read_only=True, default="")
    employee_name = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    invoice_no = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = "__all__"
        read_only_fields = list(RO) + [
            "status",
            "submitted_by",
            "approved_by",
            "customer_invoice",
        ]

    def get_employee_name(self, obj):
        e = obj.employee
        if not e:
            return ""
        return f"{e.first_name} {e.last_name}".strip()

    def get_amount(self, obj):
        return str(((obj.hours or 0) * (obj.rate or 0)).quantize(Decimal("0.01")))

    def get_invoice_no(self, obj):
        inv = obj.customer_invoice
        if not inv or inv.is_deleted:
            return ""
        return inv.invoice_no

    def validate_hours(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Hours must be greater than zero.")
        if value > 24:
            raise serializers.ValidationError("Hours cannot exceed 24 per entry.")
        return value

    def validate_rate(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Rate cannot be negative.")
        return value

    def validate(self, attrs):
        inst = self.instance
        project = attrs.get("project") or (inst.project if inst else None)
        task = attrs.get("task", inst.task if inst else None)
        employee = attrs.get("employee", inst.employee if inst else None)
        if inst is not None and inst.status != TimeEntry.Status.DRAFT:
            raise serializers.ValidationError(
                {"detail": f"Cannot edit a {inst.status} time entry."}
            )
        if task and project and task.project_id != project.id:
            raise serializers.ValidationError(
                {"task": "Task does not belong to the selected project."}
            )
        from core.access import user_organization

        request = self.context.get("request")
        req_org = user_organization(request.user) if request else None
        org_id = project.organization_id if project else None
        if req_org and org_id and req_org.id != org_id:
            raise serializers.ValidationError({"project": "Invalid project."})
        if employee and org_id and employee.organization_id != org_id:
            raise serializers.ValidationError(
                {"employee": "Employee belongs to a different organization."}
            )
        return attrs
