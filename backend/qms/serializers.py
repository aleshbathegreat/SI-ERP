from rest_framework import serializers

from core.access import user_organization
from core.doc_numbers import ensure_doc_no
from qms.models import Capa, Ncr, QualityInspection

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


def _user_label(u):
    if not u:
        return ""
    return (u.get_full_name() or u.username or str(u.pk)).strip()


def _request_org(serializer):
    request = serializer.context.get("request")
    return user_organization(request.user) if request else None


def _check_same_org(org, attrs, names):
    if not org:
        return
    for name in names:
        obj = attrs.get(name)
        if obj is None:
            continue
        if isinstance(obj, tuple):
            continue
        obj_org = getattr(obj, "organization_id", None)
        if obj_org is not None and obj_org != org.id:
            raise serializers.ValidationError({name: f"Invalid {name}."})


class QualityInspectionSerializer(serializers.ModelSerializer):
    grn_no = serializers.CharField(source="grn.grn_no", read_only=True, default="")
    item_sku = serializers.CharField(source="item.sku", read_only=True, default="")
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=""
    )
    inspector_name = serializers.SerializerMethodField()

    class Meta:
        model = QualityInspection
        fields = "__all__"
        read_only_fields = RO + ("qty_released",)
        extra_kwargs = {"inspection_no": {"required": False, "allow_blank": True}}

    def get_inspector_name(self, obj):
        return _user_label(obj.inspector)

    def validate(self, attrs):
        org = _request_org(self)
        _check_same_org(org, attrs, ("grn", "item", "warehouse"))
        inspector = attrs.get("inspector")
        if org and inspector and user_organization(inspector) != org:
            raise serializers.ValidationError({"inspector": "Invalid user."})
        inst = self.instance
        inspected = attrs.get("qty_inspected", inst.qty_inspected if inst else 0)
        rejected = attrs.get("qty_rejected", inst.qty_rejected if inst else 0)
        if inspected is not None and inspected < 0:
            raise serializers.ValidationError(
                {"qty_inspected": "Quantity cannot be negative."}
            )
        if rejected is not None and rejected < 0:
            raise serializers.ValidationError(
                {"qty_rejected": "Quantity cannot be negative."}
            )
        if rejected is not None and inspected is not None and rejected > inspected:
            raise serializers.ValidationError(
                {"qty_rejected": "Rejected quantity cannot exceed inspected quantity."}
            )
        grn = attrs.get("grn")
        if grn is not None and attrs.get("warehouse") is None and not (
            inst and inst.warehouse_id
        ):
            attrs["warehouse"] = grn.warehouse
        return attrs

    def create(self, validated_data):
        org = validated_data.get("organization") or _request_org(self)
        if org:
            ensure_doc_no(
                validated_data,
                "inspection_no",
                org,
                kind="qi",
                model=QualityInspection,
            )
        request = self.context.get("request")
        if request and not validated_data.get("inspector"):
            validated_data["inspector"] = request.user
        obj = super().create(validated_data)
        from ops.qc_hold import sync_inspection

        return sync_inspection(obj)

    def update(self, instance, validated_data):
        obj = super().update(instance, validated_data)
        from ops.qc_hold import sync_inspection

        return sync_inspection(obj)


class NcrSerializer(serializers.ModelSerializer):
    source_inspection_no = serializers.CharField(
        source="source_inspection.inspection_no", read_only=True, default=""
    )
    capa_count = serializers.SerializerMethodField()
    open_capa_count = serializers.SerializerMethodField()

    class Meta:
        model = Ncr
        fields = "__all__"
        read_only_fields = RO + ("closed_at",)
        extra_kwargs = {"ncr_no": {"required": False, "allow_blank": True}}

    def get_capa_count(self, obj):
        return obj.capas.filter(is_deleted=False).count()

    def get_open_capa_count(self, obj):
        return obj.capas.filter(is_deleted=False, status=Capa.Status.OPEN).count()

    def validate_status(self, value):
        current = self.instance.status if self.instance else None
        if value == Ncr.Status.CLOSED and current != Ncr.Status.CLOSED:
            raise serializers.ValidationError("Use the Close action to close an NCR.")
        if current == Ncr.Status.CLOSED and value != Ncr.Status.CLOSED:
            raise serializers.ValidationError("Closed NCRs cannot be reopened.")
        return value

    def validate(self, attrs):
        _check_same_org(_request_org(self), attrs, ("source_inspection",))
        if self.instance is not None and self.instance.status == Ncr.Status.CLOSED:
            raise serializers.ValidationError({"detail": "Closed NCRs cannot be edited."})
        return attrs

    def create(self, validated_data):
        org = validated_data.get("organization") or _request_org(self)
        if org:
            ensure_doc_no(validated_data, "ncr_no", org, kind="ncr", model=Ncr)
        return super().create(validated_data)


class CapaSerializer(serializers.ModelSerializer):
    ncr_no = serializers.CharField(source="ncr.ncr_no", read_only=True, default="")
    ncr_title = serializers.CharField(source="ncr.title", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Capa
        fields = "__all__"
        read_only_fields = RO + ("status", "completed_at")

    def get_owner_name(self, obj):
        return _user_label(obj.owner)

    def validate(self, attrs):
        org = _request_org(self)
        _check_same_org(org, attrs, ("ncr",))
        owner = attrs.get("owner")
        if org and owner and user_organization(owner) != org:
            raise serializers.ValidationError({"owner": "Invalid user."})
        ncr = attrs.get("ncr") or (self.instance.ncr if self.instance else None)
        if ncr is not None and ncr.status == Ncr.Status.CLOSED and self.instance is None:
            raise serializers.ValidationError(
                {"ncr": "Cannot add a CAPA to a closed NCR."}
            )
        return attrs
