"""Production exports: periods, challans, bank match, payroll bank file."""

import csv
import io
from datetime import date
from decimal import Decimal

from django.db import models
from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from finance.models import (
    AccountingPeriod,
    BankAccount,
    BankReconciliation,
    BankStatementLine,
    TaxChallan,
    VendorInvoice,
)


class AccountingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingPeriod
        fields = "__all__"
        read_only_fields = (
            "organization",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_deleted",
            "deleted_at",
            "deleted_by",
        )

    def validate_month(self, value):
        if value is None or not 1 <= int(value) <= 12:
            raise serializers.ValidationError("Month must be between 1 and 12.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        org = user_organization(request.user) if request and request.user.is_authenticated else None
        if self.instance is not None:
            org = org or self.instance.organization
        year = attrs.get("year", getattr(self.instance, "year", None))
        month = attrs.get("month", getattr(self.instance, "month", None))
        name = attrs.get("name", getattr(self.instance, "name", "") if self.instance else "")
        errors = {}
        if name is None or not str(name).strip():
            errors["name"] = "Name is required."
        else:
            attrs["name"] = str(name).strip()
        try:
            year_i = int(year)
            month_i = int(month)
        except (TypeError, ValueError):
            if year in (None, ""):
                errors["year"] = "Year is required."
            else:
                errors["year"] = "Enter a year from 2000 to 2100."
            if month in (None, ""):
                errors["month"] = "Month is required."
            else:
                errors["month"] = "Month must be between 1 and 12."
            raise serializers.ValidationError(errors)
        if not 2000 <= year_i <= 2100:
            errors["year"] = "Must be between 2000 and 2100."
        if not 1 <= month_i <= 12:
            errors["month"] = "Month must be between 1 and 12."
        self._restore = None
        if org and "year" not in errors and "month" not in errors:
            qs = AccountingPeriod.all_objects.filter(
                organization=org, year=year_i, month=month_i
            )
            if self.instance is not None and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            same_period = (
                self.instance is not None
                and int(self.instance.year) == year_i
                and int(self.instance.month) == month_i
            )
            existing = None if same_period else qs.first()
            if existing is not None and "name" not in errors:
                if existing.is_deleted and self.instance is None:
                    self._restore = existing
                elif not existing.is_deleted:
                    errors["month"] = (
                        f"Period {year_i}-{month_i:02d} already exists. Choose another month."
                    )
        if errors:
            raise serializers.ValidationError(errors)
        attrs["year"] = year_i
        attrs["month"] = month_i
        return attrs

    def create(self, validated_data):
        restore = getattr(self, "_restore", None)
        if restore is None:
            return super().create(validated_data)
        restore.is_deleted = False
        restore.deleted_at = None
        restore.deleted_by = None
        if validated_data.get("name"):
            restore.name = validated_data["name"]
        if "is_locked" in validated_data:
            restore.is_locked = validated_data["is_locked"]
        actor = validated_data.get("created_by") or validated_data.get("updated_by")
        if actor:
            restore.updated_by = actor
        restore.save()
        return restore


class TaxChallanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxChallan
        fields = "__all__"
        read_only_fields = (
            "organization",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(
                validated_data, "challan_no", org, kind="challan", model=TaxChallan
            )
        return super().create(validated_data)


class BankStatementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankStatementLine
        fields = "__all__"
        read_only_fields = (
            "organization",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )


class AccountingPeriodViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AccountingPeriod.objects.all()
    serializer_class = AccountingPeriodSerializer
    rbac_module = "finance.journals"
    filterset_fields = ("year", "month", "is_locked")

    def perform_create(self, serializer):
        from django.db import IntegrityError

        from rest_framework.exceptions import ValidationError

        try:
            super().perform_create(serializer)
        except IntegrityError as exc:
            raise ValidationError("A period for that year and month already exists.") from exc

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        obj = self.get_object()
        obj.is_locked = True
        obj.save(update_fields=["is_locked", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        obj = self.get_object()
        obj.is_locked = False
        obj.save(update_fields=["is_locked", "updated_at"])
        return Response(self.get_serializer(obj).data)


class TaxChallanViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaxChallan.objects.all()
    serializer_class = TaxChallanSerializer
    rbac_module = "finance.tax"
    search_fields = ("challan_no", "period_label")
    filterset_fields = ("tax_type", "status")

    @action(detail=False, methods=["post"], url_path="generate-wht")
    def generate_wht(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        period = request.data.get("period_label") or date.today().strftime("%Y-%m")
        from django.db.models import Sum

        amount = (
            VendorInvoice.objects.filter(
                organization=org, status__in=["approved", "paid", "submitted"]
            ).aggregate(s=Sum("wht_amount"))["s"]
            or Decimal("0")
        )
        challan_no = f"WHT-{period.replace('-', '')}-{org.code.upper()}"
        obj, _ = TaxChallan.objects.update_or_create(
            organization=org,
            challan_no=challan_no,
            defaults={
                "tax_type": "wht",
                "period_label": period,
                "amount": amount,
                "status": "generated",
                "notes": "Auto-generated from AP WHT amounts",
                "created_by": request.user,
            },
        )
        return Response(TaxChallanSerializer(obj).data)

    @action(detail=True, methods=["get"])
    def export_csv(self, request, pk=None):
        obj = self.get_object()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["challan_no", "tax_type", "period", "amount", "status"])
        w.writerow([obj.challan_no, obj.tax_type, obj.period_label, obj.amount, obj.status])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{obj.challan_no}.csv"'
        return resp


class BankStatementLineViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BankStatementLine.objects.select_related("bank_account", "reconciliation")
    serializer_class = BankStatementLineSerializer
    rbac_module = "finance.banks"
    filterset_fields = ("bank_account", "matched", "reconciliation")
    search_fields = ("description", "reference")

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """Import bank statement CSV into lines for a bank account (optional reconciliation)."""
        from finance.bank_csv import parse_bank_statement_csv, read_upload_text

        org = user_organization(request.user)
        bank_id = request.data.get("bank_account")
        recon_id = request.data.get("reconciliation_id") or request.data.get(
            "reconciliation"
        )
        raw = read_upload_text(request)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        if not bank_id and not recon_id:
            return Response(
                {"detail": "bank_account or reconciliation_id required with csv/file"},
                status=400,
            )
        if not raw.strip():
            return Response(
                {"detail": "CSV file required (multipart field 'file' or body 'csv')"},
                status=400,
            )

        recon = None
        if recon_id:
            recon = BankReconciliation.objects.filter(
                organization=org, id=recon_id
            ).select_related("bank_account").first()
            if not recon:
                return Response({"detail": "Reconciliation not found"}, status=404)
            bank = recon.bank_account
        else:
            bank = BankAccount.objects.filter(organization=org, id=bank_id).first()
            if not bank:
                return Response({"detail": "Bank account not found"}, status=404)

        rows, errors = parse_bank_statement_csv(raw)
        if not rows:
            return Response(
                {"detail": errors[0] if errors else "No rows imported", "errors": errors},
                status=400,
            )
        created = 0
        for row in rows:
            BankStatementLine.objects.create(
                organization=org,
                bank_account=bank,
                reconciliation=recon,
                txn_date=row["txn_date"],
                description=row["description"],
                amount=row["amount"],
                reference=row.get("reference") or "",
                created_by=request.user,
            )
            created += 1
        return Response(
            {
                "created": created,
                "skipped_errors": errors,
                "bank_account": bank.id,
                "reconciliation": recon.id if recon else None,
            }
        )

    @action(detail=False, methods=["post"], url_path="auto-match")
    def auto_match(self, request):
        from finance.serializers import _sync_bank_from_reconciliation

        org = user_organization(request.user)
        recon_id = request.data.get("reconciliation_id")
        if not org or not recon_id:
            return Response({"detail": "reconciliation_id required"}, status=400)
        recon = BankReconciliation.objects.filter(organization=org, id=recon_id).first()
        if not recon:
            return Response({"detail": "Reconciliation not found"}, status=404)

        lines = list(
            BankStatementLine.objects.filter(
                organization=org,
                matched=False,
            ).filter(
                models.Q(reconciliation=recon)
                | models.Q(reconciliation__isnull=True, bank_account=recon.bank_account)
            )
        )
        matched = 0
        paid = VendorInvoice.objects.filter(
            organization=org, status="paid", paid_amount__gt=0
        )
        paid_by_amt = {}
        for inv in paid:
            key = f"{abs(inv.paid_amount):.2f}"
            paid_by_amt.setdefault(key, []).append(inv)
        balances_equal = recon.statement_balance == recon.book_balance
        for line in lines:
            key = f"{abs(line.amount):.2f}"
            cands = paid_by_amt.get(key) or []
            if cands:
                paid_by_amt[key].pop(0)
                line.matched = True
                line.reconciliation = recon
                line.save(update_fields=["matched", "reconciliation", "updated_at"])
                matched += 1
            elif balances_equal:
                line.matched = True
                line.reconciliation = recon
                line.save(update_fields=["matched", "reconciliation", "updated_at"])
                matched += 1
        if matched:
            recon.status = BankReconciliation.Status.MATCHED
            recon.save(update_fields=["status", "updated_at"])
            _sync_bank_from_reconciliation(recon)
        return Response(
            {
                "matched": matched,
                "remaining_unmatched": BankStatementLine.objects.filter(
                    reconciliation=recon, matched=False
                ).count(),
                "status": recon.status,
            }
        )


class PayrollBankFileView(APIView):
    """Generate bank salary CSV for approved period."""

    rbac_module = "payroll.payslips"

    def get(self, request):
        from payroll.models import Payslip, PayrollPeriod

        org = user_organization(request.user)
        period_id = request.query_params.get("period_id")
        if not org or not period_id:
            return Response({"detail": "period_id required"}, status=400)
        period = PayrollPeriod.objects.filter(organization=org, id=period_id).first()
        if not period:
            return Response({"detail": "Period not found"}, status=404)
        slips = Payslip.objects.filter(period=period).select_related("employee")
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "employee_code",
                "employee_name",
                "account_title",
                "net_pay",
                "period",
            ]
        )
        for s in slips:
            w.writerow(
                [
                    s.employee.employee_code,
                    s.employee.full_name,
                    s.employee.full_name,
                    s.net_pay,
                    period.name,
                ]
            )
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="salary_{period.id}.csv"'
        return resp


class AnnualTaxCertificateView(APIView):
    rbac_module = "payroll.payslips"

    def get(self, request):
        from django.db.models import Sum
        from hr.models import Employee
        from payroll.models import Payslip

        org = user_organization(request.user)
        year = int(request.query_params.get("year") or date.today().year)
        emp_id = request.query_params.get("employee_id")
        if not org or not emp_id:
            return Response({"detail": "employee_id and year required"}, status=400)
        emp = Employee.objects.filter(organization=org, id=emp_id).first()
        if not emp:
            return Response({"detail": "Employee not found"}, status=404)
        agg = Payslip.objects.filter(
            employee=emp, period__organization=org, period__year=year
        ).aggregate(tax=Sum("tax"), net=Sum("net_pay"), basic=Sum("basic"))
        return Response(
            {
                "employee_code": emp.employee_code,
                "employee_name": emp.full_name,
                "year": year,
                "total_basic": agg["basic"] or 0,
                "total_tax_deducted": agg["tax"] or 0,
                "total_net_pay": agg["net"] or 0,
                "certificate": f"Annual Tax Certificate FY{year} for {emp.full_name}",
            }
        )
