"""Microsoft 365 / Graph helpers for SIERP integrations."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_SEND = "https://graph.microsoft.com/v1.0/users/{user}/sendMail"


def _post_form(url: str, data: dict[str, str], timeout: int = 30) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: dict, token: str, timeout: int = 30) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return exc.code, detail


def acquire_app_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    if not (tenant_id and client_id and client_secret):
        raise ValueError("Microsoft 365 tenant_id, client_id and client_secret are required")
    url = TOKEN_URL.format(tenant=tenant_id.strip())
    data = {
        "client_id": client_id.strip(),
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    result = _post_form(url, data)
    token = result.get("access_token")
    if not token:
        raise ValueError(f"Token response missing access_token: {result}")
    return token


def send_mail_graph(
    *,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    sender_upn: str,
    recipients: list[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> None:
    token = acquire_app_token(tenant_id, client_id, client_secret)
    content_type = "HTML" if body_html else "Text"
    content = body_html if body_html else body_text
    payload: dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {"contentType": content_type, "content": content or ""},
            "toRecipients": [
                {"emailAddress": {"address": r}} for r in recipients if r
            ],
        },
        "saveToSentItems": True,
    }
    url = GRAPH_SEND.format(user=urllib.parse.quote(sender_upn.strip()))
    status, detail = _post_json(url, payload, token)
    if status not in (200, 202):
        raise RuntimeError(f"Graph sendMail failed ({status}): {detail[:400]}")


def list_inbox_messages(token: str, upn: str, limit: int = 15) -> list[dict]:
    """Recent inbox messages. The app registration needs Mail.Read."""
    user = urllib.parse.quote((upn or "").strip())
    if not user:
        raise ValueError("Mailbox address is required")
    top = max(1, min(int(limit or 15), 25))
    url = (
        f"https://graph.microsoft.com/v1.0/users/{user}/mailFolders/inbox/messages"
        f"?$top={top}&$select=id,subject,bodyPreview,from,toRecipients,receivedDateTime,internetMessageId"
    )
    status, raw, _mime = _get(url, token)
    if status != 200:
        detail = raw[:300].decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph inbox failed ({status}): {detail}")
    payload = json.loads(raw.decode("utf-8"))
    rows = []
    for item in payload.get("value") or []:
        sender = ((item.get("from") or {}).get("emailAddress") or {}).get("address") or ""
        tos = []
        for rec in item.get("toRecipients") or []:
            addr = ((rec.get("emailAddress") or {}).get("address") or "").strip()
            if addr:
                tos.append(addr)
        rows.append(
            {
                "message_id": (item.get("internetMessageId") or item.get("id") or "")[:255],
                "subject": (item.get("subject") or "(no subject)")[:255],
                "body": (item.get("bodyPreview") or "")[:8000],
                "from_email": sender[:254],
                "to_emails": ", ".join(tos)[:500],
                "occurred_at": item.get("receivedDateTime") or "",
            }
        )
    return rows


def _get(url: str, token: str, timeout: int = 60) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            mime = resp.headers.get("Content-Type", "")
            return resp.status, resp.read(), mime
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "") if exc.headers else ""


def _put(url: str, token: str, payload: bytes, content_type: str, timeout: int = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type or "application/octet-stream",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _drive_path(folder: str, name: str = "") -> str:
    parts = [
        part
        for part in (folder or "").replace("\\", "/").split("/")
        if part not in ("", ".", "..")
    ]
    if name:
        parts.append(name.replace("/", "_").replace("\\", "_"))
    return "/".join(urllib.parse.quote(part, safe="") for part in parts)


def list_drive_items(token: str, upn: str, folder: str = "") -> list[dict]:
    user = urllib.parse.quote(upn.strip())
    path = _drive_path(folder)
    if path:
        url = (
            f"https://graph.microsoft.com/v1.0/users/{user}/drive/root:/{path}:/children"
            "?$top=200&$select=id,name,size,webUrl,file,folder"
        )
    else:
        url = (
            f"https://graph.microsoft.com/v1.0/users/{user}/drive/root/children"
            "?$top=200&$select=id,name,size,webUrl,file,folder"
        )
    status, raw, _mime = _get(url, token)
    if status != 200:
        raise RuntimeError(f"Graph folder list failed ({status}): {raw[:300].decode('utf-8', errors='replace')}")
    body = json.loads(raw.decode("utf-8"))
    rows = []
    for item in body.get("value") or []:
        if item.get("folder"):
            continue
        rows.append(
            {
                "id": item.get("id") or "",
                "name": item.get("name") or "",
                "size": int(item.get("size") or 0),
                "web_url": item.get("webUrl") or "",
                "mime_type": ((item.get("file") or {}).get("mimeType") or ""),
            }
        )
    return rows


def download_drive_item(token: str, upn: str, item_id: str) -> tuple[bytes, str, str, str]:
    user = urllib.parse.quote(upn.strip())
    item = urllib.parse.quote(item_id.strip(), safe="")
    status, raw, _mime = _get(
        f"https://graph.microsoft.com/v1.0/users/{user}/drive/items/{item}?$select=id,name,size,webUrl,file",
        token,
    )
    if status != 200:
        raise RuntimeError(f"Graph item lookup failed ({status}): {raw[:300].decode('utf-8', errors='replace')}")
    meta = json.loads(raw.decode("utf-8"))
    size = int(meta.get("size") or 0)
    if size > 25 * 1024 * 1024:
        raise ValueError("Microsoft 365 file is larger than 25 MB.")
    status, content, content_type = _get(
        f"https://graph.microsoft.com/v1.0/users/{user}/drive/items/{item}/content",
        token,
    )
    if status != 200:
        raise RuntimeError(
            f"Graph download failed ({status}): {content[:300].decode('utf-8', errors='replace')}"
        )
    name = meta.get("name") or "document"
    mime = ((meta.get("file") or {}).get("mimeType") or content_type or "application/octet-stream")
    mime = mime.split(";")[0][:120]
    return content, name, mime, meta.get("webUrl") or ""


def upload_drive_item(
    token: str,
    upn: str,
    folder: str,
    filename: str,
    content: bytes,
    mime: str,
) -> dict:
    if len(content) > 25 * 1024 * 1024:
        raise ValueError("Document is larger than 25 MB.")
    if len(content) > 4 * 1024 * 1024:
        raise ValueError("Microsoft 365 simple upload supports files up to 4 MB.")
    user = urllib.parse.quote(upn.strip())
    path = _drive_path(folder or "SIERP", filename or "document")
    url = f"https://graph.microsoft.com/v1.0/users/{user}/drive/root:/{path}:/content"
    status, raw = _put(url, token, content, mime or "application/octet-stream")
    if status not in (200, 201):
        raise RuntimeError(f"Graph upload failed ({status}): {raw[:300].decode('utf-8', errors='replace')}")
    saved = json.loads(raw.decode("utf-8"))
    return {
        "id": saved.get("id") or "",
        "name": saved.get("name") or filename,
        "web_url": saved.get("webUrl") or "",
    }


def test_connection(config: dict, secrets: dict) -> tuple[bool, str]:
    """Validate credentials by acquiring a token (does not send mail)."""
    try:
        tenant = (config or {}).get("tenant_id") or ""
        client_id = (config or {}).get("client_id") or ""
        secret = (secrets or {}).get("client_secret") or ""
        acquire_app_token(tenant, client_id, secret)
        sender = (config or {}).get("sender_upn") or ""
        if not sender:
            return True, "Token OK — set sender mailbox UPN before sending mail"
        return True, f"Microsoft Graph token OK for tenant; sender={sender}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("m365 test failed: %s", exc)
        return False, str(exc)[:400]
