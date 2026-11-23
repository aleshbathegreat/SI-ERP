from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from finance.models import TaxChallan
from hr.models import Department
from payroll.models import PayrollPeriod


class UniqueConflictTests(APITestCase):
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

    def test_duplicate_department_is_400_and_deleted_code_can_be_reused(self):
        payload = {"name": "Finance", "code": "FIN"}
        created = self.client.post("/api/hr/departments/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.content)

        again = self.client.post("/api/hr/departments/", payload, format="json")
        self.assertEqual(again.status_code, 400, again.content)
        self.assertIn("already exists", str(again.data))

        other = self.client.post(
            "/api/hr/departments/",
            {"name": "Human Resources", "code": "HR"},
            format="json",
        )
        self.assertEqual(other.status_code, 201, other.content)
        clash = self.client.patch(
            f"/api/hr/departments/{other.data['id']}/",
            {"code": "FIN"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, clash.content)
        self.assertNotEqual(clash.status_code, 500)

        deleted = self.client.delete(f"/api/hr/departments/{created.data['id']}/")
        self.assertIn(deleted.status_code, (200, 204), deleted.content)
        hidden = Department.all_objects.get(pk=created.data["id"])
        self.assertTrue(hidden.code.endswith(f"-d{hidden.pk}"))

        reused = self.client.post("/api/hr/departments/", payload, format="json")
        self.assertEqual(reused.status_code, 201, reused.content)
        self.assertNotEqual(reused.data["id"], created.data["id"])

    def test_duplicate_payroll_period_is_400_and_soft_deleted_is_restored(self):
        payload = {"name": "2026-03", "year": 2026, "month": 3}
        created = self.client.post("/api/payroll/periods/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.content)

        again = self.client.post("/api/payroll/periods/", payload, format="json")
        self.assertEqual(again.status_code, 400, again.content)
        self.assertIn("already exists", str(again.data))

        period = PayrollPeriod.objects.get(pk=created.data["id"])
        period.is_deleted = True
        period.save(update_fields=["is_deleted"])

        restored = self.client.post(
            "/api/payroll/periods/",
            {"name": "March 2026", "year": 2026, "month": 3},
            format="json",
        )
        self.assertEqual(restored.status_code, 201, restored.content)
        self.assertEqual(restored.data["id"], period.id)
        period.refresh_from_db()
        self.assertFalse(period.is_deleted)
        self.assertEqual(period.name, "March 2026")

    def test_deleted_document_number_is_released_on_recreate(self):
        original = TaxChallan.all_objects.create(
            organization=self.org,
            challan_no="CH-1",
            period_label="2026-10",
            is_deleted=True,
        )
        created = TaxChallan.objects.create(
            organization=self.org,
            challan_no="CH-1",
            period_label="2026-10",
        )
        original.refresh_from_db()
        self.assertNotEqual(created.pk, original.pk)
        self.assertTrue(original.challan_no.endswith(f"-d{original.pk}"))
        self.assertEqual(created.challan_no, "CH-1")
