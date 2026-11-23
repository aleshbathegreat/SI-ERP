"""LoA / preparer–reviewer workflow helpers with SoD enforcement."""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import AuditLog
from core.notifications import notify_org_roles

logger = logging.getLogger(__name__)


class WorkflowActionsMixin:
    workflow_status_field = "status"
    workflow_submit_to = "submitted"
    workflow_approve_to = "approved"
    workflow_reject_to = "rejected"
    workflow_post_to = "posted"
    workflow_allow_post = False

    def _org_of(self, obj):
        org = getattr(obj, "organization", None)
        if org is None and hasattr(obj, "employee"):
            org = obj.employee.organization
        if org is None and hasattr(obj, "period"):
            org = obj.period.organization
        return org

    def _set_status(self, obj, new_status, action_name, extra_fields=None):
        field = self.workflow_status_field
        old = getattr(obj, field)
        org = self._org_of(obj)
        try:
            from dms.workflow_engine import guard_module_action

            denied = guard_module_action(
                org,
                getattr(self, "rbac_module", "") or "",
                obj.pk,
                self.request.user,
                action_name,
            )
        except Exception:
            logger.exception("workflow role check failed")
            denied = None
        if denied:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(denied)
        setattr(obj, field, new_status)
        update_fields = [field]
        if hasattr(obj, "updated_at"):
            update_fields.append("updated_at")
        if extra_fields:
            for k, v in extra_fields.items():
                setattr(obj, k, v)
                update_fields.append(k)
        obj.save(update_fields=list(dict.fromkeys(update_fields)))
        AuditLog.objects.create(
            organization=org,
            user=self.request.user,
            action=action_name,
            module=getattr(self, "rbac_module", "") or "",
            object_type=obj.__class__.__name__,
            object_id=str(obj.pk),
            detail=f"{old} → {new_status}",
        )
        try:
            from dms.workflow_engine import sync_module_case

            sync_module_case(
                org,
                getattr(self, "rbac_module", "") or "",
                obj.pk,
                self.request.user,
                action_name,
            )
        except Exception:
            logger.exception("workflow case sync failed for %s #%s", getattr(self, "rbac_module", ""), obj.pk)
        notify_org_roles(
            org,
            subject=f"{obj.__class__.__name__} {action_name}: #{obj.pk}",
            message=f"{self.request.user.username} performed {action_name} ({old} → {new_status}).",
            role_codes=["approver", "admin", "owner", "finance", "hr", "payroll"],
            module=getattr(self, "rbac_module", "") or "",
            object_id=str(obj.pk),
        )
        return Response(self.get_serializer(obj).data)

    def _sod_block_self_approve(self, obj):
        if not getattr(settings, "SOD_ENFORCE", True):
            return None
        submitted_by_id = getattr(obj, "submitted_by_id", None)
        created_by_id = getattr(obj, "created_by_id", None)
        actor = self.request.user.id
        if submitted_by_id and submitted_by_id == actor:
            return Response(
                {"detail": "SoD violation: initiator cannot approve their own submission."},
                status=400,
            )
        if not submitted_by_id and created_by_id and created_by_id == actor:
            return Response(
                {"detail": "SoD violation: preparer cannot approve their own record."},
                status=400,
            )
        return None

    def _document_amount(self, obj):
        for attr in ("amount", "estimated_amount", "total", "net_payable"):
            val = getattr(obj, attr, None)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass
        return 0.0

    def _matrix_block_approve(self, obj):
        """If approval-matrix rules exist for this module, require matching role."""
        from accounts.models import UserRole
        from core.access import user_organization
        from core.models import ApprovalMatrixRule

        org = self._org_of(obj) or user_organization(self.request.user)
        module = getattr(self, "rbac_module", "") or ""
        if not org or not module:
            return None
        rules = list(
            ApprovalMatrixRule.objects.filter(
                organization=org, module_key=module, is_deleted=False
            )
        )
        if not rules:
            return None
        amount = self._document_amount(obj)
        matching = [
            r
            for r in rules
            if float(r.min_amount or 0) <= amount
            and (r.max_amount is None or amount <= float(r.max_amount))
        ]
        if not matching:
            return Response(
                {
                    "detail": (
                        f"No approval-matrix rule covers amount {amount} "
                        f"for module {module}."
                    )
                },
                status=400,
            )
        from core.access import is_owner

        if is_owner(self.request.user):
            return None
        allowed_roles = { (r.role_code or "").strip().lower() for r in matching }
        user_roles = set(
            UserRole.objects.filter(
                user=self.request.user,
                role__organization=org,
                role__is_deleted=False,
            ).values_list("role__code", flat=True)
        )
        user_roles = { (c or "").strip().lower() for c in user_roles }
        profile = getattr(self.request.user, "profile", None)
        if profile and getattr(profile, "role", None):
            user_roles.add(str(profile.role).strip().lower())
        if not (user_roles & allowed_roles):
            return Response(
                {
                    "detail": (
                        "Approval matrix: your role is not authorized for this "
                        f"amount ({amount}). Required: {', '.join(sorted(allowed_roles))}."
                    )
                },
                status=403,
            )
        return None

    def _period_locked(self, obj):
        from finance.models import AccountingPeriod

        org = self._org_of(obj)
        entry_date = getattr(obj, "entry_date", None) or getattr(obj, "invoice_date", None)
        if not org or not entry_date:
            return False
        period = AccountingPeriod.objects.filter(
            organization=org, year=entry_date.year, month=entry_date.month, is_locked=True
        ).first()
        return bool(period)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        obj = self.get_object()
        if self._period_locked(obj):
            return Response({"detail": "Accounting period is locked."}, status=400)
        current = getattr(obj, self.workflow_status_field)
        allowed = {"draft", "open", "pending"}
        if current not in allowed and current != self.workflow_submit_to:
            return Response({"detail": f"Cannot submit from status '{current}'"}, status=400)
        extra = {}
        if hasattr(obj, "submitted_by_id"):
            extra["submitted_by"] = request.user
        return self._set_status(obj, self.workflow_submit_to, "submit", extra)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        obj = self.get_object()
        if self._period_locked(obj):
            return Response({"detail": "Accounting period is locked."}, status=400)
        blocked = self._sod_block_self_approve(obj)
        if blocked:
            return blocked
        matrix_blocked = self._matrix_block_approve(obj)
        if matrix_blocked:
            return matrix_blocked
        current = getattr(obj, self.workflow_status_field)
        allowed = {self.workflow_submit_to, "pending", "processing", "submitted", "interview"}
        if current not in allowed:
            return Response({"detail": f"Cannot approve from status '{current}'"}, status=400)
        extra = {}
        if hasattr(obj, "approved_by_id"):
            extra["approved_by"] = request.user
        return self._set_status(obj, self.workflow_approve_to, "approve", extra)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        obj = self.get_object()
        current = getattr(obj, self.workflow_status_field)
        allowed = {self.workflow_submit_to, "pending", "processing", "submitted", "interview"}
        if current not in allowed:
            return Response({"detail": f"Cannot reject from status '{current}'"}, status=400)
        return self._set_status(obj, self.workflow_reject_to, "reject")

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        if not self.workflow_allow_post:
            return Response({"detail": "Posting not enabled"}, status=400)
        obj = self.get_object()
        if self._period_locked(obj):
            return Response({"detail": "Accounting period is locked."}, status=400)
        current = getattr(obj, self.workflow_status_field)
        if current != self.workflow_approve_to:
            return Response({"detail": f"Cannot post from status '{current}'"}, status=400)

        # Double-entry validation for journals
        if hasattr(obj, "lines"):
            lines = list(obj.lines.select_related("account", "cost_center").all())
            if not lines:
                return Response({"detail": "Cannot post journal without lines."}, status=400)
            debit = sum((l.debit or 0) for l in lines)
            credit = sum((l.credit or 0) for l in lines)
            if debit != credit:
                return Response(
                    {"detail": f"Unbalanced journal: debit={debit} credit={credit}"},
                    status=400,
                )
            org = self._org_of(obj)
            entry_date = getattr(obj, "entry_date", None)
            if org and entry_date:
                from finance.reporting import budget_availability_ok, refresh_budget_utilized

                ok, detail = budget_availability_ok(org, lines, entry_date)
                if not ok:
                    return Response({"detail": detail, "code": "budget_exceeded"}, status=400)

        extra = {}
        if hasattr(obj, "posted_at"):
            extra["posted_at"] = timezone.now()
        resp = self._set_status(obj, self.workflow_post_to, "post", extra)
        org = self._org_of(obj)
        entry_date = getattr(obj, "entry_date", None)
        if org and entry_date and hasattr(obj, "lines"):
            try:
                from finance.reporting import refresh_budget_utilized

                refresh_budget_utilized(org, entry_date.year)
            except Exception:
                pass
        return resp
