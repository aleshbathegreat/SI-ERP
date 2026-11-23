from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import UserProfile
from core.access import is_owner, user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from dms.files import apply_file_facts
from dms.models import (
    Document,
    DocumentAccess,
    DocumentComment,
    DocumentFolder,
    DocumentLink,
    DocumentMetadata,
    DocumentType,
    DocumentVersion,
    DocumentWebLink,
    MetadataType,
    Tag,
)
from dms.serializers import (
    DocumentFolderSerializer,
    DocumentListSerializer,
    DocumentSerializer,
    DocumentTypeSerializer,
    MetadataTypeSerializer,
    TagSerializer,
    sync_tag_text,
)


def _locked(doc, user):
    if doc.status == Document.Status.ARCHIVED:
        raise ValidationError("Restore the document before changing it.")
    if (
        doc.checked_out_by_id
        and doc.checked_out_by_id != getattr(user, "id", None)
        and not is_owner(user)
    ):
        raise ValidationError("Document is checked out by another user.")


class DocumentFolderViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentFolder.objects.select_related("parent")
    serializer_class = DocumentFolderSerializer
    search_fields = ("name", "description")
    filterset_fields = ("parent",)
    rbac_module = "dms.folders"


class DocumentTypeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    search_fields = ("name", "description")
    rbac_module = "dms.documents"


class TagViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    search_fields = ("name",)
    rbac_module = "dms.documents"


class MetadataTypeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = MetadataType.objects.all()
    serializer_class = MetadataTypeSerializer
    search_fields = ("name", "label")
    rbac_module = "dms.documents"


class DocumentViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Document.objects.select_related(
        "folder", "document_type", "checked_out_by"
    ).prefetch_related("tag_items")
    serializer_class = DocumentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = (
        "title",
        "category",
        "tags",
        "description",
        "related_module",
        "notes",
        "original_filename",
        "checksum",
    )
    filterset_fields = (
        "status",
        "folder",
        "document_type",
        "category",
        "source",
        "related_module",
        "related_id",
        "restricted",
        "tag_items",
    )
    rbac_module = "dms.documents"

    def initial(self, request, *args, **kwargs):
        if getattr(self, "action", None) in {
            "submit",
            "reject",
            "publish",
            "archive",
            "restore",
            "checkout",
            "checkin",
            "new_version",
            "comment",
            "metadata",
            "link",
            "web_link",
            "tags",
            "grant_access",
            "save_to_office365",
            "transition",
            "escalate",
            "start_workflow",
        }:
            self.rbac_action = "change"
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not is_owner(user):
            qs = qs.filter(
                Q(restricted=False)
                | Q(created_by=user)
                | Q(
                    access_entries__user=user,
                    access_entries__is_deleted=False,
                    access_entries__can_view=True,
                )
            ).distinct()
        if getattr(self, "action", None) != "list":
            qs = qs.prefetch_related(
                "versions",
                "comments",
                "metadata_values__metadata_type",
                "outgoing_links__target",
                "web_links",
                "access_entries__user",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _save_status(self, doc, status):
        doc.status = status
        doc.updated_by = self.request.user
        doc.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        doc = self.get_object()
        _locked(doc, request.user)
        if doc.status != Document.Status.DRAFT:
            raise ValidationError("Only a draft can be submitted for review.")
        return self._save_status(doc, Document.Status.IN_REVIEW)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        doc = self.get_object()
        if doc.status != Document.Status.IN_REVIEW:
            raise ValidationError("Only a document in review can be sent back.")
        return self._save_status(doc, Document.Status.DRAFT)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        doc = self.get_object()
        _locked(doc, request.user)
        if doc.status == Document.Status.PUBLISHED:
            raise ValidationError("Document is already published.")
        if doc.status == Document.Status.ARCHIVED:
            raise ValidationError("Restore the document before publishing.")
        return self._save_status(doc, Document.Status.PUBLISHED)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        doc = self.get_object()
        if doc.status == Document.Status.ARCHIVED:
            raise ValidationError("Document is already archived.")
        return self._save_status(doc, Document.Status.ARCHIVED)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        doc = self.get_object()
        if doc.status != Document.Status.ARCHIVED:
            raise ValidationError("Only an archived document can be restored.")
        return self._save_status(doc, Document.Status.DRAFT)

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, pk=None):
        doc = self.get_object()
        if doc.status == Document.Status.ARCHIVED:
            raise ValidationError("Archived documents cannot be checked out.")
        if doc.checked_out_by_id and doc.checked_out_by_id != request.user.id:
            raise ValidationError("Document is already checked out.")
        doc.checked_out_by = request.user
        doc.checked_out_at = timezone.now()
        doc.updated_by = request.user
        doc.save(
            update_fields=["checked_out_by", "checked_out_at", "updated_by", "updated_at"]
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="checkin")
    def checkin(self, request, pk=None):
        doc = self.get_object()
        if not doc.checked_out_by_id:
            raise ValidationError("Document is not checked out.")
        if doc.checked_out_by_id != request.user.id and not is_owner(request.user):
            raise ValidationError("Only the person who checked it out can check it in.")
        doc.checked_out_by = None
        doc.checked_out_at = None
        doc.updated_by = request.user
        doc.save(
            update_fields=["checked_out_by", "checked_out_at", "updated_by", "updated_at"]
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="new-version",
        parser_classes=[MultiPartParser, FormParser],
    )
    def new_version(self, request, pk=None):
        doc = self.get_object()
        _locked(doc, request.user)
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "Upload a file."})
        doc.file = uploaded
        doc.version = (doc.version or 1) + 1
        doc.updated_by = request.user
        facts = apply_file_facts(doc, uploaded)
        doc.save(
            update_fields=["file", "version", "updated_by", "updated_at", *facts.keys()]
        )
        DocumentVersion.objects.create(
            document=doc,
            version=doc.version,
            file=doc.file,
            notes=str(request.data.get("notes") or "")[:255],
            created_by=request.user,
            **facts,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        doc = self.get_object()
        if not doc.file:
            raise ValidationError("No file uploaded.")
        handle = doc.file.open("rb")
        name = doc.original_filename or doc.file.name.rsplit("/", 1)[-1]
        return FileResponse(handle, as_attachment=True, filename=name)

    @action(detail=True, methods=["get"], url_path="duplicates")
    def duplicates(self, request, pk=None):
        doc = self.get_object()
        if not doc.checksum:
            return Response([])
        rows = (
            self.get_queryset()
            .filter(checksum=doc.checksum)
            .exclude(pk=doc.pk)
            .values("id", "title", "version")[:20]
        )
        return Response(list(rows))

    @action(detail=True, methods=["post"], url_path="comment")
    def comment(self, request, pk=None):
        doc = self.get_object()
        body = str(request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Comment is required."})
        DocumentComment.objects.create(
            organization=doc.organization,
            document=doc,
            body=body,
            created_by=request.user,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="metadata")
    def metadata(self, request, pk=None):
        doc = self.get_object()
        _locked(doc, request.user)
        type_id = request.data.get("metadata_type")
        if not type_id:
            raise ValidationError({"metadata_type": "Choose a metadata type."})
        try:
            meta_type = MetadataType.objects.get(
                pk=type_id, organization=doc.organization
            )
        except (MetadataType.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"metadata_type": "Metadata type not found."})
        value = str(request.data.get("value") or "")
        row = (
            DocumentMetadata.objects.filter(document=doc, metadata_type=meta_type)
            .order_by("-id")
            .first()
        )
        if row:
            row.value = value
            row.updated_by = request.user
            row.save(update_fields=["value", "updated_by", "updated_at"])
        else:
            DocumentMetadata.objects.create(
                organization=doc.organization,
                document=doc,
                metadata_type=meta_type,
                value=value,
                created_by=request.user,
            )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="link")
    def link(self, request, pk=None):
        doc = self.get_object()
        target_id = request.data.get("target")
        if not target_id:
            raise ValidationError({"target": "Choose a document."})
        if str(target_id) == str(doc.pk):
            raise ValidationError({"target": "A document cannot link to itself."})
        try:
            target = self.get_queryset().get(pk=target_id)
        except (Document.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"target": "Document not found."})
        DocumentLink.objects.create(
            organization=doc.organization,
            document=doc,
            target=target,
            label=str(request.data.get("label") or "")[:120],
            created_by=request.user,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="web-link")
    def web_link(self, request, pk=None):
        doc = self.get_object()
        label = str(request.data.get("label") or "").strip()
        url = str(request.data.get("url") or "").strip()
        if not label or not url:
            raise ValidationError("Label and URL are required.")
        if not url.startswith(("http://", "https://")):
            raise ValidationError({"url": "URL must start with http:// or https://."})
        DocumentWebLink.objects.create(
            organization=doc.organization,
            document=doc,
            label=label[:120],
            url=url[:500],
            created_by=request.user,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="tags")
    def tags(self, request, pk=None):
        doc = self.get_object()
        _locked(doc, request.user)
        raw = request.data.get("tag_ids") or []
        if not isinstance(raw, list):
            raise ValidationError({"tag_ids": "Send a list of tag ids."})
        tags = Tag.objects.filter(organization=doc.organization, pk__in=raw)
        doc.tag_items.set(tags)
        sync_tag_text(doc)
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="grant-access")
    def grant_access(self, request, pk=None):
        doc = self.get_object()
        user_id = request.data.get("user")
        if not user_id:
            raise ValidationError({"user": "Choose a user."})
        profile = UserProfile.objects.filter(
            user_id=user_id, organization=doc.organization
        ).first()
        if profile is None:
            raise ValidationError({"user": "User is not in this organization."})
        can_change = bool(request.data.get("can_change"))
        row = (
            DocumentAccess.objects.filter(document=doc, user_id=user_id)
            .order_by("-id")
            .first()
        )
        if row:
            row.can_view = True
            row.can_change = can_change
            row.updated_by = request.user
            row.save(update_fields=["can_view", "can_change", "updated_by", "updated_at"])
        else:
            DocumentAccess.objects.create(
                organization=doc.organization,
                document=doc,
                user_id=user_id,
                can_view=True,
                can_change=can_change,
                created_by=request.user,
            )
        if not doc.restricted:
            doc.restricted = True
            doc.updated_by = request.user
            doc.save(update_fields=["restricted", "updated_by", "updated_at"])
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=False, methods=["get"], url_path="office365-files")
    def office365_files(self, request):
        from integrations.office_files import list_office_files

        org = user_organization(request.user)
        try:
            return Response(list_office_files(org))
        except Exception as exc:
            raise ValidationError(str(exc)[:400]) from exc

    @action(detail=False, methods=["post"], url_path="from-office365")
    def from_office365(self, request):
        from integrations.office_files import save_office_file

        item_id = str(request.data.get("item_id") or "").strip()
        if not item_id:
            raise ValidationError({"item_id": "Choose a Microsoft 365 file."})
        org = user_organization(request.user)
        try:
            doc = save_office_file(org, request.user, item_id)
        except Exception as exc:
            raise ValidationError(str(exc)[:400]) from exc
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="save-to-office365")
    def save_to_office365(self, request, pk=None):
        from integrations.office_files import push_document_to_office

        doc = self.get_object()
        _locked(doc, request.user)
        org = user_organization(request.user)
        try:
            push_document_to_office(org, doc)
        except Exception as exc:
            raise ValidationError(str(exc)[:400]) from exc
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="start-workflow")
    def start_workflow(self, request, pk=None):
        from dms.workflow_engine import attach_default

        doc = self.get_object()
        attach_default(doc, request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        from dms.workflow_engine import apply_transition

        doc = self.get_object()
        transition_id = request.data.get("transition")
        if not transition_id:
            raise ValidationError({"transition": "Choose an action."})
        apply_transition(
            doc,
            request.user,
            transition_id,
            comment=str(request.data.get("comment") or ""),
            signed_name=str(request.data.get("signed_name") or ""),
            meaning=str(request.data.get("meaning") or "approve"),
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)

    @action(detail=True, methods=["post"], url_path="escalate")
    def escalate(self, request, pk=None):
        from dms.workflow_engine import escalate as run_escalation

        doc = self.get_object()
        run_escalation(doc, request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=doc.pk)).data)
