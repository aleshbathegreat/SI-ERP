"""Starter email templates. One generalized message per area, shared placeholders."""

from __future__ import annotations

PLACEHOLDERS = (
    "{{organization}}",
    "{{recipient}}",
    "{{title}}",
    "{{message}}",
    "{{reference}}",
    "{{due_date}}",
    "{{link}}",
)


def _text(intro: str) -> str:
    return (
        "Hello {{recipient}},\n\n"
        f"{intro}\n\n"
        "Reference: {{reference}}\n"
        "Due: {{due_date}}\n\n"
        "{{message}}\n\n"
        "{{link}}\n\n"
        "{{organization}}"
    )


def _html(intro: str) -> str:
    return (
        "<p>Hello {{recipient}},</p>"
        f"<p>{intro}</p>"
        "<p>Reference: {{reference}}<br>Due: {{due_date}}</p>"
        "<p>{{message}}</p>"
        "<p><a href=\"{{link}}\">{{link}}</a></p>"
        "<p>{{organization}}</p>"
    )


def _row(code: str, name: str, purpose: str, intro: str) -> dict:
    return {
        "code": code,
        "name": name,
        "purpose": purpose,
        "subject": "{{title}}",
        "body_text": _text(intro),
        "body_html": _html(intro),
        "is_active": True,
    }


DEFAULT_EMAIL_TEMPLATES = [
    _row(
        "general_message",
        "General message",
        "general",
        "This is a message from {{organization}}.",
    ),
    _row(
        "action_required",
        "Action required",
        "workflow",
        "Please review {{reference}} and take the next step.",
    ),
    _row(
        "hr_notice",
        "HR notice",
        "hr",
        "This notice is from the HR team at {{organization}}.",
    ),
    _row(
        "finance_notice",
        "Finance notice",
        "finance",
        "This notice is about a finance record at {{organization}}.",
    ),
    _row(
        "payroll_notice",
        "Payroll notice",
        "payroll",
        "This notice is about payroll at {{organization}}.",
    ),
    _row(
        "billing_notice",
        "Billing notice",
        "billing",
        "This notice is about billing at {{organization}}.",
    ),
    _row(
        "sales_message",
        "Sales message",
        "sales",
        "Thank you for your interest in {{organization}}.",
    ),
    _row(
        "procurement_message",
        "Procurement message",
        "procurement",
        "This message is about a purchase at {{organization}}.",
    ),
]


def ensure_default_email_templates(organization) -> list[str]:
    """Create any missing starter templates. Leave edited or removed ones alone."""
    if organization is None:
        return []
    from core.models import EmailTemplate

    created: list[str] = []
    for row in DEFAULT_EMAIL_TEMPLATES:
        if EmailTemplate.all_objects.filter(organization=organization, code=row["code"]).exists():
            continue
        EmailTemplate.objects.create(organization=organization, **row)
        created.append(row["code"])
    return created
