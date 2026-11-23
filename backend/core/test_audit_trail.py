from datetime import date, timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from core.audit_middleware import MutationAuditMiddleware
from core.audit_text import classify_http, present
from core.models import AuditLog, Organization


class AuditLanguageTests(APITestCase):
    def test_http_create_reads_as_a_journal(self):
        info = classify_http("POST", "/api/finance/journals/", 201, "")
        self.assertEqual(info["event"], "Created journal entry")
        self.assertEqual(info["outcome"], "Completed")
        self.assertIn("Journals", info["area"])

    def test_http_approve_is_not_called_created(self):
        info = classify_http("POST", "/api/finance/journals/12/approve/", 200, "")
        self.assertEqual(info["event"], "Approved journal entry 12")
        self.assertEqual(info["stored_action"], "approved")
        self.assertEqual(info["href"], "/finance/journals/12")

    def test_plumbing_and_validation_are_dropped(self):
        self.assertIsNone(classify_http("POST", "/api/notifications/mark-read/", 200, ""))
        self.assertIsNone(classify_http("POST", "/api/finance/journals/", 400, "This field is required."))

    def test_integration_setup_denial_is_plain(self):
        info = classify_http("POST", "/api/settings/integrations/ensure-defaults/", 403, "")
        self.assertEqual(info["event"], "Not allowed to prepare the integration defaults")
        self.assertEqual(info["outcome"], "Denied")

    def test_control_failure_stays_readable(self):
        info = classify_http(
            "POST",
            "/api/finance/journals/4/approve/",
            400,
            "SoD violation: initiator cannot approve their own submission.",
        )
        self.assertEqual(info["outcome"], "Denied")
        self.assertIn("SoD", info["event"])

    def test_workflow_row_shows_the_state_change(self):
        log = SimpleNamespace(
            action="approve",
            module="finance.journals",
            object_type="JournalEntry",
            object_id="12",
            detail="submitted → approved",
            user=SimpleNamespace(username="sara", first_name="Sara", last_name="Khan"),
        )
        row = present(log)
        self.assertEqual(row["event"], "Approved journal entry 12")
        self.assertEqual(row["change"], "Changed from Submitted to Approved")
        self.assertEqual(row["who"], "Sara Khan (sara)")
        self.assertEqual(row["href"], "/finance/journals/12")
        self.assertEqual(row["outcome"], "Completed")

    def test_seed_dump_is_hidden(self):
        log = SimpleNamespace(
            action="seed",
            module="settings.audit",
            object_type="",
            object_id="",
            detail="Full JMC demo seed · employees=4 · packages=2",
            user=None,
        )
        row = present(log)
        self.assertEqual(row["event"], "Prepared starting company data")
        self.assertEqual(row["change"], "")
        self.assertEqual(row["who"], "System")


class AuditApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-audit",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.owner = User.objects.create_user("audit-owner", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.owner, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.owner
        self.org.save(update_fields=["owner"])

    def test_list_hides_noise_and_raw_fields(self):
        AuditLog.objects.create(
            organization=self.org,
            user=self.owner,
            action="post",
            module="finance",
            object_type="HTTP",
            object_id="201",
            detail="/api/finance/journals/",
        )
        AuditLog.objects.create(
            organization=self.org,
            user=self.owner,
            action="post",
            module="notifications",
            object_type="HTTP",
            object_id="200",
            detail="/api/notifications/mark-read/",
        )
        self.client.force_authenticate(self.owner)
        res = self.client.get("/api/settings/audit/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        row = res.data["results"][0]
        self.assertEqual(row["event"], "Created journal entry")
        self.assertEqual(row["role"], "Owner")
        self.assertEqual(res.data["denied"], 0)
        self.assertNotIn("object_type", row)
        self.assertNotIn("detail", row)
        self.assertNotIn("organization", row)

    def test_middleware_writes_plain_language_and_does_not_duplicate(self):
        from django.test import RequestFactory

        factory = RequestFactory()

        def created(request):
            return HttpResponse(status=201)

        request = factory.post("/api/hr/employees/")
        request.user = self.owner
        MutationAuditMiddleware(created)(request)
        log = AuditLog.objects.get()
        self.assertEqual(log.action, "created")
        self.assertEqual(log.object_type, "employee")

        def already(request):
            AuditLog.objects.create(
                organization=self.org,
                user=request.user,
                action="approve",
                module="finance.journals",
                object_type="JournalEntry",
                object_id="3",
                detail="submitted → approved",
            )
            return HttpResponse(status=200)

        request = factory.post("/api/finance/journals/3/approve/")
        request.user = self.owner
        MutationAuditMiddleware(already)(request)
        self.assertEqual(AuditLog.objects.filter(action="approve").count(), 1)
        self.assertFalse(AuditLog.objects.filter(action="approved", object_id="3").exists())
