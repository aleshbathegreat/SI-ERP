"""Tier-4 settings masters: doc number series, approval matrix, import hub."""

from __future__ import annotations

from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import can
from core.access import user_organization
from core.bulk import BulkDeleteMixin
from core.import_engine import (
    build_all_templates_zip,
    build_template_csv,
    list_catalog,
    run_import,
    run_import_zip,
)
from core.models import ApprovalMatrixRule, DocNumberSeries
from core.scoping import OrgScopedQuerysetMixin

RO = ("organization", "created_at", "updated_at", "created_by", "updated_by")


class DocNumberSeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocNumberSeries
        fields = "__all__"
        read_only_fields = RO


class ApprovalMatrixRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalMatrixRule
        fields = "__all__"
        read_only_fields = RO


class DocNumberSeriesViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocNumberSeries.objects.all()
    serializer_class = DocNumberSeriesSerializer
    search_fields = ("kind", "prefix")
    filterset_fields = ("kind", "reset_yearly")
    rbac_module = "settings.doc_series"


class ApprovalMatrixRuleViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = ApprovalMatrixRule.objects.all()
    serializer_class = ApprovalMatrixRuleSerializer
    search_fields = ("module_key", "role_code")
    filterset_fields = ("module_key", "role_code")
    rbac_module = "settings.approval_matrix"


def _hub_allowed(user, action: str = "view") -> bool:
    if can(user, "settings.import_hub", action):
        return True
    if action == "view" and can(user, "settings.import_hub", "add"):
        return True
    # Owners / admins with settings.users can use the hub.
    if can(user, "settings.users", "change") or can(user, "settings.users", "add"):
        return True
    return False


class ImportHubCatalogView(APIView):
    """List importable entities + column specs."""

    rbac_module = "settings.import_hub"

    def get(self, request):
        if not _hub_allowed(request.user, "view"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        return Response({"entities": list_catalog()})


class ImportHubTemplateView(APIView):
    """Download a CSV template (header + sample rows) for an entity."""

    rbac_module = "settings.import_hub"

    def get(self, request, entity: str):
        if not _hub_allowed(request.user, "view"):
            return Response({"detail": "Permission denied"}, status=403)
        try:
            body = build_template_csv(entity)
        except KeyError:
            return Response({"detail": f"Unknown entity '{entity}'"}, status=404)
        # UTF-8 BOM so Excel opens columns correctly
        payload = ("\ufeff" + body).encode("utf-8")
        resp = HttpResponse(payload, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = (
            f'attachment; filename="import_{entity}_template.csv"'
        )
        return resp


class ImportHubTemplatesPackView(APIView):
    """Download all CSV templates as a ZIP (README + ordered files + manifest)."""

    rbac_module = "settings.import_hub"

    def get(self, request):
        if not _hub_allowed(request.user, "view"):
            return Response({"detail": "Permission denied"}, status=403)
        data = build_all_templates_zip()
        resp = HttpResponse(data, content_type="application/zip")
        resp["Content-Disposition"] = (
            'attachment; filename="sierp_import_templates.zip"'
        )
        resp["Content-Length"] = str(len(data))
        return resp


class ImportHubPreviewView(APIView):
    """Validate CSV (dry-run). Does not write data."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    rbac_module = "settings.import_hub"

    def post(self, request):
        if not _hub_allowed(request.user, "add") and not _hub_allowed(request.user, "view"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        entity = (
            request.data.get("entity")
            or request.query_params.get("entity")
            or ""
        ).strip()
        if not entity:
            return Response(
                {"detail": "entity is required (e.g. employees, customers, items)"},
                status=400,
            )
        upload = request.FILES.get("file") or request.FILES.get("csv")
        if not upload:
            return Response({"detail": "Upload a CSV as file=…"}, status=400)
        try:
            text = upload.read().decode("utf-8-sig", errors="replace")
            result = run_import(org, entity, text, dry_run=True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:
            return Response({"detail": f"Could not parse/validate CSV: {exc}"}, status=400)
        result["filename"] = getattr(upload, "name", "")
        result["message"] = (
            "Dry-run complete — review errors then use Commit import to write data."
        )
        # Back-compat for old UI
        result["columns"] = result.get("filename_headers") or []
        return Response(result)


class ImportHubCommitView(APIView):
    """Commit CSV import (upsert / create)."""

    parser_classes = [MultiPartParser, FormParser]
    rbac_module = "settings.import_hub"

    def post(self, request):
        if not _hub_allowed(request.user, "add"):
            return Response({"detail": "Permission denied — need import add"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        entity = (request.data.get("entity") or "").strip()
        if not entity:
            return Response({"detail": "entity is required"}, status=400)
        upload = request.FILES.get("file") or request.FILES.get("csv")
        if not upload:
            return Response({"detail": "Upload a CSV as file=…"}, status=400)
        confirm = str(request.data.get("confirm") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not confirm:
            return Response(
                {"detail": "Set confirm=true after reviewing the dry-run preview"},
                status=400,
            )
        try:
            text = upload.read().decode("utf-8-sig", errors="replace")
            result = run_import(org, entity, text, dry_run=False)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:
            return Response({"detail": f"Import failed: {exc}"}, status=400)
        result["filename"] = getattr(upload, "name", "")
        result["message"] = (
            f"Import finished: {result.get('created', 0)} created, "
            f"{result.get('updated', 0)} updated, {result.get('skipped', 0)} skipped, "
            f"{result.get('error_count', 0)} errors."
        )
        status = 200 if result.get("error_count", 0) == 0 else 207
        return Response(result, status=status)


class ImportHubPackPreviewView(APIView):
    """Validate a multi-entity ZIP pack (dry-run, recommended order)."""

    parser_classes = [MultiPartParser, FormParser]
    rbac_module = "settings.import_hub"

    def post(self, request):
        if not _hub_allowed(request.user, "add") and not _hub_allowed(request.user, "view"):
            return Response({"detail": "Permission denied"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        upload = request.FILES.get("file") or request.FILES.get("zip")
        if not upload:
            return Response({"detail": "Upload a ZIP as file=…"}, status=400)
        try:
            result = run_import_zip(org, upload.read(), dry_run=True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:
            return Response({"detail": f"Could not read ZIP: {exc}"}, status=400)
        result["filename"] = getattr(upload, "name", "")
        return Response(result)


class ImportHubPackCommitView(APIView):
    """Commit a multi-entity ZIP pack after a clean dry-run."""

    parser_classes = [MultiPartParser, FormParser]
    rbac_module = "settings.import_hub"

    def post(self, request):
        if not _hub_allowed(request.user, "add"):
            return Response({"detail": "Permission denied — need import add"}, status=403)
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        upload = request.FILES.get("file") or request.FILES.get("zip")
        if not upload:
            return Response({"detail": "Upload a ZIP as file=…"}, status=400)
        confirm = str(request.data.get("confirm") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not confirm:
            return Response(
                {"detail": "Set confirm=true after reviewing the ZIP dry-run"},
                status=400,
            )
        try:
            result = run_import_zip(org, upload.read(), dry_run=False)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:
            return Response({"detail": f"ZIP import failed: {exc}"}, status=400)
        result["filename"] = getattr(upload, "name", "")
        status = 200 if result.get("error_count", 0) == 0 else 207
        return Response(result, status=status)
