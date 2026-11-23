from rest_framework import serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from comments.models import RecordComment
from comments.services import add_record_comment
from core.access import user_organization
from core.scoping import OrgScopedQuerysetMixin

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
    "author",
)


class RecordCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = RecordComment
        fields = (
            "id",
            "organization",
            "module",
            "object_id",
            "body",
            "author",
            "author_name",
            "created_at",
        )
        read_only_fields = RO + ("author_name",)

    def get_author_name(self, obj):
        if obj.author_id:
            return obj.author.get_username()
        return ""


class RecordCommentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RecordComment.objects.select_related("author")
    serializer_class = RecordCommentSerializer
    filterset_fields = ("module", "object_id")
    search_fields = ("body",)
    rbac_exempt = True
    http_method_names = ["get", "post", "head", "options", "delete"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        comment = add_record_comment(
            user_organization(request.user),
            data.get("module"),
            data.get("object_id"),
            data.get("body"),
            request.user,
        )
        if comment is None:
            raise ValidationError("A comment needs a record and some text.")
        return Response(self.get_serializer(comment).data, status=201)
