from rest_framework import serializers

from core.access import user_organization
from core.doc_numbers import ensure_doc_no
from service.models import ServiceCase, ServiceNote, ServicePart

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


class ServicePartSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    warehouse_code = serializers.CharField(
        source="warehouse.code", read_only=True, default=""
    )
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = ServicePart
        fields = (
            "id",
            "item",
            "item_sku",
            "item_name",
            "warehouse",
            "warehouse_code",
            "qty",
            "unit_cost",
            "unit_price",
            "line_total",
        )

    def get_line_total(self, obj):
        total = (obj.qty or 0) * (obj.unit_price or 0)
        return str(total)


class ServiceCaseSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=""
    )
    sales_order_no = serializers.CharField(
        source="sales_order.order_no", read_only=True, default=""
    )
    assigned_to_name = serializers.SerializerMethodField()
    note_count = serializers.SerializerMethodField()
    invoice_no = serializers.CharField(
        source="customer_invoice.invoice_no", read_only=True, default=""
    )
    parts = ServicePartSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCase
        fields = "__all__"
        read_only_fields = RO + ("opened_at", "resolved_at", "status", "customer_invoice")
        extra_kwargs = {"case_no": {"required": False, "allow_blank": True}}

    def get_assigned_to_name(self, obj):
        return _user_label(obj.assigned_to)

    def get_note_count(self, obj):
        return obj.notes.filter(is_deleted=False).count()

    def validate(self, attrs):
        org = _request_org(self)
        if org:
            customer = attrs.get("customer")
            if customer and customer.organization_id != org.id:
                raise serializers.ValidationError({"customer": "Invalid customer."})
            so = attrs.get("sales_order")
            if so and so.organization_id != org.id:
                raise serializers.ValidationError(
                    {"sales_order": "Invalid sales order."}
                )
            assignee = attrs.get("assigned_to")
            if assignee and user_organization(assignee) != org:
                raise serializers.ValidationError({"assigned_to": "Invalid user."})
        return attrs

    def create(self, validated_data):
        org = validated_data.get("organization") or _request_org(self)
        if org:
            ensure_doc_no(
                validated_data, "case_no", org, kind="case", model=ServiceCase
            )
        return super().create(validated_data)


class ServiceNoteSerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source="case.case_no", read_only=True, default="")
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceNote
        fields = "__all__"
        read_only_fields = RO

    def get_author_name(self, obj):
        return _user_label(obj.created_by)

    def validate_case(self, value):
        org = _request_org(self)
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Invalid case.")
        return value
