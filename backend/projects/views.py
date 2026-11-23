from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as SerValidationError

from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from core.workflow import WorkflowActionsMixin
from projects.models import Project, ProjectCost, ProjectTask, TimeEntry


def unbilled_time_entries(project):
    """Approved billable time not sitting on a live AR invoice."""
    from finance.models import CustomerInvoice

    return TimeEntry.objects.filter(
        organization_id=project.organization_id,
        project=project,
        status=TimeEntry.Status.APPROVED,
        billable=True,
        is_deleted=False,
    ).filter(
        Q(customer_invoice__isnull=True)
        | Q(customer_invoice__status=CustomerInvoice.Status.REJECTED)
        | Q(customer_invoice__is_deleted=True)
    )
from projects.serializers import (
    ProjectCostSerializer,
    ProjectSerializer,
    ProjectTaskSerializer,
    TimeEntrySerializer,
)


class ProjectViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related("customer")
    serializer_class = ProjectSerializer
    search_fields = ("code", "name")
    filterset_fields = ("status", "customer")
    rbac_module = "projects.projects"

    @property
    def rbac_action(self):
        if getattr(self, "action", None) == "bill_timesheets":
            return "change"
        return None

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        project = self.get_object()
        zero = Decimal("0")
        costs_total = (
            ProjectCost.objects.filter(
                organization_id=project.organization_id,
                project=project,
                is_deleted=False,
            ).aggregate(s=Sum("amount"))["s"]
            or zero
        )
        approved = TimeEntry.objects.filter(
            organization_id=project.organization_id,
            project=project,
            status=TimeEntry.Status.APPROVED,
            is_deleted=False,
        )
        line_amount = ExpressionWrapper(
            F("hours") * F("rate"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
        ts = approved.aggregate(
            total_hours=Sum("hours"),
            total_amount=Sum(line_amount),
        )
        billable = approved.filter(billable=True).aggregate(
            total_hours=Sum("hours"), total_amount=Sum(line_amount)
        )
        unbilled = unbilled_time_entries(project).aggregate(
            total_hours=Sum("hours"), total_amount=Sum(line_amount)
        )
        from finance.models import CustomerInvoice

        latest = (
            CustomerInvoice.objects.filter(
                organization_id=project.organization_id,
                project=project,
                is_deleted=False,
            )
            .order_by("-id")
            .first()
        )
        timesheet_hours = ts["total_hours"] or zero
        timesheet_amount = ts["total_amount"] or zero
        open_tasks = ProjectTask.objects.filter(
            organization_id=project.organization_id,
            project=project,
            status=ProjectTask.Status.OPEN,
            is_deleted=False,
        ).count()
        budget = project.budget_amount or zero
        total_cost = costs_total + timesheet_amount
        return Response(
            {
                "project": project.id,
                "code": project.code,
                "name": project.name,
                "budget_amount": str(budget),
                "costs_total": str(costs_total),
                "timesheet_hours": str(timesheet_hours),
                "timesheet_amount": str(timesheet_amount),
                "billable_hours": str(billable["total_hours"] or zero),
                "billable_amount": str(billable["total_amount"] or zero),
                "unbilled_hours": str(unbilled["total_hours"] or zero),
                "unbilled_amount": str(unbilled["total_amount"] or zero),
                "latest_invoice_id": latest.id if latest else None,
                "latest_invoice_no": latest.invoice_no if latest else "",
                "total_cost": str(total_cost),
                "budget_remaining": str(budget - total_cost),
                "open_tasks": open_tasks,
            }
        )

    @action(detail=True, methods=["post"], url_path="bill-timesheets")
    def bill_timesheets(self, request, pk=None):
        from datetime import timedelta

        from core.doc_numbers import ensure_doc_no
        from finance.models import CustomerInvoice

        project = self.get_object()
        if not project.customer_id:
            raise SerValidationError({"customer": "Set a customer before billing timesheets."})
        with transaction.atomic():
            project = (
                Project.objects.select_for_update()
                .select_related("customer")
                .get(pk=project.pk)
            )
            entries = list(
                unbilled_time_entries(project).select_for_update().order_by("date", "id")
            )
            total = Decimal("0")
            hours = Decimal("0")
            bits = []
            priced = []
            for entry in entries:
                line = ((entry.hours or 0) * (entry.rate or 0)).quantize(Decimal("0.01"))
                if line <= 0:
                    continue
                priced.append(entry)
                total += line
                hours += entry.hours or 0
                if len(bits) < 12:
                    bits.append(f"{entry.date} {entry.hours}h")
            total = total.quantize(Decimal("0.01"))
            if total <= 0:
                raise SerValidationError("No approved billable time left to invoice.")
            if len(priced) > len(bits):
                bits.append(f"+{len(priced) - len(bits)} more")
            terms = project.customer.payment_terms_days or 30
            inv_date = timezone.localdate()
            data = {"invoice_no": ""}
            ensure_doc_no(
                data,
                "invoice_no",
                project.organization,
                kind="ar_invoice",
                model=CustomerInvoice,
            )
            inv = CustomerInvoice.objects.create(
                organization=project.organization,
                customer=project.customer,
                project=project,
                invoice_no=data["invoice_no"],
                invoice_date=inv_date,
                due_date=inv_date + timedelta(days=terms),
                amount=total,
                status=CustomerInvoice.Status.DRAFT,
                currency=project.customer.currency or "PKR",
                description=f"Project {project.code}: " + "; ".join(bits),
                created_by=request.user,
                updated_by=request.user,
            )
            TimeEntry.objects.filter(pk__in=[entry.id for entry in priced]).update(
                customer_invoice=inv
            )
        return Response(
            {
                "invoice_id": inv.id,
                "invoice_no": inv.invoice_no,
                "amount": str(inv.amount),
                "hours": str(hours),
                "entries": len(priced),
                "href": f"/sales/invoices/{inv.id}",
            },
            status=201,
        )


class ProjectTaskViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ProjectTask.objects.select_related("project")
    serializer_class = ProjectTaskSerializer
    search_fields = ("name",)
    filterset_fields = ("status", "project")
    rbac_module = "projects.tasks"


class ProjectCostViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ProjectCost.objects.select_related("project", "cost_center")
    serializer_class = ProjectCostSerializer
    search_fields = ("description",)
    filterset_fields = ("project", "cost_center")
    rbac_module = "projects.costs"


class TimeEntryViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = TimeEntry.objects.select_related(
        "project", "task", "employee", "customer_invoice"
    )
    serializer_class = TimeEntrySerializer
    search_fields = ("notes", "project__code", "project__name", "task__name")
    filterset_fields = ("status", "project", "task", "employee", "billable", "date")
    rbac_module = "projects.timesheets"
    workflow_reject_to = "draft"

    @property
    def rbac_action(self):
        # Approve/reject require "change" (approver role); submit uses default "add".
        if getattr(self, "action", None) in ("approve", "reject"):
            return "change"
        return None

    def perform_destroy(self, instance):
        if instance.status == TimeEntry.Status.APPROVED:
            raise SerValidationError("Approved time entries cannot be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        with transaction.atomic():
            entry = self.get_object()
            was_approved = entry.status == TimeEntry.Status.APPROVED
            resp = super().approve(request, pk)
            if resp.status_code == 200 and not was_approved:
                entry.refresh_from_db()
                if entry.status == TimeEntry.Status.APPROVED and entry.task_id:
                    ProjectTask.objects.filter(pk=entry.task_id).update(
                        hours_logged=F("hours_logged") + (entry.hours or Decimal("0"))
                    )
        return resp
