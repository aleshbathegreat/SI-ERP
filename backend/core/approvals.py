"""Cross-module LoA inbox. A row appears only when the user's role may approve it."""

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import can
from core.access import is_owner, user_organization
from finance.models import Budget, CustomerInvoice, JournalEntry, VendorInvoice
from hr.models import (
    AttendanceRegularization,
    LeaveRequest,
    PerformanceReview,
    RecruitmentRequest,
)
from ops.models import PurchaseOrder, PurchaseRequisition
from payroll.models import PayrollPeriod

KIND_LABELS = {
    "journal": "Journal",
    "invoice": "Vendor bill",
    "ar_invoice": "Customer invoice",
    "budget": "Budget",
    "purchase_requisition": "Purchase request",
    "purchase_order": "Purchase order",
    "leave": "Leave",
    "recruitment": "Recruitment",
    "performance": "Performance review",
    "payroll": "Payroll run",
    "attendance": "Attendance correction",
}


def _role_codes(user, org) -> set[str]:
    from accounts.models import UserRole

    codes = {
        (code or "").strip().lower()
        for code in UserRole.objects.filter(
            user=user, role__organization=org, role__is_deleted=False
        ).values_list("role__code", flat=True)
    }
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "role", None):
        codes.add(str(profile.role).strip().lower())
    if profile and getattr(profile, "primary_role_id", None):
        code = getattr(getattr(profile, "primary_role", None), "code", "")
        if code:
            codes.add(str(code).strip().lower())
    return {c for c in codes if c}


