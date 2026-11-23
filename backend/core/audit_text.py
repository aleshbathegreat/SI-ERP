"""Turn stored audit rows into sentences an auditor can read."""

from __future__ import annotations

import re
from datetime import datetime

from django.db.models import Q

from accounts.rbac import MODULES

AREA_NAMES = {
    "finance": "Finance",
    "hr": "HR",
    "payroll": "Payroll",
    "sales": "Sales",
    "inventory": "Inventory",
    "procurement": "Procurement",
    "dms": "Documents",
    "documents": "Documents",
    "settings": "Settings",
    "crm": "CRM",
    "projects": "Projects",
    "mfg": "Manufacturing",
    "manufacturing": "Manufacturing",
    "qms": "Quality",
    "quality": "Quality",
    "service": "Service",
    "contracts": "Contracts",
    "ess": "Employee self-service",
    "billing": "Billing",
    "platform": "Platform",
    "saas": "Billing",
    "support": "Support",
}

AREA_PREFIX = {
    "finance": "finance",
    "hr": "hr",
    "payroll": "payroll",
    "sales": "sales",
    "inventory": "inventory",
    "procurement": "procurement",
    "documents": "dms",
    "settings": "settings",
    "crm": "crm",
    "projects": "projects",
    "manufacturing": "mfg",
    "quality": "qms",
    "service": "service",
    "contracts": "contracts",
}

