from django.conf import settings
from django.db import models

from accounts.models import Role
from core.models import AuditModel, Organization


class DocumentFolder(AuditModel):
    """Cabinet. Nested folders that hold documents."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_folders"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DocumentType(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_types"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_tags"
    )
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MetadataType(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_metadata_types"
    )
    name = models.CharField(max_length=120)
    label = models.CharField(max_length=120, blank=True, default="")
    required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.label or self.name


class Document(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Source(models.TextChoices):
        UPLOAD = "upload", "Upload"
        EMAIL = "email", "Email"
        SCAN = "scan", "Scan"
        GENERATED = "generated", "Generated"
        OFFICE365 = "office365", "Microsoft 365"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_documents"
    )
    folder = models.ForeignKey(
        DocumentFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="en")
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.UPLOAD
    )
    file = models.FileField(upload_to="dms/documents/%Y/%m/", blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=120, blank=True, default="")
    checksum = models.CharField(max_length=64, blank=True, default="", db_index=True)
    external_provider = models.CharField(max_length=32, blank=True, default="")
    external_item_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    external_web_url = models.URLField(max_length=500, blank=True, default="")
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    related_module = models.CharField(max_length=64, blank=True, default="")
    related_id = models.PositiveIntegerField(null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True, default="")
    tag_items = models.ManyToManyField(Tag, blank=True, related_name="documents")
    notes = models.TextField(blank=True, default="")
    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_documents_checked_out",
    )
    checked_out_at = models.DateTimeField(null=True, blank=True)
    restricted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} v{self.version}"


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.PositiveIntegerField()
    file = models.FileField(upload_to="dms/versions/%Y/%m/", blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=120, blank=True, default="")
    checksum = models.CharField(max_length=64, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_versions_created",
    )

    class Meta:
        ordering = ["-version"]
        unique_together = ("document", "version")


class DocumentMetadata(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_metadata_values"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="metadata_values"
    )
    metadata_type = models.ForeignKey(
        MetadataType, on_delete=models.CASCADE, related_name="values"
    )
    value = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["metadata_type__name"]


class DocumentComment(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_comments"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]


class DocumentLink(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_links"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="outgoing_links"
    )
    target = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="incoming_links"
    )
    label = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["-id"]


class DocumentWebLink(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_web_links"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="web_links"
    )
    label = models.CharField(max_length=120)
    url = models.URLField(max_length=500)

    class Meta:
        ordering = ["label"]


class DocumentAccess(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_access"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="access_entries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dms_access_entries",
    )
    can_view = models.BooleanField(default=True)
    can_change = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]


class WorkflowDefinition(AuditModel):
    class Target(models.TextChoices):
        DOCUMENTS = "dms.documents", "Documents"
        JOURNALS = "finance.journals", "Journals"
        BUDGETS = "finance.budgets", "Budgets"
        VENDOR_INVOICES = "finance.invoices", "Vendor invoices"
        CUSTOMER_INVOICES = "sales.invoices", "Customer invoices"
        SALES_ORDERS = "sales.orders", "Sales orders"
        REQUISITIONS = "procurement.requisitions", "Purchase requisitions"
        PURCHASE_ORDERS = "procurement.orders", "Purchase orders"
        LEAVE = "hr.leaves", "Leave requests"
        RECRUITMENT = "hr.recruitment", "Recruitment"
        PERFORMANCE = "hr.performance", "Performance reviews"
        PAYROLL = "payroll.periods", "Payroll periods"
        LOANS = "payroll.loans", "Employee loans"
        TIMESHEETS = "projects.timesheets", "Timesheets"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflows"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    applies_to = models.CharField(
        max_length=64, choices=Target.choices, default=Target.DOCUMENTS
    )
    document_type = models.ForeignKey(
        DocumentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflows",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkflowState(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_states"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="states"
    )
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=40)
    sort_order = models.PositiveIntegerField(default=0)
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    escalation_hours = models.PositiveIntegerField(null=True, blank=True)
    document_status = models.CharField(max_length=20, blank=True, default="")
    escalate_to_state = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="escalates_from",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class WorkflowTransition(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_transitions"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="transitions"
    )
    from_state = models.ForeignKey(
        WorkflowState, on_delete=models.CASCADE, related_name="outgoing"
    )
    to_state = models.ForeignKey(
        WorkflowState, on_delete=models.CASCADE, related_name="incoming"
    )
    label = models.CharField(max_length=80)
    require_comment = models.BooleanField(default=False)
    require_signature = models.BooleanField(default=False)
    block_self_approval = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    allowed_roles = models.ManyToManyField(
        Role, blank=True, related_name="workflow_transitions"
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label


class WorkflowTransitionEvent(AuditModel):
    """An ERP event that fires this transition on its own."""

    class Event(models.TextChoices):
        CREATED = "record.created", "Record created"
        UPDATED = "record.updated", "Record updated"
        SUBMITTED = "record.submitted", "Record submitted"
        APPROVED = "record.approved", "Record approved"
        REJECTED = "record.rejected", "Record rejected"
        POSTED = "record.posted", "Record posted"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_transition_events"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="transition_events"
    )
    transition = models.ForeignKey(
        WorkflowTransition, on_delete=models.CASCADE, related_name="trigger_events"
    )
    event = models.CharField(max_length=40, choices=Event.choices)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["transition", "event"],
                condition=models.Q(is_deleted=False),
                name="uniq_workflow_transition_event",
            )
        ]


class WorkflowTransitionField(AuditModel):
    """A value collected when someone takes the transition."""

    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        DATE = "date", "Date"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_transition_fields"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="transition_fields"
    )
    transition = models.ForeignKey(
        WorkflowTransition, on_delete=models.CASCADE, related_name="fields"
    )
    name = models.CharField(max_length=40)
    label = models.CharField(max_length=80)
    field_type = models.CharField(max_length=20, choices=Kind.choices, default=Kind.TEXT)
    required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=180, blank=True, default="")

    class Meta:
        ordering = ["id"]


class WorkflowTrigger(AuditModel):
    class Event(models.TextChoices):
        ON_ENTER = "on_enter", "On enter state"
        ON_LEAVE = "on_leave", "On leave state"
        ON_OVERDUE = "on_overdue", "On escalation"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_triggers"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="triggers"
    )
    event = models.CharField(max_length=20, choices=Event.choices)
    state = models.ForeignKey(
        WorkflowState,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="triggers",
    )

    class Meta:
        ordering = ["id"]


class WorkflowAction(AuditModel):
    class Kind(models.TextChoices):
        SET_STATUS = "set_status", "Set document status"
        NOTIFY = "notify", "Notify reviewers"
        NOTIFY_ROLE = "notify_role", "Notify a role"
        ADD_COMMENT = "add_comment", "Add comment"
        CREATE_TASK = "create_task", "Create a task"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_actions"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="actions"
    )
    transition = models.ForeignKey(
        WorkflowTransition,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    trigger = models.ForeignKey(
        WorkflowTrigger,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    action_type = models.CharField(max_length=20, choices=Kind.choices)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["id"]


class DocumentFlow(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_document_flows"
    )
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="flow"
    )
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.PROTECT, related_name="documents"
    )
    state = models.ForeignKey(
        WorkflowState, on_delete=models.PROTECT, related_name="documents"
    )
    entered_at = models.DateTimeField()
    escalation_due_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)
    last_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_flows_acted",
    )

    class Meta:
        ordering = ["-id"]


class DocumentSignature(AuditModel):
    class Meaning(models.TextChoices):
        APPROVE = "approve", "Approve"
        REVIEW = "review", "Review"
        ACKNOWLEDGE = "acknowledge", "Acknowledge"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_signatures"
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="signatures"
    )
    transition = models.ForeignKey(
        WorkflowTransition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signatures",
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_signatures",
    )
    signed_name = models.CharField(max_length=160)
    meaning = models.CharField(
        max_length=20, choices=Meaning.choices, default=Meaning.APPROVE
    )

    class Meta:
        ordering = ["-id"]


class WorkflowCase(AuditModel):
    """One ERP record sitting in a workflow state. Documents keep DocumentFlow."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_cases"
    )
    module = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.PROTECT, related_name="cases"
    )
    state = models.ForeignKey(
        WorkflowState, on_delete=models.PROTECT, related_name="cases"
    )
    entered_at = models.DateTimeField()
    escalation_due_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)
    last_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_workflow_cases_acted",
    )
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "module", "object_id"],
                condition=models.Q(is_deleted=False),
                name="uniq_open_workflow_case",
            )
        ]


class WorkflowHistory(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="dms_workflow_history"
    )
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="workflow_history",
    )
    case = models.ForeignKey(
        WorkflowCase,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="history",
    )
    kind = models.CharField(max_length=20, default="transition")
    from_state = models.CharField(max_length=80, blank=True, default="")
    to_state = models.CharField(max_length=80, blank=True, default="")
    label = models.CharField(max_length=80, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    detail = models.TextField(blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dms_workflow_history",
    )

    class Meta:
        ordering = ["-id"]