def _amount(obj) -> float:
    for attr in ("amount", "estimated_amount", "total", "net_payable", "principal"):
        val = getattr(obj, attr, None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 0.0


def _matrix_allows(user, org, module: str, amount: float, cache: dict | None = None) -> bool:
    """Match the approve action: no rules means RBAC change is enough."""
    from core.models import ApprovalMatrixRule

    store = cache if cache is not None else {}
    if "owner" not in store:
        store["owner"] = is_owner(user)
        store["roles"] = _role_codes(user, org)
    rules_by_module = store.setdefault("rules", {})
    if module not in rules_by_module:
        rules_by_module[module] = list(
            ApprovalMatrixRule.objects.filter(
                organization=org, module_key=module, is_deleted=False
            )
        )
    rules = rules_by_module[module]
    if not rules or store["owner"]:
        return True
    matching = [
        rule
        for rule in rules
        if float(rule.min_amount or 0) <= amount
        and (rule.max_amount is None or amount <= float(rule.max_amount))
    ]
    if not matching:
        return False
    allowed = {(rule.role_code or "").strip().lower() for rule in matching}
    return bool(store["roles"] & allowed)


def _actor_name(obj) -> str:
    user = getattr(obj, "submitted_by", None) or getattr(obj, "created_by", None)
    if user is None:
        return ""
    full = (user.get_full_name() or "").strip()
    return full or user.username or ""


def _self_submitted(user, obj) -> bool:
    submitted_by_id = getattr(obj, "submitted_by_id", None)
    created_by_id = getattr(obj, "created_by_id", None)
    if submitted_by_id and submitted_by_id == user.id:
        return True
    return not submitted_by_id and bool(created_by_id) and created_by_id == user.id


class ApprovalsInboxView(APIView):
    rbac_module = "approvals"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"count": 0, "items": []})

        items = []
        change_ok: dict[str, bool] = {}
        matrix_cache: dict = {}

        def may(module: str) -> bool:
            if module not in change_ok:
                change_ok[module] = can(request.user, module, "change")
            return change_ok[module]

        def add(module, kind, obj, label, status, api_prefix, open_path):
            if not may(module):
                return
            amount = _amount(obj)
            if not _matrix_allows(request.user, org, module, amount, matrix_cache):
                return
            own = _self_submitted(request.user, obj)
            items.append(
                {
                    "module": module,
                    "kind": kind,
                    "kind_label": KIND_LABELS.get(kind, kind),
                    "id": obj.pk,
                    "label": label,
                    "status": status,
                    "amount": f"{amount:.2f}" if amount else "",
                    "submitted_by": _actor_name(obj),
                    "can_act": not own,
                    "block_reason": (
                        "You submitted this, so someone else in the role must approve it."
                        if own
                        else ""
                    ),
                    "href": api_prefix,
                    "approve_url": f"{api_prefix}{obj.pk}/approve/",
                    "reject_url": f"{api_prefix}{obj.pk}/reject/",
                    "open_path": open_path,
                }
            )

        if may("finance.journals"):
            for row in JournalEntry.objects.filter(
                organization=org, status="submitted"
            ).select_related("submitted_by", "created_by")[:50]:
                add(
                    "finance.journals",
                    "journal",
                    row,
                    row.reference or f"Journal #{row.pk}",
                    row.status,
                    "finance/journals/",
                    f"/finance/journals/{row.pk}",
                )
        if may("finance.invoices"):
            for row in VendorInvoice.objects.filter(
                organization=org, status="submitted"
            ).select_related("vendor", "created_by")[:50]:
                add(
                    "finance.invoices",
                    "invoice",
                    row,
                    f"{row.invoice_no} · {row.vendor.name}",
                    row.status,
                    "finance/invoices/",
                    f"/finance/invoices/{row.pk}",
                )
        if may("sales.invoices"):
            for row in CustomerInvoice.objects.filter(
                organization=org, status="submitted", is_deleted=False
            ).select_related("customer", "created_by")[:50]:
                add(
                    "sales.invoices",
                    "ar_invoice",
                    row,
                    f"{row.invoice_no} · {row.customer.name}",
                    row.status,
                    "sales/invoices/",
                    f"/sales/invoices/{row.pk}",
                )
        if may("finance.budgets"):
            for row in Budget.objects.filter(
                organization=org, status="submitted"
            ).select_related("created_by")[:50]:
                add(
                    "finance.budgets",
                    "budget",
                    row,
                    f"{row.name} FY{row.fiscal_year}",
                    row.status,
                    "finance/budgets/",
                    f"/finance/budgets/{row.pk}",
                )
        if may("procurement.requisitions"):
            for row in PurchaseRequisition.objects.filter(
                organization=org, status="submitted", is_deleted=False
            ).select_related("preferred_vendor", "created_by")[:50]:
                vendor = row.preferred_vendor.name if row.preferred_vendor_id else "—"
                add(
                    "procurement.requisitions",
                    "purchase_requisition",
                    row,
                    f"{row.pr_no} · {vendor}",
                    row.status,
                    "procurement/requisitions/",
                    f"/procurement/requisitions/{row.pk}",
                )
        if may("procurement.orders"):
            for row in PurchaseOrder.objects.filter(
                organization=org, status="submitted", is_deleted=False
            ).select_related("vendor", "created_by")[:50]:
                add(
                    "procurement.orders",
                    "purchase_order",
                    row,
                    f"{row.po_no} · {row.vendor.name}",
                    row.status,
                    "procurement/orders/",
                    f"/procurement/orders/{row.pk}",
                )
        if may("hr.leaves"):
            for row in LeaveRequest.objects.filter(
                employee__organization=org, status="pending"
            ).select_related("employee", "leave_type", "created_by")[:50]:
                add(
                    "hr.leaves",
                    "leave",
                    row,
                    f"{row.employee.full_name} · {row.leave_type.name}",
                    row.status,
                    "hr/leave-requests/",
                    f"/hr/leaves/{row.pk}",
                )
        if may("hr.recruitment"):
            for row in RecruitmentRequest.objects.filter(
                organization=org, status="interview"
            ).select_related("created_by")[:50]:
                add(
                    "hr.recruitment",
                    "recruitment",
                    row,
                    row.title,
                    row.status,
                    "hr/recruitment/",
                    f"/hr/recruitment/{row.pk}",
                )
        if may("hr.performance"):
            for row in PerformanceReview.objects.filter(
                organization=org, status="submitted"
            ).select_related("employee", "created_by")[:50]:
                add(
                    "hr.performance",
                    "performance",
                    row,
                    f"{row.employee.full_name} · {row.period_label}",
                    row.status,
                    "hr/performance/",
                    f"/hr/performance/{row.pk}",
                )
        if may("payroll.periods"):
            for row in PayrollPeriod.objects.filter(
                organization=org, status="processing"
            ).select_related("created_by")[:50]:
                add(
                    "payroll.periods",
                    "payroll",
                    row,
                    row.name,
                    row.status,
                    "payroll/periods/",
                    "/payroll",
                )
        if may("hr.attendance"):
            for row in AttendanceRegularization.objects.filter(
                organization=org, status="pending"
            ).select_related("employee", "created_by")[:50]:
                add(
                    "hr.attendance",
                    "attendance",
                    row,
                    f"{row.employee.full_name} · {row.work_date}",
                    row.status,
                    "hr/attendance-regularizations/",
                    "/hr/attendance?tab=requests",
                )
        return Response({"count": len(items), "items": items})