# prefix, module key, noun. Longest prefix wins.
ROUTES = [
    ("finance/account-types", "finance.accounts", "account type"),
    ("finance/accounts", "finance.accounts", "account"),
    ("finance/cost-centers", "finance.cost_centers", "cost center"),
    ("finance/vendors", "finance.vendors", "vendor"),
    ("finance/journals", "finance.journals", "journal entry"),
    ("finance/budgets", "finance.budgets", "budget"),
    ("finance/invoices", "finance.invoices", "vendor invoice"),
    ("finance/bank-reconciliations", "finance.banks", "bank reconciliation"),
    ("finance/bank-statements", "finance.banks", "bank statement line"),
    ("finance/banks", "finance.banks", "bank account"),
    ("finance/investments", "finance.treasury", "investment"),
    ("finance/asset-depreciation", "finance.assets", "depreciation run"),
    ("finance/asset-repairs", "finance.assets", "asset repair"),
    ("finance/assets", "finance.assets", "fixed asset"),
    ("finance/maintenance-orders", "finance.maintenance", "maintenance order"),
    ("finance/pm-schedules", "finance.maintenance", "maintenance schedule"),
    ("finance/tax-codes", "finance.tax", "tax code"),
    ("finance/tax-challans", "finance.tax", "tax challan"),
    ("finance/tax-returns", "finance.tax_returns", "tax return"),
    ("finance/saved-reports", "finance.reports", "saved report"),
    ("finance/periods", "finance.journals", "accounting period"),
    ("finance/fx-rates", "finance.fx", "exchange rate"),
    ("finance/cheques", "finance.cheques", "cheque"),
    ("finance/intercompany-txns", "finance.intercompany", "intercompany transaction"),
    ("finance/intercompany", "finance.intercompany", "intercompany partner"),
    ("finance/e-invoices", "finance.einvoice", "e-invoice"),
    ("crm/leads", "crm.leads", "lead"),
    ("crm/opportunities", "crm.opportunities", "opportunity"),
    ("crm/activities", "crm.activities", "activity"),
    ("projects/projects", "projects.projects", "project"),
    ("projects/tasks", "projects.tasks", "task"),
    ("projects/costs", "projects.costs", "project cost"),
    ("projects/timesheets", "projects.timesheets", "timesheet"),
    ("hr/departments", "hr.departments", "department"),
    ("hr/designations", "hr.designations", "designation"),
    ("hr/shifts", "hr.shifts", "shift"),
    ("hr/overtime-policies", "hr.overtime", "overtime policy"),
    ("hr/employees", "hr.employees", "employee"),
    ("hr/leave-types", "hr.leave_types", "leave type"),
    ("hr/leave-balances", "hr.leaves", "leave balance"),
    ("hr/leave-requests", "hr.leaves", "leave request"),
    ("hr/recruitment", "hr.recruitment", "recruitment request"),
    ("hr/benefit-plans", "hr.benefits", "benefit plan"),
    ("hr/employee-benefits", "hr.benefits", "employee benefit"),
    ("hr/attendance-holidays", "hr.attendance", "holiday"),
    ("hr/attendance-devices", "hr.attendance_devices", "attendance device"),
    ("hr/attendance", "hr.attendance", "attendance record"),
    ("hr/probation", "hr.probation", "probation"),
    ("hr/performance", "hr.performance", "performance review"),
    ("hr/training-courses", "hr.training", "training course"),
    ("hr/training", "hr.training", "training record"),
    ("hr/separations", "hr.separation", "separation"),
    ("hr/settlements", "hr.separation", "final settlement"),
    ("hr/claims", "hr.claims", "expense claim"),
    ("hr/document-types", "hr.documents", "document type"),
    ("hr/documents", "hr.documents", "employee document"),
    ("hr/job-history", "hr.employees", "job history"),
    ("payroll/structures", "payroll.structures", "salary structure"),
    ("payroll/periods", "payroll.periods", "payroll period"),
    ("payroll/payslips", "payroll.payslips", "payslip"),
    ("payroll/loan-repayments", "payroll.loans", "loan repayment"),
    ("payroll/loans", "payroll.loans", "employee loan"),
    ("settings/roles", "settings.roles", "role"),
    ("settings/users", "settings.users", "user"),
    ("settings/integrations", "settings.integrations", "integration"),
    ("settings/email-profiles", "settings.email", "email profile"),
    ("settings/mail-messages", "settings.email", "mailbox message"),
    ("settings/email-templates", "settings.email", "email template"),
    ("settings/doc-series", "settings.doc_series", "document number series"),
    ("settings/approval-matrix", "settings.approval_matrix", "approval rule"),
    ("sales/customers", "sales.customers", "customer"),
    ("sales/quotes", "sales.quotes", "quotation"),
    ("sales/orders", "sales.orders", "sales order"),
    ("sales/deliveries", "sales.deliveries", "delivery note"),
    ("sales/returns", "sales.returns", "sales return"),
    ("sales/pricing", "sales.pricing", "price list"),
    ("sales/invoices", "sales.invoices", "customer invoice"),
    ("sales/contracts", "sales.contracts", "recurring contract"),
    ("inventory/warehouses", "inventory.warehouses", "warehouse"),
    ("inventory/bins", "inventory.bins", "bin"),
    ("inventory/pick-lists", "inventory.pick_lists", "pick list"),
    ("inventory/items", "inventory.items", "item"),
    ("inventory/stock-levels", "inventory.items", "stock level"),
    ("inventory/movements", "inventory.movements", "stock movement"),
    ("inventory/stocktakes", "inventory.stocktake", "stocktake"),
    ("inventory/batches", "inventory.batches", "batch"),
    ("inventory/lots", "inventory.lots", "lot"),
    ("inventory/serials", "inventory.serials", "serial number"),
    ("procurement/requisitions", "procurement.requisitions", "purchase requisition"),
    ("procurement/rfq-quotes", "procurement.rfq", "vendor quote"),
    ("procurement/rfqs", "procurement.rfq", "request for quotation"),
    ("procurement/orders", "procurement.orders", "purchase order"),
    ("procurement/receipts", "procurement.receipts", "goods receipt"),
    ("procurement/returns", "procurement.returns", "purchase return"),
    ("procurement/landed-costs", "procurement.landed_cost", "landed cost"),
    ("dms/folders", "dms.folders", "folder"),
    ("dms/types", "dms.documents", "document type"),
    ("dms/tags", "dms.documents", "tag"),
    ("dms/metadata-types", "dms.documents", "metadata field"),
    ("dms/documents", "dms.documents", "document"),
    ("dms/workflow-states", "dms.documents", "workflow state"),
    ("dms/workflow-transitions", "dms.documents", "workflow transition"),
    ("dms/workflow-triggers", "dms.documents", "workflow trigger"),
    ("dms/workflow-actions", "dms.documents", "workflow action"),
    ("dms/workflows", "dms.documents", "workflow"),
    ("mfg/bom-lines", "mfg.bom", "BOM line"),
    ("mfg/boms", "mfg.bom", "bill of materials"),
    ("mfg/work-orders", "mfg.work_orders", "work order"),
    ("service/notes", "service.notes", "case note"),
    ("service/cases", "service.cases", "service case"),
    ("qms/inspections", "qms.inspections", "inspection"),
    ("qms/ncrs", "qms.ncrs", "non-conformance"),
    ("qms/capas", "qms.capas", "corrective action"),
    ("contracts", "contracts.contracts", "contract"),
]

