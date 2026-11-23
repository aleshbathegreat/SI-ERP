from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from service.models import ServiceCase, ServiceNote
from service.serializers import ServiceCaseSerializer, ServiceNoteSerializer

CASE_ACTIONS = ("assign", "resolve", "close", "reopen", "issue_part", "create_invoice")


class ServiceCaseViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ServiceCase.objects.select_related(
        "customer", "sales_order", "assigned_to", "customer_invoice"
    ).prefetch_related("parts__item", "parts__warehouse")
    serializer_class = ServiceCaseSerializer
    search_fields = ("case_no", "subject", "description", "customer__name")
    filterset_fields = ("status", "priority", "customer", "sales_order", "assigned_to")
    rbac_module = "service.cases"

    @property
    def rbac_action(self):
        if getattr(self, "action", None) in CASE_ACTIONS:
            return "change"
        return None

    def _respond(self, case):
        case.refresh_from_db()
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        case = self.get_object()
        if case.status == ServiceCase.Status.CLOSED:
            raise ValidationError("Cannot assign a closed case.")
        raw = request.data.get("assigned_to", request.data.get("user"))
        if raw in (None, ""):
            case.assigned_to = None
        else:
            user = get_user_model().objects.filter(pk=raw, is_active=True).first()
            org = user_organization(request.user)
            if user is None or (org and user_organization(user) != org):
                raise ValidationError({"assigned_to": "Invalid user."})
            case.assigned_to = user
        fields = ["assigned_to", "updated_at"]
        if case.assigned_to_id and case.status == ServiceCase.Status.OPEN:
            case.status = ServiceCase.Status.IN_PROGRESS
            fields.append("status")
        case.updated_by = request.user
        fields.append("updated_by")
        case.save(update_fields=fields)
        return self._respond(case)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        case = self.get_object()
        if case.status in (ServiceCase.Status.RESOLVED, ServiceCase.Status.CLOSED):
            raise ValidationError(f"Case is already {case.status}.")
        case.status = ServiceCase.Status.RESOLVED
        case.resolved_at = timezone.now()
        case.updated_by = request.user
        case.save(update_fields=["status", "resolved_at", "updated_by", "updated_at"])
        return self._respond(case)

    @action(detail=True, methods=["post"], url_path="issue-part")
    def issue_part(self, request, pk=None):
        from decimal import Decimal

        from django.db import transaction
        from ops.parts_issue import issue_spare
        from service.models import ServicePart

        case = self.get_object()
        if case.status == ServiceCase.Status.CLOSED:
            raise ValidationError("Cannot issue parts on a closed case.")
        if case.customer_invoice_id:
            raise ValidationError("This case is already billed.")
        with transaction.atomic():
            org = user_organization(request.user)
            issued = issue_spare(
                org=org,
                item_id=request.data.get("item"),
                qty=request.data.get("qty"),
                warehouse_id=request.data.get("warehouse"),
                user=request.user,
                reference=case.case_no,
                notes=f"Service case {case.case_no}",
            )
            unit_price = issued["unit_price"]
            if request.data.get("unit_price") not in (None, ""):
                unit_price = Decimal(str(request.data.get("unit_price")))
                if unit_price < 0:
                    raise ValidationError({"unit_price": "Price cannot be negative."})
            ServicePart.objects.create(
                organization=org,
                case=case,
                item=issued["item"],
                warehouse=issued["warehouse"],
                qty=Decimal(str(request.data.get("qty"))),
                unit_cost=issued["unit_cost"],
                unit_price=unit_price,
                stock_movement=issued["movement"],
            )
            if case.status == ServiceCase.Status.OPEN:
                case.status = ServiceCase.Status.IN_PROGRESS
                case.updated_by = request.user
                case.save(update_fields=["status", "updated_by", "updated_at"])
        return self._respond(case)

    @action(detail=True, methods=["post"], url_path="create-invoice")
    def create_invoice(self, request, pk=None):
        from datetime import timedelta
        from decimal import Decimal

        from core.doc_numbers import ensure_doc_no
        from finance.models import CustomerInvoice

        case = self.get_object()
        if not case.customer_id:
            raise ValidationError({"customer": "Set a customer before billing."})
        if case.status not in (ServiceCase.Status.RESOLVED, ServiceCase.Status.CLOSED):
            raise ValidationError("Resolve the case before creating an AR invoice.")
        if (
            case.customer_invoice_id
            and case.customer_invoice.status != CustomerInvoice.Status.REJECTED
        ):
            raise ValidationError(
                {
                    "detail": "An AR invoice already exists for this case.",
                    "invoice_id": case.customer_invoice_id,
                    "invoice_no": case.customer_invoice.invoice_no,
                }
            )
        try:
            labor = Decimal(str(request.data.get("labor_amount") or 0))
        except Exception as exc:
            raise ValidationError({"labor_amount": "Labor amount must be a number."}) from exc
        if labor < 0:
            raise ValidationError({"labor_amount": "Labor amount cannot be negative."})
        parts_total = Decimal("0")
        bits = []
        for part in case.parts.select_related("item"):
            parts_total += (part.qty or 0) * (part.unit_price or 0)
            bits.append(f"{part.item.sku} x {part.qty}")
        if labor:
            bits.append(f"labor {labor}")
        amount = (parts_total + labor).quantize(Decimal("0.01"))
        if amount <= 0:
            raise ValidationError("Nothing to bill. Issue parts or enter a labor amount.")
        terms = case.customer.payment_terms_days or 30
        inv_date = timezone.localdate()
        data = {"invoice_no": ""}
        ensure_doc_no(
            data, "invoice_no", case.organization, kind="ar_invoice", model=CustomerInvoice
        )
        inv = CustomerInvoice.objects.create(
            organization=case.organization,
            customer=case.customer,
            sales_order=case.sales_order,
            invoice_no=data["invoice_no"],
            invoice_date=inv_date,
            due_date=inv_date + timedelta(days=terms),
            amount=amount,
            status=CustomerInvoice.Status.DRAFT,
            currency=case.customer.currency or "PKR",
            description=f"Service {case.case_no}: " + "; ".join(bits),
            created_by=request.user,
            updated_by=request.user,
        )
        case.customer_invoice = inv
        case.updated_by = request.user
        case.save(update_fields=["customer_invoice", "updated_by", "updated_at"])
        body = self.get_serializer(case).data
        body["invoice_id"] = inv.id
        body["href"] = f"/sales/invoices/{inv.id}"
        return Response(body, status=201)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        case = self.get_object()
        if case.status == ServiceCase.Status.CLOSED:
            raise ValidationError("Case is already closed.")
        case.status = ServiceCase.Status.CLOSED
        fields = ["status", "updated_by", "updated_at"]
        if case.resolved_at is None:
            case.resolved_at = timezone.now()
            fields.append("resolved_at")
        case.updated_by = request.user
        case.save(update_fields=fields)
        return self._respond(case)

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, pk=None):
        case = self.get_object()
        if case.status not in (ServiceCase.Status.RESOLVED, ServiceCase.Status.CLOSED):
            raise ValidationError("Only resolved or closed cases can be reopened.")
        case.status = (
            ServiceCase.Status.IN_PROGRESS
            if case.assigned_to_id
            else ServiceCase.Status.OPEN
        )
        case.resolved_at = None
        case.updated_by = request.user
        case.save(update_fields=["status", "resolved_at", "updated_by", "updated_at"])
        return self._respond(case)


class ServiceNoteViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ServiceNote.objects.select_related("case", "created_by")
    serializer_class = ServiceNoteSerializer
    search_fields = ("body", "case__case_no", "case__subject")
    filterset_fields = ("case", "is_internal")
    rbac_module = "service.notes"
