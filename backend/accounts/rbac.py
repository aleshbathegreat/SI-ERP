"""Tenant RBAC — module catalog, packages, and default role blueprints."""

from __future__ import annotations

ACTIONS = ("view", "add", "change", "delete")

MODULES = {
    "dashboard": "Dashboard",
    "approvals": "LoA · Approvals Inbox",
    "chat": "Chat · Internal conversations",
    # Finance
    "finance.accounts": "Finance · Chart of Accounts (GL)",
    "finance.cost_centers": "Finance · Cost Centers / Dimensions",
    "finance.journals": "Finance · Journals & Approvals",
    "finance.budgets": "Finance · Budgeting & Control",
    "finance.vendors": "Finance · Vendor Master (AP)",
    "finance.invoices": "Finance · AP Invoices & Payments",
    "finance.banks": "Finance · Bank Accounts & Reconciliation",
    "finance.treasury": "Finance · Treasury / Investments",
    "finance.assets": "Finance · Fixed Assets",
    "finance.tax": "Finance · Tax Codes (WHT/ST)",
    "finance.tax_returns": "Finance · Tax Returns (ST/WHT)",
    "finance.reports": "Finance · Statutory & KPI Reports",
    "finance.fx": "Finance · FX Rates",
    "finance.cheques": "Finance · Cheque Register / PDC",
    "finance.intercompany": "Finance · Intercompany",
    "finance.einvoice": "Finance · FBR E-Invoice",
    "finance.maintenance": "Finance · Maintenance (CMMS Work Orders & PM)",
    # CRM / Projects
    "crm.leads": "CRM · Leads",
    "crm.opportunities": "CRM · Opportunities",
    "crm.activities": "CRM · Activities",
    "projects.projects": "Projects · Projects",
    "projects.tasks": "Projects · Tasks",
    "projects.costs": "Projects · Costs",
    "projects.timesheets": "Projects · Timesheets",
    # Manufacturing / Contracts
    "mfg.bom": "Manufacturing · BOM",
    "mfg.work_orders": "Manufacturing · Work Orders",
    "contracts.contracts": "Contracts · Commercial Contracts",
    # Customer service / Quality
    "service.cases": "Service · Customer Cases",
    "service.notes": "Service · Case Notes",
    "qms.inspections": "Quality · Inspections",
    "qms.ncrs": "Quality · Non-Conformance Reports (NCR)",
    "qms.capas": "Quality · Corrective & Preventive Actions (CAPA)",
    # Enterprise DMS
    "dms.folders": "Documents · Folders (DMS)",
    "dms.documents": "Documents · Enterprise Documents (DMS)",
    # Sales / Inventory / Procurement
    "sales.customers": "Sales · Customers",
    "sales.quotes": "Sales · Quotations",
    "sales.orders": "Sales · Sales Orders",
    "sales.deliveries": "Sales · Delivery Notes (DN)",
    "sales.returns": "Sales · Returns / RMA",
    "sales.pricing": "Sales · Price Lists",
    "sales.invoices": "Sales · AR Invoices & Receipts",
    "sales.credit": "Sales · Credit Aging",
    "sales.contracts": "Sales · Recurring Contracts",
    "inventory.warehouses": "Inventory · Warehouses",
    "inventory.items": "Inventory · Items",
    "inventory.movements": "Inventory · Stock Movements",
    "inventory.stocktake": "Inventory · Stocktake",
    "inventory.batches": "Inventory · Warehouse Batches",
    "inventory.lots": "Inventory · Lots",
    "inventory.serials": "Inventory · Serial Numbers",
    "inventory.bins": "Inventory · Warehouse Bins",
    "inventory.pick_lists": "Inventory · Pick Lists",
    "procurement.requisitions": "Procurement · Purchase Requisitions",
    "procurement.rfq": "Procurement · Vendor RFQ",
    "procurement.orders": "Procurement · Purchase Orders",
    "procurement.receipts": "Procurement · Goods Receipts (GRN)",
    "procurement.returns": "Procurement · Purchase Returns",
    "procurement.landed_cost": "Procurement · Landed Cost",
    # HR
    "hr.departments": "HR · Departments / Org Structure",
    "hr.designations": "HR · Designations",
    "hr.employees": "HR · Employee Master & Lifecycle",
    "hr.recruitment": "HR · Recruitment & Hiring",
    "hr.benefits": "HR · Benefits / EOBI / Medical",
    "hr.attendance": "HR · Attendance",
    "hr.attendance_devices": "HR · Attendance Devices & Connectors",
    "hr.leave_types": "HR · Leave Types & Policies",
    "hr.leaves": "HR · Leave Requests & Approvals",
    "hr.probation": "HR · Probation & Confirmation",
    "hr.performance": "HR · Performance Management",
    "hr.training": "HR · Training & Development",
    "hr.separation": "HR · Separation / Exit / Settlement",
    "hr.documents": "HR · Document Management",
    "hr.shifts": "HR · Shifts",
    "hr.overtime": "HR · Overtime Policies",
    "hr.claims": "HR · Expense Claims",
    # Payroll
    "payroll.structures": "Payroll · Salary Structures",
    "payroll.periods": "Payroll · Periods & Runs",
    "payroll.payslips": "Payroll · Payslips & Registers",
    "payroll.loans": "Payroll · Employee Loans & Advances",
    # ESS + governance
    "ess": "Employee Self-Service (ESS)",
    "billing": "SaaS · Billing",
    "settings.roles": "Settings · Roles & Permissions (SoD)",
    "settings.users": "Settings · Users (Functional / ESS)",
    "settings.email": "Settings · Email SMTP & Profiles",
    "settings.integrations": "Settings · Enterprise Integrations (M365, Devices, APIs)",
    "settings.domain": "Settings · Custom Domain & Branding",
    "settings.audit": "Settings · Audit & Activity Logs",
    "settings.doc_series": "Settings · Document Number Series",
    "settings.approval_matrix": "Settings · Approval Matrix",
    "settings.import_hub": "Settings · Data Import Hub",
}

