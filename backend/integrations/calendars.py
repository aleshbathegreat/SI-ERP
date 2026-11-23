"""Copy a CRM activity to every calendar the tenant has switched on.

SIERP remains the record. Microsoft 365, Google, and CalDAV each receive a copy.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, time, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from integrations.microsoft365 import acquire_app_token
from integrations.models import IntegrationConnection

logger = logging.getLogger(__name__)

CALENDAR_KEYS = ("microsoft365_calendar", "google_calendar", "caldav_calendar")
LABELS = {
    "microsoft365_calendar": "Microsoft 365",
    "google_calendar": "Google Calendar",
    "caldav_calendar": "CalDAV",
}
APP_URL = "https://si-erp.mushaz.com"


def active_calendar_connections(organization):
    return IntegrationConnection.objects.filter(
        organization=organization,
        connector_key__in=CALENDAR_KEYS,
        is_enabled=True,
        status=IntegrationConnection.Status.ACTIVE,
    )


def _local(moment: datetime) -> datetime:
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment, timezone.get_current_timezone())
    return timezone.localtime(moment)


def _span(activity):
    """Return (all_day, start, end) or None when the activity has no date."""
    tz = timezone.get_current_timezone()
    if activity.starts_at:
        start = _local(activity.starts_at)
        end = _local(activity.ends_at) if activity.ends_at else start + timedelta(minutes=30)
        if end <= start:
            end = start + timedelta(minutes=30)
        return False, start, end
    if activity.due_date:
        start = timezone.make_aware(datetime.combine(activity.due_date, time.min), tz)
        return True, start, start + timedelta(days=1)
    return None


def _title(activity) -> str:
    prefix = "[Done] " if activity.done else ""
    return f"{prefix}{activity.subject}"[:255]


def _body(activity) -> str:
    lines = [f"Type: {activity.get_type_display()}"]
    if activity.location:
        lines.append(f"Location: {activity.location}")
    if getattr(activity, "lead_id", None) and activity.lead_id:
        lines.append(f"Lead: {activity.lead.name}")
    if getattr(activity, "opportunity_id", None) and activity.opportunity_id:
        lines.append(f"Opportunity: {activity.opportunity.name}")
    if activity.description:
        lines.append(activity.description.strip())
    if activity.outcome:
        lines.append(f"Outcome: {activity.outcome}")
    lines.append(f"Open in SI-ERP: {APP_URL}/crm/activities/{activity.pk}")
    return "\n".join(lines)


def _stamp(moment: datetime) -> str:
    utc = moment.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _ics(activity, uid: str) -> str:
    span = _span(activity)
    if span is None:
        raise ValueError("Activity has no date")
    all_day, start, end = span
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SIERP//CRM//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"SUMMARY:{_title(activity).replace(chr(10), ' ')}",
    ]
    if activity.location:
        lines.append(f"LOCATION:{activity.location.replace(chr(10), ' ')}")
    description = _body(activity).replace("\n", "\\n")
    lines.append(f"DESCRIPTION:{description}")
    if all_day:
        lines.append(f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}")
    else:
        lines.append(f"DTSTART:{_stamp(start)}")
        lines.append(f"DTEND:{_stamp(end)}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return "\r\n".join(lines)


def _request(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 25):
    req = Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code in (404, 410):
            return exc.code, detail.encode("utf-8")
        raise ValueError(f"{method} {url} failed ({exc.code}): {detail[:300]}") from exc
    except URLError as exc:
        raise ValueError(f"Could not reach {url}: {exc.reason}") from exc


def _json_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _graph_token(conn: IntegrationConnection) -> tuple[str, str]:
    cfg = conn.config or {}
    secrets = conn.secrets or {}
    upn = (cfg.get("calendar_upn") or "").strip()
    token = acquire_app_token(
        cfg.get("tenant_id", ""),
        cfg.get("client_id", ""),
        secrets.get("client_secret", ""),
    )
    if not upn:
        raise ValueError("Calendar mailbox UPN is required")
    return token, upn


def test_microsoft_calendar(conn: IntegrationConnection) -> tuple[bool, str]:
    try:
        token, upn = _graph_token(conn)
        status, raw = _request(
            "GET",
            f"https://graph.microsoft.com/v1.0/users/{quote(upn)}/calendar?$select=id,name",
            headers=_json_headers(token),
        )
        if status >= 400:
            return False, raw.decode("utf-8", errors="replace")[:300]
        name = json.loads(raw.decode("utf-8") or "{}").get("name") or upn
        return True, f"Outlook calendar ready: {name}"
    except Exception as exc:
        return False, str(exc)[:300]


def _google_token(conn: IntegrationConnection) -> tuple[str, str]:
    cfg = conn.config or {}
    secrets = conn.secrets or {}
    calendar_id = (cfg.get("calendar_id") or "primary").strip() or "primary"
    status, raw = _request(
        "POST",
        "https://oauth2.googleapis.com/token",
        data=(
            "grant_type=refresh_token"
            f"&client_id={quote(cfg.get('client_id') or '')}"
            f"&client_secret={quote(secrets.get('client_secret') or '')}"
            f"&refresh_token={quote(secrets.get('refresh_token') or '')}"
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload = json.loads(raw.decode("utf-8") or "{}")
    token = payload.get("access_token")
    if status >= 400 or not token:
        raise ValueError(payload.get("error_description") or payload.get("error") or "Google token failed")
    return token, calendar_id


def test_google_calendar(conn: IntegrationConnection) -> tuple[bool, str]:
    try:
        token, calendar_id = _google_token(conn)
        status, raw = _request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}",
            headers=_json_headers(token),
        )
        if status >= 400:
            return False, raw.decode("utf-8", errors="replace")[:300]
        name = json.loads(raw.decode("utf-8") or "{}").get("summary") or calendar_id
        return True, f"Google calendar ready: {name}"
    except Exception as exc:
        return False, str(exc)[:300]


def _caldav_auth(conn: IntegrationConnection) -> tuple[str, str]:
    import base64

    cfg = conn.config or {}
    secrets = conn.secrets or {}
    url = (cfg.get("calendar_url") or "").strip()
    if not url.startswith("https://"):
        raise ValueError("Calendar URL must start with https://")
    user = cfg.get("username") or ""
    password = secrets.get("password") or ""
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return url.rstrip("/"), token


def test_caldav_calendar(conn: IntegrationConnection) -> tuple[bool, str]:
    try:
        url, token = _caldav_auth(conn)
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop><d:displayname/></d:prop></d:propfind>'
        ).encode("utf-8")
        status, _raw = _request(
            "PROPFIND",
            url,
            data=body,
            headers={
                "Authorization": f"Basic {token}",
                "Depth": "0",
                "Content-Type": "application/xml; charset=utf-8",
            },
        )
        if status not in (200, 207):
            return False, f"CalDAV server returned {status}"
        return True, "CalDAV calendar ready"
    except Exception as exc:
        return False, str(exc)[:300]


def _graph_payload(activity) -> dict:
    all_day, start, end = _span(activity)
    zone = settings.TIME_ZONE
    wall = "%Y-%m-%dT%H:%M:%S"
    return {
        "subject": _title(activity),
        "body": {"contentType": "Text", "content": _body(activity)},
        "location": {"displayName": activity.location or ""},
        "isAllDay": all_day,
        "start": {"dateTime": start.strftime(wall), "timeZone": zone},
        "end": {"dateTime": end.strftime(wall), "timeZone": zone},
    }


def _upsert_microsoft(conn, activity, ref: dict | None) -> dict:
    token, upn = _graph_token(conn)
    payload = json.dumps(_graph_payload(activity)).encode("utf-8")
    event_id = (ref or {}).get("id")
    base = f"https://graph.microsoft.com/v1.0/users/{quote(upn)}/events"
    if event_id:
        status, raw = _request("PATCH", f"{base}/{quote(event_id)}", data=payload, headers=_json_headers(token))
        if status == 404:
            event_id = None
        else:
            return {"id": event_id}
    status, raw = _request("POST", base, data=payload, headers=_json_headers(token))
    created = json.loads(raw.decode("utf-8") or "{}")
    if status >= 400 or not created.get("id"):
        raise ValueError(created.get("error", {}).get("message") or "Microsoft calendar did not return an event")
    return {"id": created["id"]}


def _google_payload(activity) -> dict:
    all_day, start, end = _span(activity)
    zone = settings.TIME_ZONE
    if all_day:
        start_block = {"date": start.date().isoformat()}
        end_block = {"date": end.date().isoformat()}
    else:
        start_block = {"dateTime": start.isoformat(), "timeZone": zone}
        end_block = {"dateTime": end.isoformat(), "timeZone": zone}
    return {
        "summary": _title(activity),
        "description": _body(activity),
        "location": activity.location or "",
        "start": start_block,
        "end": end_block,
    }


def _upsert_google(conn, activity, ref: dict | None) -> dict:
    token, calendar_id = _google_token(conn)
    payload = json.dumps(_google_payload(activity)).encode("utf-8")
    event_id = (ref or {}).get("id")
    base = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}/events"
    if event_id:
        status, _raw = _request(
            "PATCH",
            f"{base}/{quote(event_id)}",
            data=payload,
            headers=_json_headers(token),
        )
        if status != 404:
            return {"id": event_id}
    status, raw = _request("POST", base, data=payload, headers=_json_headers(token))
    created = json.loads(raw.decode("utf-8") or "{}")
    if status >= 400 or not created.get("id"):
        raise ValueError(created.get("error", {}).get("message") or "Google calendar did not return an event")
    return {"id": created["id"]}


def _upsert_caldav(conn, activity, ref: dict | None) -> dict:
    url, token = _caldav_auth(conn)
    href = (ref or {}).get("href") or f"{url}/sierp-{activity.pk}-{uuid.uuid4().hex[:8]}.ics"
    uid = (ref or {}).get("uid") or f"sierp-activity-{activity.pk}@si-erp.mushaz.com"
    body = _ics(activity, uid).encode("utf-8")
    _request(
        "PUT",
        href,
        data=body,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "text/calendar; charset=utf-8",
        },
    )
    return {"href": href, "uid": uid}


def _delete_remote(conn, ref: dict | None) -> None:
    if not ref:
        return
    key = conn.connector_key
    if key == "microsoft365_calendar" and ref.get("id"):
        token, upn = _graph_token(conn)
        _request(
            "DELETE",
            f"https://graph.microsoft.com/v1.0/users/{quote(upn)}/events/{quote(ref['id'])}",
            headers=_json_headers(token),
        )
    elif key == "google_calendar" and ref.get("id"):
        token, calendar_id = _google_token(conn)
        _request(
            "DELETE",
            f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}/events/{quote(ref['id'])}",
            headers=_json_headers(token),
        )
    elif key == "caldav_calendar" and ref.get("href"):
        _url, token = _caldav_auth(conn)
        _request("DELETE", ref["href"], headers={"Authorization": f"Basic {token}"})


def _upsert(conn, activity, ref):
    if conn.connector_key == "microsoft365_calendar":
        return _upsert_microsoft(conn, activity, ref)
    if conn.connector_key == "google_calendar":
        return _upsert_google(conn, activity, ref)
    if conn.connector_key == "caldav_calendar":
        return _upsert_caldav(conn, activity, ref)
    return ref


def sync_activity_calendars(activity) -> None:
    """Push, update, or remove this activity on each active external calendar."""
    links = dict(activity.external_events or {})
    changed = False
    remove = bool(activity.is_deleted) or _span(activity) is None
    for conn in active_calendar_connections(activity.organization):
        current = links.get(conn.connector_key)
        try:
            if remove:
                if current:
                    _delete_remote(conn, current)
                    links.pop(conn.connector_key, None)
                    changed = True
            else:
                updated = _upsert(conn, activity, current)
                if updated != current:
                    links[conn.connector_key] = updated
                    changed = True
        except Exception as exc:
            logger.exception("calendar sync failed for %s activity %s", conn.connector_key, activity.pk)
            conn.last_error = str(exc)[:1000]
            conn.last_test_message = str(exc)[:500]
            conn.last_test_ok = False
            conn.save(update_fields=["last_error", "last_test_message", "last_test_ok", "updated_at"])
    if changed:
        type(activity).all_objects.filter(pk=activity.pk).update(external_events=links)
        activity.external_events = links
