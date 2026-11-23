from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from finance.models import Account, AccountingPeriod, JournalEntry


class AccountingPeriodCreateTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("owner1", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_duplicate_period_is_400_and_soft_deleted_is_restored(self):
        payload = {"name": "2026-10", "year": 2026, "month": 10, "is_locked": False}
        created = self.client.post("/api/finance/periods/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.content)

        again = self.client.post("/api/finance/periods/", payload, format="json")
        self.assertEqual(again.status_code, 400, again.content)
        self.assertIn("already exists", str(again.data))

        period = AccountingPeriod.objects.get(pk=created.data["id"])
        period.is_deleted = True
        period.save(update_fields=["is_deleted"])

        restored = self.client.post(
            "/api/finance/periods/",
            {"name": "October 2026", "year": 2026, "month": 10, "is_locked": False},
            format="json",
        )
        self.assertEqual(restored.status_code, 201, restored.content)
        self.assertEqual(restored.data["id"], period.id)
        period.refresh_from_db()
        self.assertFalse(period.is_deleted)
        self.assertEqual(period.name, "October 2026")

        bad = self.client.post(
            "/api/finance/periods/",
            {"name": "bad", "year": 2026, "month": 13},
            format="json",
        )
        self.assertEqual(bad.status_code, 400, bad.content)

    def test_blank_name_is_not_reported_as_a_duplicate_period(self):
        res = self.client.post(
            "/api/finance/periods/",
            {"name": " ", "year": 2026, "month": 3},
            format="json",
        )
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("name", res.data)
        self.assertNotIn("already exists", str(res.data).lower())

    def test_edit_same_period_does_not_report_duplicate(self):
        created = self.client.post(
            "/api/finance/periods/",
            {"name": "Jan", "year": 2026, "month": 1, "is_locked": False},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        patched = self.client.patch(
            f"/api/finance/periods/{created.data['id']}/",
            {"name": "January 2026", "year": 2026, "month": 1, "is_locked": False},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertEqual(patched.data["name"], "January 2026")

    def test_edit_onto_another_period_names_that_month(self):
        first = self.client.post(
            "/api/finance/periods/",
            {"name": "Jan", "year": 2026, "month": 1},
            format="json",
        )
        second = self.client.post(
            "/api/finance/periods/",
            {"name": "Feb", "year": 2026, "month": 2},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        clash = self.client.patch(
            f"/api/finance/periods/{second.data['id']}/",
            {"name": "Feb", "year": 2026, "month": 1},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, clash.content)
        self.assertIn("2026-01", str(clash.data))
        self.assertNotIn("2026-02", str(clash.data))


class AccountRequiredTests(AccountingPeriodCreateTests):
    def test_blank_code_is_assigned_and_name_stays_required(self):
        missing_name = self.client.post(
            "/api/finance/accounts/",
            {"code": " ", "name": "", "account_type": "expense"},
            format="json",
        )
        self.assertEqual(missing_name.status_code, 400, missing_name.content)
        self.assertIn("name", missing_name.data)
        self.assertNotIn("code", missing_name.data)

        created = self.client.post(
            "/api/finance/accounts/",
            {"name": "Cash", "account_type": "expense", "is_active": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertTrue(str(created.data["code"]).upper().startswith("GL-"))
        self.assertTrue(Account.objects.filter(name="Cash").exists())

    def test_account_saves_when_code_and_name_are_sent(self):
        res = self.client.post(
            "/api/finance/accounts/",
            {"code": "1100", "name": "Cash", "account_type": "expense", "is_active": True},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(Account.objects.filter(code="1100", name="Cash").exists())


class JournalRejectSodTests(AccountingPeriodCreateTests):
    def _journal(self):
        return JournalEntry.objects.create(
            organization=self.org,
            entry_date=date.today(),
            narration="sod",
            status=JournalEntry.Status.DRAFT,
            created_by=self.user,
        )

    def test_reject_own_submission_is_allowed(self):
        je = self._journal()
        submitted = self.client.post(f"/api/finance/journals/{je.id}/submit/")
        self.assertEqual(submitted.status_code, 200, submitted.content)
        rejected = self.client.post(f"/api/finance/journals/{je.id}/reject/")
        self.assertEqual(rejected.status_code, 200, rejected.content)
        self.assertEqual(rejected.data["status"], "rejected")

    def test_approve_own_submission_stays_blocked(self):
        je = self._journal()
        self.client.post(f"/api/finance/journals/{je.id}/submit/")
        approved = self.client.post(f"/api/finance/journals/{je.id}/approve/")
        self.assertEqual(approved.status_code, 400, approved.content)
        self.assertIn("initiator cannot approve", str(approved.data).lower())
