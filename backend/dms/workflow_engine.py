"""Workflow engine for documents and the rest of SIERP."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.notifications import notify_org_roles
from dms.models import (
    Document,
    DocumentComment,
    DocumentFlow,
    DocumentSignature,
    WorkflowAction,
    WorkflowCase,
    WorkflowDefinition,
    WorkflowHistory,
    WorkflowState,
    WorkflowTransition,
    WorkflowTrigger,
)


logger = logging.getLogger(__name__)


def _due(state, when):
    if not state.escalation_hours:
        return None
    return when + timedelta(hours=state.escalation_hours)


def _history(doc, user, kind, label, from_name="", to_name="", comment="", detail=""):
    return WorkflowHistory.objects.create(
        organization=doc.organization,
        document=doc,
        kind=kind,
        from_state=from_name,
        to_state=to_name,
        label=label[:80],
        comment=comment,
        detail=detail,
        actor=user if getattr(user, "is_authenticated", False) else None,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )


def _run_action(action, doc, user, label):
    cfg = action.config or {}
    if action.action_type == WorkflowAction.Kind.SET_STATUS:
        status = str(cfg.get("status") or "")
        if status in dict(Document.Status.choices):
            doc.status = status
            doc.updated_by = user if getattr(user, "is_authenticated", False) else doc.updated_by
            doc.save(update_fields=["status", "updated_by", "updated_at"])
            _history(doc, user, "action", label, detail=f"Status set to {status}")
    elif action.action_type == WorkflowAction.Kind.ADD_COMMENT:
        body = str(cfg.get("message") or label or "Workflow comment")
        DocumentComment.objects.create(
            organization=doc.organization,
            document=doc,
            body=body,
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        from comments.services import add_record_comment

        add_record_comment(doc.organization, "dms.documents", doc.pk, body, user)
        _history(doc, user, "action", label, detail=body)
    elif action.action_type == WorkflowAction.Kind.NOTIFY:
        message = str(cfg.get("message") or f"{doc.title}: {label}")
        try:
            notify_org_roles(
                doc.organization,
                subject=f"Document workflow: {doc.title}",
                message=message,
                role_codes=["approver", "admin", "owner"],
                purpose="workflow",
                module="dms.documents",
                object_id=str(doc.pk),
                href=f"/dms/documents/{doc.pk}",
            )
        except Exception:
            logger.warning("workflow notify failed for document %s", doc.pk)
        _history(doc, user, "action", label, detail=message)
    elif action.action_type == WorkflowAction.Kind.NOTIFY_ROLE:
        code = str(cfg.get("role_code") or "").strip()
        message = str(cfg.get("message") or f"{doc.title}: {label}")
        try:
            notify_org_roles(
                doc.organization,
                subject=f"Document workflow: {doc.title}",
                message=message,
                role_codes=[code] if code else None,
                purpose="workflow",
                module="dms.documents",
                object_id=str(doc.pk),
                href=f"/dms/documents/{doc.pk}",
            )
        except Exception:
            logger.warning("workflow role notify failed for document %s", doc.pk)
        _history(doc, user, "action", label, detail=message)
    elif action.action_type == WorkflowAction.Kind.CREATE_TASK:
        from tasks.services import assign_task

        title = str(cfg.get("title") or cfg.get("message") or label or "Workflow task")
        assign_task(
            doc.organization,
            title,
            body=str(cfg.get("message") or ""),
            role_code=str(cfg.get("role_code") or ""),
            module="dms.documents",
            object_id=doc.pk,
            user=user,
        )
        _history(doc, user, "action", label, detail=title)


def _run_triggers(workflow, event, state, doc, user, label):
    from django.db.models import Q

    triggers = WorkflowTrigger.objects.filter(
        workflow=workflow, event=event, is_deleted=False
    ).filter(Q(state__isnull=True) | Q(state=state))
    for trigger in triggers:
        for action in trigger.actions.filter(is_deleted=False):
            _run_action(action, doc, user, label)


def preview(workflow: WorkflowDefinition) -> dict:
    states = []
    for state in workflow.states.filter(is_deleted=False).select_related("escalate_to_state"):
        states.append(
            {
                "id": state.id,
                "name": state.name,
                "code": state.code,
                "sort_order": state.sort_order,
                "is_initial": state.is_initial,
                "is_terminal": state.is_terminal,
                "escalation_hours": state.escalation_hours,
                "document_status": state.document_status,
                "escalate_to_id": state.escalate_to_state_id,
                "escalate_to_name": state.escalate_to_state.name if state.escalate_to_state_id else "",
            }
        )
    transitions = []
    for row in (
        workflow.transitions.filter(is_deleted=False)
        .select_related("from_state", "to_state")
        .prefetch_related("actions", "allowed_roles", "trigger_events")
    ):
        transitions.append(
            {
                "id": row.id,
                "label": row.label,
                "from_state_id": row.from_state_id,
                "to_state_id": row.to_state_id,
                "from_name": row.from_state.name,
                "to_name": row.to_state.name,
                "require_comment": row.require_comment,
                "require_signature": row.require_signature,
                "block_self_approval": row.block_self_approval,
                "roles": [role.name for role in row.allowed_roles.all()],
                "events": [item.event for item in row.trigger_events.all()],
                "actions": [
                    {"id": action.id, "action_type": action.action_type, "config": action.config}
                    for action in row.actions.all()
                ],
            }
        )
    triggers = []
    for trigger in workflow.triggers.filter(is_deleted=False).select_related("state"):
        triggers.append(
            {
                "id": trigger.id,
                "event": trigger.event,
                "state_id": trigger.state_id,
                "state_name": trigger.state.name if trigger.state_id else "",
                "actions": [
                    {"id": action.id, "action_type": action.action_type, "config": action.config}
                    for action in trigger.actions.filter(is_deleted=False)
                ],
            }
        )
    return {
        "id": workflow.id,
        "name": workflow.name,
        "states": states,
        "transitions": transitions,
        "triggers": triggers,
    }


def ensure_standard(organization, user=None) -> WorkflowDefinition:
    workflow = WorkflowDefinition.objects.filter(
        organization=organization, name="Document control"
    ).first()
    if workflow:
        return workflow
    workflow = WorkflowDefinition.objects.create(
        organization=organization,
        name="Document control",
        description="Draft, review, publish, and archive with signature and escalation.",
        is_active=True,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    specs = [
        ("draft", "Draft", 1, True, False, None, Document.Status.DRAFT, None),
        ("in_review", "In review", 2, False, False, 48, Document.Status.IN_REVIEW, None),
        ("published", "Published", 3, False, False, None, Document.Status.PUBLISHED, None),
        ("archived", "Archived", 4, False, True, None, Document.Status.ARCHIVED, None),
    ]
    states = {}
    for code, name, order, initial, terminal, hours, status, _esc in specs:
        states[code] = WorkflowState.objects.create(
            organization=organization,
            workflow=workflow,
            name=name,
            code=code,
            sort_order=order,
            is_initial=initial,
            is_terminal=terminal,
            escalation_hours=hours,
            document_status=status,
            created_by=workflow.created_by,
        )
    steps = [
        ("Submit for review", "draft", "in_review", False, False, False),
        ("Send back", "in_review", "draft", True, False, False),
        ("Publish", "in_review", "published", False, True, True),
        ("Archive", "published", "archived", False, False, False),
        ("Restore", "archived", "draft", True, False, False),
    ]
    for index, (label, src, dest, comment, signature, sod) in enumerate(steps, start=1):
        transition = WorkflowTransition.objects.create(
            organization=organization,
            workflow=workflow,
            from_state=states[src],
            to_state=states[dest],
            label=label,
            require_comment=comment,
            require_signature=signature,
            block_self_approval=sod,
            sort_order=index,
            created_by=workflow.created_by,
        )
        WorkflowAction.objects.create(
            organization=organization,
            workflow=workflow,
            transition=transition,
            action_type=WorkflowAction.Kind.SET_STATUS,
            config={"status": states[dest].document_status},
            created_by=workflow.created_by,
        )
    review_trigger = WorkflowTrigger.objects.create(
        organization=organization,
        workflow=workflow,
        event=WorkflowTrigger.Event.ON_ENTER,
        state=states["in_review"],
        created_by=workflow.created_by,
    )
    WorkflowAction.objects.create(
        organization=organization,
        workflow=workflow,
        trigger=review_trigger,
        action_type=WorkflowAction.Kind.NOTIFY,
        config={"message": "A document is waiting for review."},
        created_by=workflow.created_by,
    )
    overdue = WorkflowTrigger.objects.create(
        organization=organization,
        workflow=workflow,
        event=WorkflowTrigger.Event.ON_OVERDUE,
        state=states["in_review"],
        created_by=workflow.created_by,
    )
    WorkflowAction.objects.create(
        organization=organization,
        workflow=workflow,
        trigger=overdue,
        action_type=WorkflowAction.Kind.NOTIFY,
        config={"message": "Review escalation: the document is overdue."},
        created_by=workflow.created_by,
    )
    return workflow


def _initial_state(workflow):
    state = workflow.states.filter(is_deleted=False, is_initial=True).order_by("sort_order").first()
    if state is None:
        state = workflow.states.filter(is_deleted=False).order_by("sort_order").first()
    if state is None:
        raise ValidationError("This workflow has no states.")
    return state


def attach_default(doc: Document, user=None) -> DocumentFlow:
    existing = DocumentFlow.objects.filter(document=doc).first()
    if existing:
        return existing
    ensure_standard(doc.organization, user)
    workflow = None
    if doc.document_type_id:
        workflow = WorkflowDefinition.objects.filter(
            organization=doc.organization,
            document_type=doc.document_type,
            is_active=True,
            applies_to=WorkflowDefinition.Target.DOCUMENTS,
        ).first()
    if workflow is None:
        workflow = WorkflowDefinition.objects.filter(
            organization=doc.organization,
            is_active=True,
            applies_to=WorkflowDefinition.Target.DOCUMENTS,
        ).order_by("id").first()
    if workflow is None:
        raise ValidationError("No active document workflow.")
    state = _initial_state(workflow)
    now = timezone.now()
    flow = DocumentFlow.objects.create(
        organization=doc.organization,
        document=doc,
        workflow=workflow,
        state=state,
        entered_at=now,
        escalation_due_at=_due(state, now),
        last_actor=user if getattr(user, "is_authenticated", False) else None,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    if state.document_status and doc.status != state.document_status:
        doc.status = state.document_status
        doc.save(update_fields=["status", "updated_at"])
    _history(doc, user, "transition", "Started", to_name=state.name, detail=workflow.name)
    return flow


def snapshot(doc: Document) -> dict | None:
    flow = DocumentFlow.objects.filter(document=doc).select_related("state", "workflow").first()
    if flow is None:
        return None
    now = timezone.now()
    transitions = []
    for row in flow.state.outgoing.filter(is_deleted=False, workflow=flow.workflow).select_related("to_state"):
        transitions.append(
            {
                "id": row.id,
                "label": row.label,
                "to_state": row.to_state.name,
                "require_comment": row.require_comment,
                "require_signature": row.require_signature,
                "block_self_approval": row.block_self_approval,
            }
        )
    history = []
    for row in doc.workflow_history.all()[:30]:
        actor = row.actor.get_username() if row.actor_id else ""
        history.append(
            {
                "id": row.id,
                "kind": row.kind,
                "label": row.label,
                "from_state": row.from_state,
                "to_state": row.to_state,
                "comment": row.comment,
                "detail": row.detail,
                "actor": actor,
                "at": row.created_at,
            }
        )
    signatures = []
    for row in doc.signatures.all()[:20]:
        signatures.append(
            {
                "id": row.id,
                "signed_name": row.signed_name,
                "meaning": row.meaning,
                "actor": row.signer.get_username() if row.signer_id else "",
                "signed_at": row.created_at,
            }
        )
    return {
        "flow_id": flow.id,
        "workflow_id": flow.workflow_id,
        "workflow_name": flow.workflow.name,
        "state_id": flow.state_id,
        "state_name": flow.state.name,
        "entered_at": flow.entered_at,
        "escalation_due_at": flow.escalation_due_at,
        "overdue": bool(flow.escalation_due_at and now >= flow.escalation_due_at and not flow.escalated),
        "escalated": flow.escalated,
        "transitions": transitions,
        "history": history,
        "signatures": signatures,
        "preview": preview(flow.workflow),
    }


def apply_transition(doc: Document, user, transition_id, comment="", signed_name="", meaning="approve"):
    flow = DocumentFlow.objects.filter(document=doc).select_related("state", "workflow").first()
    if flow is None:
        flow = attach_default(doc, user)
    try:
        transition = WorkflowTransition.objects.select_related("from_state", "to_state").get(
            pk=transition_id, workflow=flow.workflow, is_deleted=False
        )
    except WorkflowTransition.DoesNotExist:
        raise ValidationError("That transition is not part of this workflow.")
    if transition.from_state_id != flow.state_id:
        raise ValidationError("That action is not available from the current state.")
    comment = (comment or "").strip()
    signed_name = (signed_name or "").strip()
    if transition.require_comment and not comment:
        raise ValidationError({"comment": "A comment is required for this action."})
    if transition.require_signature and not signed_name:
        raise ValidationError({"signed_name": "Type your name to sign this action."})
    actor_id = getattr(user, "id", None)
    previous_actor = flow.last_actor_id or doc.created_by_id
    if transition.block_self_approval and previous_actor and previous_actor == actor_id:
        raise ValidationError("SoD violation: the previous actor cannot take this action.")
    if doc.checked_out_by_id and doc.checked_out_by_id != actor_id:
        from core.access import is_owner

        if not is_owner(user):
            raise ValidationError("Document is checked out by another user.")
    _run_triggers(flow.workflow, WorkflowTrigger.Event.ON_LEAVE, flow.state, doc, user, transition.label)
    previous = flow.state
    now = timezone.now()
    flow.state = transition.to_state
    flow.entered_at = now
    flow.escalation_due_at = _due(transition.to_state, now)
    flow.escalated = False
    flow.last_actor = user
    flow.updated_by = user
    flow.save(
        update_fields=[
            "state",
            "entered_at",
            "escalation_due_at",
            "escalated",
            "last_actor",
            "updated_by",
            "updated_at",
        ]
    )
    if transition.to_state.document_status in dict(Document.Status.choices):
        doc.status = transition.to_state.document_status
        doc.updated_by = user
        doc.save(update_fields=["status", "updated_by", "updated_at"])
    signature = None
    if transition.require_signature:
        signature = DocumentSignature.objects.create(
            organization=doc.organization,
            document=doc,
            transition=transition,
            signer=user,
            signed_name=signed_name[:160],
            meaning=meaning if meaning in dict(DocumentSignature.Meaning.choices) else DocumentSignature.Meaning.APPROVE,
            created_by=user,
        )
    _history(
        doc,
        user,
        "transition",
        transition.label,
        from_name=previous.name,
        to_name=transition.to_state.name,
        comment=comment,
        detail=f"Signed by {signed_name}" if signature else "",
    )
    for action in transition.actions.filter(is_deleted=False):
        _run_action(action, doc, user, transition.label)
    _run_triggers(flow.workflow, WorkflowTrigger.Event.ON_ENTER, transition.to_state, doc, user, transition.label)
    return doc


def escalate(doc: Document, user):
    flow = DocumentFlow.objects.filter(document=doc).select_related("state", "workflow").first()
    if flow is None:
        raise ValidationError("This document has no workflow.")
    now = timezone.now()
    if not flow.escalation_due_at or now < flow.escalation_due_at:
        raise ValidationError("This document is not due for escalation.")
    if flow.escalated:
        raise ValidationError("Escalation already ran for this state.")
    flow.escalated = True
    flow.updated_by = user
    target = flow.state.escalate_to_state
    detail = f"Overdue in {flow.state.name}"
    if target and target.workflow_id == flow.workflow_id:
        flow.state = target
        flow.entered_at = now
        flow.escalation_due_at = _due(target, now)
        flow.escalated = False
        detail = f"Escalated to {target.name}"
        if target.document_status in dict(Document.Status.choices):
            doc.status = target.document_status
            doc.updated_by = user
            doc.save(update_fields=["status", "updated_by", "updated_at"])
    flow.save(
        update_fields=[
            "state",
            "entered_at",
            "escalation_due_at",
            "escalated",
            "updated_by",
            "updated_at",
        ]
    )
    DocumentComment.objects.create(
        organization=doc.organization,
        document=doc,
        body=detail,
        created_by=user,
    )
    _history(doc, user, "escalation", "Escalate", to_name=flow.state.name, detail=detail)
    _run_triggers(flow.workflow, WorkflowTrigger.Event.ON_OVERDUE, flow.state, doc, user, "Escalate")
    try:
        notify_org_roles(
            doc.organization,
            subject=f"Document escalation: {doc.title}",
            message=detail,
            role_codes=["approver", "admin", "owner"],
            purpose="workflow",
            module="dms.documents",
            object_id=str(doc.pk),
            href=f"/dms/documents/{doc.pk}",
        )
    except Exception:
        logger.warning("escalation notify failed for document %s", doc.pk)
    return doc


ACTION_LABELS = {
    "submit": ("submit", "submit for review", "submit for approval"),
    "approve": ("approve", "publish", "approved"),
    "reject": ("reject", "send back", "rejected"),
    "post": ("post", "posted"),
}


def _actor(user):
    return user if getattr(user, "is_authenticated", False) else None


def _case_history(case, user, kind, label, from_name="", to_name="", comment="", detail=""):
    return WorkflowHistory.objects.create(
        organization=case.organization,
        document=None,
        case=case,
        kind=kind,
        from_state=from_name,
        to_state=to_name,
        label=(label or "")[:80],
        comment=comment,
        detail=detail,
        actor=_actor(user),
        created_by=_actor(user),
    )


def _notify_case(case, user, label, message):
    try:
        notify_org_roles(
            case.organization,
            subject=f"Workflow: {case.module} #{case.object_id}",
            message=message,
            role_codes=["approver", "admin", "owner", "finance", "hr", "payroll"],
            purpose="workflow",
            module=case.module,
            object_id=str(case.object_id),
        )
    except Exception:
        logger.warning("workflow notify failed for %s #%s", case.module, case.object_id)
    _case_history(case, user, "action", label, detail=message)


def _run_case_notices(case, user, label):
    from django.db.models import Q

    transition = (
        WorkflowTransition.objects.filter(
            workflow=case.workflow, to_state=case.state, label=label, is_deleted=False
        )
        .order_by("id")
        .first()
    )
    actions = []
    if transition is not None:
        actions.extend(transition.actions.filter(is_deleted=False))
    triggers = WorkflowTrigger.objects.filter(
        workflow=case.workflow,
        event=WorkflowTrigger.Event.ON_ENTER,
        is_deleted=False,
    ).filter(Q(state__isnull=True) | Q(state=case.state))
    for trigger in triggers:
        actions.extend(trigger.actions.filter(is_deleted=False))
    for action in actions:
        cfg = action.config or {}
        if action.action_type == WorkflowAction.Kind.NOTIFY:
            message = str(cfg.get("message") or f"{case.module} #{case.object_id}: {label}")
            _notify_case(case, user, label, message)
        elif action.action_type == WorkflowAction.Kind.NOTIFY_ROLE:
            code = str(cfg.get("role_code") or "").strip()
            message = str(cfg.get("message") or f"{case.module} #{case.object_id}: {label}")
            try:
                notify_org_roles(
                    case.organization,
                    subject=f"Workflow: {case.module} #{case.object_id}",
                    message=message,
                    role_codes=[code] if code else None,
                    purpose="workflow",
                    module=case.module,
                    object_id=str(case.object_id),
                )
            except Exception:
                logger.warning("workflow role notify failed for %s #%s", case.module, case.object_id)
            _case_history(case, user, "action", label, detail=message)
        elif action.action_type == WorkflowAction.Kind.ADD_COMMENT:
            from comments.services import add_record_comment

            body = str(cfg.get("message") or label or "Workflow comment")
            add_record_comment(case.organization, case.module, case.object_id, body, user)
            _case_history(case, user, "action", label, detail=body)
        elif action.action_type == WorkflowAction.Kind.CREATE_TASK:
            from tasks.services import assign_task

            title = str(cfg.get("title") or cfg.get("message") or label or "Workflow task")
            assign_task(
                case.organization,
                title,
                body=str(cfg.get("message") or ""),
                role_code=str(cfg.get("role_code") or ""),
                module=case.module,
                object_id=case.object_id,
                user=user,
            )
            _case_history(case, user, "action", label, detail=title)


def launch_case(org, module, object_id, user=None):
    if org is None or not module or module == WorkflowDefinition.Target.DOCUMENTS:
        return None
    existing = WorkflowCase.objects.filter(
        organization=org, module=module, object_id=str(object_id)
    ).first()
    if existing:
        return existing
    workflow = (
        WorkflowDefinition.objects.filter(
            organization=org, is_active=True, applies_to=module
        )
        .order_by("id")
        .first()
    )
    if workflow is None:
        return None
    try:
        state = _initial_state(workflow)
    except ValidationError:
        return None
    now = timezone.now()
    return WorkflowCase.objects.create(
        organization=org,
        module=module,
        object_id=str(object_id),
        workflow=workflow,
        state=state,
        entered_at=now,
        escalation_due_at=_due(state, now),
        last_actor=_actor(user),
        created_by=_actor(user),
    )


def _event_code(action_name):
    raw = (action_name or "").strip().lower()
    if raw.startswith("record."):
        return raw
    mapped = {
        "create": "record.created",
        "created": "record.created",
        "update": "record.updated",
        "updated": "record.updated",
        "submit": "record.submitted",
        "submitted": "record.submitted",
        "approve": "record.approved",
        "approved": "record.approved",
        "reject": "record.rejected",
        "rejected": "record.rejected",
        "post": "record.posted",
        "posted": "record.posted",
    }
    return mapped.get(raw, f"record.{raw}")


def _match_transition(case, action_name):
    event = _event_code(action_name)
    rows = list(case.state.outgoing.filter(workflow=case.workflow).prefetch_related("trigger_events"))
    for row in rows:
        if any(item.event == event for item in row.trigger_events.all()):
            return row
    raw = (action_name or "").strip().lower()
    if raw.startswith("record."):
        raw = raw.split(".", 1)[1]
    wanted = {raw, raw.replace("_", " ")}
    for alias in ACTION_LABELS.get(raw, ()):
        wanted.add(alias.lower())
    for row in rows:
        if row.label.strip().lower() in wanted:
            return row
    return None


def actor_may_take(user, transition):
    role_ids = list(transition.allowed_roles.values_list("id", flat=True))
    if not role_ids:
        return True
    from core.access import is_owner

    if is_owner(user):
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    if profile and profile.primary_role_id in role_ids:
        return True
    from accounts.models import UserRole

    return UserRole.objects.filter(user_id=user.id, role_id__in=role_ids).exists()


def _state_for_action(org, module, object_id, workflow):
    case = (
        WorkflowCase.objects.filter(organization=org, module=module, object_id=str(object_id))
        .select_related("state")
        .first()
    )
    if case is not None:
        return case.state
    return _initial_state(workflow)


def guard_module_action(org, module, object_id, user, action_name):
    """Block the desk action when the matching step is limited to other roles."""
    if org is None or not module or module == WorkflowDefinition.Target.DOCUMENTS:
        return None
    workflow = (
        WorkflowDefinition.objects.filter(organization=org, is_active=True, applies_to=module)
        .order_by("id")
        .first()
    )
    if workflow is None:
        return None
    try:
        state = _state_for_action(org, module, object_id, workflow)
    except ValidationError:
        return None

    class _Holder:
        pass

    holder = _Holder()
    holder.state = state
    holder.workflow = workflow
    transition = _match_transition(holder, action_name)
    if transition is None or actor_may_take(user, transition):
        return None
    return "Your role cannot take this workflow step."


def advance_case(case, transition, user, comment="", signed_name="", enforce_gates=True, fields=None):
    if transition.workflow_id != case.workflow_id or transition.from_state_id != case.state_id:
        raise ValidationError("That action is not available from the current state.")
    comment = (comment or "").strip()
    signed_name = (signed_name or "").strip()
    supplied = fields if isinstance(fields, dict) else {}
    actor = _actor(user)
    if enforce_gates:
        if not actor_may_take(user, transition):
            raise ValidationError("Your role cannot take this workflow step.")
        if transition.require_comment and not comment:
            raise ValidationError({"comment": "A comment is required for this action."})
        if transition.require_signature and not signed_name:
            raise ValidationError({"signed_name": "Type your name to sign this action."})
        if transition.block_self_approval and case.last_actor_id and actor and case.last_actor_id == actor.id:
            raise ValidationError("SoD violation: the previous actor cannot take this action.")
        missing = {}
        for field in transition.fields.all():
            if field.required and not str(supplied.get(field.name) or "").strip():
                missing[field.name] = f"{field.label} is required."
        if missing:
            raise ValidationError(missing)
    previous = case.state
    now = timezone.now()
    case.state = transition.to_state
    case.entered_at = now
    case.escalation_due_at = _due(transition.to_state, now)
    case.escalated = False
    case.last_actor = actor
    case.updated_by = actor
    update_fields = [
        "state",
        "entered_at",
        "escalation_due_at",
        "escalated",
        "last_actor",
        "updated_by",
        "updated_at",
    ]
    if supplied:
        merged = dict(case.context or {})
        merged.update({key: value for key, value in supplied.items() if value not in (None, "")})
        case.context = merged
        update_fields.append("context")
    case.save(update_fields=update_fields)
    detail = f"Signed by {signed_name}" if signed_name else ""
    _case_history(
        case,
        user,
        "transition",
        transition.label,
        from_name=previous.name,
        to_name=transition.to_state.name,
        comment=comment,
        detail=detail,
    )
    _run_case_notices(case, user, transition.label)
    return case


def on_record_event(org, module, object_id, user, event):
    """Launch or move a case when an ERP record is created or changes state."""
    if org is None or not module or module == WorkflowDefinition.Target.DOCUMENTS:
        return None
    case = launch_case(org, module, object_id, user)
    if case is None:
        return None
    action_name = event.split(".", 1)[1] if str(event).startswith("record.") else event
    transition = _match_transition(case, action_name)
    if transition is None:
        if not str(event).endswith(".created"):
            _case_history(
                case,
                user,
                "note",
                action_name or "",
                detail=f"No transition for {event} from {case.state.name}.",
            )
        return case
    if not actor_may_take(user, transition):
        _case_history(
            case,
            user,
            "blocked",
            transition.label,
            detail="This role cannot take this step.",
        )
        return case
    return advance_case(case, transition, user, enforce_gates=False)


def sync_module_case(org, module, object_id, user, action_name):
    """Follow submit, approve, reject, and post when a workflow applies to that area."""
    return on_record_event(org, module, object_id, user, f"record.{action_name}")
