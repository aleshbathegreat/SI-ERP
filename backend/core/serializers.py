from rest_framework import serializers

from core.models import (
    Organization,
    PlatformStaff,
    SaaSInvoice,
    SubscriptionPackage,
    SubscriptionPayment,
    SupportTicket,
    SupportTicketMessage,
)


class SubscriptionPackageSerializer(serializers.ModelSerializer):
    effective_module_keys = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPackage
        fields = (
            "id",
            "name",
            "code",
            "price",
            "interval",
            "summary",
            "module_keys",
            "core_module_keys",
            "effective_module_keys",
            "module_count",
            "max_functional_users",
            "max_ess_users",
            "max_attendance_devices",
            "attendance_connectors",
            "active",
            "sort",
        )

    def get_effective_module_keys(self, obj):
        from accounts.rbac import effective_package_modules

        return effective_package_modules(obj)

    def get_module_count(self, obj):
        from accounts.rbac import effective_package_modules

        return len(effective_package_modules(obj))

    def validate_module_keys(self, value):
        from accounts.rbac import ASSIGNABLE_MODULE_KEYS, expand_module_keys

        if not isinstance(value, list):
            raise serializers.ValidationError("module_keys must be a list")
        # Expand aliases; drop core/shell keys into assignable-only set
        expanded = expand_module_keys(value)
        return [k for k in expanded if k in ASSIGNABLE_MODULE_KEYS]

    def validate_core_module_keys(self, value):
        from accounts.rbac import CORE_MODULE_KEYS, MODULES, expand_module_keys

        if value in (None, []):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("core_module_keys must be a list")
        expanded = expand_module_keys(value)
        bad = [k for k in expanded if k not in MODULES]
        if bad:
            raise serializers.ValidationError(f"Unknown modules: {', '.join(bad[:8])}")
        # Ensure minimum core always present
        return sorted(set(expanded) | set(CORE_MODULE_KEYS))

    def validate_attendance_connectors(self, value):
        from hr.connectors import ALL_CONNECTOR_KEYS

        if value in (None, []):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("attendance_connectors must be a list")
        if "*" in value or "all" in value:
            return ["*"]
        bad = [k for k in value if k not in ALL_CONNECTOR_KEYS]
        if bad:
            raise serializers.ValidationError(
                f"Unknown connectors: {', '.join(bad[:8])}"
            )
        return list(dict.fromkeys(value))


class OrganizationSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="package.name", read_only=True)
    subscription_open = serializers.SerializerMethodField()
    subscription_in_grace = serializers.SerializerMethodField()
    days_until_lock = serializers.SerializerMethodField()
    brand_logo_url = serializers.SerializerMethodField()
    brand_logo_dark_url = serializers.SerializerMethodField()
    brand_favicon_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "code",
            "email",
            "phone",
            "ntn",
            "strn",
            "timezone",
            "currency",
            "plan",
            "plan_status",
            "trial_ends",
            "subscription_ends",
            "grace_days",
            "package",
            "package_name",
            "subscription_open",
            "subscription_in_grace",
            "days_until_lock",
            "custom_domain",
            "custom_domain_verified",
            "brand_name",
            "brand_tagline",
            "brand_primary_color",
            "brand_secondary_color",
            "brand_logo_url",
            "brand_logo_dark_url",
            "brand_favicon_url",
        )

    def get_subscription_open(self, obj):
        from core.access import subscription_open

        return subscription_open(obj)

    def get_subscription_in_grace(self, obj):
        from core.access import subscription_in_grace

        return subscription_in_grace(obj)

    def get_days_until_lock(self, obj):
        from core.access import days_until_lock

        return days_until_lock(obj)

    def _media(self, field):
        from core.tenancy import _abs_media

        return _abs_media(field, self.context.get("request"))

    def get_brand_logo_url(self, obj):
        return self._media(obj.brand_logo)

    def get_brand_logo_dark_url(self, obj):
        return self._media(obj.brand_logo_dark) or self._media(obj.brand_logo)

    def get_brand_favicon_url(self, obj):
        return self._media(obj.brand_favicon)


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = (
            "id",
            "plan",
            "kind",
            "period_start",
            "period_end",
            "amount",
            "currency",
            "reference",
            "environment",
            "basket_id",
            "transaction_id",
            "status",
            "status_code",
            "status_message",
            "instrument_alias",
            "notes",
            "created_at",
        )


class SaaSInvoiceSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    organization_code = serializers.CharField(
        source="organization.code", read_only=True
    )
    package_name = serializers.CharField(source="package.name", read_only=True)

    class Meta:
        model = SaaSInvoice
        fields = (
            "id",
            "invoice_no",
            "organization",
            "organization_name",
            "organization_code",
            "package",
            "package_name",
            "plan_code",
            "description",
            "period_start",
            "period_end",
            "amount",
            "tax_amount",
            "total",
            "currency",
            "status",
            "issue_date",
            "due_date",
            "paid_at",
            "payment",
            "notes",
            "created_at",
        )
        read_only_fields = ("invoice_no", "total", "paid_at", "created_at")


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketMessage
        fields = (
            "id",
            "body",
            "is_internal",
            "is_from_platform",
            "author",
            "author_name",
            "created_at",
        )
        read_only_fields = ("author", "is_from_platform", "created_at")

    def get_author_name(self, obj):
        if not obj.author_id:
            return "System"
        return obj.author.get_full_name() or obj.author.username


class SupportTicketSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    organization_code = serializers.CharField(
        source="organization.code", read_only=True
    )
    assignee_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "ticket_no",
            "organization",
            "organization_name",
            "organization_code",
            "subject",
            "category",
            "priority",
            "status",
            "created_by",
            "created_by_name",
            "assignee",
            "assignee_name",
            "last_message_at",
            "created_at",
            "updated_at",
            "messages",
        )
        read_only_fields = (
            "ticket_no",
            "created_by",
            "last_message_at",
            "created_at",
            "updated_at",
        )

    def get_assignee_name(self, obj):
        if not obj.assignee_id:
            return None
        return obj.assignee.get_full_name() or obj.assignee.username

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return None
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_messages(self, obj):
        request = self.context.get("request")
        qs = obj.messages.all()
        # Hide internal notes from non-platform users
        if request and request.user:
            from core.platform_rbac import is_platform_user

            if not is_platform_user(request.user):
                qs = qs.filter(is_internal=False)
        return SupportTicketMessageSerializer(qs, many=True).data


class PlatformStaffSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PlatformStaff
        fields = (
            "id",
            "user",
            "username",
            "email",
            "full_name",
            "role",
            "is_active",
            "title",
            "notes",
            "capabilities",
            "created_at",
        )
        read_only_fields = ("user", "created_at", "username", "email", "full_name", "capabilities")

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_capabilities(self, obj):
        from core.platform_rbac import ROLE_CAPS

        return ROLE_CAPS.get(obj.role, [])
