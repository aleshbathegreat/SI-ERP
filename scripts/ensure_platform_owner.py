"""Ensure dedicated platform owner vs tenant admin separation (run in /app)."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import ensure_default_roles
from core.models import CompanyLink, Organization

org = Organization.objects.filter(code="jmc").first() or Organization.objects.first()
assert org, "no org"

# Platform owner
platform, created = User.objects.get_or_create(
    username="platform",
    defaults={
        "email": "platform@sigbl.com",
        "first_name": "Platform",
        "last_name": "Owner",
        "is_staff": True,
        "is_superuser": True,
    },
)
if created:
    platform.set_password("Platform@123")
    platform.save()
else:
    platform.is_staff = True
    platform.is_superuser = True
    if not platform.has_usable_password():
        platform.set_password("Platform@123")
    platform.save()
# Keep platform user out of tenant membership
UserProfile.objects.filter(user=platform).delete()
CompanyLink.objects.filter(user=platform).delete()
UserRole.objects.filter(user=platform).delete()

# Tenant admin must NOT be platform superuser
admin = User.objects.filter(username="admin").first()
if admin:
    admin.is_superuser = False
    admin.is_staff = True
    admin.save(update_fields=["is_superuser", "is_staff"])
    ensure_default_roles(org)
    owner_role = Role.objects.filter(organization=org, code="owner").first()
    org.owner = admin
    org.save(update_fields=["owner", "updated_at"])
    UserProfile.objects.update_or_create(
        user=admin,
        defaults={
            "organization": org,
            "role": UserProfile.RoleCode.OWNER,
            "designation": "Organizational Super User",
            "primary_role": owner_role,
        },
    )
    if owner_role:
        UserRole.objects.get_or_create(user=admin, role=owner_role)
    CompanyLink.objects.get_or_create(user=admin, organization=org)

print(
    "platform",
    platform.username,
    "superuser=",
    platform.is_superuser,
    "has_profile=",
    UserProfile.objects.filter(user=platform).exists(),
)
print(
    "admin",
    admin.username if admin else None,
    "superuser=",
    admin.is_superuser if admin else None,
    "is_owner=",
    org.owner_id == (admin.id if admin else None),
)
