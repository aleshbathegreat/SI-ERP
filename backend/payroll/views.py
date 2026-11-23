import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from django.db.models import Count, Sum
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from core.workflow import WorkflowActionsMixin
from hr.models import Employee
from payroll.emails import send_period_payslips, send_payslip_email
from payroll.models import EmployeeLoan, LoanRepayment, PayrollPeriod, Payslip, SalaryStructure
from payroll.serializers import (
    EmployeeLoanSerializer,
    LoanRepaymentSerializer,
    PayrollPeriodSerializer,
    PayslipSerializer,
    SalaryStructureSerializer,
)


def _d(v, default="0") -> Decimal:
    try:
        return Decimal(str(v if v is not None else default))
    except Exception:
        return Decimal(default)


class SalaryStructureViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer
    search_fields = ("name", "code")
    rbac_module = "payroll.structures"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        currency = serializer.validated_data.get("currency") or getattr(org, "currency", None) or "PKR"
        serializer.save(
            organization=org,
            currency=str(currency).upper()[:3],
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        currency = serializer.validated_data.get("currency")
        extras = {}
        if currency:
            extras["currency"] = str(currency).upper()[:3]
        serializer.save(updated_by=self.request.user, **extras)


class PayrollPeriodViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = PayrollPeriod.objects.all()
    serializer_class = PayrollPeriodSerializer
    filterset_fields = ("status", "year", "month")
    search_fields = ("name",)
    rbac_module = "payroll.periods"
    workflow_submit_to = "processing"
    workflow_approve_to = "approved"
    workflow_reject_to = "open"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        currency = serializer.validated_data.get("currency") or getattr(org, "currency", None) or "PKR"
        serializer.save(
            organization=org,
            currency=str(currency).upper()[:3],
            created_by=self.request.user,
        )

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        period = self.get_object()
        agg = period.payslips.aggregate(
            slip_count=Count("id"),
            total_basic=Sum("basic"),
            total_gross=Sum("gross_pay"),
            total_allowances=Sum("allowances"),
            total_deductions=Sum("total_deductions"),
            total_tax=Sum("income_tax"),
            total_eobi=Sum("eobi"),
            total_pf=Sum("provident_fund"),
            total_loans=Sum("loan_repayment"),
            total_net=Sum("net_pay"),
            total_employer_cost=Sum("employer_cost"),
        )
        return Response(
            {
                "period": PayrollPeriodSerializer(period).data,
                "slip_count": agg["slip_count"] or 0,
                "total_basic": str(agg["total_basic"] or 0),
                "total_gross": str(agg["total_gross"] or 0),
                "total_allowances": str(agg["total_allowances"] or 0),
                "total_deductions": str(agg["total_deductions"] or 0),
                "total_tax": str(agg["total_tax"] or 0),
                "total_eobi": str(agg["total_eobi"] or 0),
                "total_pf": str(agg["total_pf"] or 0),
                "total_loans": str(agg["total_loans"] or 0),
                "total_net": str(agg["total_net"] or 0),
                "total_employer_cost": str(agg["total_employer_cost"] or 0),
            }
        )

    @action(detail=True, methods=["get"], url_path="bank-advice")
    def bank_advice(self, request, pk=None):
        """CSV of bank-transfer net pay for the period."""
        period = self.get_object()
        slips = (
            period.payslips.filter(payment_method=Payslip.PaymentMethod.BANK)
            .select_related("employee", "employee__department")
            .order_by("employee__employee_code")
        )
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "Sr No",
                "Employee Code",
                "Employee Name",
                "Department",
                "Bank Name",
                "Account / IBAN",
                "Net Salary",
            ]
        )
        total = Decimal("0")
        for index, slip in enumerate(slips, start=1):
            emp = slip.employee
            dept = getattr(getattr(emp, "department", None), "name", "") or ""
            account = (slip.bank_account or getattr(emp, "bank_iban", "") or "").strip()
            net = _d(slip.net_pay)
            total += net
            writer.writerow(
                [
                    index,
                    getattr(emp, "employee_code", "") or "",
                    getattr(emp, "full_name", "") or "",
                    dept,
                    getattr(emp, "bank_name", "") or "",
                    account,
                    f"{net:.2f}",
                ]
            )
        writer.writerow(["", "", "", "", "", "Total", f"{total:.2f}"])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="Bank_Advice_{period.year}_{period.month:02d}.csv"'
        return resp

    @action(detail=True, methods=["get"])
    def statutory(self, request, pk=None):
        """Income-tax withholding and EOBI shares for the period."""
        period = self.get_object()
        slips = list(period.payslips.select_related("employee"))
        tax = eobi_emp = eobi_er = Decimal("0")
        rows = []
        for slip in slips:
            tax += _d(slip.income_tax)
            eobi_emp += _d(slip.eobi)
            eobi_er += _d(slip.employer_social_security)
            rows.append(
                {
                    "employee_id": slip.employee_id,
                    "employee_code": slip.employee.employee_code,
                    "employee_name": slip.employee.full_name,
                    "income_tax": f"{_d(slip.income_tax):.2f}",
                    "eobi_employee": f"{_d(slip.eobi):.2f}",
                    "eobi_employer": f"{_d(slip.employer_social_security):.2f}",
                }
            )
        return Response(
            {
                "period_id": period.id,
                "period_name": period.name,
                "currency": period.currency,
                "headcount": len(rows),
                "income_tax": f"{tax:.2f}",
                "eobi_employee": f"{eobi_emp:.2f}",
                "eobi_employer": f"{eobi_er:.2f}",
                "eobi_payable": f"{(eobi_emp + eobi_er):.2f}",
                "rows": rows,
            }
        )

    @action(detail=True, methods=["post"], url_path="generate-payslips")
    def generate_payslips(self, request, pk=None):
        """Create/refresh payslips with intl earnings, statutory, and active loan EMIs."""
        period = self.get_object()
        if period.status in (PayrollPeriod.Status.PAID, PayrollPeriod.Status.CLOSED):
            return Response(
                {"detail": f"Cannot generate slips while period is {period.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org = period.organization
        employees = Employee.objects.filter(
            organization=org, status__in=["active", "probation"]
        )
        structure = (
            SalaryStructure.objects.filter(organization=org, is_active=True).order_by("code").first()
        )
        org_currency = getattr(org, "currency", None) or "PKR"
        created = 0
        updated = 0
        loans_applied = 0
        skipped_docs = []
        for emp in employees:
            from hr.lifecycle_service import document_compliance

            compliance = document_compliance(emp)
            if compliance.get("blocks_payroll"):
                skipped_docs.append(
                    {
                        "employee_id": emp.id,
                        "employee_code": emp.employee_code,
                        "blocking_count": compliance.get("blocking_count"),
                    }
                )
                continue
            basic = _d(emp.basic_salary)
            housing = transport = medical = meal = other = Decimal("0")
            tax_rate = Decimal("5")
            eobi_fixed = Decimal("500")
            pf_rate = Decimal("8.33")
            emp_pf_rate = Decimal("8.33")
            currency = period.currency or org_currency or "PKR"
            tax_free = bool(getattr(emp, "is_tax_free", False))
            attendance_free = bool(getattr(emp, "is_attendance_free", False))

            if structure:
                currency = structure.currency or currency
                if not basic or basic == 0:
                    basic = _d(structure.basic)
                housing = _d(structure.housing)
                transport = _d(structure.transport)
                medical = _d(structure.medical)
                meal = _d(structure.meal)
                other = _d(structure.other_allowances)
                tax_rate = _d(structure.income_tax_rate, "5")
                eobi_fixed = _d(structure.social_security_fixed, "500")
                pf_rate = _d(structure.provident_fund_rate, "8.33")
                emp_pf_rate = _d(structure.employer_pf_rate, "8.33")
            elif basic:
                housing = (basic * Decimal("0.45")).quantize(Decimal("0.01"))
                transport = (basic * Decimal("0.10")).quantize(Decimal("0.01"))
                medical = (basic * Decimal("0.05")).quantize(Decimal("0.01"))

            if tax_free:
                income_tax = Decimal("0")
            else:
                income_tax = (basic * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            eobi = eobi_fixed if basic else Decimal("0")
            pf = (basic * pf_rate / Decimal("100")).quantize(Decimal("0.01"))
            employer_pf = (basic * emp_pf_rate / Decimal("100")).quantize(Decimal("0.01"))

            # Active loans with payroll deduction
            loan_amt = Decimal("0")
            active_loans = EmployeeLoan.objects.filter(
                employee=emp,
                status=EmployeeLoan.Status.ACTIVE,
                deduct_from_payroll=True,
                outstanding_balance__gt=0,
            )
            loan_rows = []
            for loan in active_loans:
                inst = min(_d(loan.monthly_installment), _d(loan.outstanding_balance))
                if inst <= 0:
                    continue
                loan_amt += inst
                loan_rows.append((loan, inst))

            # Attendance / unpaid leave → days worked (+ OT from punches)
            from calendar import monthrange

            from django.db.models import Sum as DjSum
            from hr.leave_service import payroll_day_factor
            from hr.models import AttendanceRecord, LeaveRequest

            days_in_month = monthrange(period.year, period.month)[1]
            unpaid_days = Decimal("0")
            ot_hours = Decimal("0")
            ot_pay = Decimal("0")
            if attendance_free:
                days_worked = Decimal(str(days_in_month))
            else:
                records = list(
                    AttendanceRecord.objects.filter(
                        employee=emp,
                        work_date__year=period.year,
                        work_date__month=period.month,
                    )
                )
                # Paid leave days in month (attendance on_leave + paid leave type)
                paid_leave_dates = set()
                unpaid_leave_dates = set()
                for lr in LeaveRequest.objects.filter(
                    employee=emp,
                    status="approved",
                    start_date__lte=date(period.year, period.month, days_in_month),
                    end_date__gte=date(period.year, period.month, 1),
                ).select_related("leave_type"):
                    from datetime import timedelta as _td

                    d = max(lr.start_date, date(period.year, period.month, 1))
                    end = min(lr.end_date, date(period.year, period.month, days_in_month))
                    while d <= end:
                        if lr.leave_type.is_paid:
                            paid_leave_dates.add(d)
                        else:
                            unpaid_leave_dates.add(d)
                        d += _td(days=1)

                factor_sum = Decimal("0")
                ot_minutes = 0
                if records:
                    for rec in records:
                        ot_minutes += int(rec.overtime_minutes or 0)
                        if rec.work_date in unpaid_leave_dates:
                            continue
                        if rec.status == "on_leave" and rec.work_date in paid_leave_dates:
                            factor_sum += Decimal("1")
                            continue
                        if rec.status == "on_leave":
                            continue
                        factor_sum += payroll_day_factor(
                            rec.status, is_half_day=bool(rec.is_half_day)
                        )
                    days_worked = factor_sum
                else:
                    unpaid_days = Decimal(str(len(unpaid_leave_dates)))
                    days_worked = Decimal(str(days_in_month)) - unpaid_days

                unpaid_days = Decimal(str(len(unpaid_leave_dates)))
                if days_worked < 0:
                    days_worked = Decimal("0")
                if days_worked > days_in_month:
                    days_worked = Decimal(str(days_in_month))

                ot_hours = (Decimal(str(ot_minutes)) / Decimal("60")).quantize(
                    Decimal("0.01")
                )
                # OT at 1.5× hourly (basic / (days_in_month * 8))
                if ot_hours > 0 and basic:
                    hourly = (basic / Decimal(str(days_in_month)) / Decimal("8")).quantize(
                        Decimal("0.0001")
                    )
                    ot_pay = (hourly * ot_hours * Decimal("1.5")).quantize(Decimal("0.01"))

                # Prorate basic if less than full month
                if days_in_month and days_worked < days_in_month and basic:
                    basic = (basic * days_worked / Decimal(str(days_in_month))).quantize(
                        Decimal("0.01")
                    )
                    if not tax_free:
                        income_tax = (basic * tax_rate / Decimal("100")).quantize(
                            Decimal("0.01")
                        )
                pf = (basic * pf_rate / Decimal("100")).quantize(Decimal("0.01"))
                employer_pf = (basic * emp_pf_rate / Decimal("100")).quantize(
                    Decimal("0.01")
                )

            taxable_monthly = (
                basic + housing + transport + medical + meal + other + ot_pay
            )
            employer_eobi = Decimal("0")
            if (currency or "").upper() == "PKR":
                from payroll.pk_statutory import eobi_shares, monthly_income_tax

                if basic:
                    eobi, employer_eobi = eobi_shares()
                else:
                    eobi = Decimal("0")
                income_tax = (
                    Decimal("0") if tax_free else monthly_income_tax(taxable_monthly)
                )

            defaults = dict(
                currency=currency,
                basic=basic,
                housing_allowance=housing,
                transport_allowance=transport,
                medical_allowance=medical,
                meal_allowance=meal,
                other_earnings=other,
                overtime=ot_pay,
                overtime_hours=ot_hours,
                income_tax=income_tax,
                tax=income_tax,
                social_security=eobi,
                eobi=eobi,
                provident_fund=pf,
                employer_provident_fund=employer_pf,
                employer_social_security=employer_eobi,
                bank_account=(getattr(emp, "bank_iban", "") or "")[:64],
                loan_repayment=loan_amt,
                days_worked=days_worked,
                unpaid_leave_days=unpaid_days,
                payment_method=Payslip.PaymentMethod.BANK,
                payment_date=period.pay_date,
                created_by=request.user,
            )
            slip, was_created = Payslip.objects.get_or_create(
                period=period, employee=emp, defaults=defaults
            )
            if was_created:
                created += 1
            else:
                for k, v in defaults.items():
                    if k == "created_by":
                        continue
                    setattr(slip, k, v)
                slip.updated_by = request.user
                slip.save()
                updated += 1

            for loan, inst in loan_rows:
                repay, r_created = LoanRepayment.objects.get_or_create(
                    loan=loan,
                    payslip=slip,
                    defaults={
                        "amount": inst,
                        "due_date": period.pay_date or date(period.year, period.month, 28),
                        "status": LoanRepayment.Status.PENDING,
                        "created_by": request.user,
                    },
                )
                if not r_created:
                    repay.amount = inst
                    repay.save(update_fields=["amount", "updated_at"])
                loans_applied += 1

        if period.status == PayrollPeriod.Status.OPEN and (created or updated):
            period.status = PayrollPeriod.Status.PROCESSING
            period.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "created": created,
                "updated": updated,
                "loans_applied": loans_applied,
                "period_status": period.status,
                "skipped_doc_compliance": skipped_docs,
                "skipped_doc_count": len(skipped_docs),
            }
        )

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        period = self.get_object()
        if period.status != PayrollPeriod.Status.APPROVED:
            return Response(
                {"detail": "Period must be approved before marking paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not period.payslips.exists():
            return Response({"detail": "No payslips in this period."}, status=400)

        # Apply pending loan repayments linked to this period's slips
        for repay in LoanRepayment.objects.filter(
            payslip__period=period, status=LoanRepayment.Status.PENDING
        ).select_related("loan"):
            loan = repay.loan
            amt = _d(repay.amount)
            loan.outstanding_balance = max(Decimal("0"), _d(loan.outstanding_balance) - amt)
            loan.total_repaid = _d(loan.total_repaid) + amt
            if loan.outstanding_balance <= 0:
                loan.status = EmployeeLoan.Status.CLOSED
                loan.outstanding_balance = Decimal("0")
            loan.save()
            repay.status = LoanRepayment.Status.PAID
            repay.paid_date = period.pay_date or date.today()
            repay.save(update_fields=["status", "paid_date", "updated_at"])

        for slip in period.payslips.all():
            if not slip.payment_date:
                slip.payment_date = period.pay_date or date.today()
                slip.save(update_fields=["payment_date", "updated_at"])

        resp = self._set_status(period, PayrollPeriod.Status.PAID, "mark_paid")
        # Auto-email payslips after payment (best-effort)
        mail = send_period_payslips(period)
        data = resp.data if hasattr(resp, "data") else {}
        if isinstance(data, dict):
            data = {**data, "email": mail}
            return Response(data)
        return resp

    @action(detail=True, methods=["post"], url_path="send-payslips")
    def send_payslips(self, request, pk=None):
        """Email professional payslips to employees via tenant SMTP."""
        period = self.get_object()
        if not period.payslips.exists():
            return Response({"detail": "No payslips in this period."}, status=400)
        ids = request.data.get("payslip_ids")
        only_ids = [int(x) for x in ids] if isinstance(ids, list) else None
        result = send_period_payslips(period, only_ids=only_ids)
        status_code = (
            status.HTTP_200_OK
            if result["sent"] or result["skipped"]
            else status.HTTP_400_BAD_REQUEST
        )
        if result["sent"] == 0 and result["failed"] > 0 and result["skipped"] == 0:
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    @action(detail=True, methods=["post"], url_path="post-to-gl")
    def post_to_gl(self, request, pk=None):
        """Post period totals to GL: Dr salary expense / Cr liabilities + net payable."""
        from finance.models import Account, JournalEntry, JournalLine

        period = self.get_object()
        if period.gl_journal_id:
            return Response(
                {"detail": "Already posted", "journal_id": period.gl_journal_id},
                status=400,
            )
        if period.status not in (
            PayrollPeriod.Status.APPROVED,
            PayrollPeriod.Status.PAID,
        ):
            return Response(
                {"detail": "Period must be approved (or paid) before GL posting."},
                status=400,
            )
        slips = list(period.payslips.all())
        if not slips:
            return Response({"detail": "No payslips"}, status=400)

        org = period.organization
        codes = {
            "expense": request.data.get("expense_account") or "5100",
            "payable": request.data.get("payable_account") or "2100",
            "tax": request.data.get("tax_account") or "2200",
            "eobi": request.data.get("eobi_account") or "2210",
            "pf": request.data.get("pf_account") or "2220",
        }
        accts = {}
        for key, code in codes.items():
            acct = Account.objects.filter(organization=org, code=code).first()
            if not acct:
                return Response(
                    {
                        "detail": f"Missing GL account code '{code}' for {key}. "
                        "Pass expense_account / payable_account / tax_account / eobi_account / pf_account."
                    },
                    status=400,
                )
            accts[key] = acct

        gross = sum((_d(s.gross_pay) for s in slips), Decimal("0"))
        tax = sum((_d(s.income_tax or s.tax) for s in slips), Decimal("0"))
        eobi = sum((_d(s.eobi or s.social_security) for s in slips), Decimal("0"))
        pf = sum((_d(s.provident_fund) for s in slips), Decimal("0"))
        other_ded = sum(
            (
                _d(s.pension)
                + _d(s.loan_repayment)
                + _d(s.advance_recovery)
                + _d(s.other_deductions)
                for s in slips
            ),
            Decimal("0"),
        )
        net = sum((_d(s.net_pay) for s in slips), Decimal("0"))
        # Ensure balance: expense = net + tax + eobi + pf + other
        credit_sum = net + tax + eobi + pf + other_ded
        if gross != credit_sum:
            # Prefer recomputed net from components if drift
            net = gross - tax - eobi - pf - other_ded
            if net < 0:
                return Response({"detail": "Negative net from components"}, status=400)

        entry_date = period.pay_date or date(period.year, period.month, 1)
        journal = JournalEntry.objects.create(
            organization=org,
            entry_date=entry_date,
            reference=f"PAY-{period.year}-{period.month:02d}",
            narration=f"Payroll posting {period.name}",
            status=JournalEntry.Status.POSTED,
            created_by=request.user,
            submitted_by=request.user,
            approved_by=request.user,
        )
        JournalLine.objects.create(
            journal=journal,
            account=accts["expense"],
            debit=gross,
            credit=Decimal("0"),
            description="Salary expense",
        )
        if tax:
            JournalLine.objects.create(
                journal=journal,
                account=accts["tax"],
                debit=Decimal("0"),
                credit=tax,
                description="Income tax payable",
            )
        if eobi:
            JournalLine.objects.create(
                journal=journal,
                account=accts["eobi"],
                debit=Decimal("0"),
                credit=eobi,
                description="EOBI / social security payable",
            )
        if pf:
            JournalLine.objects.create(
                journal=journal,
                account=accts["pf"],
                debit=Decimal("0"),
                credit=pf,
                description="Provident fund payable",
            )
        payable_credit = net + other_ded
        if payable_credit:
            JournalLine.objects.create(
                journal=journal,
                account=accts["payable"],
                debit=Decimal("0"),
                credit=payable_credit,
                description="Net salary / other deductions payable",
            )
        if hasattr(journal, "posted_at"):
            from django.utils import timezone

            journal.posted_at = timezone.now()
            journal.save(update_fields=["posted_at", "updated_at"])
        period.gl_journal = journal
        period.save(update_fields=["gl_journal", "updated_at"])
        return Response(
            {
                "journal_id": journal.id,
                "reference": journal.reference,
                "gross": str(gross),
                "net": str(net),
                "tax": str(tax),
                "eobi": str(eobi),
                "pf": str(pf),
            }
        )


class PayslipViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    queryset = Payslip.objects.select_related("employee", "period")
    serializer_class = PayslipSerializer
    filterset_fields = ("period", "employee")
    search_fields = ("employee__first_name", "employee__last_name", "employee__employee_code")
    rbac_module = "payroll.payslips"

    @action(detail=False, methods=["get"], url_path="tax-certificate")
    def tax_certificate(self, request):
        from payroll.pk_statutory import current_fiscal_year, tax_certificate

        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        employee_id = request.query_params.get("employee")
        if not employee_id:
            return Response({"detail": "employee is required"}, status=400)
        emp = Employee.objects.filter(organization=org, pk=employee_id).first()
        if not emp:
            return Response({"detail": "Employee not found"}, status=404)
        label = request.query_params.get("fiscal_year") or current_fiscal_year(date.today())
        try:
            return Response(tax_certificate(emp, label))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return self.queryset.none()
        return self.queryset.filter(period__organization=org)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="send-email")
    def send_email(self, request, pk=None):
        slip = self.get_object()
        ok, detail = send_payslip_email(slip)
        return Response(
            {"sent": ok, "detail": detail},
            status=status.HTTP_200_OK if ok else status.HTTP_400_BAD_REQUEST,
        )


class EmployeeLoanViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = EmployeeLoan.objects.select_related("employee", "guarantor")
    serializer_class = EmployeeLoanSerializer
    search_fields = (
        "loan_number",
        "employee__first_name",
        "employee__last_name",
        "employee__employee_code",
        "purpose",
    )
    filterset_fields = ("status", "loan_type", "employee")
    rbac_module = "payroll.loans"
    workflow_submit_to = "pending"
    workflow_approve_to = "approved"
    workflow_reject_to = "rejected"

    def perform_create(self, serializer):
        org = user_organization(self.request.user)
        currency = serializer.validated_data.get("currency") or getattr(org, "currency", None) or "PKR"
        serializer.save(
            organization=org,
            currency=str(currency).upper()[:3],
            created_by=self.request.user,
        )

    @action(detail=False, methods=["post"], url_path="calculate-emi")
    def calculate_emi(self, request):
        """Compute EMI / installment from principal, annual rate %, and tenure months."""
        principal = _d(request.data.get("principal"))
        rate = _d(request.data.get("interest_rate"))
        tenure = int(request.data.get("tenure_months") or 12) or 12
        if principal <= 0:
            return Response({"detail": "principal must be > 0"}, status=400)
        tmp = EmployeeLoan(principal=principal, interest_rate=rate, tenure_months=tenure)
        emi = tmp.compute_installment()
        total_payable = (emi * tenure).quantize(Decimal("0.01"))
        return Response(
            {
                "principal": str(principal),
                "interest_rate": str(rate),
                "tenure_months": tenure,
                "monthly_installment": str(emi),
                "total_payable": str(total_payable),
                "total_interest": str((total_payable - principal).quantize(Decimal("0.01"))),
            }
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        loan = self.get_object()
        if loan.status not in (EmployeeLoan.Status.APPROVED, EmployeeLoan.Status.DRAFT):
            return Response(
                {"detail": f"Cannot activate loan in status {loan.status}."},
                status=400,
            )
        if not loan.monthly_installment or loan.monthly_installment <= 0:
            loan.monthly_installment = loan.compute_installment()
        if not loan.disbursed_amount:
            loan.disbursed_amount = loan.principal
        if not loan.outstanding_balance:
            loan.outstanding_balance = loan.disbursed_amount or loan.principal
        loan.status = EmployeeLoan.Status.ACTIVE
        if not loan.disbursement_date:
            loan.disbursement_date = date.today()
        if not loan.start_date:
            loan.start_date = date.today()
        loan.save()
        return Response(EmployeeLoanSerializer(loan).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        loan = self.get_object()
        loan.status = EmployeeLoan.Status.CLOSED
        loan.outstanding_balance = Decimal("0")
        loan.save(update_fields=["status", "outstanding_balance", "updated_at"])
        return Response(EmployeeLoanSerializer(loan).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset())
        agg = qs.aggregate(
            count=Count("id"),
            principal=Sum("principal"),
            outstanding=Sum("outstanding_balance"),
            repaid=Sum("total_repaid"),
        )
        by_status = {
            row["status"]: row["c"]
            for row in qs.values("status").annotate(c=Count("id"))
        }
        return Response(
            {
                "count": agg["count"] or 0,
                "principal": str(agg["principal"] or 0),
                "outstanding": str(agg["outstanding"] or 0),
                "repaid": str(agg["repaid"] or 0),
                "by_status": by_status,
            }
        )


class LoanRepaymentViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    queryset = LoanRepayment.objects.select_related("loan", "loan__employee", "payslip")
    serializer_class = LoanRepaymentSerializer
    filterset_fields = ("loan", "status", "payslip")
    rbac_module = "payroll.loans"

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return self.queryset.none()
        return self.queryset.filter(loan__organization=org)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
