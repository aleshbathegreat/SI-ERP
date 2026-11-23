from accounts.models import Organization, Role, UserRole
from django.contrib.auth import get_user_model
from accounts.rbac import can, allowed_modules, grants_for

User = get_user_model()
org = Organization.objects.get(code="jmc")
for code in ("owner", "admin", "finance"):
    r = Role.objects.get(organization=org, code=code)
    print(code, "projects.projects", (r.permissions or {}).get("projects.projects"))

for u in User.objects.filter(is_active=True):
    prof = getattr(u, "profile", None)
    if not prof or prof.organization_id != org.id:
        continue
    links = list(UserRole.objects.filter(user=u).values_list("role__code", flat=True))
    if not (
        set(links) & {"admin", "owner"}
        or (prof.role in ("admin", "owner"))
        or "admin" in u.username.lower()
    ):
        continue
    print(
        "---",
        u.username,
        "profile",
        prof.role,
        "links",
        links,
        "can",
        can(u, "projects.projects", "view"),
    )
    print("   allowed?", "projects.projects" in allowed_modules(u))
    print("   grants", grants_for(u).get("projects.projects"))
