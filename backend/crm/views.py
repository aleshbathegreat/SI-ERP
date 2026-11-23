from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Prefetch, Q, Sum
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as SerValidationError
from rest_framework.response import Response

from accounts.rbac import can
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from crm.models import STAGE_PROBABILITY, Activity, Lead, Opportunity
from crm.serializers import ActivitySerializer, LeadSerializer, OpportunitySerializer
from crm.services import (
    build_forecast,
    convert_lead,
    create_quote_from_opportunity,
    find_lead_duplicates,
)

PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
BOARD_CARD_LIMIT = 80


def _calendar_bounds(start_raw, end_raw):
    """Inclusive start and exclusive end. Date-only values are local midnights."""
    tz = timezone.get_current_timezone()
    today = timezone.localdate()

    def parse_bound(raw):
        moment = parse_datetime(raw)
        if moment:
            if timezone.is_naive(moment):
                moment = timezone.make_aware(moment, tz)
            return moment
        day = parse_date(raw or "")
        if day:
            return timezone.make_aware(datetime.combine(day, time.min), tz)
        raise SerValidationError("Use a date (YYYY-MM-DD) for start and end.")

    if not start_raw and not end_raw:
        start_day = today.replace(day=1)
        if start_day.month == 12:
            end_day = date(start_day.year + 1, 1, 1)
        else:
            end_day = date(start_day.year, start_day.month + 1, 1)
        return (
            timezone.make_aware(datetime.combine(start_day, time.min), tz),
            timezone.make_aware(datetime.combine(end_day, time.min), tz),
        )
    if not start_raw or not end_raw:
        raise SerValidationError("Provide both start and end.")
    start = parse_bound(start_raw)
    end = parse_bound(end_raw)
    if end <= start:
        raise SerValidationError("End must be after start.")
    return start, end


class LeadViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Lead.objects.select_related(
        "owner", "converted_customer", "converted_opportunity"
    )
    serializer_class = LeadSerializer
    search_fields = ("name", "company", "email", "phone", "source", "industry", "campaign")
    filterset_fields = ("status", "owner")
    rbac_module = "crm.leads"

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        lead = self.get_object()
        try:
            customer, opportunity, created = convert_lead(
                lead, user=request.user, data=request.data or {}
            )
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        lead.refresh_from_db()
        return Response(
            {
                "lead": self.get_serializer(lead).data,
                "created": created,
                "customer_id": customer.id if customer else None,
                "customer_code": customer.code if customer else "",
                "opportunity_id": opportunity.id if opportunity else None,
                "href": f"/crm/opportunities/{opportunity.id}" if opportunity else "",
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="check-duplicate")
    def check_duplicate(self, request):
        exclude = request.query_params.get("exclude")
        try:
            exclude_id = int(exclude) if exclude else None
        except (TypeError, ValueError):
            exclude_id = None
        from core.access import user_organization

        organization = user_organization(request.user)
        if organization is None:
            return Response({"leads": [], "customers": []})
        leads, customers = find_lead_duplicates(
            organization.id,
            email=request.query_params.get("email") or "",
            phone=request.query_params.get("phone") or "",
            company=request.query_params.get("company") or "",
            exclude_id=exclude_id,
        )
        return Response(
            {
                "leads": [
                    {
                        "id": row.id,
                        "name": row.name,
                        "company": row.company,
                        "status": row.status,
                        "email": row.email,
                    }
                    for row in leads
                ],
                "customers": [
                    {"id": row.id, "name": row.name, "code": row.code}
                    for row in customers
                ],
            }
        )


class OpportunityViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Opportunity.objects.select_related("lead", "customer", "owner")
    serializer_class = OpportunitySerializer
    search_fields = ("name", "next_step", "competitor", "close_reason")
    filterset_fields = ("stage", "lead", "customer", "owner")
    rbac_module = "crm.opportunities"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related(
            Prefetch(
                "activities",
                queryset=Activity.objects.filter(done=False).order_by("due_date", "id"),
                to_attr="open_activities",
            )
        )

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        opp = self.get_object()
        stage = request.data.get("stage")
        if stage not in dict(Opportunity.Stage.choices):
            raise SerValidationError({"stage": "Unknown stage."})
        payload = {"stage": stage}
        reason = request.data.get("close_reason")
        if reason not in (None, ""):
            payload["close_reason"] = reason
        serializer = self.get_serializer(opp, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def board(self, request):
        qs = self.filter_queryset(self.get_queryset())
        columns = []
        far = date(9999, 12, 31)
        for stage, label in Opportunity.Stage.choices:
            stage_qs = qs.filter(stage=stage)
            count = stage_qs.count()
            amount = stage_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
            rows = list(stage_qs.order_by("-id")[:500])
            rows.sort(
                key=lambda row: (
                    PRIORITY_RANK.get(row.priority, 2),
                    row.expected_close or far,
                    -row.id,
                )
            )
            shown = rows[:BOARD_CARD_LIMIT]
            columns.append(
                {
                    "stage": stage,
                    "label": label,
                    "probability": STAGE_PROBABILITY.get(stage, 0),
                    "count": count,
                    "amount": str(Decimal(amount).quantize(Decimal("0.01"))),
                    "truncated": count > len(shown),
                    "cards": self.get_serializer(shown, many=True).data,
                }
            )
        return Response(columns)

    @action(detail=True, methods=["post"], url_path="create-quote")
    def create_quote(self, request, pk=None):
        opp = self.get_object()
        if not can(request.user, "sales.quotes", "add"):
            raise PermissionDenied("Missing permission: sales.quotes:add")
        try:
            quote, created = create_quote_from_opportunity(opp, user=request.user)
        except SerValidationError:
            raise
        except Exception as e:
            raise SerValidationError(str(e)) from e
        opp.refresh_from_db()
        return Response(
            {
                "opportunity": self.get_serializer(opp).data,
                "created": created,
                "quotation_id": quote.id,
                "quote_no": quote.quote_no,
                "href": f"/sales/quotes/{quote.id}",
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def pipeline(self, request):
        qs = self.filter_queryset(self.get_queryset())
        stages = []
        open_count = 0
        open_amount = Decimal("0")
        weighted = Decimal("0")
        won_amount = Decimal("0")
        won_count = 0
        lost_count = 0
        open_rows = []
        for stage, label in Opportunity.Stage.choices:
            rows = list(qs.filter(stage=stage))
            amount = sum((row.amount or Decimal("0") for row in rows), Decimal("0"))
            stage_weighted = sum(
                (
                    (row.amount or Decimal("0"))
                    * Decimal(row.probability or 0)
                    / Decimal(100)
                    for row in rows
                ),
                Decimal("0"),
            )
            amount = amount.quantize(Decimal("0.01"))
            stage_weighted = stage_weighted.quantize(Decimal("0.01"))
            stages.append(
                {
                    "stage": stage,
                    "label": label,
                    "count": len(rows),
                    "amount": str(amount),
                    "weighted": str(stage_weighted),
                }
            )
            if stage == Opportunity.Stage.WON:
                won_amount = amount
                won_count = len(rows)
            elif stage == Opportunity.Stage.LOST:
                lost_count = len(rows)
            else:
                open_count += len(rows)
                open_amount += amount
                weighted += stage_weighted
                open_rows.extend(rows)
        closed = won_count + lost_count
        win_rate = None
        if closed:
            win_rate = str(
                (Decimal(won_count) * Decimal(100) / Decimal(closed)).quantize(
                    Decimal("0.1")
                )
            )
        return Response(
            {
                "open_count": open_count,
                "open_amount": str(open_amount.quantize(Decimal("0.01"))),
                "weighted_amount": str(weighted.quantize(Decimal("0.01"))),
                "won_amount": str(won_amount),
                "won_count": won_count,
                "lost_count": lost_count,
                "win_rate": win_rate,
                "stages": stages,
                "forecast": build_forecast(open_rows),
            }
        )


class ActivityViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Activity.objects.select_related("lead", "opportunity", "owner")
    serializer_class = ActivitySerializer
    search_fields = ("subject", "description", "location")
    filterset_fields = ("type", "done", "lead", "opportunity", "priority", "owner")
    rbac_module = "crm.activities"

    def get_queryset(self):
        qs = super().get_queryset()
        flag = (self.request.query_params.get("overdue") or "").lower()
        if flag in ("1", "true", "yes"):
            qs = qs.filter(done=False, due_date__lt=timezone.localdate())
        return qs

    def perform_create(self, serializer):
        if "owner" not in self.request.data:
            serializer.validated_data["owner"] = self.request.user
        super().perform_create(serializer)
        self._sync_calendars(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._sync_calendars(serializer.instance)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        row = Activity.all_objects.filter(pk=instance.pk).first()
        if row:
            self._sync_calendars(row)

    def bulk_delete(self, request):
        ids = request.data.get("ids") or []
        response = super().bulk_delete(request)
        if getattr(response, "status_code", 0) == 200 and isinstance(ids, list):
            for row in Activity.all_objects.filter(pk__in=ids):
                self._sync_calendars(row)
        return response

    def _sync_calendars(self, activity):
        from integrations.calendars import sync_activity_calendars

        sync_activity_calendars(activity)

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        start, end = _calendar_bounds(
            request.query_params.get("start"),
            request.query_params.get("end"),
        )
        qs = self.filter_queryset(self.get_queryset())
        if (request.query_params.get("mine") or "").lower() in ("1", "true", "yes"):
            qs = qs.filter(owner=request.user)
        kind = (request.query_params.get("type") or "").strip()
        if kind:
            qs = qs.filter(type=kind)
        qs = qs.filter(
            Q(starts_at__lt=end)
            & (Q(ends_at__gte=start) | Q(ends_at__isnull=True, starts_at__gte=start))
            | Q(
                starts_at__isnull=True,
                due_date__gte=timezone.localtime(start).date(),
                due_date__lt=timezone.localtime(end).date(),
            )
        ).order_by("starts_at", "due_date", "id")
        rows = list(qs[:500])
        return Response(self.get_serializer(rows, many=True).data)

    @action(detail=False, methods=["get"], url_path="calendar-targets")
    def calendar_targets(self, request):
        from integrations.calendars import LABELS, active_calendar_connections
        from core.access import user_organization

        organization = user_organization(request.user)
        if organization is None:
            return Response([])
        rows = [
            {"key": conn.connector_key, "name": LABELS.get(conn.connector_key, conn.display_name)}
            for conn in active_calendar_connections(organization)
        ]
        return Response(rows)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        row = self.get_object()
        payload = {"done": True}
        if "outcome" in request.data:
            payload["outcome"] = request.data.get("outcome") or ""
        serializer = self.get_serializer(row, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._sync_calendars(serializer.instance)
        return Response(self.get_serializer(serializer.instance).data)