ALL_MODULE_KEYS = list(MODULES.keys())
FINANCE_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("finance.")]
HR_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("hr.")]
PAYROLL_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("payroll.")]
SALES_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("sales.")]
INVENTORY_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("inventory.")]
PROCUREMENT_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("procurement.")]
CRM_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("crm.")]
PROJECTS_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("projects.")]
MFG_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("mfg.")]
CONTRACTS_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("contracts.")]
SERVICE_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("service.")]
QMS_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("qms.")]
DMS_KEYS = [k for k in ALL_MODULE_KEYS if k.startswith("dms.")]
OPS_KEYS = SALES_KEYS + INVENTORY_KEYS + PROCUREMENT_KEYS
ERP_OPERATIONAL = (
    FINANCE_KEYS
    + HR_KEYS
    + PAYROLL_KEYS
    + OPS_KEYS
    + CRM_KEYS
    + PROJECTS_KEYS
    + MFG_KEYS
    + CONTRACTS_KEYS
    + DMS_KEYS
    + SERVICE_KEYS
    + QMS_KEYS
    + ["dashboard", "ess", "settings.audit"]
)

# Always included in every subscription package (platform shell + governance)
CORE_MODULE_KEYS = [
    "dashboard",
    "approvals",
    "chat",
    "ess",
    "settings.roles",
    "settings.users",
    "settings.email",
    "settings.integrations",
    "settings.domain",
    "settings.audit",
    "settings.doc_series",
    "settings.approval_matrix",
    "settings.import_hub",
]

# Assignable product modules (sold on packages)
ASSIGNABLE_MODULE_KEYS = (
    FINANCE_KEYS
    + HR_KEYS
    + PAYROLL_KEYS
    + OPS_KEYS
    + CRM_KEYS
    + PROJECTS_KEYS
    + MFG_KEYS
    + CONTRACTS_KEYS
    + DMS_KEYS
    + SERVICE_KEYS
    + QMS_KEYS
    + ["billing"]
)

