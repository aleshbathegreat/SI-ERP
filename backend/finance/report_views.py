"""Tax returns, saved reports, and finance report export (xlsx/csv/json)."""

from __future__ import annotations

import csv
import io
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from finance.models import SavedReport, TaxReturn, TaxReturnLine
from finance.tax_returns import rebuild_tax_return

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)


class TaxReturnLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxReturnLine
        fields = (
            "id",
            "line_type",
            "description",
            "tax_code",
            "taxable_amount",
            "tax_amount",
            "source_type",
            "source_id",
            "source_ref",
        )


class TaxReturnSerializer(serializers.ModelSerializer):
    lines = TaxReturnLineSerializer(many=True, required=False)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = TaxReturn
        fields = "__all__"
        read_only_fields = list(RO) + ["totals", "filed_at"]

    def get_line_count(self, obj):
        return obj.lines.count()

    def validate(self, attrs):
        start = attrs.get("period_start", getattr(self.instance, "period_start", None))
        end = attrs.get("period_end", getattr(self.instance, "period_end", None))
        if start and end and end < start:
            raise serializers.ValidationError("period_end must be on/after period_start.")
        if self.instance and self.instance.status == TaxReturn.Status.FILED:
            raise serializers.ValidationError("Filed returns are read-only.")
        return attrs

    def _sync_lines(self, tr, lines):
        tr.lines.all().delete()
        TaxReturnLine.objects.bulk_create(
            [TaxReturnLine(tax_return=tr, **row) for row in lines]
        )

    def create(self, validated_data):
        lines = validated_data.pop("lines", None)
        tr = super().create(validated_data)
        if lines:
            self._sync_lines(tr, lines)
        return tr

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        tr = super().update(instance, validated_data)
        if lines is not None:
            self._sync_lines(tr, lines)
        return tr


class TaxReturnViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaxReturn.objects.prefetch_related("lines")
    serializer_class = TaxReturnSerializer
    search_fields = ("notes", "filing_ref")
    filterset_fields = ("return_type", "status")
    rbac_module = "finance.tax_returns"

    def perform_destroy(self, instance):
        if instance.status == TaxReturn.Status.FILED:
            raise ValidationError("Filed returns cannot be deleted.")
        return super().perform_destroy(instance)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """Create a draft return for the period and pull lines from invoices / challans."""
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        data = request.data or {}
        rtype = data.get("return_type") or data.get("type") or TaxReturn.ReturnType.SALES_TAX
        if rtype not in TaxReturn.ReturnType.values:
            raise ValidationError({"return_type": "Use sales_tax or wht."})
        try:
            start = date.fromisoformat(str(data.get("period_start"))[:10])
            end = date.fromisoformat(str(data.get("period_end"))[:10])
        except (TypeError, ValueError):
            raise ValidationError("period_start and period_end (YYYY-MM-DD) are required.")
        if end < start:
            raise ValidationError("period_end must be on/after period_start.")
        tr = TaxReturn.objects.create(
            organization=org,
            return_type=rtype,
            period_start=start,
            period_end=end,
            notes=str(data.get("notes") or ""),
            created_by=request.user,
            updated_by=request.user,
        )
        rebuild_tax_return(tr)
        return Response(self.get_serializer(tr).data, status=201)

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk=None):
        tr = self.get_object()
        try:
            rebuild_tax_return(tr)
        except ValueError as e:
            raise ValidationError(str(e))
        tr.refresh_from_db()
        return Response(self.get_serializer(tr).data)

    @action(detail=True, methods=["post"], url_path="file")
    def file_return(self, request, pk=None):
        tr = self.get_object()
        if tr.status == TaxReturn.Status.FILED:
            raise ValidationError("Already filed.")
        tr.status = TaxReturn.Status.FILED
        tr.filed_at = timezone.now()
        tr.filing_ref = str((request.data or {}).get("filing_ref") or "")[:128]
        tr.updated_by = request.user
        tr.save()
        return Response(self.get_serializer(tr).data)

    @action(detail=True, methods=["get"], url_path="export-csv")
    def export_csv(self, request, pk=None):
        tr = self.get_object()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["type", "description", "tax_code", "taxable_amount", "tax_amount", "source"])
        for ln in tr.lines.all():
            w.writerow(
                [
                    ln.line_type,
                    ln.description,
                    ln.tax_code,
                    ln.taxable_amount,
                    ln.tax_amount,
                    f"{ln.source_type}:{ln.source_ref}",
                ]
            )
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = (
            f'attachment; filename="tax-return-{tr.return_type}-{tr.period_end}.csv"'
        )
        return resp


class SavedReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedReport
        fields = "__all__"
        read_only_fields = RO

    def get_created_by_name(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.get_username()) if u else ""

    def validate_report_key(self, value):
        if value not in REPORT_KEYS:
            raise serializers.ValidationError(f"Unknown report. Use one of: {', '.join(REPORT_KEYS)}")
        return value


class SavedReportViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SavedReport.objects.select_related("created_by")
    serializer_class = SavedReportSerializer
    search_fields = ("name", "report_key")
    filterset_fields = ("report_key",)
    rbac_module = "finance.reports"


REPORT_KEYS = (
    "trial_balance",
    "income_statement",
    "balance_sheet",
    "ap_ageing",
    "ar_ageing",
    "stock_valuation",
    "wht_register",
    "payroll_register",
)


def _parse_date(raw):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        raise ValidationError(f"Invalid date: {raw}")


def run_report(org, key: str, params: dict) -> dict:
    from finance import reporting as R

    as_of = _parse_date(params.get("as_of"))
    year = int(params["year"]) if params.get("year") else (as_of.year if as_of else date.today().year)
    if key == "trial_balance":
        return R.trial_balance(org, as_of=as_of)
    if key == "income_statement":
        return R.income_statement(org, year=year)
    if key == "balance_sheet":
        return R.balance_sheet(org, as_of=as_of)
    if key == "ap_ageing":
        return R.ap_ageing(org, as_of=as_of)
    if key == "ar_ageing":
        return R.ar_ageing(org, as_of=as_of)
    if key == "stock_valuation":
        return R.stock_valuation(org)
    if key == "wht_register":
        return R.wht_register(
            org,
            date_from=_parse_date(params.get("date_from")) or date(year, 1, 1),
            date_to=_parse_date(params.get("date_to")) or as_of or date(year, 12, 31),
        )
    if key == "payroll_register":
        return R.payroll_register_summary(org, year=year)
    raise ValidationError(f"Unknown report '{key}'. Use one of: {', '.join(REPORT_KEYS)}")


def _flatten(report: dict) -> tuple[list[str], list[list]]:
    """Pick the tabular section of a report payload."""
    for k in ("lines", "invoices"):
        rows = report.get(k)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            cols = list(rows[0].keys())
            return cols, [[r.get(c, "") for c in cols] for r in rows]
    if isinstance(report.get("assets"), list):  # balance sheet
        cols = ["section", "code", "name", "amount"]
        out = []
        for sec in ("assets", "liabilities", "equity"):
            for r in report.get(sec, []):
                out.append([sec, r.get("code", ""), r.get("name", ""), r.get("amount", "")])
        return cols, out
    return [], []


class FinanceReportRunView(APIView):
    """GET /finance/reports/run/?report=ar_ageing&export=json|xlsx|csv&as_of=&year="""

    rbac_module = "finance.reports"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        key = request.query_params.get("report") or ""
        params = {k: v for k, v in request.query_params.items()}
        saved_id = request.query_params.get("saved")
        if saved_id:
            sr = SavedReport.objects.filter(organization=org, pk=saved_id).first()
            if not sr:
                return Response({"detail": "Saved report not found"}, status=404)
            key = sr.report_key
            params = {**(sr.params or {}), **params}
        report = run_report(org, key, params)
        fmt = (request.query_params.get("export") or "json").lower()
        if fmt == "json":
            return Response({"report": key, "data": report})
        cols, rows = _flatten(report)
        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(cols)
            w.writerows(rows)
            resp = HttpResponse(buf.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{key}.csv"'
            return resp
        if fmt == "xlsx":
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = key[:31]
            ws.append(cols)
            for r in rows:
                ws.append([str(v) if v is not None else "" for v in r])
            out = io.BytesIO()
            wb.save(out)
            resp = HttpResponse(
                out.getvalue(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )
            resp["Content-Disposition"] = f'attachment; filename="{key}.xlsx"'
            return resp
        return Response({"detail": "export must be json, csv or xlsx"}, status=400)