# path verb → (past sentence, plain infinitive, stored action)
ACTION_WORDS = {
    "approve": ("Approved", "approve", "approved"),
    "reject": ("Rejected", "reject", "rejected"),
    "submit": ("Submitted", "submit", "submitted"),
    "post": ("Posted", "post", "posted"),
    "void": ("Voided", "void", "voided"),
    "cancel": ("Cancelled", "cancel", "cancelled"),
    "publish": ("Published", "publish", "published"),
    "archive": ("Archived", "archive", "archived"),
    "restore": ("Restored", "restore", "restored"),
    "transition": ("Advanced the workflow on", "advance the workflow on", "workflow"),
    "escalate": ("Escalated", "escalate", "escalated"),
    "checkout": ("Checked out", "check out", "checkout"),
    "checkin": ("Checked in", "check in", "checkin"),
    "check-in": ("Checked in", "check in", "checkin"),
    "grant-access": ("Changed access on", "change access on", "access"),
    "start-workflow": ("Started the workflow on", "start the workflow on", "workflow"),
    "from-office365": ("Saved a file from Microsoft 365 into", "save from Microsoft 365 into", "office"),
    "save-to-office365": ("Saved", "save to Microsoft 365", "office"),
    "new-version": ("Filed a new version of", "file a new version of", "version"),
    "comment": ("Commented on", "comment on", "comment"),
    "close": ("Closed", "close", "closed"),
    "reopen": ("Reopened", "reopen", "reopened"),
    "pay": ("Recorded a payment on", "record a payment on", "payment"),
    "import": ("Imported into", "import into", "import"),
    "export": ("Exported", "export", "export"),
    "pull-sync": ("Synchronised", "synchronise", "sync"),
    "lock": ("Locked", "lock", "locked"),
    "unlock": ("Unlocked", "unlock", "unlocked"),
    "reverse": ("Reversed", "reverse", "reversed"),
    "ensure-standard": ("Prepared the standard document workflow", "prepare the standard document workflow", "workflow"),
    "ensure-defaults": ("Prepared the integration defaults", "prepare the integration defaults", "updated"),
}

METHOD_WORDS = {
    "post": ("Created", "create", "created"),
    "put": ("Updated", "update", "updated"),
    "patch": ("Updated", "update", "updated"),
    "delete": ("Removed", "remove", "removed"),
}

STORED_VERBS = {
    "created": "Created",
    "create": "Created",
    "updated": "Updated",
    "update": "Updated",
    "removed": "Removed",
    "delete": "Removed",
    "submit": "Submitted",
    "submitted": "Submitted",
    "approve": "Approved",
    "approved": "Approved",
    "reject": "Rejected",
    "rejected": "Rejected",
    "post": "Posted",
    "posted": "Posted",
    "void": "Voided",
    "voided": "Voided",
    "publish": "Published",
    "published": "Published",
    "archive": "Archived",
    "archived": "Archived",
    "restore": "Restored",
    "restored": "Restored",
    "workflow": "Changed the workflow on",
    "escalated": "Escalated",
    "checkout": "Checked out",
    "checkin": "Checked in",
    "access": "Changed access on",
    "office": "Updated Microsoft 365 for",
    "version": "Filed a new version of",
    "comment": "Commented on",
    "closed": "Closed",
    "reopened": "Reopened",
    "payment": "Recorded a payment on",
    "import": "Imported",
    "export": "Exported",
    "sync": "Synchronised",
    "device_pull": "Synchronised",
    "device_sync": "Synchronised",
    "locked": "Locked",
    "unlocked": "Unlocked",
    "reversed": "Reversed",
    "login": "Signed in",
    "seed": "Prepared starting data",
}

