from rest_framework import serializers

from contracts.models import Contract
from core.doc_numbers import ensure_doc_no

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


class ContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=""
    )
    vendor_name = serializers.CharField(
        source="vendor.name", read_only=True, default=""
    )

    class Meta:
        model = Contract
        fields = "__all__"
        read_only_fields = RO

    def create(self, validated_data):
        from core.access import user_organization

        request = self.context.get("request")
        org = validated_data.get("organization") or (
            user_organization(request.user) if request else None
        )
        if org:
            ensure_doc_no(
                validated_data, "contract_no", org, kind="contract", model=Contract
            )
        return super().create(validated_data)
