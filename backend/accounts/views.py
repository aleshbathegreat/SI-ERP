from django.contrib.auth import authenticate
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import pyotp

from accounts.mfa import LoginRateThrottle, issue_auth_payload
from accounts.serializers import LoginSerializer, UserSerializer
from core.access import (
    is_owner,
    subscription_closed_message,
    subscription_open,
    user_organization,
)
from core.platform_rbac import is_platform_user
from core.serializers import OrganizationSerializer


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    rbac_exempt = True
    subscription_exempt = True
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        profile = getattr(user, "profile", None)
        if profile and profile.mfa_enabled:
            code = str(request.data.get("mfa_code", "")).strip()
            if not code:
                return Response(
                    {"detail": "MFA required", "mfa_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not profile.mfa_secret or not pyotp.TOTP(profile.mfa_secret).verify(
                code, valid_window=1
            ):
                return Response(
                    {"detail": "Invalid MFA code", "mfa_required": True}, status=401
                )

        org = user_organization(user)
        if org and not is_platform_user(user):
            try:
                from core.subscription_lifecycle import sync_org_plan_status

                sync_org_plan_status(org)
                org.refresh_from_db()
            except Exception:
                pass
            if not subscription_open(org):
                msg = subscription_closed_message(org)
                # Owners may still sign in to renew on Billing; others are blocked.
                if not is_owner(user):
                    return Response(
                        {
                            "detail": msg,
                            "code": "subscription_closed",
                            "subscription_open": False,
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        payload = issue_auth_payload(user, request=request)
        if org and not payload.get("subscription_open") and not is_platform_user(user):
            payload["detail"] = subscription_closed_message(org)
            payload["code"] = "subscription_closed"
        return Response(payload)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    subscription_exempt = True
    rbac_exempt = True

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        from accounts.rbac import allowed_modules, ensure_default_roles
        from core.access import ensure_default_packages
        from core.platform_rbac import (
            is_platform_user,
            platform_capabilities,
            platform_role,
        )

        user = self.get_object()
        ensure_default_packages()
        org = user_organization(user)
        if org:
            ensure_default_roles(org)
        profile = getattr(user, "profile", None)
        employee = getattr(user, "employee", None)

        return Response(
            {
                "user": UserSerializer(user).data,
                "organization": OrganizationSerializer(
                    org, context={"request": request}
                ).data
                if org
                else None,
                "subscription_open": subscription_open(org) if org else False,
                "permissions": allowed_modules(user),
                "mfa_enabled": bool(profile and profile.mfa_enabled),
                "is_platform_user": is_platform_user(user),
                "platform_role": platform_role(user),
                "platform_capabilities": platform_capabilities(user),
                "employee_id": employee.id if employee else None,
            }
        )


class DashboardStatsView(APIView):
    """Operations snapshot with charts + operational sentiments."""

    rbac_module = "dashboard"

    def get(self, request):
        from calendar import month_abbr
        from datetime import date
        from decimal import Decimal

        from django.db.models import Count, Sum
        from django.db.models.functions import TruncMonth

        from finance.models import Account, Budget, JournalEntry, Vendor, VendorInvoice
        from hr.models import AttendanceRecord, Employee, LeaveRequest
        from payroll.models import PayrollPeriod, Payslip

        org = user_organization(request.user)
        empty = {
            "employees": 0,
            "active_employees": 0,
            "vendors": 0,
            "accounts": 0,
            "pending_leaves": 0,
            "open_payroll_periods": 0,
            "approved_leaves": 0,
            "module_mix": [],
            "leave_status": [],
            "journal_status": [],
            "ap_status": [],
            "payroll_status": [],
            "budget": {"total": "0", "utilized": "0", "pct": 0},
            "attendance_month": {"present": 0, "absent": 0, "late": 0, "other": 0},
            "trend_6m": [],
            "sentiments": [],
            "health_score": 100,
        }
        if not org:
            return Response(empty)

        employees = Employee.objects.filter(organization=org).count()
        active_employees = Employee.objects.filter(
            organization=org, status="active"
        ).count()
        vendors = Vendor.objects.filter(organization=org).count()
        accounts = Account.objects.filter(organization=org).count()
        pending_leaves = LeaveRequest.objects.filter(
            employee__organization=org, status="pending"
        ).count()
        open_payroll = PayrollPeriod.objects.filter(
            organization=org, status="open"
        ).count()

        leave_status = list(
            LeaveRequest.objects.filter(employee__organization=org)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        journal_status = list(
            JournalEntry.objects.filter(organization=org)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        ap_status = list(
            VendorInvoice.objects.filter(organization=org)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        payroll_status = list(
            PayrollPeriod.objects.filter(organization=org)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        journals_n = JournalEntry.objects.filter(organization=org).count()
        invoices_n = VendorInvoice.objects.filter(organization=org).count()
        leaves_n = LeaveRequest.objects.filter(employee__organization=org).count()
        periods_n = PayrollPeriod.objects.filter(organization=org).count()
        module_mix = [
            {"label": "Finance journals", "value": journals_n, "color": "#4BA3C7"},
            {"label": "AP invoices", "value": invoices_n, "color": "#E08A5A"},
            {"label": "Leave requests", "value": leaves_n, "color": "#4CAF7A"},
            {"label": "Payroll periods", "value": periods_n, "color": "#7B8CDE"},
        ]

        budget_agg = Budget.objects.filter(organization=org).aggregate(
            total=Sum("amount"), utilized=Sum("utilized")
        )
        b_total = Decimal(str(budget_agg["total"] or 0))
        b_util = Decimal(str(budget_agg["utilized"] or 0))
        b_pct = float((b_util / b_total * 100) if b_total else 0)

        today = date.today()
        att = AttendanceRecord.objects.filter(
            organization=org, work_date__year=today.year, work_date__month=today.month
        )
        attendance_month = {
            "present": att.filter(status__in=["present", "regularized"]).count(),
            "absent": att.filter(status="absent").count(),
            "late": att.filter(status="late").count(),
            "other": att.exclude(
                status__in=["present", "regularized", "absent", "late"]
            ).count(),
        }

        start = date(today.year, today.month, 1)
        months_back = []
        y, m = start.year, start.month
        for _ in range(6):
            months_back.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months_back.reverse()

        posted = (
            JournalEntry.objects.filter(
                organization=org,
                status="posted",
                entry_date__gte=date(months_back[0][0], months_back[0][1], 1),
            )
            .annotate(ym=TruncMonth("entry_date"))
            .values("ym")
            .annotate(count=Count("id"))
        )
        posted_map = {}
        for row in posted:
            ym = row["ym"]
            if ym:
                posted_map[(ym.year, ym.month)] = row["count"]

        slips = (
            Payslip.objects.filter(
                period__organization=org,
                period__year__gte=months_back[0][0],
            )
            .values("period__year", "period__month")
            .annotate(count=Count("id"))
        )
        slip_map = {
            (r["period__year"], r["period__month"]): r["count"] for r in slips
        }

        trend_6m = []
        for yy, mm in months_back:
            trend_6m.append(
                {
                    "label": f"{month_abbr[mm]} {str(yy)[2:]}",
                    "journals": posted_map.get((yy, mm), 0),
                    "payslips": slip_map.get((yy, mm), 0),
                }
            )

        sentiments = []
        score = 100
        approved_leaves = next(
            (x["count"] for x in leave_status if x["status"] == "approved"), 0
        )

        if pending_leaves == 0:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Leave queue clear",
                    "detail": "No pending leave requests waiting on approvers.",
                }
            )
        elif pending_leaves <= 3:
            sentiments.append(
                {
                    "tone": "calm",
                    "title": "Light leave backlog",
                    "detail": f"{pending_leaves} request(s) awaiting approval.",
                }
            )
            score -= 5
        else:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Leave backlog building",
                    "detail": f"{pending_leaves} pending leaves — clear Approvals / Leave.",
                }
            )
            score -= min(25, pending_leaves * 3)

        draft_j = next((x["count"] for x in journal_status if x["status"] == "draft"), 0)
        submitted_j = next(
            (x["count"] for x in journal_status if x["status"] == "submitted"), 0
        )
        if submitted_j:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Journals awaiting approval",
                    "detail": f"{submitted_j} submitted journal(s) need a reviewer.",
                }
            )
            score -= min(20, submitted_j * 4)
        elif draft_j:
            sentiments.append(
                {
                    "tone": "calm",
                    "title": "Draft journals on hand",
                    "detail": f"{draft_j} draft(s) — submit when ready.",
                }
            )
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "GL workflow steady",
                    "detail": "No journals stuck in approval.",
                }
            )

        if open_payroll:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Open payroll period",
                    "detail": f"{open_payroll} open period(s) — generate, approve, or close.",
                }
            )
            score -= 10
        else:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Payroll periods tidy",
                    "detail": "No open payroll runs left idle.",
                }
            )

        if b_total and b_pct >= 90:
            sentiments.append(
                {
                    "tone": "attention",
                    "title": "Budget nearly consumed",
                    "detail": f"{b_pct:.0f}% utilized — posting may hit commitment checks.",
                }
            )
            score -= 15
        elif b_total and b_pct >= 70:
            sentiments.append(
                {
                    "tone": "calm",
                    "title": "Budget tracking well",
                    "detail": f"{b_pct:.0f}% utilized against approved budgets.",
                }
            )
        elif b_total:
            sentiments.append(
                {
                    "tone": "positive",
                    "title": "Budget headroom",
                    "detail": f"Only {b_pct:.0f}% utilized — room to operate.",
                }
            )

        if employees:
            sentiments.append(
                {
                    "tone": "positive"
                    if active_employees >= employees * 0.8
                    else "calm",
                    "title": f"{active_employees} active of {employees} employees",
                    "detail": "HR headcount pulse for this tenant.",
                }
            )

        score = max(0, min(100, score))

        return Response(
            {
                "employees": employees,
                "active_employees": active_employees,
                "vendors": vendors,
                "accounts": accounts,
                "pending_leaves": pending_leaves,
                "open_payroll_periods": open_payroll,
                "approved_leaves": approved_leaves,
                "module_mix": module_mix,
                "leave_status": leave_status,
                "journal_status": journal_status,
                "ap_status": ap_status,
                "payroll_status": payroll_status,
                "budget": {
                    "total": str(b_total),
                    "utilized": str(b_util),
                    "pct": round(b_pct, 1),
                },
                "attendance_month": attendance_month,
                "trend_6m": trend_6m,
                "sentiments": sentiments,
                "health_score": score,
            }
        )
