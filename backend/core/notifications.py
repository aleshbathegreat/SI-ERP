"""Email / in-app style notifications."""

from __future__ import annotations

import logging

from core.mailer import send_platform_email, send_tenant_email

logger = logging.getLogger(__name__)


def notify_user(user, subject: str, message: str, organization=None, purpose: str = "general") -> bool:
    if not user or not getattr(user, "email", None):
        return False
    org = organization
    if org is None:
        from core.access import user_organization

        org = user_organization(user)
    if org:
        return send_tenant_email(org, subject, message, [user.email], purpose=purpose)
    return send_platform_email(subject, message, [user.email])


def _email_later(organization_id, subject, message, emails, purpose):
    """Send after the request returns so approve and reject are not stuck on SMTP."""
    import threading

    from django.db import close_old_connections

    recipients = list(emails)

    def run():
        close_old_connections()
        try:
            from core.models import Organization

            org = Organization.objects.filter(pk=organization_id).first()
            if org is not None:
                send_tenant_email(org, subject, message, recipients, purpose=purpose)
        except Exception:
            logger.exception("workflow email failed for org %s", organization_id)
        finally:
            close_old_connections()

    threading.Thread(target=run, name="workflow-email", daemon=True).start()


def notify_org_roles(
    organization,
    subject: str,
    message: str,
    role_codes: list[str] | None = None,
    purpose: str = "workflow",
    module: str = "",
    object_id: str = "",
    href: str = "",
):
    if organization is None:
        return 0
    from accounts.models import UserProfile, UserRole

    users = []
    seen = set()

    def add(user):
        if user is None or user.id in seen:
            return
        seen.add(user.id)
        users.append(user)

    qs = UserRole.objects.filter(role__organization=organization).select_related("user", "role")
    if role_codes:
        qs = qs.filter(role__code__in=role_codes)
    for link in qs:
        add(link.user)
    if role_codes:
        profiles = UserProfile.objects.filter(
            organization=organization,
            is_active_member=True,
            role__in=role_codes,
        ).select_related("user")
        for profile in profiles:
            add(profile.user)
        primaries = UserProfile.objects.filter(
            organization=organization,
            is_active_member=True,
            primary_role__code__in=role_codes,
        ).select_related("user")
        for profile in primaries:
            add(profile.user)
    emails = [user.email for user in users if getattr(user, "email", None)]
    sent = len(emails)
    if emails:
        _email_later(organization.pk, subject, message, emails, purpose)
    try:
        from notifications.services import push_inbox, record_href

        push_inbox(
            organization,
            users,
            title=subject,
            body=message,
            href=href or (record_href(module, object_id) if module else "/inbox"),
            module=module,
            object_id=str(object_id or ""),
            kind="workflow" if purpose == "workflow" else (purpose or "system")[:20],
        )
    except Exception:
        logger.exception("inbox write failed for org %s", getattr(organization, "code", "?"))
    logger.info(
        "NOTIFY org=%s subject=%s recipients=%s",
        getattr(organization, "code", "?"),
        subject,
        sent,
    )
    return sent


def notify_system(subject: str, message: str, recipients: list[str]) -> bool:
    return send_platform_email(subject, message, recipients)
