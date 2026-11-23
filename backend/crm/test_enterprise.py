from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from crm.models import Activity, Lead, Opportunity


class CrmEnterpriseTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-crm",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("crm-owner", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_hot_lead_scores_from_rating(self):
        r = self.client.post(
            "/api/crm/leads/",
            {"name": "Sara", "rating": "hot", "industry": "Retail"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["score"], 80)
        self.assertEqual(r.data["industry"], "Retail")

    def test_explicit_lead_score_is_kept(self):
        r = self.client.post(
            "/api/crm/leads/",
            {"name": "Sara", "rating": "hot", "score": 15},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["score"], 15)

    def test_lost_opportunity_requires_reason_and_stage_sets_probability(self):
        r = self.client.post(
            "/api/crm/opportunities/",
            {"name": "Deal", "stage": "lost"},
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("close_reason", r.data)

        r = self.client.post(
            "/api/crm/opportunities/",
            {"name": "Deal", "stage": "negotiation", "amount": "10000"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["probability"], 70)
        self.assertEqual(r.data["weighted_amount"], "7000.00")

        r = self.client.patch(
            f"/api/crm/opportunities/{r.data['id']}/",
            {"stage": "lost", "close_reason": "Price"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["probability"], 0)

    def test_pipeline_forecast(self):
        Opportunity.objects.create(
            organization=self.org,
            name="Open",
            amount=Decimal("1000"),
            stage=Opportunity.Stage.PROPOSAL,
            probability=40,
        )
        Opportunity.objects.create(
            organization=self.org,
            name="Won",
            amount=Decimal("500"),
            stage=Opportunity.Stage.WON,
            probability=100,
        )
        r = self.client.get("/api/crm/opportunities/pipeline/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["open_count"], 1)
        self.assertEqual(r.data["open_amount"], "1000.00")
        self.assertEqual(r.data["weighted_amount"], "400.00")
        self.assertEqual(r.data["won_amount"], "500.00")

    def test_activity_requires_a_record_and_marks_completed(self):
        r = self.client.post(
            "/api/crm/activities/",
            {"subject": "Call", "type": "call"},
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)

        lead = Lead.objects.create(organization=self.org, name="Ali")
        r = self.client.post(
            "/api/crm/activities/",
            {
                "subject": "Call Ali",
                "type": "call",
                "lead": lead.id,
                "due_date": "2020-01-01",
                "priority": "high",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.data["is_overdue"])

        r = self.client.patch(
            f"/api/crm/activities/{r.data['id']}/",
            {"done": True},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(r.data["is_overdue"])
        self.assertIsNotNone(r.data["completed_at"])
        row = Activity.objects.get(pk=r.data["id"])
        self.assertIsNotNone(row.completed_at)
        self.assertLessEqual(row.completed_at, timezone.now())

    def test_lost_lead_requires_a_reason(self):
        r = self.client.post(
            "/api/crm/leads/",
            {"name": "Sara", "status": "lost"},
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post(
            "/api/crm/leads/",
            {"name": "Sara", "status": "lost", "lost_reason": "No budget", "priority": "urgent"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["priority"], "urgent")
        self.assertEqual(r.data["lost_reason"], "No budget")

    def test_move_stage_sets_probability_and_lost_date(self):
        created = self.client.post(
            "/api/crm/opportunities/",
            {"name": "Deal", "stage": "prospecting", "amount": "2000"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        opp_id = created.data["id"]
        moved = self.client.post(
            f"/api/crm/opportunities/{opp_id}/move/",
            {"stage": "negotiation"},
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(moved.data["stage"], "negotiation")
        self.assertEqual(moved.data["probability"], 70)
        lost = self.client.post(
            f"/api/crm/opportunities/{opp_id}/move/",
            {"stage": "lost"},
            format="json",
        )
        self.assertEqual(lost.status_code, 400, lost.content)
        lost = self.client.post(
            f"/api/crm/opportunities/{opp_id}/move/",
            {"stage": "lost", "close_reason": "Went with another vendor"},
            format="json",
        )
        self.assertEqual(lost.status_code, 200, lost.content)
        self.assertEqual(lost.data["probability"], 0)
        self.assertIsNotNone(lost.data["lost_on"])

    def test_board_and_forecast(self):
        Opportunity.objects.create(
            organization=self.org,
            name="This month",
            amount=Decimal("1000"),
            stage=Opportunity.Stage.PROPOSAL,
            probability=40,
            priority="high",
            expected_close=date.today().replace(day=1),
        )
        Opportunity.objects.create(
            organization=self.org,
            name="Slipped",
            amount=Decimal("500"),
            stage=Opportunity.Stage.PROSPECTING,
            probability=10,
            expected_close=date.today().replace(day=1) - timedelta(days=40),
        )
        board = self.client.get("/api/crm/opportunities/board/")
        self.assertEqual(board.status_code, 200, board.content)
        self.assertEqual(len(board.data), 5)
        proposal = next(col for col in board.data if col["stage"] == "proposal")
        self.assertEqual(proposal["cards"][0]["name"], "This month")
        self.assertEqual(proposal["probability"], 40)

        pipeline = self.client.get("/api/crm/opportunities/pipeline/")
        self.assertEqual(pipeline.status_code, 200, pipeline.content)
        self.assertIsNone(pipeline.data["win_rate"])
        slipped = next(row for row in pipeline.data["forecast"] if row["key"] == "overdue")
        self.assertEqual(slipped["count"], 1)
        self.assertEqual(slipped["weighted"], "50.00")

        won = self.client.post(
            f"/api/crm/opportunities/{proposal['cards'][0]['id']}/move/",
            {"stage": "won"},
            format="json",
        )
        self.assertEqual(won.status_code, 200, won.content)
        pipeline = self.client.get("/api/crm/opportunities/pipeline/")
        self.assertEqual(pipeline.data["won_count"], 1)
        self.assertEqual(pipeline.data["win_rate"], "100.0")

    def test_duplicate_lead_and_customer_match(self):
        from ops.models import Customer

        Lead.objects.create(
            organization=self.org,
            name="Sara",
            company="Sara Mills",
            email="sara@saramills.com",
            phone="0300-1112233",
        )
        Customer.objects.create(
            organization=self.org,
            code="C-1",
            name="Sara Mills",
            email="sales@saramills.com",
        )
        r = self.client.get(
            "/api/crm/leads/check-duplicate/",
            {"email": "sara@saramills.com", "company": "Sara Mills"},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["leads"][0]["name"], "Sara")
        self.assertEqual(r.data["customers"][0]["code"], "C-1")

        phone = self.client.get(
            "/api/crm/leads/check-duplicate/",
            {"phone": "+92 300 1112233"},
        )
        self.assertEqual(phone.data["leads"][0]["email"], "sara@saramills.com")

    def test_complete_activity_records_outcome(self):
        lead = Lead.objects.create(organization=self.org, name="Ali")
        created = self.client.post(
            "/api/crm/activities/",
            {"subject": "Call Ali", "type": "call", "lead": lead.id},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data["owner"], self.user.id)
        done = self.client.post(
            f"/api/crm/activities/{created.data['id']}/complete/",
            {"outcome": "Asked for a revised quote"},
            format="json",
        )
        self.assertEqual(done.status_code, 200, done.content)
        self.assertTrue(done.data["done"])
        self.assertEqual(done.data["outcome"], "Asked for a revised quote")
        self.assertIsNotNone(done.data["completed_at"])

    def test_calendar_lists_timed_and_all_day_activities(self):
        lead = Lead.objects.create(organization=self.org, name="Ali")
        meeting = self.client.post(
            "/api/crm/activities/",
            {
                "subject": "Site visit",
                "type": "meeting",
                "lead": lead.id,
                "starts_at": "2026-11-10T09:00:00",
                "ends_at": "2026-11-10T10:30:00",
                "location": "Plant gate",
            },
            format="json",
        )
        self.assertEqual(meeting.status_code, 201, meeting.content)
        self.assertEqual(meeting.data["due_date"], "2026-11-10")
        self.assertFalse(meeting.data["all_day"])
        self.assertEqual(meeting.data["location"], "Plant gate")

        backwards = self.client.post(
            "/api/crm/activities/",
            {
                "subject": "Bad",
                "type": "meeting",
                "lead": lead.id,
                "starts_at": "2026-11-10T11:00:00",
                "ends_at": "2026-11-10T10:00:00",
            },
            format="json",
        )
        self.assertEqual(backwards.status_code, 400, backwards.content)

        call = self.client.post(
            "/api/crm/activities/",
            {
                "subject": "Follow-up call",
                "type": "call",
                "lead": lead.id,
                "due_date": "2026-11-12",
                "owner": None,
            },
            format="json",
        )
        self.assertEqual(call.status_code, 201, call.content)
        self.assertTrue(call.data["all_day"])
        self.assertIsNone(call.data["owner"])

        listed = self.client.get(
            "/api/crm/activities/calendar/",
            {"start": "2026-11-01", "end": "2026-12-01"},
        )
        self.assertEqual(listed.status_code, 200, listed.content)
        subjects = {row["subject"] for row in listed.data}
        self.assertEqual(subjects, {"Site visit", "Follow-up call"})

        mine = self.client.get(
            "/api/crm/activities/calendar/",
            {"start": "2026-11-01", "end": "2026-12-01", "mine": "1"},
        )
        self.assertEqual([row["subject"] for row in mine.data], ["Site visit"])

    def test_enabled_calendars_each_receive_a_copy(self):
        from unittest.mock import patch

        from integrations.models import IntegrationConnection

        for key in ("microsoft365_calendar", "google_calendar", "caldav_calendar"):
            IntegrationConnection.objects.create(
                organization=self.org,
                connector_key=key,
                display_name=key,
                is_enabled=key != "caldav_calendar",
                status=IntegrationConnection.Status.ACTIVE,
            )
        lead = Lead.objects.create(organization=self.org, name="Ali")
        activity = Activity.objects.create(
            organization=self.org,
            lead=lead,
            subject="Site visit",
            type="meeting",
            starts_at=timezone.now(),
        )

        def fake_upsert(conn, row, ref):
            return {"id": f"{conn.connector_key}-event"}

        with patch("integrations.calendars._upsert", side_effect=fake_upsert):
            from integrations.calendars import sync_activity_calendars

            sync_activity_calendars(activity)
        activity.refresh_from_db()
        self.assertEqual(
            set(activity.external_events),
            {"microsoft365_calendar", "google_calendar"},
        )
        self.assertNotIn("caldav_calendar", activity.external_events)

        targets = self.client.get("/api/crm/activities/calendar-targets/")
        self.assertEqual(targets.status_code, 200, targets.content)
        self.assertEqual(
            {row["key"] for row in targets.data},
            {"microsoft365_calendar", "google_calendar"},
        )
