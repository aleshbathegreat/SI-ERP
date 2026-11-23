from django.utils import timezone
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.bulk import BulkDeleteMixin
from core.doc_numbers import ensure_doc_no
from core.scoping import OrgScopedQuerysetMixin
from qms.models import Capa, Ncr, QualityInspection
from qms.serializers import CapaSerializer, NcrSerializer, QualityInspectionSerializer


class QualityInspectionViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = QualityInspection.objects.select_related(
        "grn", "item", "warehouse", "inspector"
    )
    serializer_class = QualityInspectionSerializer
    search_fields = ("inspection_no", "notes", "item__sku", "item__name", "grn__grn_no")
    filterset_fields = ("result", "grn", "item", "warehouse", "inspector")
    rbac_module = "qms.inspections"

    @action(detail=True, methods=["post"], url_path="create-ncr")
    def create_ncr(self, request, pk=None):
        """Raise an NCR from a failed / conditional inspection (idempotent)."""
        from accounts.rbac import can
        from rest_framework.exceptions import PermissionDenied

        if not can(request.user, "qms.ncrs", "add"):
            raise PermissionDenied("Missing permission: qms.ncrs:add")
        insp = self.get_object()
        if insp.result == QualityInspection.Result.PASS:
            raise ValidationError("Only failed or conditional inspections can raise an NCR.")
        existing = (
            Ncr.objects.filter(organization=insp.organization, source_inspection=insp)
            .exclude(status=Ncr.Status.CLOSED)
            .first()
        )
        if existing:
            return Response(
                {"ncr": existing.id, "ncr_no": existing.ncr_no, "created": False}
            )
        data = {}
        ensure_doc_no(data, "ncr_no", insp.organization, kind="ncr", model=Ncr)
        ncr = Ncr.objects.create(
            organization=insp.organization,
            ncr_no=data["ncr_no"],
            title=f"Nonconformance · {insp.item.sku} ({insp.inspection_no})",
            source_inspection=insp,
            severity=(
                Ncr.Severity.HIGH
                if insp.result == QualityInspection.Result.FAIL
                else Ncr.Severity.MEDIUM
            ),
            description=insp.notes or "",
            created_by=request.user,
        )
        return Response(
            {"ncr": ncr.id, "ncr_no": ncr.ncr_no, "created": True},
            status=http_status.HTTP_201_CREATED,
        )


class NcrViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Ncr.objects.select_related("source_inspection")
    serializer_class = NcrSerializer
    search_fields = ("ncr_no", "title", "description")
    filterset_fields = ("status", "severity", "disposition", "source_inspection")
    rbac_module = "qms.ncrs"

    @property
    def rbac_action(self):
        if getattr(self, "action", None) == "close":
            return "change"
        return None

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        ncr = self.get_object()
        if ncr.status == Ncr.Status.CLOSED:
            raise ValidationError("NCR is already closed.")
        disposition = request.data.get("disposition") or ncr.disposition
        if disposition not in Ncr.Disposition.values:
            raise ValidationError(
                {"disposition": "Set a disposition (rework, scrap, use_as_is, return_vendor) before closing."}
            )
        if ncr.capas.filter(is_deleted=False, status=Capa.Status.OPEN).exists():
            raise ValidationError("Complete all open CAPAs before closing this NCR.")
        ncr.disposition = disposition
        ncr.status = Ncr.Status.CLOSED
        ncr.closed_at = timezone.now()
        ncr.updated_by = request.user
        ncr.save(
            update_fields=["disposition", "status", "closed_at", "updated_by", "updated_at"]
        )
        from ops.qc_hold import apply_ncr_disposition

        apply_ncr_disposition(ncr, user=request.user)
        return Response(self.get_serializer(ncr).data)


class CapaViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Capa.objects.select_related("ncr", "owner")
    serializer_class = CapaSerializer
    search_fields = ("action", "ncr__ncr_no", "ncr__title")
    filterset_fields = ("status", "ncr", "owner")
    rbac_module = "qms.capas"

    @property
    def rbac_action(self):
        if getattr(self, "action", None) == "complete":
            return "change"
        return None

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        capa = self.get_object()
        if capa.status == Capa.Status.DONE:
            raise ValidationError("CAPA is already complete.")
        capa.status = Capa.Status.DONE
        capa.completed_at = timezone.now()
        capa.updated_by = request.user
        capa.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
        return Response(self.get_serializer(capa).data)
