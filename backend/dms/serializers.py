from django.db import transaction
from rest_framework import serializers

from core.access import is_owner, user_organization
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

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)
FILE_RO = ("original_filename", "file_size", "mime_type", "checksum")


def _org(serializer):
    request = serializer.context.get("request")
    return user_organization(request.user) if request else None


def _same_org(value, org, label):
    if value and org and value.organization_id != org.id:
        raise serializers.ValidationError(f"{label} not in this organization.")
    return value


def sync_tag_text(doc):
    names = list(doc.tag_items.order_by("name").values_list("name", flat=True))
    text = ", ".join(names)[:255]
    if doc.tags != text:
        doc.tags = text
        doc.save(update_fields=["tags"])


class DocumentFolderSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default="")
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFolder
        fields = "__all__"
        read_only_fields = RO

    def get_document_count(self, obj):
        return obj.documents.filter(is_deleted=False).count()

    def validate_parent(self, value):
        value = _same_org(value, _org(self), "Folder")
        if value and self.instance:
            node = value
            while node is not None:
                if node.pk == self.instance.pk:
                    raise serializers.ValidationError(
                        "A folder cannot be its own ancestor."
                    )
                node = node.parent
        return value


class DocumentTypeSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentType
        fields = "__all__"
        read_only_fields = RO

    def get_document_count(self, obj):
        return obj.documents.filter(is_deleted=False).count()

    def validate_name(self, value):
        org = _org(self)
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Name is required.")
        qs = DocumentType.objects.filter(organization=org, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A document type with this name already exists.")
        return name


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"
        read_only_fields = RO

    def validate_name(self, value):
        org = _org(self)
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Name is required.")
        qs = Tag.objects.filter(organization=org, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A tag with this name already exists.")
        return name


class MetadataTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataType
        fields = "__all__"
        read_only_fields = RO

    def validate_name(self, value):
        org = _org(self)
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Name is required.")
        qs = MetadataType.objects.filter(organization=org, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A metadata type with this name already exists.")
        return name

    def validate(self, attrs):
        if not (attrs.get("label") or (self.instance and self.instance.label)):
            attrs["label"] = attrs.get("name") or getattr(self.instance, "name", "")
        return attrs


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = (
            "id",
            "version",
            "file",
            "original_filename",
            "file_size",
            "mime_type",
            "checksum",
            "notes",
            "created_at",
            "created_by",
        )
        read_only_fields = fields


class DocumentCommentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentComment
        fields = ("id", "body", "created_at", "created_by", "created_by_name")
        read_only_fields = fields

    def get_created_by_name(self, obj):
        user = obj.created_by
        return user.get_username() if user else ""


class DocumentMetadataSerializer(serializers.ModelSerializer):
    metadata_type_name = serializers.CharField(
        source="metadata_type.name", read_only=True, default=""
    )
    metadata_type_label = serializers.SerializerMethodField()

    class Meta:
        model = DocumentMetadata
        fields = ("id", "metadata_type", "metadata_type_name", "metadata_type_label", "value")
        read_only_fields = fields

    def get_metadata_type_label(self, obj):
        return obj.metadata_type.label or obj.metadata_type.name


class DocumentLinkSerializer(serializers.ModelSerializer):
    target_title = serializers.CharField(source="target.title", read_only=True, default="")

    class Meta:
        model = DocumentLink
        fields = ("id", "target", "target_title", "label")
        read_only_fields = fields


class DocumentWebLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentWebLink
        fields = ("id", "label", "url")
        read_only_fields = fields


class DocumentAccessSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = DocumentAccess
        fields = ("id", "user", "username", "can_view", "can_change")
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default="")
    document_type_name = serializers.CharField(
        source="document_type.name", read_only=True, default=""
    )
    checked_out_by_name = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField()
    versions = DocumentVersionSerializer(many=True, read_only=True)
    comments = DocumentCommentSerializer(many=True, read_only=True)
    metadata_values = DocumentMetadataSerializer(many=True, read_only=True)
    links = DocumentLinkSerializer(source="outgoing_links", many=True, read_only=True)
    web_links = DocumentWebLinkSerializer(many=True, read_only=True)
    access_entries = DocumentAccessSerializer(many=True, read_only=True)
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "organization",
            "folder",
            "folder_name",
            "document_type",
            "document_type_name",
            "title",
            "category",
            "description",
            "language",
            "source",
            "file",
            "original_filename",
            "file_size",
            "mime_type",
            "checksum",
            "external_provider",
            "external_item_id",
            "external_web_url",
            "version",
            "status",
            "related_module",
            "related_id",
            "tags",
            "tag_items",
            "tag_names",
            "notes",
            "checked_out_by",
            "checked_out_by_name",
            "checked_out_at",
            "restricted",
            "versions",
            "comments",
            "metadata_values",
            "links",
            "web_links",
            "access_entries",
            "workflow",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = RO + FILE_RO + (
            "version",
            "status",
            "tags",
            "checked_out_by",
            "checked_out_at",
            "external_provider",
            "external_item_id",
            "external_web_url",
        )

    def get_checked_out_by_name(self, obj):
        user = obj.checked_out_by
        return user.get_username() if user else ""

    def get_tag_names(self, obj):
        return ", ".join(obj.tag_items.order_by("name").values_list("name", flat=True))

    def get_workflow(self, obj):
        from dms.workflow_engine import snapshot

        return snapshot(obj)

    def validate_folder(self, value):
        return _same_org(value, _org(self), "Folder")

    def validate_document_type(self, value):
        return _same_org(value, _org(self), "Document type")

    def validate_tag_items(self, value):
        org = _org(self)
        for tag in value:
            _same_org(tag, org, "Tag")
        return value

    def validate(self, attrs):
        inst = self.instance
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            inst
            and inst.checked_out_by_id
            and user
            and inst.checked_out_by_id != getattr(user, "id", None)
            and not is_owner(user)
        ):
            raise serializers.ValidationError(
                "Document is checked out by another user."
            )
        if inst and inst.status == Document.Status.ARCHIVED and attrs:
            raise serializers.ValidationError("Restore the document before editing it.")
        return attrs

    def _store_file(self, doc, uploaded, user):
        facts = apply_file_facts(doc, uploaded)
        if not facts:
            return
        doc.save(update_fields=[*facts.keys(), "updated_at"])
        DocumentVersion.objects.create(
            document=doc,
            version=doc.version,
            file=doc.file,
            notes="",
            created_by=user,
            **facts,
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tag_items", None)
        uploaded = validated_data.get("file")
        doc = super().create(validated_data)
        if tags is not None:
            doc.tag_items.set(tags)
            sync_tag_text(doc)
        if uploaded:
            request = self.context.get("request")
            self._store_file(doc, uploaded, getattr(request, "user", None))
        request = self.context.get("request")
        from dms.workflow_engine import attach_default

        attach_default(doc, getattr(request, "user", None))
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop("tag_items", None)
        uploaded = validated_data.get("file")
        doc = super().update(instance, validated_data)
        if tags is not None:
            doc.tag_items.set(tags)
            sync_tag_text(doc)
        if uploaded:
            request = self.context.get("request")
            doc.version = (doc.version or 1) + 1
            doc.save(update_fields=["version", "updated_at"])
            self._store_file(doc, uploaded, getattr(request, "user", None))
        return doc


class DocumentListSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default="")
    document_type_name = serializers.CharField(
        source="document_type.name", read_only=True, default=""
    )
    checked_out_by_name = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "folder",
            "folder_name",
            "document_type",
            "document_type_name",
            "category",
            "language",
            "source",
            "version",
            "status",
            "tag_names",
            "original_filename",
            "file_size",
            "mime_type",
            "external_web_url",
            "checked_out_by_name",
            "restricted",
            "updated_at",
        )
        read_only_fields = fields

    def get_checked_out_by_name(self, obj):
        user = obj.checked_out_by
        return user.get_username() if user else ""

    def get_tag_names(self, obj):
        return ", ".join(obj.tag_items.order_by("name").values_list("name", flat=True))
