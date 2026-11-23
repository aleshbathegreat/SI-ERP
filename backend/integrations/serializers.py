from rest_framework import serializers

from integrations.catalog import catalog_by_key
from integrations.models import IntegrationConnection


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    connector_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    recommended = serializers.SerializerMethodField()
    secrets_set = serializers.SerializerMethodField()
    # write-only secrets merge
    secrets_input = serializers.DictField(required=False, write_only=True)

    class Meta:
        model = IntegrationConnection
        fields = (
            "id",
            "connector_key",
            "connector_name",
            "category",
            "recommended",
            "display_name",
            "status",
            "is_enabled",
            "config",
            "secrets_input",
            "secrets_set",
            "last_tested_at",
            "last_test_ok",
            "last_test_message",
            "last_error",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "status",
            "last_tested_at",
            "last_test_ok",
            "last_test_message",
            "last_error",
            "created_at",
            "updated_at",
            "secrets_set",
            "connector_name",
            "category",
            "recommended",
        )

    def get_connector_name(self, obj):
        meta = catalog_by_key(obj.connector_key)
        return (meta or {}).get("name") or obj.display_name or obj.connector_key

    def get_category(self, obj):
        meta = catalog_by_key(obj.connector_key)
        return (meta or {}).get("category")

    def get_recommended(self, obj):
        meta = catalog_by_key(obj.connector_key)
        return bool((meta or {}).get("recommended"))

    def get_secrets_set(self, obj):
        return obj.secrets_set_keys

    def validate_connector_key(self, value):
        if not catalog_by_key(value):
            raise serializers.ValidationError("Unknown connector_key")
        return value

    def create(self, validated):
        secrets_input = validated.pop("secrets_input", None) or {}
        meta = catalog_by_key(validated["connector_key"])
        if meta and not validated.get("display_name"):
            validated["display_name"] = meta["name"]
        obj = IntegrationConnection(**validated)
        if secrets_input:
            obj.secrets = {**(obj.secrets or {}), **{k: v for k, v in secrets_input.items() if v}}
        obj.save()
        return obj

    def update(self, instance, validated):
        secrets_input = validated.pop("secrets_input", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if secrets_input:
            merged = dict(instance.secrets or {})
            for k, v in secrets_input.items():
                if v == "" or v is None:
                    continue
                merged[k] = v
            instance.secrets = merged
        instance.save()
        return instance