ROLE_LABELS = {
    "owner": "Owner",
    "admin": "Administrator",
    "finance": "Finance lead",
    "hr": "HR lead",
    "payroll": "Payroll lead",
    "initiator": "Preparer",
    "approver": "Approver",
    "employee": "Employee",
    "viewer": "Auditor",
}

ROUTE_OF = {}
for _prefix, _module, _noun in ROUTES:
    ROUTE_OF.setdefault((_module, _noun), _prefix)

CONTROL_HINTS = (
    "sod",
    "approval matrix",
    "period is locked",
    "not authorized",
    "cannot post",
    "cannot approve",
    "cannot submit",
    "cannot reject",
    "unbalanced",
    "budget",
    "segregation",
    "posting not enabled",
)

NOISE_BITS = (
    "/notifications",
    "/health",
    "/schema",
    "/docs",
    "/ops/",
    "/dashboard",
    "/settings/audit",
    "/auth/",
    "/me",
    "/billing/status",
    "/plans",
    "mark-read",
    "/token",
)

HTTP_METHODS = {"post", "put", "patch", "delete"}
USELESS_STATUSES = ["400", "404", "405", "409", "422", "500", "502", "503"]
VERB_TAILS = (
    "approve",
    "reject",
    "submit",
    "post",
    "void",
    "publish",
    "archive",
    "restore",
    "transition",
    "escalate",
    "checkout",
    "checkin",
    "grant-access",
    "start-workflow",
)


def noise_filter() -> Q:
    """Rows that are plumbing, not a business event."""
    q = Q(module__in=["notifications", "health", "schema", "docs", "ops", "dashboard"])
    for bit in NOISE_BITS:
        q |= Q(detail__icontains=bit)
    q |= Q(object_type="HTTP", object_id__in=USELESS_STATUSES)
    return q


def kind_filter(kind: str) -> Q | None:
    kind = (kind or "").strip().lower()
    if kind == "created":
        q = Q(action__in=["created", "create", "post"])
        for verb in VERB_TAILS:
            q &= ~_endswith_verb(verb)
        return q
    if kind == "updated":
        return Q(action__in=["updated", "update", "put", "patch"])
    if kind == "removed":
        return Q(action__in=["removed", "delete"])
    if kind == "submitted":
        return Q(action__in=["submit", "submitted"]) | _endswith_verb("submit")
    if kind == "approved":
        return Q(action__in=["approve", "approved"]) | _endswith_verb("approve")
    if kind == "rejected":
        return Q(action__in=["reject", "rejected"]) | _endswith_verb("reject")
    if kind == "posted":
        return Q(action__in=["post", "posted"]) & (~Q(object_type="HTTP") | _endswith_verb("post"))
    return None


def denied_filter() -> Q:
    return Q(action="denied") | Q(object_type="HTTP", object_id__in=["401", "403"])


