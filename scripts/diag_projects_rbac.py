from accounts.models import Organization, Role, UserRole
from django.contrib.auth import get_user_model
from accounts.rbac import (
    can,
    grants_for,
    org_entitled_modules,
    effective_package_modules,
    allowed_modules,
)

User = get_user_model()
org = Organization.objects.filter(code="jmc").first() or Organization.objects.first()
print("ORG", org.id, org.code, "package_id", org.package_id)
ent = org_entitled_modules(org)
print("entitled is None?", ent is None)
if ent is not None:
    print("entitled project keys", [k for k in ent if k.startswith("projects.")])
    print("entitled count", len(ent))
    if org.package_id:
        pkg = org.package
        print("pkg.code", getattr(pkg, "code", None), getattr(pkg, "name", None))
        print("pkg.module_keys", pkg.module_keys)
        print("pkg.core_module_keys", getattr(pkg, "core_module_keys", None))
        eff = effective_package_modules(pkg)
        print("effective project keys", [k for k in eff if k.startswith("projects.")])
        print("effective has sales.customers?", "sales.customers" in eff)
        print("effective has sales.orders?", "sales.orders" in eff)

for code in ("admin", "owner", "finance"):
    role = Role.objects.filter(organization=org, code=code).first()
    if not role:
        print("NO ROLE", code)
        continue
    perms = role.permissions or {}
    print(
        code,
        "projects.projects=",
        perms.get("projects.projects"),
        "perm_keys=",
        len(perms),
    )

for u in User.objects.filter(is_active=True).order_by("id")[:80]:
    prof = getattr(u, "profile", None)
    if not prof or prof.organization_id != org.id:
        continue
    roles = list(UserRole.objects.filter(user=u).values_list("role__code", flat=True))
    interesting = (
        "admin" in roles
        or (prof and prof.role in ("admin", "owner", "finance"))
        or "admin" in (u.username or "").lower()
        or "owner" in (u.username or "").lower()
    )
    if not interesting:
        continue
    print(
        "USER",
        u.id,
        u.username,
        "profile.role=",
        getattr(prof, "role", None),
        "links=",
        roles,
    )
    print("  can view projects.projects", can(u, "projects.projects", "view"))
    am = allowed_modules(u)
    print("  allowed projects", [k for k in am if k.startswith("projects.")])
    g = grants_for(u)
    print(
        "  grants projects",
        {k: sorted(v) for k, v in g.items() if k.startswith("projects.")},
    )