MODULE_GROUPS = [
    {
        "id": "core",
        "label": "Core (always included)",
        "core": True,
        "keys": CORE_MODULE_KEYS,
    },
    {
        "id": "finance",
        "label": "Finance",
        "core": False,
        "keys": FINANCE_KEYS,
    },
    {
        "id": "sales",
        "label": "Sales",
        "core": False,
        "keys": SALES_KEYS,
    },
    {
        "id": "inventory",
        "label": "Inventory",
        "core": False,
        "keys": INVENTORY_KEYS,
    },
    {
        "id": "procurement",
        "label": "Procurement",
        "core": False,
        "keys": PROCUREMENT_KEYS,
    },
    {
        "id": "crm",
        "label": "CRM",
        "core": False,
        "keys": CRM_KEYS,
    },
    {
        "id": "projects",
        "label": "Projects",
        "core": False,
        "keys": PROJECTS_KEYS,
    },
    {
        "id": "mfg",
        "label": "Manufacturing",
        "core": False,
        "keys": MFG_KEYS,
    },
    {
        "id": "contracts",
        "label": "Contracts",
        "core": False,
        "keys": CONTRACTS_KEYS,
    },
    {
        "id": "service",
        "label": "Customer Service",
        "core": False,
        "keys": SERVICE_KEYS,
    },
    {
        "id": "qms",
        "label": "Quality (QMS)",
        "core": False,
        "keys": QMS_KEYS,
    },
    {
        "id": "dms",
        "label": "Documents (DMS)",
        "core": False,
        "keys": DMS_KEYS,
    },
    {
        "id": "hr",
        "label": "HR",
        "core": False,
        "keys": HR_KEYS,
    },
    {
        "id": "payroll",
        "label": "Payroll",
        "core": False,
        "keys": PAYROLL_KEYS,
    },
    {
        "id": "saas",
        "label": "SaaS billing",
        "core": False,
        "keys": ["billing"],
    },
]


def expand_module_keys(keys: list[str] | None) -> list[str]:
    """Expand coarse aliases (finance/hr/payroll) and keep fine-grained keys."""
    out: set[str] = set()
    for k in keys or []:
        key = (k or "").strip()
        if not key:
            continue
        if key == "finance":
            out.update(FINANCE_KEYS)
        elif key == "hr":
            out.update(HR_KEYS)
        elif key == "payroll":
            out.update(PAYROLL_KEYS)
        elif key == "sales":
            out.update(SALES_KEYS)
        elif key == "inventory":
            out.update(INVENTORY_KEYS)
        elif key == "procurement":
            out.update(PROCUREMENT_KEYS)
        elif key == "crm":
            out.update(CRM_KEYS)
        elif key == "projects":
            out.update(PROJECTS_KEYS)
        elif key == "mfg":
            out.update(MFG_KEYS)
        elif key == "contracts":
            out.update(CONTRACTS_KEYS)
        elif key == "dms":
            out.update(DMS_KEYS)
        elif key == "service":
            out.update(SERVICE_KEYS)
        elif key == "qms":
            out.update(QMS_KEYS)
        elif key == "ops":
            out.update(OPS_KEYS)
        elif key == "core":
            out.update(CORE_MODULE_KEYS)
        elif key == "all":
            out.update(ALL_MODULE_KEYS)
        elif key in MODULES:
            out.add(key)
    return sorted(out)


def package_module_catalog() -> list[dict]:
    groups = []
    for g in MODULE_GROUPS:
        groups.append(
            {
                "id": g["id"],
                "label": g["label"],
                "core": g["core"],
                "modules": [
                    {"key": k, "label": MODULES[k], "core": g["core"]}
                    for k in g["keys"]
                    if k in MODULES
                ],
            }
        )
    return groups


