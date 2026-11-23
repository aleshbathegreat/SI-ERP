from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from crm.models import RATING_SCORE, STAGE_PROBABILITY, Activity, Lead, Opportunity

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


def _user_label(u):
    if not u:
        return ""
    return (u.get_full_name() or u.username or str(u.pk)).strip()


class LeadSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(
        min_value=0, max_value=100, required=False, allow_null=True
    )
    owner_name = serializers.SerializerMethodField()
    converted_customer_name = serializers.CharField(
        source="converted_customer.name", read_only=True, default=""
    )
    converted_opportunity_name = serializers.CharField(
        source="converted_opportunity.name", read_only=True, default=""
    )

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = RO + ("converted_customer", "converted_opportunity")

    def get_owner_name(self, obj):
        return _user_label(obj.owner)

    def validate_status(self, value):
        # "converted" is only reachable through POST /crm/leads/{id}/convert/
        current = self.instance.status if self.instance else None
        if value == Lead.Status.CONVERTED and current != Lead.Status.CONVERTED:
            raise serializers.ValidationError(
                "Use the Convert action to convert a lead."
            )
        return value

    def validate(self, attrs):
        if attrs.get("score") is None:
            attrs.pop("score", None)
        rating = attrs.get("rating", getattr(self.instance, "rating", Lead.Rating.WARM))
        if "score" not in attrs and (
            self.instance is None or "rating" in self.initial_data
        ):
            attrs["score"] = RATING_SCORE.get(rating, 50)
        status = attrs.get("status", getattr(self.instance, "status", Lead.Status.NEW))
        reason = attrs.get("lost_reason", getattr(self.instance, "lost_reason", ""))
        if status == Lead.Status.LOST and not str(reason or "").strip():
            raise serializers.ValidationError(
                {"lost_reason": "A lost reason is required when the lead is Lost."}
            )
        return attrs


class OpportunitySerializer(serializers.ModelSerializer):
    probability = serializers.IntegerField(
        min_value=0, max_value=100, required=False, allow_null=True
    )
    lead_name = serializers.CharField(source="lead.name", read_only=True, default="")
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=""
    )
    owner_name = serializers.SerializerMethodField()
    weighted_amount = serializers.SerializerMethodField()
    next_activity = serializers.SerializerMethodField()
    next_activity_label = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = RO

    def get_owner_name(self, obj):
        return _user_label(obj.owner)

    def get_weighted_amount(self, obj):
        amount = Decimal(obj.amount or 0)
        probability = Decimal(obj.probability or 0)
        return str((amount * probability / Decimal(100)).quantize(Decimal("0.01")))

    def _next_open_activity(self, obj):
        if hasattr(obj, "_next_activity_row"):
            return obj._next_activity_row
        rows = getattr(obj, "open_activities", None)
        if rows is None:
            rows = list(obj.activities.filter(done=False).order_by("due_date", "id")[:1])
        row = rows[0] if rows else None
        obj._next_activity_row = row
        return row

    def get_next_activity(self, obj):
        row = self._next_open_activity(obj)
        if row is None:
            return None
        due = row.due_date
        return {
            "id": row.id,
            "subject": row.subject,
            "type": row.type,
            "due_date": due.isoformat() if due else None,
            "is_overdue": bool(due and due < timezone.localdate()),
        }

    def get_next_activity_label(self, obj):
        info = self.get_next_activity(obj)
        if not info:
            return ""
        if info["is_overdue"]:
            return f"Overdue · {info['subject']}"
        if info["due_date"]:
            return f"{info['due_date']} · {info['subject']}"
        return info["subject"]

    def validate(self, attrs):
        stage = attrs.get("stage", getattr(self.instance, "stage", None))
        raw_probability = self.initial_data.get("probability", None)
        if attrs.get("probability") is None:
            attrs.pop("probability", None)
        if "stage" in attrs and raw_probability in (None, ""):
            attrs["probability"] = STAGE_PROBABILITY.get(stage, 10)
        elif self.instance is None and "probability" not in attrs:
            attrs["probability"] = STAGE_PROBABILITY.get(
                attrs.get("stage", Opportunity.Stage.PROSPECTING), 10
            )
        reason = attrs.get(
            "close_reason", getattr(self.instance, "close_reason", "")
        )
        if stage == Opportunity.Stage.LOST and not str(reason or "").strip():
            raise serializers.ValidationError(
                {
                    "close_reason": "A close reason is required when the stage is Lost."
                }
            )
        today = timezone.localdate()
        if stage == Opportunity.Stage.WON:
            if not attrs.get("won_on"):
                attrs["won_on"] = getattr(self.instance, "won_on", None) or today
            attrs["lost_on"] = None
        elif stage == Opportunity.Stage.LOST:
            if not attrs.get("lost_on"):
                attrs["lost_on"] = getattr(self.instance, "lost_on", None) or today
            attrs["won_on"] = None
        elif "stage" in attrs:
            attrs["won_on"] = None
            attrs["lost_on"] = None
        return attrs


class ActivitySerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True, default="")
    opportunity_name = serializers.CharField(
        source="opportunity.name", read_only=True, default=""
    )
    owner_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    all_day = serializers.SerializerMethodField()
    calendar_sync = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = "__all__"
        read_only_fields = RO + ("completed_at", "external_events")

    def get_owner_name(self, obj):
        return _user_label(obj.owner)

    def get_is_overdue(self, obj):
        if obj.done or not obj.due_date:
            return False
        return obj.due_date < timezone.localdate()

    def get_all_day(self, obj):
        return obj.starts_at is None

    def get_calendar_sync(self, obj):
        from integrations.calendars import LABELS

        names = [
            LABELS.get(key, key)
            for key, ref in (obj.external_events or {}).items()
            if ref
        ]
        return ", ".join(names)

    def validate(self, attrs):
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        opportunity = attrs.get(
            "opportunity", getattr(self.instance, "opportunity", None)
        )
        if lead is None and opportunity is None:
            raise serializers.ValidationError(
                "Link this activity to a lead or an opportunity."
            )
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts and ends and ends < starts:
            raise serializers.ValidationError(
                {"ends_at": "The end must be at or after the start."}
            )
        due = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if starts and not due:
            moment = starts
            if timezone.is_aware(moment):
                moment = timezone.localtime(moment)
            attrs["due_date"] = moment.date()
        if "done" in attrs:
            if attrs["done"]:
                attrs["completed_at"] = timezone.now()
            else:
                attrs["completed_at"] = None
        return attrs
