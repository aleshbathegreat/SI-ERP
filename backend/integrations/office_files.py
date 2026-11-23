"""Save Microsoft 365 files into the document system, and store a document back."""

from __future__ import annotations

from django.core.files.base import ContentFile

from dms.files import apply_file_facts
from dms.models import Document, DocumentVersion
from integrations.microsoft365 import (
    acquire_app_token,
    download_drive_item,
    list_drive_items,
    upload_drive_item,
)
from integrations.models import IntegrationConnection


def office_credentials(organization):
    for key in ("excel_onedrive", "microsoft365_mail"):
        conn = (
            IntegrationConnection.objects.filter(
                organization=organization,
                connector_key=key,
                is_enabled=True,
            )
            .exclude(status=IntegrationConnection.Status.DISABLED)
            .first()
        )
        if conn is None:
            continue
        cfg = conn.config or {}
        secrets = conn.secrets or {}
        tenant = (cfg.get("tenant_id") or "").strip()
        client_id = (cfg.get("client_id") or "").strip()
        secret = secrets.get("client_secret") or ""
        upn = (cfg.get("mailbox_upn") or cfg.get("sender_upn") or "").strip()
        folder = (cfg.get("drive_path") or "SIERP").strip() or "SIERP"
        if tenant and client_id and secret and upn:
            return tenant, client_id, secret, upn, folder
    raise ValueError(
        "Enable Microsoft 365 OneDrive under Settings → Integrations, with a mailbox UPN."
    )


def list_office_files(organization):
    tenant, client_id, secret, upn, folder = office_credentials(organization)
    token = acquire_app_token(tenant, client_id, secret)
    return list_drive_items(token, upn, folder)


def _store_bytes(doc, content: bytes, name: str, user):
    upload = ContentFile(content, name=name[:255] or "document")
    doc.file.save(name[:255] or "document", upload, save=False)
    facts = apply_file_facts(doc, doc.file)
    doc.updated_by = user
    doc.save()
    DocumentVersion.objects.create(
        document=doc,
        version=doc.version,
        file=doc.file,
        notes="Saved from Microsoft 365",
        created_by=user,
        **facts,
    )
    return doc


def save_office_file(organization, user, item_id: str) -> Document:
    tenant, client_id, secret, upn, _folder = office_credentials(organization)
    token = acquire_app_token(tenant, client_id, secret)
    content, name, mime, web_url = download_drive_item(token, upn, item_id)
    title = name.rsplit(".", 1)[0][:255] or name[:255]
    existing = Document.objects.filter(
        organization=organization, external_item_id=item_id
    ).first()
    if existing:
        if existing.status == Document.Status.ARCHIVED:
            raise ValueError("Restore the document before saving a new Microsoft 365 copy.")
        existing.version = (existing.version or 1) + 1
        existing.external_provider = "microsoft365"
        existing.external_web_url = (web_url or "")[:500]
        existing.source = Document.Source.OFFICE365
        existing.mime_type = mime
        return _store_bytes(existing, content, name, user)
    doc = Document(
        organization=organization,
        title=title,
        source=Document.Source.OFFICE365,
        external_provider="microsoft365",
        external_item_id=item_id[:255],
        external_web_url=(web_url or "")[:500],
        mime_type=mime,
        created_by=user,
        version=1,
    )
    return _store_bytes(doc, content, name, user)


def push_document_to_office(organization, doc: Document) -> Document:
    if not doc.file:
        raise ValueError("Upload a file before saving it to Microsoft 365.")
    tenant, client_id, secret, upn, folder = office_credentials(organization)
    token = acquire_app_token(tenant, client_id, secret)
    with doc.file.open("rb") as handle:
        content = handle.read()
    filename = doc.original_filename or doc.file.name.replace("\\", "/").rsplit("/", 1)[-1]
    saved = upload_drive_item(
        token,
        upn,
        folder,
        filename or f"{doc.title}.bin",
        content,
        doc.mime_type or "application/octet-stream",
    )
    doc.external_provider = "microsoft365"
    doc.external_item_id = (saved.get("id") or "")[:255]
    doc.external_web_url = (saved.get("web_url") or "")[:500]
    if doc.source in (Document.Source.UPLOAD, Document.Source.OFFICE365, ""):
        doc.source = Document.Source.OFFICE365
    doc.save(
        update_fields=[
            "external_provider",
            "external_item_id",
            "external_web_url",
            "source",
            "updated_at",
        ]
    )
    return doc
