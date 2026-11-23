from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import is_owner, user_organization
from core.bulk import BulkDeleteMixin
from core.mailbox import pull_inbox, record_outbound, split_addresses, store_inbound, usable_profiles
from core.mailer import send_platform_email, send_tenant_email
from core.models import (
    EmailTemplate,
    MailMessage,
    PlatformSmtpSettings,
    TenantEmailProfile,
    TenantSmtpSettings,
)
from core.scoping import OrgScopedQuerysetMixin


class PlatformSmtpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password_set = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSmtpSettings
        fields = (
            "host",
            "port",
            "username",
            "password",
            "password_set",
            "use_tls",
            "use_ssl",
            "from_email",
            "from_name",
            "reply_to",
            "is_active",
            "updated_at",
        )
        read_only_fields = ("updated_at", "password_set")

    def get_password_set(self, obj):
        return bool(obj.password)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.password = password
        instance.save()
        return instance


class TenantSmtpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password_set = serializers.SerializerMethodField()

    class Meta:
        model = TenantSmtpSettings
        fields = (
            "host",
            "port",
            "username",
            "password",
            "password_set",
            "use_tls",
            "use_ssl",
            "from_email",
            "from_name",
            "reply_to",
            "is_active",
            "updated_at",
        )
        read_only_fields = ("updated_at", "password_set")

    def get_password_set(self, obj):
        return bool(obj.password)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.password = password
        instance.save()
        return instance


