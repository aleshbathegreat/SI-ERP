"""Header inbox — support tickets, billing alerts, with read/unread state."""

from __future__ import annotations

from datetime import date, datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import (
    days_until_lock,
    effective_end_date,
    subscription_in_grace,
    subscription_open,
    user_organization,
)
from core.models import NotificationRead, SaaSInvoice, SupportTicket
from core.platform_rbac import has_platform_cap, is_platform_user


def _stamp_dt(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _collect_items(user) -> list[dict]:
    items: list[dict] = []
    org = user_organization(user)

    if is_platform_user(user) and has_platform_cap(user, "tickets"):
        qs = (
            SupportTicket.objects.exclude(status__in=["resolved", "closed"])
            .select_related("organization")
            .order_by("-updated_at")[:12]
        )
        for t in qs:
            stamp = _stamp_dt(t.last_message_at or t.updated_at)
            items.append(
                {
                    "id": f"ticket-{t.id}",
                    "kind": "support",
                    "title": t.subject,
                    "body": f"{t.ticket_no} · {t.organization.name} · {t.status}",
                    "href": "/platform/tickets",
                    "created_at": stamp or None,
                    "source_stamp": stamp,
                    "severity": t.priority,
                    "meta": {"ticket_id": t.id, "status": t.status},
                }
            )

    if is_platform_user(user) and has_platform_cap(user, "invoices"):
        unpaid = (
            SaaSInvoice.objects.filter(status__in=["sent", "overdue"])
            .select_related("organization")
            .order_by("-id")[:8]
        )
        for inv in unpaid:
            stamp = _stamp_dt(inv.updated_at)
            items.append(
                {
                    "id": f"invoice-{inv.id}",
                    "kind": "billing",
                    "title": f"Invoice {inv.invoice_no}",
                    "body": f"{inv.organization.name} · {inv.total} {inv.currency} · {inv.status}",
                    "href": "/platform/invoices",
                    "created_at": stamp or None,
                    "source_stamp": stamp,
                    "severity": "high" if inv.status == "overdue" else "normal",
                    "meta": {"invoice_id": inv.id},
                }
            )

    if org:
        tqs = (
            SupportTicket.objects.filter(organization=org)
            .exclude(status__in=["resolved", "closed"])
            .order_by("-updated_at")[:10]
        )
        for t in tqs:
            waiting = t.status == SupportTicket.Status.WAITING
            stamp = _stamp_dt(t.last_message_at or t.updated_at)
            items.append(
                {
                    "id": f"ticket-{t.id}",
                    "kind": "support",
                    "title": t.subject,
                    "body": (
                        f"{t.ticket_no} · platform replied — your turn"
                        if waiting
                        else f"{t.ticket_no} · {t.status}"
                    ),
                    "href": "/support",
                    "created_at": stamp or None,
                    "source_stamp": stamp,
                    "severity": "high" if waiting else t.priority,
                    "meta": {"ticket_id": t.id, "status": t.status},
                }
            )

        end = effective_end_date(org)
        today = date.today()
        days_to_end = (end - today).days if end else None
        is_trial = org.plan == "trial"
        kind_label = "Trial" if is_trial else "Subscription"

        if end and days_to_end is not None and 0 <= days_to_end <= 7 and subscription_open(org):
            stamp = f"prewarn:{org.plan}:{end}:{days_to_end}"
            items.append(
                {
                    "id": f"sub-prewarn-{org.id}",
                    "kind": "billing",
                    "title": (
                        f"{kind_label} ends today"
                        if days_to_end == 0
                        else f"{kind_label} ends in {days_to_end} day(s)"
                    ),
                    "body": (
                        f"Period end {end.isoformat()}. Renew on Billing to keep access."
                    ),
                    "href": "/billing",
                    "created_at": None,
                    "source_stamp": stamp,
                    "priority": "urgent" if days_to_end <= 1 else "high",
                    "meta": {"days_to_end": days_to_end},
                }
            )

        if subscription_in_grace(org) or not subscription_open(org):
            days = days_until_lock(org)
            stamp = (
                f"{org.plan_status}:{org.subscription_ends}:{org.trial_ends}:"
                f"{'open' if subscription_open(org) else 'closed'}"
            )
            items.append(
                {
                    "id": f"sub-{org.id}",
                    "kind": "billing",
                    "title": (
                        f"{kind_label} locked"
                        if not subscription_open(org)
                        else f"{kind_label} in grace period"
                    ),
                    "body": (
                        "Renew on Billing to reopen the ERP."
                        if not subscription_open(org)
                        else f"Access remains open for {days if days is not None else 'a few'} more day(s)."
                    ),
                    "href": "/billing",
                    "created_at": None,
                    "source_stamp": stamp,
                    "priority": "urgent" if not subscription_open(org) else "high",
                    "meta": {},
                }
            )

    try:
        from notifications.models import InboxMessage

        for msg in InboxMessage.objects.filter(recipient=user).order_by("-id")[:12]:
            stamp = _stamp_dt(msg.created_at)
            items.append(
                {
                    "id": f"inbox-{msg.id}",
                    "kind": msg.kind or "workflow",
                    "title": msg.title,
                    "body": msg.body,
                    "href": msg.href or "/inbox",
                    "created_at": stamp or None,
                    "source_stamp": stamp,
                    "severity": "normal",
                    "meta": {"inbox_id": msg.id},
                }
            )
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        unique.append(it)
    return unique


def _apply_read_state(user, items: list[dict]) -> list[dict]:
    keys = [it["id"] for it in items]
    reads = {
        r.key: r.source_stamp
        for r in NotificationRead.objects.filter(user=user, key__in=keys)
    }
    for it in items:
        stamped = it.get("source_stamp") or ""
        saved = reads.get(it["id"])
        it["read"] = bool(saved is not None and saved == stamped)
    return items


def _sort_items(items: list[dict]) -> list[dict]:
    rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    def _ts(value: str | None) -> float:
        if not value:
            return 0.0
        try:
            return datetime.fromisoformat(value.replace("Z", "")).timestamp()
        except Exception:
            return 0.0

    # Unread first, then severity, then newest
    items.sort(
        key=lambda x: (
            0 if not x.get("read") else 1,
            rank.get(x.get("severity") or "normal", 2),
            -_ts(x.get("created_at")),
        )
    )
    return items


def _mark_keys(user, pairs: list[tuple[str, str]]) -> int:
    """pairs = [(key, source_stamp), ...]"""
    n = 0
    for key, stamp in pairs:
        if not key:
            continue
        NotificationRead.objects.update_or_create(
            user=user,
            key=key[:64],
            defaults={"source_stamp": (stamp or "")[:64]},
        )
        n += 1
        if key.startswith("inbox-") and key[6:].isdigit():
            from django.utils import timezone

            from notifications.models import InboxMessage

            InboxMessage.objects.filter(
                recipient=user, id=int(key[6:]), read_at__isnull=True
            ).update(read_at=timezone.now())
    return n


class NotificationsInboxView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        items = _apply_read_state(request.user, _collect_items(request.user))
        items = _sort_items(items)[:20]
        unread = sum(1 for it in items if not it.get("read"))
        return Response(
            {
                "count": len(items),
                "unread": unread,
                "items": items,
            }
        )

    def post(self, request):
        """
        Mark notifications read.
        Body: { "ids": ["ticket-1", ...], "all": false }
          or  { "all": true }
        """
        mark_all = bool(request.data.get("all"))
        ids = request.data.get("ids") or []
        if not isinstance(ids, list):
            ids = []

        current = {it["id"]: it for it in _collect_items(request.user)}
        pairs: list[tuple[str, str]] = []

        if mark_all:
            pairs = [(it["id"], it.get("source_stamp") or "") for it in current.values()]
        else:
            for nid in ids:
                key = str(nid)
                it = current.get(key)
                if it:
                    pairs.append((key, it.get("source_stamp") or ""))
                else:
                    # Still record read for stale/gone items
                    pairs.append((key, request.data.get("source_stamp") or ""))

        marked = _mark_keys(request.user, pairs)
        items = _apply_read_state(request.user, list(current.values()))
        items = _sort_items(items)[:20]
        unread = sum(1 for it in items if not it.get("read"))
        return Response(
            {
                "ok": True,
                "marked": marked,
                "count": len(items),
                "unread": unread,
                "items": items,
            }
        )


class NotificationMarkReadView(APIView):
    """POST /api/notifications/mark-read/ — alias for inbox POST."""

    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def post(self, request):
        return NotificationsInboxView().post(request)
