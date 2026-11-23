"""Send, receive, and track tenant mailbox mail. SIERP keeps the log."""

from __future__ import annotations

import email
import imaplib
import logging
import re
import uuid
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.access import is_owner, user_organization
from core.mailer import _smtp_send
from core.models import MailMessage, TenantEmailProfile, TenantSmtpSettings

logger = logging.getLogger(__name__)

_ADDR_SPLIT = re.compile(r"[,;]")


def usable_profiles(user):
    org = user_organization(user)
    if org is None:
        return TenantEmailProfile.objects.none()
    qs = TenantEmailProfile.objects.filter(organization=org, is_active=True).select_related(
        "user", "employee"
    )
    if is_owner(user):
        return qs
    return qs.filter(
        Q(owner_type=TenantEmailProfile.OwnerType.SHARED)
        | Q(user=user)
        | Q(employee__user=user)
    )


def split_addresses(raw: str) -> list[str]:
    seen = []
    for part in _ADDR_SPLIT.split(raw or ""):
        addr = part.strip()
        if addr and addr not in seen:
            seen.append(addr)
    return seen


def _with_signature(profile, body: str) -> str:
    text = body or ""
    signature = (profile.signature or "").strip()
    if signature and signature not in text:
        text = f"{text.rstrip()}\n\n-- \n{signature}"
    return text


def deliver_profile_mail(profile, subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """Send as this mailbox. Microsoft 365 first, then the tenant SMTP. No platform fallback."""
    org = profile.organization
    graph_error = ""
    try:
        from integrations.services import send_via_m365_as

        if send_via_m365_as(org, profile.email, subject, body, recipients, None):
            return True, ""
    except Exception as exc:  # noqa: BLE001
        graph_error = str(exc)[:400]
        logger.warning("mailbox graph send failed: %s", graph_error)

    smtp = TenantSmtpSettings.objects.filter(organization=org).first()
    if smtp and smtp.is_active and smtp.host and profile.email:
        try:
            _smtp_send(
                host=smtp.host,
                port=smtp.port,
                username=smtp.username,
                password=smtp.password,
                use_tls=smtp.use_tls,
                use_ssl=smtp.use_ssl,
                from_email=profile.email,
                from_name=profile.name,
                reply_to=profile.reply_to or smtp.reply_to,
                recipients=recipients,
                subject=subject,
                body=body,
            )
            return True, ""
        except Exception as exc:  # noqa: BLE001
            smtp_error = str(exc)[:400]
            joined = "; ".join(part for part in (graph_error, smtp_error) if part)
            return False, joined or "Send failed"
    if graph_error:
        return False, graph_error
    return False, "Turn on Microsoft 365 mail or tenant SMTP before sending."


def _log_activity(org, user, lead, opportunity, subject: str, description: str, outcome: str):
    if not lead and not opportunity:
        return
    from crm.models import Activity

    Activity.objects.create(
        organization=org,
        lead=lead,
        opportunity=opportunity,
        type=Activity.Type.EMAIL,
        subject=(subject or "Email")[:255],
        description=description[:4000],
        done=True,
        completed_at=timezone.now(),
        outcome=outcome[:255],
        owner=user,
        created_by=user,
    )


def record_outbound(profile, user, subject: str, body: str, recipients: list[str], lead=None, opportunity=None):
    text = _with_signature(profile, body)
    ok, error = deliver_profile_mail(profile, subject, text, recipients)
    message = MailMessage.objects.create(
        organization=profile.organization,
        profile=profile,
        direction=MailMessage.Direction.OUT,
        status=MailMessage.Status.SENT if ok else MailMessage.Status.FAILED,
        subject=subject[:255],
        body=text[:8000],
        from_email=profile.email,
        to_emails=", ".join(recipients)[:500],
        message_id=f"<sierp.{uuid.uuid4().hex}@si-erp.mushaz.com>",
        error=error,
        lead=lead,
        opportunity=opportunity,
        occurred_at=timezone.now(),
        created_by=user,
    )
    if ok:
        _log_activity(
            profile.organization,
            user,
            lead,
            opportunity,
            subject,
            f"To {message.to_emails}\n\n{text[:2000]}",
            "Sent",
        )
    return message


def _decode_header(value) -> str:
    if not value:
        return ""
    chunks = []
    for text, enc in decode_header(value):
        if isinstance(text, bytes):
            chunks.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            chunks.append(text)
    return "".join(chunks).strip()


def _plain_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != "text/plain":
                continue
            if "attachment" in (part.get("Content-Disposition") or "").lower():
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")[:8000]
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")[:8000]


def _when(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value).replace("Z", "+00:00"))
        if parsed is None:
            try:
                parsed = parsedate_to_datetime(str(value))
            except (TypeError, ValueError, IndexError):
                parsed = None
    if parsed is None:
        return timezone.now()
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def pull_graph(profile, limit: int = 15) -> list[dict]:
    from integrations.microsoft365 import acquire_app_token, list_inbox_messages
    from integrations.services import get_active_m365_mail

    conn = get_active_m365_mail(profile.organization)
    if not conn:
        raise ValueError(
            "Turn on Microsoft 365 mail under Settings → Integrations. Inbox copy needs Mail.Read."
        )
    cfg = conn.config or {}
    secrets = conn.secrets or {}
    token = acquire_app_token(
        cfg.get("tenant_id", ""),
        cfg.get("client_id", ""),
        secrets.get("client_secret", ""),
    )
    return list_inbox_messages(token, profile.email, limit)


