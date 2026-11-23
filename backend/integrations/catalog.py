"""Enterprise integration catalog."""

from __future__ import annotations

# Categories: microsoft | hr | finance | messaging | identity | platform
INTEGRATION_CATALOG: list[dict] = [
    {
        "key": "microsoft365_mail",
        "name": "Microsoft 365 · Email (Graph)",
        "category": "microsoft",
        "recommended": True,
        "priority": 1,
        "summary": "Send workflow, approval, payslip and alert emails via Microsoft Graph.",
        "capabilities": ["mail.send", "notifications", "html"],
        "config_fields": [
            {"key": "tenant_id", "label": "Azure AD Tenant ID", "secret": False},
            {"key": "client_id", "label": "Application (client) ID", "secret": False},
            {"key": "client_secret", "label": "Client secret", "secret": True},
            {"key": "sender_upn", "label": "Sender mailbox UPN / email", "secret": False},
        ],
        "docs_hint": "App registration with Mail.Send (application) + admin consent.",
    },
    {
        "key": "microsoft365_smtp",
        "name": "Microsoft 365 · SMTP (Exchange Online)",
        "category": "microsoft",
        "recommended": True,
        "priority": 2,
        "summary": "Alternate M365 path using smtp.office365.com (authenticated SMTP).",
        "capabilities": ["mail.send"],
        "config_fields": [],
        "linked_module": "settings.email",
        "docs_hint": "Configure under Email SMTP with host smtp.office365.com port 587 TLS.",
    },
    {
        "key": "microsoft365_sso",
        "name": "Microsoft Entra ID · SSO (OIDC)",
        "category": "identity",
        "recommended": False,
        "priority": 3,
        "summary": "Single sign-on for functional users via Azure AD / Entra ID.",
        "capabilities": ["sso", "oidc"],
        "config_fields": [
            {"key": "tenant_id", "label": "Directory (tenant) ID", "secret": False},
            {"key": "client_id", "label": "Application (client) ID", "secret": False},
            {"key": "client_secret", "label": "Client secret", "secret": True},
            {"key": "redirect_uri", "label": "Redirect URI", "secret": False},
        ],
        "docs_hint": "Optional; enable when IT approves SSO.",
    },
    {
        "key": "microsoft365_calendar",
        "name": "Microsoft 365 · Calendar",
        "category": "calendar",
        "recommended": False,
        "priority": 4,
        "summary": "Copy CRM meetings and calls into an Outlook calendar. Use it together with Google and CalDAV.",
        "capabilities": ["calendar.read", "calendar.write"],
        "config_fields": [
            {"key": "tenant_id", "label": "Azure AD Tenant ID", "secret": False},
            {"key": "client_id", "label": "Application (client) ID", "secret": False},
            {"key": "client_secret", "label": "Client secret", "secret": True},
            {"key": "calendar_upn", "label": "Calendar mailbox UPN", "secret": False},
        ],
        "linked_module": "crm.activities",
        "docs_hint": "App registration with Calendars.ReadWrite (application) and admin consent. The mailbox is the Outlook calendar that receives the events.",
    },
    {
        "key": "google_calendar",
        "name": "Google Calendar",
        "category": "calendar",
        "recommended": False,
        "priority": 4,
        "summary": "Copy CRM meetings and calls into a Google calendar. Turn this on with Microsoft and CalDAV if you use more than one.",
        "capabilities": ["calendar.read", "calendar.write"],
        "config_fields": [
            {"key": "client_id", "label": "OAuth client ID", "secret": False},
            {"key": "client_secret", "label": "OAuth client secret", "secret": True},
            {"key": "refresh_token", "label": "Refresh token", "secret": True},
            {"key": "calendar_id", "label": "Calendar ID (email or primary)", "secret": False},
        ],
        "linked_module": "crm.activities",
        "docs_hint": "Google Cloud OAuth client with the Calendar API enabled. The refresh token needs calendar events scope.",
    },
    {
        "key": "caldav_calendar",
        "name": "CalDAV · Apple, Nextcloud, and others",
        "category": "calendar",
        "recommended": False,
        "priority": 4,
        "summary": "Copy CRM meetings to any CalDAV calendar, including Apple, Nextcloud, Fastmail, and Zoho.",
        "capabilities": ["calendar.read", "calendar.write"],
        "config_fields": [
            {"key": "calendar_url", "label": "Calendar URL", "secret": False},
            {"key": "username", "label": "Username", "secret": False},
            {"key": "password", "label": "Password or app password", "secret": True},
        ],
        "linked_module": "crm.activities",
        "docs_hint": "Use the CalDAV collection URL, not the website home page. Apple and most hosts publish it under the account calendar settings.",
    },
    {
        "key": "microsoft_teams",
        "name": "Microsoft Teams · Notifications",
        "category": "messaging",
        "recommended": False,
        "priority": 5,
        "summary": "Adaptive card / webhook alerts for approvals and payroll milestones.",
        "capabilities": ["notify"],
        "config_fields": [
            {"key": "webhook_url", "label": "Incoming webhook URL", "secret": True},
        ],
    },
    {
        "key": "attendance_biometric",
        "name": "Attendance · Biometric devices",
        "category": "hr",
        "recommended": True,
        "priority": 1,
        "summary": "Sync check-in/out from approved biometric terminals.",
        "capabilities": ["attendance.sync", "webhook", "pull"],
        "config_fields": [],
        "linked_module": "hr.attendance",
        "docs_hint": "Manage devices under HR → Attendance → Devices.",
    },
    {
        "key": "smtp_generic",
        "name": "Email · Tenant SMTP",
        "category": "platform",
        "recommended": True,
        "priority": 2,
        "summary": "Generic SMTP for any approved corporate mail system.",
        "capabilities": ["mail.send"],
        "config_fields": [],
        "linked_module": "settings.email",
    },
    {
        "key": "bank_salary_file",
        "name": "Bank · Salary payment file",
        "category": "finance",
        "recommended": False,
        "priority": 6,
        "summary": "Generate bank-compatible salary payment files from approved payroll.",
        "capabilities": ["payroll.bank_file"],
        "config_fields": [
            {"key": "bank_code", "label": "Bank format (UBL/HBL/MCB/Custom)", "secret": False},
            {"key": "company_account", "label": "Company account number", "secret": False},
        ],
        "linked_module": "payroll.payslips",
    },
    {
        "key": "insurance_api",
        "name": "Insurance provider API",
        "category": "hr",
        "recommended": False,
        "priority": 7,
        "summary": "Optional API sync for group medical limits / enrollments.",
        "capabilities": ["hr.benefits", "rest"],
        "config_fields": [
            {"key": "base_url", "label": "API base URL", "secret": False},
            {"key": "api_key", "label": "API key", "secret": True},
        ],
    },
    {
        "key": "webhook_outbound",
        "name": "Outbound webhooks",
        "category": "platform",
        "recommended": False,
        "priority": 8,
        "summary": "Push ERP events (leave approved, payroll paid, invoice posted) to external systems.",
        "capabilities": ["webhook"],
        "config_fields": [
            {"key": "endpoint_url", "label": "HTTPS endpoint", "secret": False},
            {"key": "shared_secret", "label": "HMAC secret", "secret": True},
            {"key": "events", "label": "Event filter (csv)", "secret": False},
        ],
    },
    {
        "key": "rest_openapi",
        "name": "SI-ERP REST / OpenAPI",
        "category": "platform",
        "recommended": False,
        "priority": 8,
        "summary": "First-class REST APIs with JWT for partners and future interfaces.",
        "capabilities": ["api"],
        "config_fields": [],
        "docs_hint": "/api/schema/ swagger/",
    },
    {
        "key": "google_workspace",
        "name": "Google Workspace · Gmail",
        "category": "messaging",
        "recommended": False,
        "priority": 9,
        "summary": "Competitive alternate mail path via Gmail API / SMTP.",
        "capabilities": ["mail.send"],
        "config_fields": [
            {"key": "client_id", "label": "OAuth client ID", "secret": False},
            {"key": "client_secret", "label": "OAuth client secret", "secret": True},
            {"key": "refresh_token", "label": "Refresh token", "secret": True},
            {"key": "sender", "label": "Sender email", "secret": False},
        ],
    },
    {
        "key": "whatsapp_business",
        "name": "WhatsApp Business · Alerts",
        "category": "messaging",
        "recommended": False,
        "priority": 10,
        "summary": "Optional payslip / approval alerts via Meta Cloud API.",
        "capabilities": ["notify"],
        "config_fields": [
            {"key": "phone_number_id", "label": "Phone number ID", "secret": False},
            {"key": "access_token", "label": "Access token", "secret": True},
        ],
    },
    {
        "key": "fbr_iris",
        "name": "FBR / IRIS · Tax assist",
        "category": "finance",
        "recommended": False,
        "priority": 11,
        "summary": "Export-ready challans and WHT statements; portal automation optional phase.",
        "capabilities": ["tax.export"],
        "config_fields": [],
        "linked_module": "finance.tax",
    },
    {
        "key": "excel_onedrive",
        "name": "Microsoft 365 · OneDrive / SharePoint",
        "category": "microsoft",
        "recommended": True,
        "priority": 12,
        "summary": "Save Word, Excel and other Office files into Documents, and store a document back in OneDrive or SharePoint.",
        "capabilities": ["files.read", "files.write"],
        "config_fields": [
            {"key": "tenant_id", "label": "Azure AD Tenant ID", "secret": False},
            {"key": "client_id", "label": "Application (client) ID", "secret": False},
            {"key": "client_secret", "label": "Client secret", "secret": True},
            {"key": "mailbox_upn", "label": "OneDrive mailbox UPN", "secret": False},
            {"key": "drive_path", "label": "Folder path (for example SIERP)", "secret": False},
        ],
        "linked_module": "dms.documents",
        "docs_hint": "App registration with Files.ReadWrite.All (application) and admin consent.",
    },
]


def catalog_by_key(key: str) -> dict | None:
    for item in INTEGRATION_CATALOG:
        if item["key"] == key:
            return item
    return None


def public_catalog() -> list[dict]:
    return [
        {
            "key": i["key"],
            "name": i["name"],
            "category": i["category"],
            "recommended": i.get("recommended", False),
            "priority": i.get("priority", 99),
            "summary": i["summary"],
            "capabilities": i.get("capabilities", []),
            "config_fields": [
                {"key": f["key"], "label": f["label"], "secret": f.get("secret", False)}
                for f in i.get("config_fields", [])
            ],
            "linked_module": i.get("linked_module"),
            "docs_hint": i.get("docs_hint", ""),
        }
        for i in sorted(INTEGRATION_CATALOG, key=lambda x: (x.get("priority", 99), x["name"]))
    ]
