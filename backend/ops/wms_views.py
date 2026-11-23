from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from ops.models import (
    DeliveryNote,
    PickList,
    SalesOrder,
    Warehouse,
    WarehouseBin,
)
from ops.wms import (
    PickListSerializer,
    WarehouseBinSerializer,
    confirm_pick,
    create_pick_list,
    put_away,
)


class WarehouseBinViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WarehouseBin.objects.select_related("warehouse")
    serializer_class = WarehouseBinSerializer
    search_fields = ("code", "name", "aisle", "rack", "level", "warehouse__code")
    filterset_fields = ("warehouse", "active")
    rbac_module = "inventory.bins"

    @action(detail=True, methods=["post"], url_path="put-away")
    def put_away(self, request, pk=None):
        b = self.get_object()
        org = user_organization(request.user)
        put_away(
            org=org,
            bin_obj=b,
            item_id=request.data.get("item"),
            qty=request.data.get("qty") or 0,
            user=request.user,
        )
        return Response(self.get_serializer(b).data)


class PickListViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PickList.objects.select_related(
        "warehouse", "sales_order", "delivery_note"
    ).prefetch_related("lines__item", "lines__bin")
    serializer_class = PickListSerializer
    search_fields = ("pick_no", "sales_order__order_no", "delivery_note__dn_no", "notes")
    filterset_fields = ("status", "warehouse", "sales_order", "delivery_note")
    rbac_module = "inventory.pick_lists"

    def perform_destroy(self, instance):
        if instance.status == PickList.Status.DONE:
            raise ValidationError("Completed pick lists cannot be deleted.")
        return super().perform_destroy(instance)

    @action(detail=False, methods=["post"], url_path="create-from-order")
    def create_from_order(self, request):
        org = user_organization(request.user)
        so = dn = wh = None
        if request.data.get("sales_order"):
            so = SalesOrder.objects.filter(
                pk=request.data["sales_order"], organization=org
            ).first()
            if not so:
                raise ValidationError({"sales_order": "Not found."})
        if request.data.get("delivery_note"):
            dn = DeliveryNote.objects.filter(
                pk=request.data["delivery_note"], organization=org
            ).first()
            if not dn:
                raise ValidationError({"delivery_note": "Not found."})
        if request.data.get("warehouse"):
            wh = Warehouse.objects.filter(
                pk=request.data["warehouse"], organization=org, is_deleted=False
            ).first()
            if not wh:
                raise ValidationError({"warehouse": "Invalid warehouse."})
        pl = create_pick_list(
            org=org,
            user=request.user,
            sales_order=so,
            delivery_note=dn,
            warehouse=wh,
            notes=request.data.get("notes") or "",
        )
        data = self.get_serializer(pl).data
        data["href"] = f"/inventory/pick-lists/{pl.id}"
        return Response(data, status=201)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        pl = self.get_object()
        if pl.status != PickList.Status.DRAFT:
            raise ValidationError("Only draft pick lists can be started.")
        pl.status = PickList.Status.PICKING
        pl.updated_by = request.user
        pl.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(self.get_serializer(pl).data)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        pl = self.get_object()
        deduct = request.data.get("deduct_bin", True)
        if isinstance(deduct, str):
            deduct = deduct.lower() not in ("0", "false", "no")
        confirm_pick(
            pl,
            user=request.user,
            lines=request.data.get("lines"),
            deduct_bin=bool(deduct),
        )
        pl.refresh_from_db()
        return Response(self.get_serializer(pl).data)