# When a package was sold with an older fine-grained key, auto-entitle sibling
# modules added later in the same product family (avoids stale JSON hiding nav).
MODULE_COMPANIONS: dict[str, tuple[str, ...]] = {
    "sales.orders": (
        "sales.quotes",
        "sales.invoices",
        "sales.deliveries",
        "sales.returns",
        "sales.pricing",
        "sales.credit",
        "sales.contracts",
        "contracts.contracts",
        "projects.projects",
        "projects.tasks",
        "projects.costs",
        "projects.timesheets",
    ),
    "sales.customers": (
        "sales.quotes",
        "sales.invoices",
        "sales.deliveries",
        "sales.returns",
        "sales.pricing",
        "sales.credit",
        "sales.contracts",
        "crm.leads",
        "crm.opportunities",
        "crm.activities",
        "contracts.contracts",
        "projects.projects",
        "projects.tasks",
        "projects.costs",
        "projects.timesheets",
        "service.cases",
        "service.notes",
    ),
    "sales.invoices": ("sales.credit", "sales.contracts", "finance.einvoice"),
    "procurement.orders": (
        "procurement.receipts",
        "procurement.requisitions",
        "procurement.rfq",
        "procurement.returns",
        "procurement.landed_cost",
    ),
    "inventory.items": (
        "inventory.stocktake",
        "inventory.batches",
        "inventory.lots",
        "inventory.serials",
        "inventory.bins",
        "inventory.pick_lists",
        "mfg.bom",
        "mfg.work_orders",
    ),
    "inventory.movements": (
        "inventory.stocktake",
        "inventory.batches",
        "inventory.lots",
        "inventory.serials",
        "inventory.bins",
        "inventory.pick_lists",
    ),
    "dms.folders": ("dms.documents",),
    "dms.documents": ("dms.folders",),
    "finance.banks": ("finance.cheques",),
    "finance.accounts": ("finance.fx", "finance.intercompany", "finance.einvoice"),
    "finance.journals": ("finance.fx", "finance.intercompany"),
    "finance.assets": ("finance.einvoice", "finance.maintenance"),
    "finance.maintenance": ("finance.assets",),
    "service.cases": ("service.notes",),
    "service.notes": ("service.cases",),
    "qms.inspections": ("qms.ncrs", "qms.capas"),
    "qms.ncrs": ("qms.inspections", "qms.capas"),
    "qms.capas": ("qms.inspections", "qms.ncrs"),
    "procurement.receipts": ("qms.inspections", "qms.ncrs", "qms.capas"),
    "finance.tax": ("finance.einvoice", "finance.tax_returns"),
    "finance.tax_returns": ("finance.tax",),
    "finance.invoices": ("finance.einvoice",),
    "crm.leads": ("crm.opportunities", "crm.activities"),
    "crm.opportunities": ("crm.leads", "crm.activities"),
    "crm.activities": ("crm.leads", "crm.opportunities"),
    "projects.projects": (
        "projects.tasks",
        "projects.costs",
        "projects.timesheets",
        "contracts.contracts",
    ),
    "projects.tasks": ("projects.projects", "projects.costs", "projects.timesheets"),
    "projects.costs": ("projects.projects", "projects.tasks", "projects.timesheets"),
    "projects.timesheets": ("projects.projects", "projects.tasks", "projects.costs"),
    "mfg.bom": ("mfg.work_orders", "inventory.lots", "inventory.serials"),
    "mfg.work_orders": ("mfg.bom", "inventory.lots", "inventory.serials"),
    "contracts.contracts": ("sales.contracts", "projects.projects"),
}


def _with_module_companions(keys: list[str]) -> list[str]:
    out = set(keys)
    for key, companions in MODULE_COMPANIONS.items():
        if key in out:
            out.update(companions)
    return sorted(out)


def effective_package_modules(package) -> list[str]:
    """Core + assigned package modules (expanded).

    Always unions live CORE_MODULE_KEYS so newly added platform-core modules
    (e.g. settings.integrations) are entitled even when package JSON is stale.
    Also grants MODULE_COMPANIONS so O2C/P2P siblings (quotes, AR, GRN) appear
    when the parent commerce modules were already entitled.
    """
    assigned = expand_module_keys(getattr(package, "module_keys", None) if package else None)
    pkg_core = expand_module_keys(
        getattr(package, "core_module_keys", None) if package else None
    )
    core = set(CORE_MODULE_KEYS) | set(pkg_core)
    return _with_module_companions(sorted(core | set(assigned)))


