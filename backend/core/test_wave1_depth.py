from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from crm.models import Lead, Opportunity
from mfg.models import Bom, BomLine, WorkOrder
from finance.models import CustomerInvoice
from ops.models import Customer, Item, SalesQuotation, StockLevel, Warehouse
from projects.models import Project, ProjectTask, TimeEntry


class Wave1DepthTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("owner1", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.approver = User.objects.create_user("appr1", password="x-long-password-2")
        UserProfile.objects.create(
            user=self.approver, organization=self.org, role=UserProfile.RoleCode.APPROVER
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # ---- CRM -------------------------------------------------------------
    def test_lead_convert_and_quote(self):
        lead = Lead.objects.create(
            organization=self.org,
            name="Ali Khan",
            company="Khan Traders",
            email="ali@khan.test",
            phone="0300",
        )
        r = self.client.post(f"/api/crm/leads/{lead.id}/convert/", {}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        lead.refresh_from_db()
        self.assertEqual(lead.status, "converted")
        self.assertEqual(lead.converted_customer.name, "Khan Traders")
        opp = lead.converted_opportunity
        self.assertEqual(opp.lead_id, lead.id)
        self.assertEqual(opp.customer_id, lead.converted_customer_id)
        # idempotent
        r2 = self.client.post(f"/api/crm/leads/{lead.id}/convert/", {}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(Customer.objects.filter(organization=self.org).count(), 1)

        opp.amount = Decimal("5000")
        opp.save()
        r = self.client.post(
            f"/api/crm/opportunities/{opp.id}/create-quote/", {}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        q = SalesQuotation.objects.get(pk=r.data["quotation_id"])
        self.assertEqual(q.opportunity_id, opp.id)
        self.assertEqual(q.status, "draft")
        self.assertEqual(q.amount, Decimal("5000"))

    def test_lead_cannot_be_set_converted_via_patch(self):
        lead = Lead.objects.create(organization=self.org, name="X")
        r = self.client.patch(
            f"/api/crm/leads/{lead.id}/", {"status": "converted"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_opportunity_probability_bounds(self):
        r = self.client.post(
            "/api/crm/opportunities/",
            {"name": "Deal", "probability": 150},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.post(
            "/api/crm/opportunities/",
            {"name": "Deal", "probability": 40, "close_reason": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)

    # ---- Projects --------------------------------------------------------
    def test_timesheet_approve_and_summary(self):
        proj = Project.objects.create(
            organization=self.org, code="P1", name="Proj", budget_amount=1000
        )
        task = ProjectTask.objects.create(organization=self.org, project=proj, name="T")
        r = self.client.post(
            "/api/projects/timesheets/",
            {
                "project": proj.id,
                "task": task.id,
                "date": "2026-10-01",
                "hours": "4.5",
                "rate": "100",
                "billable": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        tid = r.data["id"]
        self.assertEqual(r.data["status"], "draft")
        r = self.client.post(f"/api/projects/timesheets/{tid}/submit/")
        self.assertEqual(r.status_code, 200, r.content)
        # SoD: submitter cannot approve
        r = self.client.post(f"/api/projects/timesheets/{tid}/approve/")
        self.assertEqual(r.status_code, 400)
        self.client.force_authenticate(self.approver)
        r = self.client.post(f"/api/projects/timesheets/{tid}/approve/")
        self.assertEqual(r.status_code, 200, r.content)
        task.refresh_from_db()
        self.assertEqual(task.hours_logged, Decimal("4.50"))
        self.assertEqual(TimeEntry.objects.get(pk=tid).status, "approved")

        r = self.client.get(f"/api/projects/projects/{proj.id}/summary/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Decimal(r.data["timesheet_hours"]), Decimal("4.5"))
        self.assertEqual(Decimal(r.data["timesheet_amount"]), Decimal("450"))
        self.assertEqual(r.data["open_tasks"], 1)
        self.assertEqual(Decimal(r.data["budget_amount"]), Decimal("1000"))

    def _approve_time(self, project, **fields):
        payload = {
            "project": project.id,
            "date": "2026-10-02",
            "hours": "1",
            "rate": "100",
            "billable": True,
        }
        payload.update(fields)
        self.client.force_authenticate(self.user)
        r = self.client.post("/api/projects/timesheets/", payload, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        tid = r.data["id"]
        r = self.client.post(f"/api/projects/timesheets/{tid}/submit/")
        self.assertEqual(r.status_code, 200, r.content)
        self.client.force_authenticate(self.approver)
        r = self.client.post(f"/api/projects/timesheets/{tid}/approve/")
        self.assertEqual(r.status_code, 200, r.content)
        self.client.force_authenticate(self.user)
        return tid

    def test_bill_approved_timesheets(self):
        cust = Customer.objects.create(
            organization=self.org,
            code="C1",
            name="Cust",
            payment_terms_days=15,
            currency="PKR",
        )
        proj = Project.objects.create(
            organization=self.org,
            code="P9",
            name="Billable",
            customer=cust,
            status=Project.Status.ACTIVE,
        )
        r = self.client.post(
            f"/api/projects/projects/{proj.id}/bill-timesheets/", {}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        billed = self._approve_time(proj, hours="4", rate="100", date="2026-10-02")
        self._approve_time(proj, hours="2", rate="80", billable=False, date="2026-10-03")
        self.client.force_authenticate(self.user)
        r = self.client.post(
            "/api/projects/timesheets/",
            {
                "project": proj.id,
                "date": "2026-10-04",
                "hours": "1",
                "rate": "50",
                "billable": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)

        r = self.client.get(f"/api/projects/projects/{proj.id}/summary/")
        self.assertEqual(Decimal(r.data["unbilled_amount"]), Decimal("400"))
        self.assertEqual(Decimal(r.data["timesheet_amount"]), Decimal("560"))

        r = self.client.post(
            f"/api/projects/projects/{proj.id}/bill-timesheets/", {}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.data["amount"]), Decimal("400.00"))
        self.assertEqual(r.data["entries"], 1)
        inv = CustomerInvoice.objects.get(pk=r.data["invoice_id"])
        self.assertEqual(inv.project_id, proj.id)
        self.assertEqual(inv.customer_id, cust.id)
        self.assertEqual(inv.status, CustomerInvoice.Status.DRAFT)
        self.assertEqual(inv.currency, "PKR")
        self.assertEqual(inv.due_date, inv.invoice_date + timedelta(days=15))
        self.assertEqual(TimeEntry.objects.get(pk=billed).customer_invoice_id, inv.id)

        r = self.client.post(
            f"/api/projects/projects/{proj.id}/bill-timesheets/", {}, format="json"
        )
        self.assertEqual(r.status_code, 400)

        inv.status = CustomerInvoice.Status.REJECTED
        inv.save(update_fields=["status"])
        r = self.client.post(
            f"/api/projects/projects/{proj.id}/bill-timesheets/", {}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotEqual(r.data["invoice_id"], inv.id)
        self.assertEqual(
            TimeEntry.objects.get(pk=billed).customer_invoice_id, r.data["invoice_id"]
        )

        bare = Project.objects.create(organization=self.org, code="P8", name="No customer")
        self._approve_time(bare, hours="3", rate="10", date="2026-10-05")
        r = self.client.post(
            f"/api/projects/projects/{bare.id}/bill-timesheets/", {}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    # ---- MFG -------------------------------------------------------------
    def _mfg_setup(self, with_stock=True):
        wh = Warehouse.objects.create(organization=self.org, code="W1", name="Main")
        fg = Item.objects.create(organization=self.org, sku="FG", name="FG")
        comp = Item.objects.create(organization=self.org, sku="C1", name="Comp")
        r = self.client.post(
            "/api/mfg/boms/",
            {
                "item": fg.id,
                "code": "B1",
                "name": "Bom",
                "lines": [{"component": comp.id, "qty": "2"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.data["lines"]), 1)
        bom = Bom.objects.get(pk=r.data["id"])
        if with_stock:
            StockLevel.objects.create(
                organization=self.org, warehouse=wh, item=comp, qty=Decimal("100")
            )
            comp.qty_on_hand = Decimal("100")
            comp.save()
        wo = WorkOrder.objects.create(
            organization=self.org,
            wo_no="WO1",
            bom=bom,
            item=fg,
            qty_planned=5,
            warehouse=wh,
        )
        return wo, bom, comp

    def test_wo_complete_rules(self):
        wo, bom, comp = self._mfg_setup()
        r = self.client.post(f"/api/mfg/work-orders/{wo.id}/complete/", {}, format="json")
        self.assertEqual(r.status_code, 400)  # still draft
        self.client.post(f"/api/mfg/work-orders/{wo.id}/release/")
        r = self.client.post(f"/api/mfg/work-orders/{wo.id}/complete/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        lvl = StockLevel.objects.get(item=comp)
        self.assertEqual(lvl.qty, Decimal("90"))

    def test_wo_complete_blocks_without_stock_or_lines(self):
        wo, bom, comp = self._mfg_setup(with_stock=False)
        self.client.post(f"/api/mfg/work-orders/{wo.id}/release/")
        r = self.client.post(f"/api/mfg/work-orders/{wo.id}/complete/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Insufficient", str(r.data))
        bom.lines.all().delete()
        r = self.client.post(f"/api/mfg/work-orders/{wo.id}/complete/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no component lines", str(r.data))

    def test_bom_update_replaces_lines(self):
        wo, bom, comp = self._mfg_setup()
        c2 = Item.objects.create(organization=self.org, sku="C2", name="C2")
        r = self.client.patch(
            f"/api/mfg/boms/{bom.id}/",
            {"lines": [{"component": c2.id, "qty": "3"}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            list(BomLine.objects.filter(bom=bom).values_list("component_id", flat=True)),
            [c2.id],
        )
