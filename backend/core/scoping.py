"""Tenant queryset scoping for ERP viewsets."""

import logging

from django.db import models as dj_models

from core.access import user_organization

logger = logging.getLogger(__name__)

# Codes the product looks up by the value the user chose. Never invent one.
SKIP_CODE_AUTOFILL = {"EmailTemplate", "Role", "Currency", "UnitOfMeasure"}

CODE_KIND = {
    "Account": "gl",
    "AccountType": "at",
    "CostCenter": "cc",
    "Department": "dep",
    "Designation": "des",
    "Shift": "sh",
    "LeaveType": "lt",
    "BenefitPlan": "ben",
    "TrainingCourse": "trn",
    "DocumentTypeDefinition": "doc",
    "SalaryStructure": "ss",
    "TaxCode": "tax",
    "Project": "prj",
    "IntercompanyPartner": "ic",
    "Bom": "bom",
    "WarehouseBin": "bin",
    "Customer": "customer",
    "Vendor": "vendor",
    "Warehouse": "warehouse",
    "PriceList": "pl",
}


class OrgScopedQuerysetMixin:
    org_field = "organization"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if getattr(self, "action", None) == "create" and request.method == "POST":
            self._assign_blank_code(request)

    def _assign_blank_code(self, request):
        """Give a blank master `code` the next number so create forms can omit it."""
        try:
            model = self.get_queryset().model
        except Exception:
            model = getattr(getattr(self, "queryset", None), "model", None)
        if model is None or model.__name__ in SKIP_CODE_AUTOFILL:
            return
        try:
            field = model._meta.get_field("code")
        except Exception:
            return
        if not isinstance(field, dj_models.CharField):
            return
        data = request.data
        if not isinstance(data, dict):
            return
        current = data.get("code")
        if current is not None and str(current).strip():
            return
        org = user_organization(request.user)
        if org is None:
            return
        from core.doc_numbers import next_doc_no

        kind = CODE_KIND.get(model.__name__, model.__name__.lower()[:8])
        filled = data.copy()
        filled["code"] = next_doc_no(org, kind=kind, model=model, field="code")
        request._full_data = filled

    def get_queryset(self):
        qs = super().get_queryset()
        org = user_organization(self.request.user)
        if org is None:
            return qs.none()
        return qs.filter(**{self.org_field: org})

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        obj = serializer.save(organization=org, created_by=self.request.user)
        module = getattr(self, "rbac_module", "") or ""
        if module and module != "dms.documents":
            try:
                from dms.workflow_engine import on_record_event

                on_record_event(org, module, obj.pk, self.request.user, "record.created")
            except Exception:
                logger.exception("workflow launch failed for %s #%s", module, getattr(obj, "pk", ""))
        return obj
