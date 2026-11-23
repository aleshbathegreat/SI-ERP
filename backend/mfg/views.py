from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as SerValidationError

from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from mfg.models import Bom, BomLine, WorkOrder
from mfg.serializers import (
    BomLineSerializer,
    BomSerializer,
    WorkOrderSerializer,
    complete_work_order,
    release_work_order,
)


class BomViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Bom.objects.select_related("item").prefetch_related("lines__component")
    serializer_class = BomSerializer
    search_fields = ("code", "name", "item__sku", "item__name")
    filterset_fields = ("is_active", "item")
    rbac_module = "mfg.bom"


class BomLineViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BomLine.objects.select_related("bom", "component", "bom__organization")
    serializer_class = BomLineSerializer
    filterset_fields = ("bom", "component")
    rbac_module = "mfg.bom"
    org_field = "bom__organization"

    def perform_create(self, serializer):
        serializer.save()


class WorkOrderViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related("item", "bom", "warehouse")
    serializer_class = WorkOrderSerializer
    search_fields = ("wo_no", "notes", "item__sku", "item__name", "bom__code")
    filterset_fields = ("status", "item", "bom", "warehouse")
    rbac_module = "mfg.work_orders"

    def perform_destroy(self, instance):
        if instance.status not in (WorkOrder.Status.DRAFT, WorkOrder.Status.CANCELLED):
            raise SerValidationError("Only draft/cancelled work orders can be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, pk=None):
        wo = self.get_object()
        try:
            release_work_order(wo, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        wo.refresh_from_db()
        return Response(self.get_serializer(wo).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        wo = self.get_object()
        data = request.data or {}
        qty = data.get("qty")
        try:
            complete_work_order(
                wo,
                qty=qty,
                user=request.user,
                batch_no=data.get("batch_no"),
                serial_nos=data.get("serial_nos") or data.get("serial_no"),
                expiry_date=data.get("expiry_date"),
                lot=data.get("lot"),
            )
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        wo.refresh_from_db()
        return Response(self.get_serializer(wo).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        wo = self.get_object()
        if wo.status == WorkOrder.Status.DONE:
            return Response({"detail": "Cannot cancel a completed work order."}, status=400)
        wo.status = WorkOrder.Status.CANCELLED
        wo.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(wo).data)