def pull_imap(profile, limit: int = 15) -> list[dict]:
    host = (profile.imap_host or "").strip()
    if not host:
        raise ValueError("IMAP host is required.")
    port = int(profile.imap_port or (993 if profile.imap_use_ssl else 143))
    client_cls = imaplib.IMAP4_SSL if profile.imap_use_ssl else imaplib.IMAP4
    client = client_cls(host, port, timeout=20)
    try:
        user = profile.imap_username or profile.email
        client.login(user, profile.imap_password or "")
        client.select("INBOX", readonly=True)
        status, data = client.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()[-max(1, min(limit, 25)) :]
        rows = []
        for num in reversed(ids):
            fetched = client.fetch(num, "(RFC822.PEEK)")
            if fetched[0] != "OK":
                continue
            raw = b""
            for item in fetched[1] or []:
                if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], (bytes, bytearray)):
                    raw = bytes(item[1])
                    break
            if not raw:
                continue
            if len(raw) > 120000:
                raw = raw[:120000]
            parsed = email.message_from_bytes(raw)
            from_list = email.utils.getaddresses([parsed.get("From") or ""])
            to_list = email.utils.getaddresses([parsed.get("To") or ""])
            rows.append(
                {
                    "message_id": (_decode_header(parsed.get("Message-ID")) or f"imap:{num.decode()}")[:255],
                    "subject": (_decode_header(parsed.get("Subject")) or "(no subject)")[:255],
                    "body": _plain_body(parsed),
                    "from_email": (from_list[0][1] if from_list else "")[:254],
                    "to_emails": ", ".join(addr for _, addr in to_list if addr)[:500],
                    "occurred_at": parsed.get("Date") or "",
                }
            )
        return rows
    finally:
        try:
            client.logout()
        except Exception:
            pass


def pull_inbox(profile, limit: int = 15) -> list[dict]:
    if profile.inbound == TenantEmailProfile.Inbound.GRAPH:
        return pull_graph(profile, limit)
    if profile.inbound == TenantEmailProfile.Inbound.IMAP:
        return pull_imap(profile, limit)
    raise ValueError("This mailbox is send-only. Choose Microsoft 365 inbox or IMAP to receive mail.")


def _match_lead(org, from_email: str):
    if not from_email:
        return None, None
    from crm.models import Lead, Opportunity

    lead = (
        Lead.objects.filter(organization=org, email__iexact=from_email).order_by("-id").first()
    )
    if not lead:
        return None, None
    opportunity = (
        Opportunity.objects.filter(organization=org, lead=lead)
        .exclude(stage=Opportunity.Stage.LOST)
        .order_by("-id")
        .first()
    )
    return lead, opportunity


def store_inbound(profile, rows: list[dict], user) -> tuple[int, int]:
    imported = 0
    skipped = 0
    org = profile.organization
    for row in rows:
        message_id = (row.get("message_id") or "").strip()[:255]
        if message_id and MailMessage.objects.filter(organization=org, message_id=message_id).exists():
            skipped += 1
            continue
        from_email = (row.get("from_email") or "").strip()[:254]
        lead, opportunity = _match_lead(org, from_email)
        subject = (row.get("subject") or "(no subject)")[:255]
        body = (row.get("body") or "")[:8000]
        MailMessage.objects.create(
            organization=org,
            profile=profile,
            direction=MailMessage.Direction.IN,
            status=MailMessage.Status.RECEIVED,
            subject=subject,
            body=body,
            from_email=from_email,
            to_emails=(row.get("to_emails") or profile.email)[:500],
            message_id=message_id,
            lead=lead,
            opportunity=opportunity,
            occurred_at=_when(row.get("occurred_at")),
            created_by=user,
        )
        _log_activity(
            org,
            user,
            lead,
            opportunity,
            subject,
            f"From {from_email}\n\n{body[:2000]}",
            "Received",
        )
        imported += 1
    return imported, skipped
