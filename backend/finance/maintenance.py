"""CMMS helpers: PM schedule roll-forward and due work-order generation."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction

from core.doc_numbers import ensure_doc_no
from finance.models import MaintenanceWorkOrder, PmSchedule

OPEN_STATUSES = (
    MaintenanceWorkOrder.Status.OPEN,
    MaintenanceWorkOrder.Status.SCHEDULED,
    MaintenanceWorkOrder.Status.IN_PROGRESS,
)


def roll_schedule_forward(schedule: PmSchedule, done_on: date) -> None:
    schedule.last_done = done_on
    schedule.next_due = done_on + timedelta(days=max(1, schedule.frequency_days or 1))
    schedule.save(update_fields=["last_done", "next_due", "updated_at"])


def mark_done(mwo: MaintenanceWorkOrder, *, user=None, done_on: date | None = None):
    done_on = done_on or mwo.completed_date or date.today()
    mwo.status = MaintenanceWorkOrder.Status.DONE
    mwo.completed_date = done_on
    if user is not None:
        mwo.updated_by = user
    mwo.save(update_fields=["status", "completed_date", "updated_by", "updated_at"])
    if mwo.pm_schedule_id and mwo.pm_schedule.active:
        roll_schedule_forward(mwo.pm_schedule, done_on)
    return mwo


def generate_due_work_orders(org, *, user=None, today: date | None = None):
    """Create an open MWO for each active schedule due on/before today."""
    today = today or date.today()
    created: list[MaintenanceWorkOrder] = []
    skipped = 0
    with transaction.atomic():
        schedules = (
            PmSchedule.objects.select_for_update()
            .select_related("asset")
            .filter(
                organization=org,
                active=True,
                next_due__isnull=False,
                next_due__lte=today,
            )
        )
        for sch in schedules:
            if sch.asset.is_deleted or MaintenanceWorkOrder.objects.filter(
                organization=org, pm_schedule=sch, status__in=OPEN_STATUSES
            ).exists():
                skipped += 1
                continue
            data: dict = {}
            ensure_doc_no(data, "mwo_no", org, kind="mwo", model=MaintenanceWorkOrder)
            created.append(
                MaintenanceWorkOrder.objects.create(
                    organization=org,
                    mwo_no=data["mwo_no"],
                    asset=sch.asset,
                    pm_schedule=sch,
                    title=sch.title,
                    description=f"Preventive maintenance ({sch.frequency_days}d cycle)",
                    status=MaintenanceWorkOrder.Status.OPEN,
                    scheduled_date=sch.next_due,
                    created_by=user,
                )
            )
    return created, skipped
