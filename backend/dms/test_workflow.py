from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from dms.models import DocumentFlow


class DocumentWorkflowTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-flow",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("flow-owner", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _transition(self, doc, label):
        return next(row for row in doc["workflow"]["transitions"] if row["label"] == label)

    def test_standard_workflow_signature_sod_and_escalation(self):
        created = self.client.post("/api/dms/documents/", {"title": "Policy"}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data["workflow"]["state_name"], "Draft")
        self.assertEqual(created.data["workflow"]["preview"]["states"][0]["name"], "Draft")
        self.assertTrue(created.data["workflow"]["preview"]["triggers"])

        doc_id = created.data["id"]
        submit = self._transition(created.data, "Submit for review")
        moved = self.client.post(
            f"/api/dms/documents/{doc_id}/transition/",
            {"transition": submit["id"]},
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(moved.data["status"], "in_review")
        self.assertEqual(moved.data["workflow"]["state_name"], "In review")
        self.assertTrue(any(row["kind"] == "action" for row in moved.data["workflow"]["history"]))

        publish = self._transition(moved.data, "Publish")
        unsigned = self.client.post(
            f"/api/dms/documents/{doc_id}/transition/",
            {"transition": publish["id"]},
            format="json",
        )
        self.assertEqual(unsigned.status_code, 400, unsigned.content)
        blocked = self.client.post(
            f"/api/dms/documents/{doc_id}/transition/",
            {"transition": publish["id"], "signed_name": "Flow Owner", "meaning": "approve"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400, blocked.content)
        self.assertIn("SoD", str(blocked.data))

        DocumentFlow.objects.filter(document_id=doc_id).update(
            escalation_due_at=timezone.now() - timedelta(hours=1)
        )
        overdue = self.client.get(f"/api/dms/documents/{doc_id}/")
        self.assertTrue(overdue.data["workflow"]["overdue"])
        escalated = self.client.post(f"/api/dms/documents/{doc_id}/escalate/")
        self.assertEqual(escalated.status_code, 200, escalated.content)
        self.assertTrue(escalated.data["workflow"]["escalated"])
        self.assertTrue(
            any(row["kind"] == "escalation" for row in escalated.data["workflow"]["history"])
        )

        preview = self.client.get(f"/api/dms/workflows/{created.data['workflow']['workflow_id']}/preview/")
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertGreaterEqual(len(preview.data["transitions"]), 5)

    def test_case_follows_a_journal_post(self):
        from dms.models import WorkflowCase, WorkflowDefinition, WorkflowState, WorkflowTransition
        from dms.workflow_engine import sync_module_case

        workflow = WorkflowDefinition.objects.create(
            organization=self.org,
            name="Journal control",
            applies_to="finance.journals",
            is_active=True,
            created_by=self.user,
        )
        draft = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Draft",
            code="draft",
            is_initial=True,
            sort_order=1,
            created_by=self.user,
        )
        posted = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Posted",
            code="posted",
            is_terminal=True,
            sort_order=2,
            created_by=self.user,
        )
        WorkflowTransition.objects.create(
            organization=self.org,
            workflow=workflow,
            from_state=draft,
            to_state=posted,
            label="Post",
            created_by=self.user,
        )
        sync_module_case(self.org, "finance.journals", 42, self.user, "post")
        case = WorkflowCase.objects.get(module="finance.journals", object_id="42")
        self.assertEqual(case.state_id, posted.id)
        self.assertEqual(case.workflow_id, workflow.id)

    def test_role_blocks_a_step_and_an_event_opens_it(self):
        from accounts.models import Role, UserRole
        from dms.models import WorkflowDefinition, WorkflowState, WorkflowTransition, WorkflowTransitionEvent
        from dms.workflow_engine import guard_module_action, on_record_event

        User = get_user_model()
        clerk = User.objects.create_user("flow-clerk", password="x-long-password-1")
        UserProfile.objects.create(
            user=clerk, organization=self.org, role=UserProfile.RoleCode.EMPLOYEE
        )
        role = Role.objects.create(organization=self.org, name="Journal approver", code="journal-approver")
        workflow = WorkflowDefinition.objects.create(
            organization=self.org,
            name="Journal events",
            applies_to="finance.journals",
            is_active=True,
            created_by=self.user,
        )
        draft = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Draft",
            code="draft",
            is_initial=True,
            created_by=self.user,
        )
        posted = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Posted",
            code="posted",
            is_terminal=True,
            created_by=self.user,
        )
        step = WorkflowTransition.objects.create(
            organization=self.org,
            workflow=workflow,
            from_state=draft,
            to_state=posted,
            label="Release",
            created_by=self.user,
        )
        step.allowed_roles.add(role)
        WorkflowTransitionEvent.objects.create(
            organization=self.org,
            workflow=workflow,
            transition=step,
            event="record.posted",
            created_by=self.user,
        )
        self.assertEqual(
            guard_module_action(self.org, "finance.journals", 9, clerk, "post"),
            "Your role cannot take this workflow step.",
        )
        UserRole.objects.create(user=clerk, role=role)
        self.assertIsNone(guard_module_action(self.org, "finance.journals", 9, clerk, "post"))
        on_record_event(self.org, "finance.journals", 9, clerk, "record.posted")
        from dms.models import WorkflowCase

        case = WorkflowCase.objects.get(module="finance.journals", object_id="9")
        self.assertEqual(case.state_id, posted.id)

    def test_workflow_writes_inbox_comment_and_task(self):
        from comments.models import RecordComment
        from dms.models import WorkflowAction, WorkflowDefinition, WorkflowState, WorkflowTransition
        from dms.workflow_engine import sync_module_case
        from notifications.models import InboxMessage
        from tasks.models import WorkTask

        workflow = WorkflowDefinition.objects.create(
            organization=self.org,
            name="Journal notices",
            applies_to="finance.journals",
            is_active=True,
            created_by=self.user,
        )
        draft = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Draft",
            code="draft",
            is_initial=True,
            created_by=self.user,
        )
        posted = WorkflowState.objects.create(
            organization=self.org,
            workflow=workflow,
            name="Posted",
            code="posted",
            is_terminal=True,
            created_by=self.user,
        )
        step = WorkflowTransition.objects.create(
            organization=self.org,
            workflow=workflow,
            from_state=draft,
            to_state=posted,
            label="Post",
            created_by=self.user,
        )
        WorkflowAction.objects.create(
            organization=self.org,
            workflow=workflow,
            transition=step,
            action_type=WorkflowAction.Kind.NOTIFY,
            config={"message": "Journal posted"},
            created_by=self.user,
        )
        WorkflowAction.objects.create(
            organization=self.org,
            workflow=workflow,
            transition=step,
            action_type=WorkflowAction.Kind.ADD_COMMENT,
            config={"message": "Posted by workflow"},
            created_by=self.user,
        )
        WorkflowAction.objects.create(
            organization=self.org,
            workflow=workflow,
            transition=step,
            action_type=WorkflowAction.Kind.CREATE_TASK,
            config={"title": "File the journal", "role_code": "owner", "message": "Archive the posting"},
            created_by=self.user,
        )
        sync_module_case(self.org, "finance.journals", 77, self.user, "post")
        self.assertTrue(
            InboxMessage.objects.filter(recipient=self.user, title__contains="finance.journals").exists()
        )
        self.assertTrue(
            RecordComment.objects.filter(module="finance.journals", object_id="77", body="Posted by workflow").exists()
        )
        self.assertTrue(WorkTask.objects.filter(title="File the journal", role_code="owner").exists())
        inbox = self.client.get("/api/inbox/")
        self.assertEqual(inbox.status_code, 200, inbox.content)
        self.assertGreaterEqual(inbox.data["count"], 1)
        tasks = self.client.get("/api/work-tasks/")
        self.assertEqual(tasks.status_code, 200, tasks.content)
        task_id = tasks.data["results"][0]["id"]
        done = self.client.post(f"/api/work-tasks/{task_id}/complete/")
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.data["status"], "done")
        note = self.client.post(
            "/api/comments/",
            {"module": "finance.journals", "object_id": "77", "body": "Looks right"},
            format="json",
        )
        self.assertEqual(note.status_code, 201, note.content)
        listed = self.client.get("/api/comments/", {"module": "finance.journals", "object_id": "77"})
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertGreaterEqual(listed.data["count"], 2)
