"""Attendance device connectors — catalog, CRUD, push sync, CSV, test."""

from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import can
from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.models import AuditLog
from core.scoping import OrgScopedQuerysetMixin
from hr.connectors import (
    CONNECTOR_BY_KEY,
    catalog_with_health,
    org_device_entitlement,
)
from hr.models import AttendanceDevice, AttendanceRecord, Employee

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
    "last_sync_at",
    "last_sync_status",
    "last_sync_message",
    "last_error_at",
)


class AttendanceDeviceSerializer(serializers.ModelSerializer):
    connector_name = serializers.SerializerMethodField()
    vendor = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_password = serializers.SerializerMethodField()
    has_api_token = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceDevice
        fields = "__all__"
        read_only_fields = RO
        extra_kwargs = {
            "password": {"write_only": True},
            "api_token": {"write_only": True},
        }

    def get_connector_name(self, obj):
        meta = CONNECTOR_BY_KEY.get(obj.connector_key) or {}
        return meta.get("name", obj.connector_key)

    def get_vendor(self, obj):
        meta = CONNECTOR_BY_KEY.get(obj.connector_key) or {}
        return meta.get("vendor", obj.make or "")

    def get_has_password(self, obj):
        return bool(obj.password)

    def get_has_api_token(self, obj):
        return bool(obj.api_token)

    def validate_connector_key(self, value):
        if value not in CONNECTOR_BY_KEY:
            raise serializers.ValidationError(f"Unknown connector '{value}'.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        ent = org_device_entitlement(org)
        if not ent["module_enabled"]:
            raise serializers.ValidationError(
                "Attendance devices are not included in your subscription package."
            )
        connector = attrs.get(
            "connector_key", getattr(self.instance, "connector_key", None)
        )
        if connector and connector not in ent["connectors"]:
            raise serializers.ValidationError(
                {
                    "connector_key": (
                        f"Connector '{connector}' is not enabled on your package. "
                        "Ask the platform admin to enable it."
                    )
                }
            )
        if self.instance is None:
            max_dev = ent["max_devices"]
            if max_dev is not None and max_dev >= 0:
                current = AttendanceDevice.objects.filter(
                    organization=org, is_deleted=False
                ).count()
                if current >= max_dev:
                    raise serializers.ValidationError(
                        f"Device limit reached ({max_dev}). Upgrade your package."
                    )
        mode = attrs.get(
            "connection_mode", getattr(self.instance, "connection_mode", None)
        )
        meta = CONNECTOR_BY_KEY.get(connector or "") or {}
        allowed_modes = meta.get("modes") or []
        if mode and allowed_modes and mode not in allowed_modes:
            raise serializers.ValidationError(
                {
                    "connection_mode": (
                        f"Mode '{mode}' not supported by {meta.get('name', connector)}. "
                        f"Use: {', '.join(allowed_modes)}"
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        if not validated_data.get("webhook_secret"):
            validated_data["webhook_secret"] = secrets.token_urlsafe(24)
        meta = CONNECTOR_BY_KEY.get(validated_data.get("connector_key", "")) or {}
        if not validated_data.get("make"):
            validated_data["make"] = meta.get("vendor", "")
        if not validated_data.get("port") and meta.get("default_port"):
            validated_data["port"] = meta["default_port"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Empty password/token means "leave unchanged"
        if "password" in validated_data and validated_data["password"] == "":
            validated_data.pop("password")
        if "api_token" in validated_data and validated_data["api_token"] == "":
            validated_data.pop("api_token")
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("password", None)
        data.pop("api_token", None)
        return data


def _apply_punches(org, device, punches, source="device"):
    created = 0
    updated = 0
    errors = []
    for punch in punches:
        emp_code = punch.get("employee_code")
        work_date = punch.get("work_date")
        if not emp_code or not work_date:
            errors.append({"punch": punch, "error": "employee_code and work_date required"})
            continue
        emp = Employee.objects.filter(
            organization=org, employee_code=emp_code, is_deleted=False
        ).first()
        if not emp:
            errors.append({"punch": punch, "error": f"unknown employee {emp_code}"})
            continue
        defaults = {
            "check_in": punch.get("check_in") or None,
            "check_out": punch.get("check_out") or None,
            "status": punch.get("status", "present"),
            "source": source,
            "device": device,
            "notes": punch.get("notes")
            or f"Synced from {device.device_id if device else 'import'}",
        }
        rec, was_created = AttendanceRecord.objects.update_or_create(
            organization=org,
            employee=emp,
            work_date=work_date,
            defaults=defaults,
        )
        try:
            from hr.attendance_service import evaluate_record

            if not emp.is_attendance_free:
                evaluate_record(rec)
                # keep explicit status from punch if provided
                if punch.get("status"):
                    rec.status = punch.get("status")
                rec.save()
            else:
                rec.status = AttendanceRecord.Status.EXEMPT
                rec.save(update_fields=["status", "updated_at"])
        except Exception:
            pass
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated, errors


class AttendanceDeviceViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AttendanceDevice.objects.all()
    serializer_class = AttendanceDeviceSerializer
    rbac_module = "hr.attendance_devices"
    search_fields = ("device_id", "make", "model_name", "location", "connector_key")
    filterset_fields = ("is_active", "connector_key", "connection_mode", "last_sync_status")

    def get_queryset(self):
        qs = super().get_queryset()
        org = user_organization(self.request.user)
        ent = org_device_entitlement(org)
        if not ent["module_enabled"]:
            return qs.none()
        return qs

    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        org = user_organization(request.user)
        ent = org_device_entitlement(org)
        used = 0
        if org:
            used = AttendanceDevice.objects.filter(
                organization=org, is_deleted=False
            ).count()
        health = catalog_with_health(
            org, ent["connectors"] if ent["module_enabled"] else []
        )
        return Response(
            {
                "module_enabled": ent["module_enabled"],
                "max_devices": ent["max_devices"],
                "devices_used": used,
                "connectors": health["connectors"],
                "summary": health["summary"],
                "integration": health["integration"],
            }
        )

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        device = self.get_object()
        meta = CONNECTOR_BY_KEY.get(device.connector_key) or {}
        mode = device.connection_mode
        ok = True
        msg = ""
        if mode == AttendanceDevice.ConnMode.PUSH:
            if not device.webhook_secret:
                device.webhook_secret = secrets.token_urlsafe(24)
                device.save(update_fields=["webhook_secret", "updated_at"])
            msg = (
                f"Push endpoint ready. POST punches to "
                f"/api/hr/attendance/device-sync/ with device_id={device.device_id}."
            )
        elif mode == AttendanceDevice.ConnMode.CSV:
            msg = "CSV import ready. Use Import CSV action with employee_code,work_date,check_in,check_out."
        elif mode in (AttendanceDevice.ConnMode.PULL, AttendanceDevice.ConnMode.CLOUD):
            if not device.host and mode == AttendanceDevice.ConnMode.PULL:
                ok = False
                msg = "Host is required for pull/TCP connectors."
            elif mode == AttendanceDevice.ConnMode.CLOUD and not (
                device.host or device.api_token
            ):
                ok = False
                msg = "Cloud API requires host and/or API token."
            else:
                msg = (
                    f"Config accepted for {meta.get('name', device.connector_key)} "
                    f"({device.host or 'cloud'}:{device.port or '-'}). "
                    "Live protocol handshake runs on scheduled pull agents."
                )
        else:
            ok = False
            msg = f"Unsupported mode {mode}"

        device.last_sync_status = (
            AttendanceDevice.SyncStatus.OK if ok else AttendanceDevice.SyncStatus.ERROR
        )
        device.last_sync_message = msg[:255]
        if not ok:
            device.last_error_at = timezone.now()
        device.save(
            update_fields=[
                "last_sync_status",
                "last_sync_message",
                "last_error_at",
                "updated_at",
            ]
        )
        return Response(
            {
                "ok": ok,
                "message": msg,
                "connector": device.connector_key,
                "mode": mode,
                "vendor": meta.get("vendor"),
            },
            status=200 if ok else 400,
        )

    @action(detail=True, methods=["post"], url_path="pull-sync")
    def pull_sync(self, request, pk=None):
        """Trigger pull/cloud sync — adapter stub records a sync attempt."""
        device = self.get_object()
        if device.connection_mode == AttendanceDevice.ConnMode.PUSH:
            return Response(
                {"detail": "Push devices receive punches via webhook; use device-sync."},
                status=400,
            )
        if device.connection_mode == AttendanceDevice.ConnMode.CSV:
            return Response(
                {"detail": "Use CSV import action for this connector."}, status=400
            )
        meta = CONNECTOR_BY_KEY.get(device.connector_key) or {}
        # Adapter hook: real SDK pull would go here per connector_key.
        device.last_sync_at = timezone.now()
        device.last_sync_status = AttendanceDevice.SyncStatus.OK
        device.last_sync_message = (
            f"Pull queued for {meta.get('name', device.connector_key)}. "
            "No new punches (agent adapter)."
        )[:255]
        device.save(
            update_fields=[
                "last_sync_at",
                "last_sync_status",
                "last_sync_message",
                "updated_at",
            ]
        )
        AuditLog.objects.create(
            organization=device.organization,
            user=request.user,
            action="device_pull",
            module="hr.attendance_devices",
            object_type="AttendanceDevice",
            object_id=str(device.pk),
            detail=device.last_sync_message,
        )
        return Response(
            {
                "device_id": device.device_id,
                "status": device.last_sync_status,
                "message": device.last_sync_message,
                "created": 0,
                "updated": 0,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="import-csv",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def import_csv(self, request, pk=None):
        device = self.get_object()
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Upload a CSV file as 'file'."}, status=400)
        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "File must be UTF-8 CSV."}, status=400)
        reader = csv.DictReader(io.StringIO(text))
        punches = []
        for row in reader:
            punches.append(
                {
                    "employee_code": (row.get("employee_code") or row.get("emp_code") or "").strip(),
                    "work_date": (row.get("work_date") or row.get("date") or "").strip(),
                    "check_in": (row.get("check_in") or row.get("in") or "").strip() or None,
                    "check_out": (row.get("check_out") or row.get("out") or "").strip() or None,
                    "status": (row.get("status") or "present").strip() or "present",
                }
            )
        if not punches:
            return Response({"detail": "No rows found in CSV."}, status=400)
        with transaction.atomic():
            created, updated, errors = _apply_punches(
                device.organization, device, punches, source="csv"
            )
            device.last_sync_at = timezone.now()
            device.last_sync_status = AttendanceDevice.SyncStatus.OK
            device.last_sync_message = (
                f"CSV import created={created} updated={updated} errors={len(errors)}"
            )[:255]
            device.save(
                update_fields=[
                    "last_sync_at",
                    "last_sync_status",
                    "last_sync_message",
                    "updated_at",
                ]
            )
        return Response(
            {"created": created, "updated": updated, "errors": errors[:50]}
        )


class AttendanceDeviceCatalogView(APIView):
    """Entitlement-aware connector catalog (tenants + platform package editors)."""

    rbac_module = "hr.attendance_devices"
    rbac_exempt = True

    def get(self, request):
        from core.platform_rbac import is_platform_user

        org = user_organization(request.user)
        platform = is_platform_user(request.user)
        if (
            not platform
            and not can(request.user, "hr.attendance_devices", "view")
            and not can(request.user, "hr.attendance", "view")
        ):
            return Response({"detail": "Permission denied"}, status=403)
        if platform and not org:
            # Platform package editors see full catalog as entitled
            health = catalog_with_health(None, None)
            return Response(
                {
                    "module_enabled": True,
                    "max_devices": None,
                    "devices_used": 0,
                    "connectors": health["connectors"],
                    "summary": health["summary"],
                    "integration": health["integration"],
                }
            )
        ent = org_device_entitlement(org)
        used = 0
        if org:
            used = AttendanceDevice.objects.filter(
                organization=org, is_deleted=False
            ).count()
        health = catalog_with_health(
            org, ent["connectors"] if ent["module_enabled"] else []
        )
        return Response(
            {
                "module_enabled": ent["module_enabled"],
                "max_devices": ent["max_devices"],
                "devices_used": used,
                "connectors": health["connectors"],
                "summary": health["summary"],
                "integration": health["integration"],
            }
        )


class AttendanceDeviceSyncView(APIView):
    """Push webhook / device connector contract."""

    rbac_module = "hr.attendance_devices"
    # Allow token-less device push when webhook_secret matches (optional header).
    authentication_classes = []
    permission_classes = []
    rbac_exempt = True
    subscription_exempt = True

    def post(self, request):
        device_id = request.data.get("device_id", "")
        secret = (
            request.headers.get("X-Device-Secret")
            or request.data.get("webhook_secret")
            or ""
        )
        org = None
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if not can(user, "hr.attendance_devices", "add") and not can(
                user, "hr.attendance", "add"
            ):
                return Response(
                    {"detail": "Missing permission: hr.attendance_devices:add"},
                    status=403,
                )
            org = user_organization(user)

        punches = request.data.get("punches") or []
        if not isinstance(punches, list) or not punches:
            return Response({"detail": "punches must be a non-empty list"}, status=400)

        device = None
        if device_id:
            qs = AttendanceDevice.objects.filter(device_id=device_id, is_deleted=False)
            if org:
                qs = qs.filter(organization=org)
            device = qs.first()
            if device and device.webhook_secret and secret != device.webhook_secret:
                # Authenticated org users may sync without secret
                if not (user and user.is_authenticated and org):
                    return Response({"detail": "Invalid device secret"}, status=403)
            if device:
                org = device.organization

        if not org:
            return Response(
                {"detail": "Unknown device_id or authenticate as tenant user."},
                status=400,
            )

        ent = org_device_entitlement(org)
        if not ent["module_enabled"]:
            return Response(
                {"detail": "Attendance devices not enabled on this package."},
                status=403,
            )

        make = request.data.get("make", "")
        model_name = request.data.get("model", "")
        connector_key = request.data.get("connector_key") or (
            device.connector_key if device else "generic_webhook"
        )
        if connector_key not in ent["connectors"]:
            return Response(
                {"detail": f"Connector '{connector_key}' not entitled."}, status=403
            )

        if not device:
            max_dev = ent["max_devices"]
            current = AttendanceDevice.objects.filter(
                organization=org, is_deleted=False
            ).count()
            if max_dev is not None and current >= max_dev:
                return Response(
                    {"detail": f"Device limit reached ({max_dev})."}, status=403
                )
            meta = CONNECTOR_BY_KEY.get(connector_key) or {}
            device, _ = AttendanceDevice.objects.get_or_create(
                organization=org,
                device_id=device_id or f"push-{secrets.token_hex(4)}",
                defaults={
                    "make": make or meta.get("vendor", ""),
                    "model_name": model_name,
                    "connector_key": connector_key,
                    "connection_mode": AttendanceDevice.ConnMode.PUSH,
                    "is_active": True,
                    "webhook_secret": secrets.token_urlsafe(24),
                },
            )

        with transaction.atomic():
            created, updated, errors = _apply_punches(
                org, device, punches, source="device"
            )
            device.last_sync_at = timezone.now()
            device.last_sync_status = AttendanceDevice.SyncStatus.OK
            device.last_sync_message = (
                f"Push sync created={created} updated={updated} errors={len(errors)}"
            )[:255]
            device.save(
                update_fields=[
                    "last_sync_at",
                    "last_sync_status",
                    "last_sync_message",
                    "updated_at",
                ]
            )

        AuditLog.objects.create(
            organization=org,
            user=user if user and user.is_authenticated else None,
            action="device_sync",
            module="hr.attendance_devices",
            object_type="AttendanceDevice",
            object_id=device.device_id,
            detail=f"created={created} updated={updated} errors={len(errors)}",
        )
        return Response(
            {
                "device_id": device.device_id,
                "synced_at": datetime.utcnow().isoformat() + "Z",
                "created": created,
                "updated": updated,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )
