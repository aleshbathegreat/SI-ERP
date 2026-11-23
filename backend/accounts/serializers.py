from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import ACTIONS, MODULES, allowed_modules
from core.access import is_owner
from core.serializers import OrganizationSerializer


class RoleSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "code",
            "description",
            "permissions",
            "is_system",
            "member_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_system", "created_at", "updated_at")

    def get_member_count(self, obj):
        return obj.user_links.count()

    def validate_permissions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("permissions must be an object")
        cleaned = {}
        for key, actions in value.items():
            if key not in MODULES:
                raise serializers.ValidationError(f"Unknown module: {key}")
            if not isinstance(actions, list):
                raise serializers.ValidationError(f"actions for {key} must be a list")
            cleaned[key] = [a for a in actions if a in ACTIONS]
        return cleaned


class UserProfileSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    primary_role_name = serializers.CharField(source="primary_role.name", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "role",
            "phone",
            "designation",
            "organization",
            "is_active_member",
            "primary_role",
            "primary_role_name",
        )


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()
    role_ids = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
            "profile",
            "permissions",
            "role_ids",
            "is_owner",
        )
        read_only_fields = ("is_superuser",)

    def get_permissions(self, obj):
        return allowed_modules(obj)

    def get_role_ids(self, obj):
        return list(
            UserRole.objects.filter(user=obj).values_list("role_id", flat=True)
        )

    def get_is_owner(self, obj):
        return is_owner(obj)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TenantUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    role_ids = serializers.SerializerMethodField()
    role_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "profile",
            "role_ids",
            "role_names",
        )

    def get_role_ids(self, obj):
        return list(UserRole.objects.filter(user=obj).values_list("role_id", flat=True))

    def get_role_names(self, obj):
        return list(
            UserRole.objects.filter(user=obj).values_list("role__name", flat=True)
        )


class AssignRolesSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )


class InviteUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    role_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )


class ModuleCatalogSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    actions = serializers.ListField(child=serializers.CharField())