def org_entitled_modules(org) -> list[str] | None:
    """None = no package restriction (legacy full access)."""
    if org is None:
        return []
    pkg = getattr(org, "package", None)
    if pkg is None:
        return None
    return effective_package_modules(pkg)


def full_permissions() -> dict:
    return {key: list(ACTIONS) for key in ALL_MODULE_KEYS}


def view_only_permissions(keys: list[str] | None = None) -> dict:
    keys = keys or ALL_MODULE_KEYS
    return {key: ["view"] for key in keys if key in MODULES}


def module_permissions(keys: list[str], actions: list[str] | None = None) -> dict:
    actions = actions or list(ACTIONS)
    return {key: list(actions) for key in keys if key in MODULES}


def merge_perms(*parts: dict) -> dict:
    out: dict[str, list[str]] = {}
    for part in parts:
        for key, actions in part.items():
            cur = set(out.get(key, []))
            cur.update(actions or [])
            out[key] = sorted(cur)
    return out


DEFAULT_ROLE_BLUEPRINTS = [
    {
        "code": "owner",
        "name": "Organizational Super User",
        "description": "System administration and organizational-level visibility; billing & SoD.",
        "is_system": True,
        "permissions": full_permissions(),
    },
    {
        "code": "admin",
        "name": "Organizational Super User (Admin)",
        "description": "Org admin: modules, users, roles, audit. Billing view only.",
        "is_system": True,
        "permissions": merge_perms(
            module_permissions([k for k in ALL_MODULE_KEYS if k != "billing"]),
            {"billing": ["view"]},
        ),
    },
    {
        "code": "finance",
        "name": "Department Super User · Finance",
        "description": (
            "Full Finance + commerce ops (O2C/P2P/inventory) plus CRM, Projects, "
            "Manufacturing, and Contracts."
        ),
        "is_system": True,
        "permissions": merge_perms(
            module_permissions(
                FINANCE_KEYS
                + OPS_KEYS
                + CRM_KEYS
                + PROJECTS_KEYS
                + MFG_KEYS
                + CONTRACTS_KEYS
                + DMS_KEYS
                + SERVICE_KEYS
                + QMS_KEYS
            ),
            {
                "dashboard": list(ACTIONS),
                "approvals": ["view", "change"],
                "billing": ["view"],
                "settings.audit": ["view"],
                "hr.employees": ["view"],
            },
        ),
    },
    {
        "code": "hr",
        "name": "Department Super User · HR",
        "description": "Full HR functional access (Org, Recruitment, Employees, Benefits, Attendance, Leave, ESS oversight).",
        "is_system": True,
        "permissions": merge_perms(
            module_permissions(HR_KEYS),
            {
                "dashboard": list(ACTIONS),
                "approvals": ["view", "change"],
                "ess": ["view", "change"],
                "payroll.structures": ["view"],
                "payroll.payslips": ["view"],
                "payroll.loans": ["view", "add", "change"],
                "settings.audit": ["view"],
            },
        ),
    },
    {
        "code": "payroll",
        "name": "Department Super User · Payroll",
        "description": "Full Payroll functional access; approved HR attendance/leave/employee read; GL interface add.",
        "is_system": True,
        "permissions": merge_perms(
            module_permissions(PAYROLL_KEYS),
            {
                "dashboard": list(ACTIONS),
                "approvals": ["view", "change"],
                "hr.employees": ["view"],
                "hr.attendance": ["view"],
                "hr.leaves": ["view"],
                "hr.benefits": ["view"],
                "finance.journals": ["view", "add"],
                "finance.reports": ["view"],
                "ess": ["view"],
                "settings.audit": ["view"],
            },
        ),
    },
    {
        "code": "initiator",
        "name": "Department Initiator",
        "description": "Create/enter/submit transactions for review (no approve/delete).",
        "is_system": True,
        "permissions": merge_perms(
            module_permissions(
                [
                    "finance.journals",
                    "finance.invoices",
                    "finance.budgets",
                    "finance.cheques",
                    "finance.fx",
                    "finance.einvoice",
                    "finance.tax_returns",
                    "sales.orders",
                    "sales.quotes",
                    "sales.invoices",
                    "sales.contracts",
                    "procurement.orders",
                    "procurement.requisitions",
                    "procurement.rfq",
                    "crm.leads",
                    "crm.opportunities",
                    "crm.activities",
                    "projects.projects",
                    "projects.tasks",
                    "projects.costs",
                    "projects.timesheets",
                    "mfg.bom",
                    "mfg.work_orders",
                    "contracts.contracts",
                    "finance.maintenance",
                    "service.cases",
                    "service.notes",
                    "qms.inspections",
                    "qms.ncrs",
                    "qms.capas",
                    "hr.leaves",
                    "hr.attendance",
                    "hr.recruitment",
                    "hr.claims",
                    "payroll.payslips",
                ],
                ["view", "add"],
            ),
            {
                "dashboard": ["view"],
                "approvals": ["view"],
                "finance.accounts": ["view"],
                "finance.vendors": ["view"],
                "sales.customers": ["view"],
                "inventory.items": ["view"],
                "inventory.warehouses": ["view"],
                "inventory.lots": ["view"],
                "inventory.batches": ["view"],
                "inventory.serials": ["view"],
                "hr.employees": ["view"],
                "hr.leave_types": ["view"],
                "payroll.periods": ["view"],
            },
        ),
    },
    {
        "code": "approver",
        "name": "Department Reviewer / Approver",
        "description": (
            "Review/approve within LoA (finance, O2C/P2P, CRM/projects/MFG, "
            "HR leave/attendance/recruitment, payroll)."
        ),
        "is_system": True,
        "permissions": {
            "dashboard": ["view"],
            "approvals": ["view", "change"],
            "finance.journals": ["view", "change"],
            "finance.invoices": ["view", "change"],
            "finance.budgets": ["view", "change"],
            "finance.cheques": ["view", "change"],
            "finance.einvoice": ["view", "change"],
            "finance.tax_returns": ["view", "change"],
            "finance.maintenance": ["view", "change"],
            "service.cases": ["view", "change"],
            "service.notes": ["view", "change"],
            "qms.inspections": ["view", "change"],
            "qms.ncrs": ["view", "change"],
            "qms.capas": ["view", "change"],
            "finance.reports": ["view"],
            "sales.orders": ["view", "change"],
            "sales.quotes": ["view", "change"],
            "sales.invoices": ["view", "change"],
            "sales.contracts": ["view", "change"],
            "procurement.orders": ["view", "change"],
            "procurement.requisitions": ["view", "change"],
            "procurement.rfq": ["view", "change"],
            "crm.leads": ["view", "change"],
            "crm.opportunities": ["view", "change"],
            "projects.projects": ["view", "change"],
            "projects.costs": ["view", "change"],
            "projects.timesheets": ["view", "change"],
            "mfg.work_orders": ["view", "change"],
            "contracts.contracts": ["view", "change"],
            "hr.leaves": ["view", "change"],
            "hr.attendance": ["view", "change"],
            "hr.recruitment": ["view", "change"],
            "hr.performance": ["view", "change"],
            "hr.claims": ["view", "change"],
            "hr.employees": ["view"],
            "payroll.periods": ["view", "change"],
            "payroll.payslips": ["view"],
            "settings.audit": ["view"],
        },
    },
    {
        "code": "viewer",
        "name": "Auditor",
        "description": "Read-only records, reports and audit trails.",
        "is_system": True,
        "permissions": view_only_permissions(
            [k for k in ERP_OPERATIONAL if k != "ess"]
            + ["settings.audit", "billing", "ess", "approvals"]
        ),
    },
    {
        "code": "employee",
        "name": "Employee Self-Service User",
        "description": "ESS — Own leave, attendance exceptions and payslips only.",
        "is_system": True,
        "permissions": {
            "dashboard": ["view"],
            "ess": ["view", "add", "change"],
            "hr.leaves": ["view", "add"],
            "hr.attendance": ["view", "add"],
            "payroll.payslips": ["view"],
        },
    },
]


