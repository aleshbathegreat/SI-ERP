from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import ApprovalMatrixRule, Organization
from finance.models import Budget
from hr.models import Employee, LeaveRequest, LeaveType, RecruitmentRequest
from payroll.models import PayrollPeriod


class ApprovalsInboxTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.owner = User.objects.create_user("owner1", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.owner, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.owner
        self.org.save()
        ensure_default_roles(self.org)
        self.approver = User.objects.create_user("appr1", password="x-long-password-2")
        UserProfile.objects.create(
            user=self.approver,
            organization=self.org,
            role=UserProfile.RoleCode.APPROVER,
        )
        self.client = APIClient()

    def test_approve_url_is_api_relative_and_approver_can_approve(self):
        budget = Budget.objects.create(
            organization=self.org,
            name="FY budget",
            fiscal_year=2026,
            amount=1000,
            status=Budget.Status.SUBMITTED,
            created_by=self.owner,
        )
        RecruitmentRequest.objects.create(
            organization=self.org, title="Open role", status=RecruitmentRequest.Status.OPEN
        )
        interview = RecruitmentRequest.objects.create(
            organization=self.org,
            title="Interview role",
            status=RecruitmentRequest.Status.INTERVIEW,
            created_by=self.owner,
        )

        self.client.force_authenticate(self.approver)
        inbox = self.client.get("/api/approvals/inbox/")
        self.assertEqual(inbox.status_code, 200, inbox.content)
        kinds = {item["kind"]: item for item in inbox.data["items"]}
        self.assertIn("budget", kinds)
        self.assertIn("recruitment", kinds)
        self.assertEqual(kinds["recruitment"]["id"], interview.id)
        self.assertFalse(kinds["budget"]["approve_url"].startswith("/api/"))
        self.assertTrue(kinds["budget"]["approve_url"].endswith(f"{budget.id}/approve/"))

        approved = self.client.post("/api/" + kinds["budget"]["approve_url"])
        self.assertEqual(approved.status_code, 200, approved.content)
        budget.refresh_from_db()
        self.assertEqual(budget.status, Budget.Status.APPROVED)

    def test_inbox_is_limited_to_the_role_that_can_approve(self):
        User = get_user_model()
        payroll = User.objects.create_user("pay1", password="x-long-password-3")
        UserProfile.objects.create(
            user=payroll, organization=self.org, role=UserProfile.RoleCode.PAYROLL
        )
        hr = User.objects.create_user("hr1", password="x-long-password-4")
        UserProfile.objects.create(
            user=hr, organization=self.org, role=UserProfile.RoleCode.HR
        )
        Budget.objects.create(
            organization=self.org,
            name="FY budget",
            fiscal_year=2026,
            amount=1000,
            status=Budget.Status.SUBMITTED,
            created_by=self.owner,
        )
        PayrollPeriod.objects.create(
            organization=self.org,
            name="Nov 2026",
            year=2026,
            month=11,
            status=PayrollPeriod.Status.PROCESSING,
            created_by=self.owner,
        )
        employee = Employee.objects.create(
            organization=self.org,
            employee_code="E1",
            first_name="Ada",
            last_name="Khan",
            email="ada@example.com",
        )
        leave_type = LeaveType.objects.create(
            organization=self.org, name="Annual", code="AL"
        )
        LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=date.today(),
            end_date=date.today(),
            days=1,
            status=LeaveRequest.Status.PENDING,
            created_by=self.owner,
        )

        self.client.force_authenticate(payroll)
        payroll_kinds = {
            item["kind"] for item in self.client.get("/api/approvals/inbox/").data["items"]
        }
        self.assertEqual(payroll_kinds, {"payroll"})

        self.client.force_authenticate(hr)
        hr_kinds = {
            item["kind"] for item in self.client.get("/api/approvals/inbox/").data["items"]
        }
        self.assertIn("leave", hr_kinds)
        self.assertNotIn("payroll", hr_kinds)
        self.assertNotIn("budget", hr_kinds)

    def test_matrix_hides_bands_outside_the_role(self):
        User = get_user_model()
        finance = User.objects.create_user("fin1", password="x-long-password-5")
        UserProfile.objects.create(
            user=finance, organization=self.org, role=UserProfile.RoleCode.FINANCE
        )
        Budget.objects.create(
            organization=self.org,
            name="Large",
            fiscal_year=2026,
            amount=50000,
            status=Budget.Status.SUBMITTED,
            created_by=self.owner,
        )
        ApprovalMatrixRule.objects.create(
            organization=self.org,
            module_key="finance.budgets",
            min_amount=0,
            role_code="finance",
        )
        self.client.force_authenticate(self.approver)
        approver_kinds = {
            item["kind"] for item in self.client.get("/api/approvals/inbox/").data["items"]
        }
        self.assertNotIn("budget", approver_kinds)

        self.client.force_authenticate(finance)
        finance_kinds = {
            item["kind"] for item in self.client.get("/api/approvals/inbox/").data["items"]
        }
        self.assertIn("budget", finance_kinds)

    def test_submitter_sees_the_row_but_cannot_act(self):
        Budget.objects.create(
            organization=self.org,
            name="Own",
            fiscal_year=2026,
            amount=10,
            status=Budget.Status.SUBMITTED,
            created_by=self.approver,
        )
        self.client.force_authenticate(self.approver)
        row = next(
            item
            for item in self.client.get("/api/approvals/inbox/").data["items"]
            if item["kind"] == "budget"
        )
        self.assertFalse(row["can_act"])
        self.assertTrue(row["block_reason"])
