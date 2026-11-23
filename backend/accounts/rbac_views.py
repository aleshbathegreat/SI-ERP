from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import ACTIONS, MODULES, ensure_default_roles
from accounts.serializers import (
    AssignRolesSerializer,
    InviteUserSerializer,
    RoleSerializer,
    TenantUserSerializer,
)
from core.access import is_owner, user_organization
from core.bulk import BulkDeleteMixin
from core.models import CompanyLink
from core.scoping import OrgScopedQuerysetMixin


class RoleViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    rbac_module = "settings.roles"
    search_fields = ("name", "code")

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        serializer.save(organization=org, created_by=self.request.user, is_system=False)

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System roles cannot be deleted.")
        instance.delete()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.is_system and "code" in serializer.validated_data:
            serializer.validated_data.pop("code", None)
        serializer.save(updated_by=self.request.user)


class TenantUserViewSet(viewsets.ReadOnlyModelViewSet):
    """List / manage tenant members and role assignments."""

    serializer_class = TenantUserSerializer
    rbac_module = "settings.users"
    search_fields = ("username", "email", "first_name", "last_name")

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return User.objects.none()
        return User.objects.filter(profile__organization=org).select_related("profile")

    @action(detail=False, methods=["post"], url_path="invite")
    def invite(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        ser = InviteUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if User.objects.filter(username=data["username"]).exists():
            return Response({"detail": "Username already exists"}, status=400)
        # Seat caps from subscription package
        pkg = getattr(org, "package", None)
        if pkg:
            active_count = User.objects.filter(
                profile__organization=org, is_active=True
            ).count()
            cap = int(pkg.max_functional_users or 0) + int(pkg.max_ess_users or 0)
            if cap and active_count >= cap:
                return Response(
                    {
                        "detail": f"Seat limit reached ({active_count}/{cap}). Upgrade package or deactivate users.",
                        "code": "seat_limit",
                        "used": active_count,
                        "limit": cap,
                    },
                    status=400,
                )
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"],
                email=data.get("email", ""),
                password=data["password"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
            ensure_default_roles(org)
            role_ids = data.get("role_ids") or []
            roles = list(Role.objects.filter(organization=org, id__in=role_ids))
            if not roles:
                fallback = Role.objects.filter(organization=org, code="employee").first()
                if fallback:
                    roles = [fallback]
            primary = roles[0] if roles else None
            legacy = (
                primary.code
                if primary and primary.code in dict(UserProfile.RoleCode.choices)
                else UserProfile.RoleCode.EMPLOYEE
            )
            UserProfile.objects.create(
                user=user,
                organization=org,
                role=legacy,
                primary_role=primary,
                phone=data.get("phone", ""),
                designation=data.get("designation", ""),
            )
            for role in roles:
                UserRole.objects.get_or_create(user=user, role=role)
            CompanyLink.objects.get_or_create(user=user, organization=org)
        if user.email:
            from core.notifications import notify_user

            notify_user(
                user,
                "Your account is ready",
                f"Hello {user.first_name or user.username},\n\n"
                f"You were added to {org.name}.\n"
                f"Sign in with username: {user.username}\n"
                "If you need a new password, use Forgot password on the sign-in page.\n\n"
                "— SI-ERP",
                organization=org,
            )
        return Response(TenantUserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="assign-roles")
    def assign_roles(self, request, pk=None):
        org = user_organization(request.user)
        user = self.get_object()
        ser = AssignRolesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        role_ids = ser.validated_data["role_ids"]
        roles = Role.objects.filter(organization=org, id__in=role_ids)
        UserRole.objects.filter(user=user, role__organization=org).delete()
        for role in roles:
            UserRole.objects.get_or_create(user=user, role=role)
        profile = getattr(user, "profile", None)
        if profile:
            first = roles.first()
            if first:
                profile.role = (
                    first.code
                    if first.code in dict(UserProfile.RoleCode.choices)
                    else profile.role
                )
                profile.primary_role = first
                profile.save(update_fields=["role", "primary_role", "updated_at"])
        return Response(TenantUserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="set-active")
    def set_active(self, request, pk=None):
        user = self.get_object()
        if is_owner(user):
            return Response({"detail": "Cannot deactivate tenant owner."}, status=400)
        active = bool(request.data.get("is_active", True))
        user.is_active = active
        user.save(update_fields=["is_active"])
        profile = getattr(user, "profile", None)
        if profile:
            profile.is_active_member = active
            profile.save(update_fields=["is_active_member", "updated_at"])
        return Response(TenantUserSerializer(user).data)


class ModuleCatalogView(APIView):
    rbac_module = "settings.roles"
    subscription_exempt = False

    def get(self, request):
        return Response(
            [
                {"key": key, "label": label, "actions": list(ACTIONS)}
                for key, label in MODULES.items()
            ]
        )


class EnsureRolesView(APIView):
    """Bootstrap missing default system roles for current tenant (non-destructive)."""

    rbac_module = "settings.roles"

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        result = ensure_default_roles(org)
        if isinstance(result, dict):
            created = result.get("created") or []
            updated = result.get("updated") or []
        else:
            created = result or []
            updated = []
        return Response(
            {
                "created": created,
                "updated": updated,
                "roles": RoleSerializer(
                    Role.objects.filter(organization=org), many=True
                ).data,
            }
        )