def ensure_default_roles(organization):
    """Create missing system roles; merge newly catalogued modules into existing ones.

    Does not remove or shrink custom SoD grants — only adds missing module keys
    (and missing actions for those keys) from the live blueprint.
    """
    from accounts.models import Role

    created = []
    updated = []
    for bp in DEFAULT_ROLE_BLUEPRINTS:
        role, was_created = Role.objects.get_or_create(
            organization=organization,
            code=bp["code"],
            defaults={
                "name": bp["name"],
                "description": bp["description"],
                "permissions": bp["permissions"],
                "is_system": bp["is_system"],
            },
        )
        if was_created:
            created.append(bp["code"])
            continue
        if not role.is_system:
            continue
        desired = bp.get("permissions") or {}
        current = dict(role.permissions or {})
        changed = False
        for key, actions in desired.items():
            if key not in MODULES:
                continue
            want = set(actions or [])
            have = set(current.get(key) or [])
            if not want - have:
                continue
            current[key] = sorted(have | want)
            changed = True
        if role.name != bp["name"] or role.description != bp["description"]:
            role.name = bp["name"]
            role.description = bp["description"]
            changed = True
        if changed:
            role.permissions = current
            role.save(update_fields=["name", "description", "permissions", "updated_at"])
            updated.append(bp["code"])
    return {"created": created, "updated": updated}


