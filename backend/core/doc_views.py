"""Next document number helper for UI prefill."""

from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import user_organization
from core.doc_numbers import KIND_PREFIX, next_doc_no


class NextDocNoView(APIView):
    """GET /api/docs/next-number/?kind=po → { number: 'PO-2026-00001' }"""

    rbac_exempt = True

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        kind = (request.query_params.get("kind") or "doc").lower().strip()
        if kind not in KIND_PREFIX:
            return Response(
                {"detail": f"Unknown kind. Use one of: {', '.join(sorted(KIND_PREFIX))}"},
                status=400,
            )
        model = None
        field = ""
        if kind == "invoice":
            from finance.models import VendorInvoice

            model, field = VendorInvoice, "invoice_no"
        elif kind == "po":
            from ops.models import PurchaseOrder

            model, field = PurchaseOrder, "po_no"
        elif kind == "so":
            from ops.models import SalesOrder

            model, field = SalesOrder, "order_no"
        elif kind == "loan":
            from payroll.models import EmployeeLoan

            model, field = EmployeeLoan, "loan_number"
        elif kind == "challan":
            from finance.models import TaxChallan

            model, field = TaxChallan, "challan_no"
        elif kind == "asset":
            from finance.models import FixedAsset

            model, field = FixedAsset, "asset_code"
        elif kind == "customer":
            from ops.models import Customer

            model, field = Customer, "code"
        elif kind == "item":
            from ops.models import Item

            model, field = Item, "sku"
        number = next_doc_no(org, kind=kind, model=model, field=field)
        return Response({"kind": kind, "number": number})
