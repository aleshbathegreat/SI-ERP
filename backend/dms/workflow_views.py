from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from accounts.models import Role
from dms.models import (
    WorkflowAction,
    WorkflowCase,
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
    WorkflowTransitionEvent,
    WorkflowTransitionField,
    WorkflowTrigger,
)
from dms.serializers import RO
from dms.workflow_engine import advance_case, ensure_standard, launch_case, preview


class WorkflowStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowState
        fields = "__all__"
        read_only_fields = RO


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    from_name = serializers.CharField(source="from_state.name", read_only=True, default="")
    to_name = serializers.CharField(source="to_state.name", read_only=True, default="")
    allowed_roles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), required=False
    )
    role_names = serializers.SerializerMethodField()
    event_codes = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTransition
        fields = (
            "id",
            "organization",
            "workflow",
            "from_state",
            "to_state",
            "from_name",
            "to_name",
            "label",
            "require_comment",
            "require_signature",
            "block_self_approval",
            "allowed_roles",
            "role_names",
            "event_codes",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO + ("from_name", "to_name", "role_names", "event_codes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and "allowed_roles" in self.fields:
            from core.access import user_organization

            org = user_organization(request.user)
            if org is not None:
                self.fields["allowed_roles"].queryset = Role.objects.filter(organization=org)

    def get_role_names(self, obj):
        return list(obj.allowed_roles.values_list("name", flat=True))

    def get_event_codes(self, obj):
        return list(obj.trigger_events.values_list("event", flat=True))


class WorkflowTriggerSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True, default="")

    class Meta:
        model = WorkflowTrigger
        fields = (
            "id",
            "organization",
            "workflow",
            "event",
            "state",
            "state_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO + ("state_name",)


class WorkflowActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAction
        fields = "__all__"
        read_only_fields = RO


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    states = WorkflowStateSerializer(many=True, read_only=True)
    transitions = WorkflowTransitionSerializer(many=True, read_only=True)
    triggers = WorkflowTriggerSerializer(many=True, read_only=True)
    actions = WorkflowActionSerializer(many=True, read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowDefinition
        fields = (
            "id",
            "organization",
            "name",
            "description",
            "applies_to",
            "document_type",
            "is_active",
            "states",
            "transitions",
            "triggers",
            "actions",
            "preview",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = RO + ("states", "transitions", "triggers", "actions", "preview")

    def get_preview(self, obj):
        return preview(obj)


class WorkflowDefinitionListSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(
        source="document_type.name", read_only=True, default=""
    )
    applies_to_label = serializers.SerializerMethodField()
    state_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowDefinition
        fields = (
            "id",
            "name",
            "description",
            "applies_to",
            "applies_to_label",
            "document_type",
            "document_type_name",
            "is_active",
            "state_count",
        )
        read_only_fields = fields

    def get_applies_to_label(self, obj):
        return dict(WorkflowDefinition.Target.choices).get(obj.applies_to, obj.applies_to)

    def get_state_count(self, obj):
        return obj.states.filter(is_deleted=False).count()


class WorkflowDefinitionViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowDefinition.objects.select_related("document_type").prefetch_related(
        "states", "transitions", "triggers", "actions"
    )
    serializer_class = WorkflowDefinitionSerializer
    search_fields = ("name", "description")
    filterset_fields = ("is_active", "document_type", "applies_to")
    rbac_module = "dms.documents"

    def get_serializer_class(self):
        if self.action == "list":
            return WorkflowDefinitionListSerializer
        return WorkflowDefinitionSerializer

    def initial(self, request, *args, **kwargs):
        if getattr(self, "action", None) == "ensure_standard_workflow":
            self.rbac_action = "add"
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="ensure-standard")
    def ensure_standard_workflow(self, request):
        from core.access import user_organization

        workflow = ensure_standard(user_organization(request.user), request.user)
        return Response(WorkflowDefinitionSerializer(workflow, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="preview")
    def preview_action(self, request, pk=None):
        return Response(preview(self.get_object()))


class WorkflowStateViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowState.objects.select_related("workflow")
    serializer_class = WorkflowStateSerializer
    filterset_fields = ("workflow",)
    search_fields = ("name", "code")
    rbac_module = "dms.documents"


class WorkflowTransitionViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowTransition.objects.select_related(
        "workflow", "from_state", "to_state"
    ).prefetch_related("allowed_roles", "trigger_events")
    serializer_class = WorkflowTransitionSerializer
    filterset_fields = ("workflow", "from_state")
    search_fields = ("label",)
    rbac_module = "dms.documents"


class WorkflowTriggerViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowTrigger.objects.select_related("workflow", "state")
    serializer_class = WorkflowTriggerSerializer
    filterset_fields = ("workflow", "event")
    rbac_module = "dms.documents"


class WorkflowTransitionEventSerializer(serializers.ModelSerializer):
    transition_label = serializers.CharField(source="transition.label", read_only=True, default="")

    class Meta:
        model = WorkflowTransitionEvent
        fields = (
            "id",
            "organization",
            "workflow",
            "transition",
            "transition_label",
            "event",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO + ("transition_label",)


class WorkflowTransitionEventViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowTransitionEvent.objects.select_related("workflow", "transition")
    serializer_class = WorkflowTransitionEventSerializer
    filterset_fields = ("workflow", "transition", "event")
    rbac_module = "dms.documents"


class WorkflowTransitionFieldSerializer(serializers.ModelSerializer):
    transition_label = serializers.CharField(source="transition.label", read_only=True, default="")

    class Meta:
        model = WorkflowTransitionField
        fields = (
            "id",
            "organization",
            "workflow",
            "transition",
            "transition_label",
            "name",
            "label",
            "field_type",
            "required",
            "help_text",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO + ("transition_label",)


class WorkflowTransitionFieldViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowTransitionField.objects.select_related("workflow", "transition")
    serializer_class = WorkflowTransitionFieldSerializer
    filterset_fields = ("workflow", "transition")
    search_fields = ("name", "label")
    rbac_module = "dms.documents"


class WorkflowActionViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WorkflowAction.objects.select_related("workflow", "transition", "trigger")
    serializer_class = WorkflowActionSerializer
    filterset_fields = ("workflow", "transition", "trigger", "action_type")
    rbac_module = "dms.documents"


class WorkflowCaseSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True, default="")
    workflow_name = serializers.CharField(source="workflow.name", read_only=True, default="")

    class Meta:
        model = WorkflowCase
        fields = (
            "id",
            "organization",
            "module",
            "object_id",
            "workflow",
            "workflow_name",
            "state",
            "state_name",
            "entered_at",
            "escalation_due_at",
            "escalated",
            "context",
            "created_at",
            "updated_at",
        )
        read_only_fields = RO + (
            "module",
            "object_id",
            "workflow",
            "workflow_name",
            "state",
            "state_name",
            "entered_at",
            "escalation_due_at",
            "escalated",
            "context",
        )


class WorkflowCaseViewSet(OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowCase.objects.select_related("workflow", "state")
    serializer_class = WorkflowCaseSerializer
    filterset_fields = ("workflow", "module", "object_id")
    rbac_module = "dms.documents"

    def initial(self, request, *args, **kwargs):
        if getattr(self, "action", None) == "launch":
            self.rbac_action = "add"
        elif getattr(self, "action", None) == "transition":
            self.rbac_action = "change"
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def launch(self, request):
        from core.access import user_organization

        module = str(request.data.get("module") or "").strip()
        object_id = request.data.get("object_id")
        if not module or object_id in (None, ""):
            raise serializers.ValidationError("Choose an area and a record.")
        case = launch_case(user_organization(request.user), module, object_id, request.user)
        if case is None:
            raise serializers.ValidationError("No active workflow applies to this area, or it has no states.")
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        case = self.get_object()
        try:
            row = WorkflowTransition.objects.get(
                pk=request.data.get("transition"),
                workflow=case.workflow,
                is_deleted=False,
            )
        except (WorkflowTransition.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError("That transition is not part of this workflow.")
        advance_case(
            case,
            row,
            request.user,
            comment=request.data.get("comment") or "",
            signed_name=request.data.get("signed_name") or "",
            enforce_gates=True,
            fields=request.data.get("fields") if isinstance(request.data.get("fields"), dict) else {},
        )
        case.refresh_from_db()
        return Response(self.get_serializer(case).data)
