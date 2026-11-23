from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from hr.models import AttendanceHoliday, AttendanceRecord, Department, Employee, LeaveBalance, LeaveType
from payroll.models import EmployeeLoan


class EssDashboardTests(APITestCase):
    def test_dashboard_summarizes_the_employees_own_workplace(self):
        org = Organization.objects.create(
            name="Acme",
            code="ess-dash",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        ensure_default_roles(org)
        User = get_user_model()
        user = User.objects.create_user("ess-ada", password="x-long-password-1", first_name="Ada")
        UserProfile.objects.create(user=user, organization=org, role=UserProfile.RoleCode.EMPLOYEE)
        dept = Department.objects.create(organization=org, name="Software", code="SW")
        me = Employee.objects.create(
            organization=org,
            user=user,
            employee_code="E1",
            first_name="Ada",
            last_name="Khan",
            email="ada@example.com",
            department=dept,
            date_of_birth=date(1990, date.today().month, 2),
        )
        Employee.objects.create(
            organization=org,
            employee_code="E2",
            first_name="Sam",
            last_name="Lee",
            email="sam@example.com",
            department=dept,
            date_of_birth=date(1992, date.today().month, 9),
        )
        leave_type = LeaveType.objects.create(organization=org, name="Annual", code="AL", annual_quota=14)
        LeaveBalance.objects.create(
            organization=org,
            employee=me,
            leave_type=leave_type,
            year=date.today().year,
            accrued=14,
            used=1,
        )
        AttendanceRecord.objects.create(
            organization=org,
            employee=me,
            work_date=date.today(),
            status=AttendanceRecord.Status.LATE,
            late_minutes=12,
        )
        AttendanceHoliday.objects.create(
            organization=org,
            name="Founders day",
            holiday_date=date.today() + timedelta(days=3),
        )
        EmployeeLoan.objects.create(
            organization=org,
            employee=me,
            loan_number="LN1",
            principal=Decimal("1000"),
            outstanding_balance=Decimal("800"),
            monthly_installment=Decimal("100"),
            status=EmployeeLoan.Status.ACTIVE,
        )
        client = APIClient()
        client.force_authenticate(user)
        res = client.get("/api/ess/dashboard/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["workplace"]["department"], "Software")
        self.assertEqual(res.data["month_attendance"]["late"], 1)
        self.assertEqual(res.data["month_attendance"]["present"], 1)
        self.assertEqual(res.data["leave_summary"]["balances"][0]["name"], "Annual")
        self.assertEqual(res.data["loan"]["count"], 1)
        self.assertEqual(res.data["holidays"][0]["name"], "Founders day")
        self.assertEqual(res.data["birthdays"][0]["name"], "Sam Lee")