def parse_day(value: str):
    try:
        return datetime.strptime((value or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def present(log) -> dict:
    user = getattr(log, "user", None)
    action = (getattr(log, "action", "") or "").strip().lower()
    module = (getattr(log, "module", "") or "").strip()
    object_type = (getattr(log, "object_type", "") or "").strip()
    object_id = (getattr(log, "object_id", "") or "").strip()
    detail = (getattr(log, "detail", "") or "").strip()
    who = _who(user)
    role = _role(user)

    if object_type == "HTTP" or detail.startswith("/") or detail.startswith("http"):
        method = action if action in HTTP_METHODS else "post"
        status = object_id if object_id.isdigit() else 0
        info = classify_http(method, detail, status, "")
        if info:
            return _row(who, role, info)
        return {
            "who": who,
            "role": role,
            "event": "Activity outside the business trail",
            "area": area_label(module),
            "record": "",
            "href": "",
            "outcome": "Completed",
            "change": "",
        }

    if action == "seed":
        return {
            "who": who,
            "role": role,
            "event": "Prepared starting company data",
            "area": area_label(module) or "Settings",
            "record": "",
            "href": "",
            "outcome": "Completed",
            "change": "",
        }

    noun = _class_label(object_type)
    ident = f" {object_id}" if object_id else ""
    href = _href(ROUTE_OF.get((module, noun), ""), object_id)
    if action == "denied":
        event = _sentence(detail) or f"Not allowed to change {noun}{ident}"
        return {
            "who": who,
            "role": role,
            "event": event,
            "area": area_label(module),
            "record": _record(noun, object_id),
            "href": href,
            "outcome": "Denied",
            "change": "",
        }

    verb = STORED_VERBS.get(action) or action.replace("_", " ").capitalize()
    event = f"{verb} {noun}{ident}".strip()
    change = human_change(detail, action)
    if change.lower() == event.lower():
        change = ""
    return {
        "who": who,
        "role": role,
        "event": event,
        "area": area_label(module),
        "record": _record(noun, object_id),
        "href": href,
        "outcome": "Completed",
        "change": change,
    }


def classify_http(method: str, path: str, status, message: str = ""):
    if is_noise_path(path):
        return None
    try:
        code = int(status or 0)
    except (TypeError, ValueError):
        code = 0
    denied = code in (401, 403) or (code == 400 and _is_control(message))
    if code and not (200 <= code < 300) and not denied:
        return None

    module, noun, record_id, verb_key, prefix = _match(path)
    href = _href(prefix, record_id)
    past, plain, stored = ACTION_WORDS.get(verb_key) or METHOD_WORDS.get(
        (method or "").lower(), ("Updated", "update", "updated")
    )
    if verb_key == "from-office365":
        event = "Saved a file from Microsoft 365"
        denied_event = "Not allowed to save a file from Microsoft 365"
    elif verb_key == "save-to-office365":
        event = f"Saved document {record_id} to Microsoft 365".replace("  ", " ").strip()
        denied_event = f"Not allowed to save document {record_id} to Microsoft 365".strip()
    elif verb_key == "ensure-standard":
        event = "Prepared the standard document workflow"
        denied_event = "Not allowed to prepare the standard document workflow"
    elif verb_key == "ensure-defaults":
        event = "Prepared the integration defaults"
        denied_event = "Not allowed to prepare the integration defaults"
    else:
        event = f"{past} {noun}" + (f" {record_id}" if record_id else "")
        denied_event = f"Not allowed to {plain} {noun}" + (f" {record_id}" if record_id else "")

    if denied:
        sentence = _sentence(message)
        return {
            "stored_action": "denied",
            "module": module,
            "noun": noun,
            "record_id": record_id,
            "stored_detail": sentence,
            "event": sentence or denied_event.strip(),
            "area": area_label(module),
            "record": _record(noun, record_id),
            "href": href,
            "outcome": "Denied",
            "change": "",
        }

    return {
        "stored_action": stored,
        "module": module,
        "noun": noun,
        "record_id": record_id,
        "stored_detail": "",
        "event": event.strip(),
        "area": area_label(module),
        "record": _record(noun, record_id),
        "href": href,
        "outcome": "Completed",
        "change": "",
    }


def is_noise_path(path: str) -> bool:
    text = (path or "").lower()
    return any(bit in text for bit in NOISE_BITS)


def area_label(module: str) -> str:
    key = (module or "").strip()
    if key in MODULES:
        return MODULES[key]
    dotted = key.replace("-", "_").replace("/", ".")
    if dotted in MODULES:
        return MODULES[dotted]
    head = key.split(".")[0].split("/")[0]
    return AREA_NAMES.get(head, "General")


def human_change(detail: str, action: str = "") -> str:
    text = (detail or "").strip()
    if not text or text.startswith("/") or text.startswith("http") or "/api/" in text:
        return ""
    if action == "seed" or text.lower().startswith("full jmc"):
        return ""
    if "traceback" in text.lower() or text[:1] in "{[":
        return ""
    arrow = re.match(r"^(.+?)\s*(?:→|->)\s*(.+)$", text)
    if arrow:
        return f"Changed from {_labelize(arrow.group(1))} to {_labelize(arrow.group(2))}"
    stats = re.match(r"created=(\d+)\s+updated=(\d+)\s+errors=(\d+)", text)
    if stats:
        return f"{stats.group(1)} added, {stats.group(2)} updated, {stats.group(3)} errors"
    return text[:240]


def _endswith_verb(verb: str) -> Q:
    return Q(detail__iendswith=f"/{verb}/") | Q(detail__iendswith=f"/{verb}")


def _match(path: str):
    raw = (path or "").split("?", 1)[0]
    if "/api/" in raw:
        raw = raw.split("/api/", 1)[1]
    raw = raw.strip("/")
    best = None
    for prefix, module, noun in ROUTES:
        if raw == prefix or raw.startswith(prefix + "/"):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, module, noun)
    prefix = ""
    if best:
        prefix, module, noun = best
        rest = raw[len(prefix) :].strip("/")
    else:
        parts = [p for p in raw.split("/") if p]
        head = parts[0] if parts else ""
        module = head
        noun = (parts[-1] if parts else "record").replace("-", " ")
        prefix = "/".join(parts[:-1]) if len(parts) > 1 else head
        rest = "/".join(parts[1:]) if len(parts) > 1 else ""
        if rest.isdigit():
            return module, noun, rest, "", prefix
    record_id = ""
    verb_key = ""
    tail = [p for p in rest.split("/") if p] if rest else []
    if tail and tail[0].isdigit():
        record_id = tail[0]
        tail = tail[1:]
    if tail and tail[0] in ACTION_WORDS:
        verb_key = tail[0]
    return module, noun, record_id, verb_key, prefix


def _role(user) -> str:
    profile = getattr(user, "profile", None) if user else None
    if profile is None:
        return ""
    code = (getattr(profile, "role", "") or "").strip().lower()
    if code in ROLE_LABELS:
        return ROLE_LABELS[code]
    primary = getattr(profile, "primary_role", None)
    return (getattr(primary, "name", "") or "").strip()


def _href(prefix: str, record_id: str) -> str:
    if prefix and record_id and str(record_id).isdigit():
        return f"/{prefix}/{record_id}"
    return ""


def _who(user) -> str:
    if not user:
        return "System"
    first = (getattr(user, "first_name", "") or "").strip()
    last = (getattr(user, "last_name", "") or "").strip()
    username = (getattr(user, "username", "") or "").strip()
    full = f"{first} {last}".strip()
    if full and username and full.lower() != username.lower():
        return f"{full} ({username})"
    return full or username or "System"


def _class_label(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return "record"
    if " " in text:
        return text[0].lower() + text[1:]
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return spaced.replace("_", " ").lower()


def _record(noun: str, record_id: str) -> str:
    if not noun:
        return record_id
    label = noun[:1].upper() + noun[1:]
    if record_id:
        return f"{label} {record_id}"
    return label


def _labelize(value: str) -> str:
    words = (value or "").replace("_", " ").strip()
    if not words:
        return value
    return words[:1].upper() + words[1:]


def _sentence(message: str) -> str:
    text = " ".join((message or "").split())
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _is_control(message: str) -> bool:
    text = (message or "").lower()
    return any(hint in text for hint in CONTROL_HINTS)


def _row(who: str, role: str, info: dict) -> dict:
    return {
        "who": who,
        "role": role,
        "event": info["event"],
        "area": info["area"],
        "record": info["record"],
        "href": info.get("href") or "",
        "outcome": info["outcome"],
        "change": info["change"],
    }
