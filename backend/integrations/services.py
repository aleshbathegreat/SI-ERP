"""Connector test / send dispatch."""

from __future__ import annotations

from django.utils import timezone

from integrations.catalog import catalog_by_key
from integrations.microsoft365 import send_mail_graph, test_connection as m365_test
from integrations.models import IntegrationConnection


def get_active_m365_mail(organization) -> IntegrationConnection | None:
    return (
        IntegrationConnection.objects.filter(
            organization=organization,
            connector_key="microsoft365_mail",
            is_enabled=True,
            status=IntegrationConnection.Status.ACTIVE,
        ).first()
    )


def send_via_m365_as(organization, sender_upn, subject: str, body: str, recipients: list[str], html: str | None):
    conn = get_active_m365_mail(organization)
    if not conn or not (sender_upn or "").strip():
        return False
    cfg = conn.config or {}
    secrets = conn.secrets or {}
    send_mail_graph(
        tenant_id=cfg.get("tenant_id", ""),
        client_id=cfg.get("client_id", ""),
        client_secret=secrets.get("client_secret", ""),
        sender_upn=sender_upn.strip(),
        recipients=recipients,
        subject=subject,
        body_text=body,
        body_html=html,
    )
    return True


def send_via_m365(organization, subject: str, body: str, recipients: list[str], html: str | None):
    conn = get_active_m365_mail(organization)
    if not conn:
        return False
    return send_via_m365_as(
        organization,
        (conn.config or {}).get("sender_upn", ""),
        subject,
        body,
        recipients,
        html,
    )


def test_connector(conn: IntegrationConnection) -> IntegrationConnection:
    meta = catalog_by_key(conn.connector_key)
    ok = False
    message = "Not implemented"
    if conn.connector_key == "microsoft365_mail":
        ok, message = m365_test(conn.config or {}, conn.secrets or {})
    elif conn.connector_key in ("microsoft365_smtp", "smtp_generic"):
        ok, message = True, "Use Settings → Email SMTP to configure and send a test message."
    elif conn.connector_key == "attendance_biometric":
        from hr.models import AttendanceDevice

        n = AttendanceDevice.objects.filter(organization_id=conn.organization_id).count()
        ok = True
        message = f"Attendance device hub ready — {n} device(s) registered. Manage under HR → Attendance."
    elif conn.connector_key == "rest_openapi":
        ok, message = True, "OpenAPI schema available at /api/schema/swagger/"
    elif conn.connector_key == "bank_salary_file":
        ok, message = True, "Bank salary file generation available from Payroll periods."
    elif conn.connector_key == "microsoft365_calendar":
        from integrations.calendars import test_microsoft_calendar

        ok, message = test_microsoft_calendar(conn)
    elif conn.connector_key == "google_calendar":
        from integrations.calendars import test_google_calendar

        ok, message = test_google_calendar(conn)
    elif conn.connector_key == "caldav_calendar":
        from integrations.calendars import test_caldav_calendar

        ok, message = test_caldav_calendar(conn)
    elif conn.connector_key == "webhook_outbound":
        url = (conn.config or {}).get("endpoint_url") or ""
        ok = bool(url.startswith("https://"))
        message = "Webhook endpoint OK" if ok else "Set a valid HTTPS endpoint_url"
    elif conn.connector_key in (
        "microsoft365_sso",
        "microsoft_teams",
        "google_workspace",
        "whatsapp_business",
        "insurance_api",
        "excel_onedrive",
        "fbr_iris",
    ):
        # Credential presence check for competitive connectors
        fields = (meta or {}).get("config_fields") or []
        missing = []
        for f in fields:
            key = f["key"]
            if f.get("secret"):
                if not (conn.secrets or {}).get(key):
                    missing.append(key)
            else:
                if not (conn.config or {}).get(key):
                    missing.append(key)
        if missing:
            ok, message = False, f"Missing fields: {', '.join(missing)}"
        else:
            ok, message = True, "Configuration saved — connector ready for activation"
    else:
        ok, message = True, "Connector registered"

    conn.last_tested_at = timezone.now()
    conn.last_test_ok = ok
    conn.last_test_message = message[:500]
    if ok:
        conn.status = (
            IntegrationConnection.Status.ACTIVE
            if conn.is_enabled
            else IntegrationConnection.Status.CONFIGURED
        )
        conn.last_error = ""
    else:
        conn.status = IntegrationConnection.Status.ERROR
        conn.last_error = message
    conn.save(
        update_fields=[
            "last_tested_at",
            "last_test_ok",
            "last_test_message",
            "status",
            "last_error",
            "updated_at",
        ]
    )
    return conn
