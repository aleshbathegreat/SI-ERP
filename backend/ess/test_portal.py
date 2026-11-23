from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import AuditLog, Organization
from hr.models import AttendanceRecord, Employee, PerformanceReview


class EssPortalTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="ess-portal",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        ensure_default_roles(self.org)
        User = get_user_model()
        self.user = User.objects.create_user("ess-portal", password="x-long-password-1", first_name="Ada")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.EMPLOYEE
        )
        self.me = Employee.objects.create(
            organization=self.org,
            user=self.user,
            employee_code="E1",
            first_name="Ada",
            last_name="Khan",
            email="ada@example.com",
            basic_salary="1000",
        )
        other = User.objects.create_user("ess-other", password="x-long-password-1")
        self.other_emp = Employee.objects.create(
            organization=self.org,
            user=other,
            employee_code="E2",
            first_name="Sam",
            last_name="Lee",
            email="sam@example.com",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_attendance_month_is_scoped(self):
        AttendanceRecord.objects.create(
            organization=self.org,
            employee=self.me,
            work_date=date(2026, 11, 2),
            status=AttendanceRecord.Status.PRESENT,
            worked_minutes=480,
        )
        AttendanceRecord.objects.create(
            organization=self.org,
            employee=self.me,
            work_date=date(2026, 10, 2),
            status=AttendanceRecord.Status.ABSENT,
        )
        res = self.client.get("/api/ess/attendance/", {"month": "2026-11"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["work_date"], "2026-11-02")

    def test_profile_updates_contact_and_ignores_salary(self):
        res = self.client.patch(
            "/api/ess/profile/",
            {"address": "Block 4", "basic_salary": "9", "phone": "03001112222"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.me.refresh_from_db()
        self.assertEqual(self.me.address, "Block 4")
        self.assertEqual(self.me.phone, "03001112222")
        self.assertEqual(str(self.me.basic_salary), "1000.00")

    def test_performance_is_own_reviews_only(self):
        PerformanceReview.objects.create(
            organization=self.org, employee=self.me, period_label="2026", goals="Ship the release"
        )
        PerformanceReview.objects.create(
            organization=self.org, employee=self.other_emp, period_label="Hidden"
        )
        res = self.client.get("/api/ess/performance/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["period_label"], "2026")
        saved = self.client.patch(
            "/api/ess/performance/",
            {"id": res.data[0]["id"], "achievements": "Delivered", "self_rating": "4"},
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.data[0]["achievements"], "Delivered")

    def test_activity_lists_only_the_signed_in_user(self):
        AuditLog.objects.create(
            organization=self.org, user=self.user, action="update", module="ess", object_type="Employee"
        )
        AuditLog.objects.create(
            organization=self.org,
            user=self.other_emp.user,
            action="update",
            module="ess",
            object_type="Employee",
        )
        res = self.client.get("/api/ess/activity/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data), 1)

    def test_task_stays_with_the_assignee(self):
        created = self.client.post(
            "/api/ess/tasks/",
            {"title": "Close the books", "priority": "high", "checklist": ["Export", "Review"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        moved = self.client.patch(
            "/api/ess/tasks/",
            {"id": created.data["id"], "status": "in_progress"},
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(moved.data["status"], "in_progress")
        self.assertEqual(len(moved.data["checklist"]), 2)
        outsider = APIClient()
        outsider.force_authenticate(self.other_emp.user)
        UserProfile.objects.create(
            user=self.other_emp.user, organization=self.org, role=UserProfile.RoleCode.EMPLOYEE
        )
        denied = outsider.patch(
            "/api/ess/tasks/",
            {"id": created.data["id"], "status": "done"},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)