def grants_for(user) -> dict[str, set[str]]:
    from accounts.models import Role, UserRole
    from core.access import user_organization

    org = user_organization(user)
    if org is None:
        return {}

    found: dict[str, set[str]] = {}
    links = UserRole.objects.filter(
        user=user, role__organization=org, role__is_deleted=False
    ).select_related("role")
    for link in links:
        for key, actions in (link.role.permissions or {}).items():
            found.setdefault(key, set()).update(actions or [])

    profile = getattr(user, "profile", None)
    if profile and profile.role and not links.exists():
        role = Role.objects.filter(
            organization=org, code=profile.role, is_deleted=False
        ).first()
        if role:
            for key, actions in (role.permissions or {}).items():
                found.setdefault(key, set()).update(actions or [])

    # Sibling commerce modules added after roles were frozen (quotes/AR/GRN).
    for parent, companions in MODULE_COMPANIONS.items():
        parent_actions = found.get(parent)
        if not parent_actions:
            continue
        for child in companions:
            found.setdefault(child, set()).update(parent_actions)

    return found


def can(user, module: str, action: str) -> bool:
    from core.access import is_owner, user_organization

    if not getattr(user, "is_authenticated", False):
        return False
    org = user_organization(user)
    if org is None:
        return False
    if module not in MODULES:
        return False
    if action not in ACTIONS:
        return False
    entitled = org_entitled_modules(org)
    if entitled is not None and module not in entitled:
        return False
    if is_owner(user):
        return True
    # Platform core settings (import hub, users, audit, …) for any org member
    # with at least one role — avoids stale role JSON blocking governance screens.
    if module in CORE_MODULE_KEYS and grants_for(user):
        return True
    return action in grants_for(user).get(module, set())


def allowed_modules(user) -> dict[str, list[str]]:
    from core.access import is_owner, user_organization

    org = user_organization(user)
    entitled = org_entitled_modules(org)
    if is_owner(user):
        keys = entitled if entitled is not None else ALL_MODULE_KEYS
        return {k: list(ACTIONS) for k in keys if k in MODULES}
    grants = grants_for(user)
    out = {k: sorted(list(v)) for k, v in grants.items() if v}
    if grants:
        for key in CORE_MODULE_KEYS:
            if entitled is not None and key not in entitled:
                continue
            out.setdefault(key, list(ACTIONS))
    if entitled is not None:
        out = {k: v for k, v in out.items() if k in entitled}
    return out


def require_perm(user, module: str, action: str) -> bool:
    return can(user, module, action)
