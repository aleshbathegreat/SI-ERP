from accounts.models import Organization
from accounts.rbac import (
    CONTRACTS_KEYS,
    CRM_KEYS,
    FINANCE_KEYS,
    MFG_KEYS,
    MODULES,
    PROJECTS_KEYS,
    ensure_default_roles,
)

print("modules", len(MODULES))
print(
    "finance",
    len(FINANCE_KEYS),
    "crm",
    len(CRM_KEYS),
    "mfg",
    len(MFG_KEYS),
    "contracts",
    len(CONTRACTS_KEYS),
    "projects",
    len(PROJECTS_KEYS),
)
for org in Organization.objects.filter(is_active=True):
    result = ensure_default_roles(org)
    print(org.code, result)
