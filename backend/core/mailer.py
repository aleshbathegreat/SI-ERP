"""Tenant + platform SMTP mailer."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from django.conf import settings

logger = logging.getLogger(__name__)


def _django_fallback_send(
    subject: str,
    message: str,
    from_email: str,
    recipients: list[str],
    html_message: str | None = None,
):
    from django.core.mail import EmailMultiAlternatives

    msg = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipients,
    )
    if html_message:
        msg.attach_alternative(html_message, "text/html")
    msg.send(fail_silently=False)


def _smtp_send(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    use_tls: bool,
    use_ssl: bool,
    from_email: str,
    from_name: str,
    reply_to: str,
    recipients: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
):
    if not host or not from_email:
        raise ValueError("SMTP host and from_email are required")

    # Gmail app passwords are often pasted with spaces
    password = (password or "").replace(" ", "")

    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))

    msg["Subject"] = subject
    msg["From"] = formataddr((from_name or "", from_email))
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
    try:
        if use_tls and not use_ssl:
            server.starttls()
        if username:
            server.login(username, password or "")
        server.sendmail(from_email, recipients, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_platform_email(
    subject: str,
    message: str,
    recipients: list[str],
    html_message: str | None = None,
) -> bool:
    """System emails — platform SMTP, else Django EMAIL_* settings."""
    from core.models import PlatformSmtpSettings

    recipients = [r for r in recipients if r]
    if not recipients:
        return False
    cfg = PlatformSmtpSettings.load()
    try:
        if cfg.is_active and cfg.host and cfg.from_email:
            _smtp_send(
                host=cfg.host,
                port=cfg.port,
                username=cfg.username,
                password=cfg.password,
                use_tls=cfg.use_tls,
                use_ssl=cfg.use_ssl,
                from_email=cfg.from_email,
                from_name=cfg.from_name,
                reply_to=cfg.reply_to,
                recipients=recipients,
                subject=f"[SI-ERP] {subject}",
                body=message,
                html_body=html_message,
            )
        else:
            _django_fallback_send(
                subject=f"[SI-ERP] {subject}",
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sigbl.com"),
                recipients=recipients,
                html_message=html_message,
            )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("send_platform_email failed: %s", exc)
        return False


def send_tenant_template_email(
    organization,
    template_code: str,
    recipients: list[str],
    context: dict | None = None,
    purpose: str | None = None,
) -> bool:
    """Resolve EmailTemplate by code and send. Soft-fails if missing/inactive."""
    from core.models import EmailTemplate

    if organization is None or not template_code:
        return False
    tpl = EmailTemplate.objects.filter(
        organization=organization, code=template_code, is_active=True
    ).first()
    if not tpl:
        logger.info("email template %s not found for org %s", template_code, organization.id)
        return False
    subject, body, html = tpl.render(context)
    return send_tenant_email(
        organization,
        subject,
        body,
        recipients,
        purpose=purpose or tpl.purpose,
        html_message=html or None,
    )


def send_tenant_email(
    organization,
    subject: str,
    message: str,
    recipients: list[str],
    purpose: str = "general",
    html_message: str | None = None,
) -> bool:
    """Tenant workflow emails — tenant SMTP + email profile, else platform."""
    from core.models import TenantEmailProfile, TenantSmtpSettings

    recipients = [r for r in recipients if r]
    if not recipients or organization is None:
        return False

    profile = (
        TenantEmailProfile.objects.filter(
            organization=organization, purpose=purpose, is_active=True
        ).first()
        or TenantEmailProfile.objects.filter(
            organization=organization, is_default=True, is_active=True
        ).first()
        or TenantEmailProfile.objects.filter(
            organization=organization, is_active=True
        ).first()
    )

    smtp = getattr(organization, "smtp_settings", None)
    if smtp is None:
        smtp = TenantSmtpSettings.objects.filter(organization=organization).first()

    from_email = (profile.email if profile else None) or (smtp.from_email if smtp else "")
    from_name = (
        (profile.name if profile else None)
        or (smtp.from_name if smtp else "")
        or organization.brand_name
        or organization.name
    )
    reply_to = (profile.reply_to if profile else "") or (smtp.reply_to if smtp else "")

    brand = organization.brand_name or organization.name
    subject_full = f"[{brand}] {subject}"
    try:
        # Prefer Microsoft 365 Graph when tenant enabled
        try:
            from integrations.services import send_via_m365

            if send_via_m365(
                organization, subject_full, message, recipients, html_message
            ):
                return True
        except Exception as m365_exc:  # noqa: BLE001
            logger.warning("M365 Graph send failed, falling back to SMTP: %s", m365_exc)

        if smtp and smtp.is_active and smtp.host and from_email:
            _smtp_send(
                host=smtp.host,
                port=smtp.port,
                username=smtp.username,
                password=smtp.password,
                use_tls=smtp.use_tls,
                use_ssl=smtp.use_ssl,
                from_email=from_email,
                from_name=from_name,
                reply_to=reply_to,
                recipients=recipients,
                subject=subject_full,
                body=message,
                html_body=html_message,
            )
            return True
        return send_platform_email(subject, message, recipients, html_message=html_message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("send_tenant_email failed: %s", exc)
        try:
            return send_platform_email(
                subject, message, recipients, html_message=html_message
            )
        except Exception:
            return False
