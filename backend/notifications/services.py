"""Write in-app notices. Email stays in core.notifications."""

from __future__ import annotations

RECORD_ROUTES = {
    "dms.documents": "/dms/documents",
    "finance.journals": "/finance/journals",
    "finance.budgets": "/finance/budgets",
    "finance.invoices": "/finance/invoices",
    "sales.invoices": "/sales/invoices",
    "sales.orders": "/sales/orders",
    "procurement.requisitions": "/procurement/requisitions",
    "procurement.orders": "/procurement/orders",
    "hr.leaves": "/hr/leaves",
    "hr.recruitment": "/hr/recruitment",
    "hr.performance": "/hr/performance",
    "payroll.periods": "/payroll/periods",
    "payroll.loans": "/payroll/loans",
    "projects.timesheets": "/projects/timesheets",
}


def record_href(module: str, object_id) -> str:
    base = RECORD_ROUTES.get(module or "")
    if not base or object_id in (None, ""):
        return "/inbox"
    return f"{base}/{object_id}"


def push_inbox(organization, users, title, body, href="", module="", object_id="", kind="workflow") -> int:
    if organization is None:
        return 0
    from notifications.models import InboxMessage

    seen = set()
    rows = []
    link = (href or record_href(module, object_id) or "/inbox")[:255]
    for user in users:
        if user is None or getattr(user, "id", None) in seen:
            continue
        seen.add(user.id)
        rows.append(
            InboxMessage(
                organization=organization,
                recipient=user,
                title=(title or "Notice")[:180],
                body=body or "",
                href=link,
                module=(module or "")[:64],
                object_id=str(object_id or "")[:64],
                kind=(kind or "workflow")[:20],
            )
        )
    if rows:
        InboxMessage.objects.bulk_create(rows)
    return len(rows)