class TenantEmailProfileSerializer(serializers.ModelSerializer):
    imap_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    imap_password_set = serializers.SerializerMethodField()
    owner_label = serializers.SerializerMethodField()

    class Meta:
        model = TenantEmailProfile
        fields = (
            "id",
            "name",
            "email",
            "purpose",
            "reply_to",
            "signature",
            "owner_type",
            "user",
            "employee",
            "owner_label",
            "inbound",
            "imap_host",
            "imap_port",
            "imap_username",
            "imap_password",
            "imap_password_set",
            "imap_use_ssl",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "owner_label", "imap_password_set")

    def get_imap_password_set(self, obj):
        return bool(obj.imap_password)

    def get_owner_label(self, obj):
        if obj.owner_type == TenantEmailProfile.OwnerType.USER and obj.user_id:
            full = obj.user.get_full_name()
            return full or obj.user.username or obj.user.email
        if obj.owner_type == TenantEmailProfile.OwnerType.EMPLOYEE and obj.employee_id:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip() or obj.employee.employee_code
        return "Shared"

    def validate(self, attrs):
        owner = attrs.get("owner_type", getattr(self.instance, "owner_type", "shared"))
        user = attrs["user"] if "user" in attrs else getattr(self.instance, "user", None)
        employee = attrs["employee"] if "employee" in attrs else getattr(self.instance, "employee", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if owner == TenantEmailProfile.OwnerType.SHARED:
            attrs["user"] = None
            attrs["employee"] = None
        elif owner == TenantEmailProfile.OwnerType.USER:
            if user is None:
                raise serializers.ValidationError({"user": "Choose the full user for this mailbox."})
            if org and user_organization(user) != org:
                raise serializers.ValidationError({"user": "That user is not in this tenant."})
            attrs["employee"] = None
        elif owner == TenantEmailProfile.OwnerType.EMPLOYEE:
            if employee is None:
                raise serializers.ValidationError({"employee": "Choose the employee for this mailbox."})
            if org and employee.organization_id != org.id:
                raise serializers.ValidationError({"employee": "That employee is not in this tenant."})
            attrs["user"] = None
        inbound = attrs.get("inbound", getattr(self.instance, "inbound", "none"))
        host = attrs.get("imap_host", getattr(self.instance, "imap_host", ""))
        if inbound == TenantEmailProfile.Inbound.IMAP and not (host or "").strip():
            raise serializers.ValidationError({"imap_host": "IMAP host is required to receive mail."})
        return attrs

    def _keep_password(self, instance, password):
        if password:
            instance.imap_password = password
            instance.save(update_fields=["imap_password", "updated_at"])
        return instance

    def create(self, validated_data):
        password = validated_data.pop("imap_password", "")
        instance = super().create(validated_data)
        return self._keep_password(instance, password)

    def update(self, instance, validated_data):
        password = validated_data.pop("imap_password", "")
        instance = super().update(instance, validated_data)
        return self._keep_password(instance, password)


class IsPlatformOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        from core.platform_rbac import has_platform_cap

        return bool(
            request.user
            and request.user.is_authenticated
            and has_platform_cap(request.user, "smtp")
        )


class PlatformSmtpView(APIView):
    """Platform owner configures system SMTP."""

    permission_classes = [IsPlatformOwner]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        cfg = PlatformSmtpSettings.load()
        return Response(PlatformSmtpSerializer(cfg).data)

    def put(self, request):
        cfg = PlatformSmtpSettings.load()
        ser = PlatformSmtpSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(PlatformSmtpSerializer(cfg).data)

    def post(self, request):
        """Send test system email."""
        to = request.data.get("email") or request.user.email
        if not to:
            return Response({"detail": "email required"}, status=400)
        ok = send_platform_email("Platform SMTP test", "Platform SMTP is working.", [to])
        return Response({"sent": ok, "to": to}, status=200 if ok else 400)


class TenantSmtpView(APIView):
    """Tenant owner/admin configures their SMTP."""

    rbac_module = "settings.email"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        cfg, _ = TenantSmtpSettings.objects.get_or_create(organization=org)
        return Response(TenantSmtpSerializer(cfg).data)

    def put(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not (is_owner(request.user) or request.user.is_superuser):
            # Still allow if RBAC grants settings.email change (HasModulePermission already ran)
            pass
        cfg, _ = TenantSmtpSettings.objects.get_or_create(organization=org)
        ser = TenantSmtpSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(TenantSmtpSerializer(cfg).data)

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        to = request.data.get("email") or request.user.email
        purpose = request.data.get("purpose", "general")
        if not to:
            return Response({"detail": "email required"}, status=400)
        ok = send_tenant_email(
            org,
            "Tenant SMTP test",
            f"Tenant SMTP test for {org.name}.",
            [to],
            purpose=purpose,
        )
        return Response({"sent": ok, "to": to}, status=200 if ok else 400)


class TenantEmailProfileViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TenantEmailProfile.objects.select_related("user", "employee")
    serializer_class = TenantEmailProfileSerializer
    rbac_module = "settings.email"
    search_fields = ("name", "email", "purpose", "owner_type")
    filterset_fields = ("purpose", "is_active", "is_default", "owner_type", "inbound")

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        serializer.save(organization=org, created_by=self.request.user)


class MailMessageSerializer(serializers.ModelSerializer):
    profile_name = serializers.CharField(source="profile.name", read_only=True)
    profile_email = serializers.CharField(source="profile.email", read_only=True)

    class Meta:
        model = MailMessage
        fields = (
            "id",
            "profile",
            "profile_name",
            "profile_email",
            "direction",
            "status",
            "subject",
            "body",
            "from_email",
            "to_emails",
            "error",
            "lead",
            "opportunity",
            "occurred_at",
            "created_at",
        )


class MailMessageViewSet(OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MailMessage.objects.select_related("profile")
    serializer_class = MailMessageSerializer
    rbac_module = "settings.email"
    filterset_fields = ("profile", "direction", "status", "lead", "opportunity")
    search_fields = ("subject", "from_email", "to_emails", "body")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(profile__in=usable_profiles(self.request.user))

    @action(detail=False, methods=["get"])
    def profiles(self, request):
        rows = usable_profiles(request.user)
        return Response(TenantEmailProfileSerializer(rows, many=True).data)

    @action(detail=False, methods=["post"])
    def send(self, request):
        org = user_organization(request.user)
        profile = usable_profiles(request.user).filter(pk=request.data.get("profile")).first()
        if not profile:
            return Response({"detail": "Choose a mailbox you can send from."}, status=400)
        subject = (request.data.get("subject") or "").strip()
        if not subject:
            return Response({"detail": "Subject is required."}, status=400)
        recipients = split_addresses(request.data.get("to") or "")
        if not recipients or any("@" not in item for item in recipients):
            return Response({"detail": "Enter at least one email address."}, status=400)
        lead = None
        opportunity = None
        if request.data.get("lead"):
            from crm.models import Lead

            lead = Lead.objects.filter(organization=org, pk=request.data.get("lead")).first()
            if not lead:
                return Response({"detail": "Lead not found."}, status=400)
        if request.data.get("opportunity"):
            from crm.models import Opportunity

            opportunity = Opportunity.objects.filter(
                organization=org, pk=request.data.get("opportunity")
            ).first()
            if not opportunity:
                return Response({"detail": "Opportunity not found."}, status=400)
        message = record_outbound(
            profile,
            request.user,
            subject[:255],
            request.data.get("body") or "",
            recipients,
            lead=lead,
            opportunity=opportunity,
        )
        return Response(MailMessageSerializer(message).data, status=201)

    @action(detail=False, methods=["post"])
    def fetch(self, request):
        profile = usable_profiles(request.user).filter(pk=request.data.get("profile")).first()
        if not profile:
            return Response({"detail": "Choose a mailbox you can read."}, status=400)
        try:
            rows = pull_inbox(profile)
            imported, skipped = store_inbound(profile, rows, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001
            logger_detail = str(exc)[:400]
            return Response({"detail": logger_detail or "Inbox check failed."}, status=400)
        return Response({"imported": imported, "skipped": skipped})


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = (
            "id",
            "code",
            "name",
            "purpose",
            "subject",
            "body_text",
            "body_html",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class EmailTemplateViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    rbac_module = "settings.email"
    search_fields = ("code", "name", "subject", "purpose")
    filterset_fields = ("purpose", "is_active")

    def get_queryset(self):
        org = user_organization(self.request.user)
        if org is not None:
            from core.email_defaults import ensure_default_email_templates

            ensure_default_email_templates(org)
        return super().get_queryset()

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        serializer.save(organization=org, created_by=self.request.user)
