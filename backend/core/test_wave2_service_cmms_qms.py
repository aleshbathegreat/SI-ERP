from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from finance.models import FixedAsset, MaintenanceWorkOrder, PmSchedule
from ops.models import Customer, Item


class Wave2Tests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme2",
            code="acme2",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("owner2", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_service_case_lifecycle(self):
        cust = Customer.objects.create(organization=self.org, code="C1", name="Cust")
        r = self.client.post(
            "/api/service/cases/",
            {"subject": "Broken", "customer": cust.id, "priority": "high"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.data["case_no"].startswith("CS-"))
        cid = r.data["id"]
        r = self.client.post(
            f"/api/service/cases/{cid}/assign/", {"assigned_to": self.user.id}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "in_progress")
        r = self.client.post(f"/api/service/cases/{cid}/resolve/", {}, format="json")
        self.assertEqual(r.data["status"], "resolved")
        self.assertIsNotNone(r.data["resolved_at"])
        r = self.client.post(f"/api/service/cases/{cid}/close/", {}, format="json")
        self.assertEqual(r.data["status"], "closed")
        r = self.client.post(f"/api/service/cases/{cid}/reopen/", {}, format="json")
        self.assertEqual(r.data["status"], "in_progress")
        r = self.client.post(
            "/api/service/notes/", {"case": cid, "body": "called"}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        r = self.client.get(f"/api/service/notes/?case={cid}")
        self.assertEqual(len(r.data["results"] if "results" in r.data else r.data), 1)

    def test_cmms_generate_due_and_complete(self):
        asset = FixedAsset.objects.create(
            organization=self.org, asset_code="FA-1", name="Pump"
        )
        r = self.client.post(
            "/api/finance/pm-schedules/",
            {
                "asset": asset.id,
                "title": "Lubricate",
                "frequency_days": 10,
                "next_due": str(date.today() - timedelta(days=1)),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        r = self.client.post("/api/finance/pm-schedules/generate-due/", {}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["created"], 1)
        r2 = self.client.post("/api/finance/pm-schedules/generate-due/", {}, format="json")
        self.assertEqual(r2.data["created"], 0)
        mwo = MaintenanceWorkOrder.objects.get(organization=self.org)
        self.assertTrue(mwo.mwo_no.startswith("MWO-"))
        r = self.client.post(
            f"/api/finance/maintenance-orders/{mwo.id}/complete/",
            {"cost": "50"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "done")
        sch = PmSchedule.objects.get(organization=self.org)
        self.assertEqual(sch.last_done, date.today())
        self.assertEqual(sch.next_due, date.today() + timedelta(days=10))
        self.assertEqual(MaintenanceWorkOrder.objects.get().cost, Decimal("50"))

    def test_qms_flow(self):
        item = Item.objects.create(organization=self.org, sku="S1", name="Bolt")
        r = self.client.post(
            "/api/qms/inspections/",
            {
                "item": item.id,
                "result": "fail",
                "qty_inspected": "10",
                "qty_rejected": "3",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        bad = self.client.post(
            "/api/qms/inspections/",
            {"item": item.id, "result": "fail", "qty_inspected": "1", "qty_rejected": "3"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        r = self.client.post(
            f"/api/qms/inspections/{r.data['id']}/create-ncr/", {}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        ncr_id = r.data["ncr"]
        r = self.client.post(
            "/api/qms/capas/",
            {"ncr": ncr_id, "action": "Fix supplier"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        capa_id = r.data["id"]
        r = self.client.post(
            f"/api/qms/ncrs/{ncr_id}/close/", {"disposition": "scrap"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.post(f"/api/qms/capas/{capa_id}/complete/", {}, format="json")
        self.assertEqual(r.data["status"], "done")
        r = self.client.post(
            f"/api/qms/ncrs/{ncr_id}/close/", {"disposition": "scrap"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "closed")

    def test_service_parts_invoice_and_maintenance_issue(self):
        from finance.models import CustomerInvoice
        from ops.models import Item, StockLevel, Warehouse

        wh = Warehouse.objects.create(organization=self.org, code="W1", name="Main")
        item = Item.objects.create(
            organization=self.org,
            sku="SP1",
            name="Seal",
            default_warehouse=wh,
            unit_cost=Decimal("10"),
            sales_price=Decimal("25"),
        )
        StockLevel.objects.create(
            organization=self.org, warehouse=wh, item=item, qty=Decimal("5")
        )
        cust = Customer.objects.create(organization=self.org, code="C2", name="Cust")
        case = self.client.post(
            "/api/service/cases/",
            {"subject": "Leak", "customer": cust.id},
            format="json",
        )
        self.assertEqual(case.status_code, 201, case.content)
        cid = case.data["id"]
        issued = self.client.post(
            f"/api/service/cases/{cid}/issue-part/",
            {"item": item.id, "qty": "2"},
            format="json",
        )
        self.assertEqual(issued.status_code, 200, issued.content)
        self.assertEqual(issued.data["status"], "in_progress")
        self.assertEqual(len(issued.data["parts"]), 1)
        self.assertEqual(
            StockLevel.objects.get(item=item, warehouse=wh).qty, Decimal("3")
        )
        over = self.client.post(
            f"/api/service/cases/{cid}/issue-part/",
            {"item": item.id, "qty": "9"},
            format="json",
        )
        self.assertEqual(over.status_code, 400)
        held = StockLevel.objects.get(item=item, warehouse=wh)
        held.qty_qc_hold = held.qty
        held.save(update_fields=["qty_qc_hold"])
        blocked = self.client.post(
            f"/api/service/cases/{cid}/issue-part/",
            {"item": item.id, "qty": "1"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)
        held.qty_qc_hold = Decimal("0")
        held.save(update_fields=["qty_qc_hold"])
        early = self.client.post(
            f"/api/service/cases/{cid}/create-invoice/", {}, format="json"
        )
        self.assertEqual(early.status_code, 400)
        self.client.post(f"/api/service/cases/{cid}/resolve/", {}, format="json")
        billed = self.client.post(
            f"/api/service/cases/{cid}/create-invoice/",
            {"labor_amount": "15"},
            format="json",
        )
        self.assertEqual(billed.status_code, 201, billed.content)
        inv = CustomerInvoice.objects.get(pk=billed.data["invoice_id"])
        self.assertEqual(inv.amount, Decimal("65.00"))
        self.assertEqual(inv.status, "draft")
        again = self.client.post(
            f"/api/service/cases/{cid}/create-invoice/", {}, format="json"
        )
        self.assertEqual(again.status_code, 400)

        asset = FixedAsset.objects.create(
            organization=self.org, asset_code="FA-2", name="Motor"
        )
        mwo = self.client.post(
            "/api/finance/maintenance-orders/",
            {"asset": asset.id, "title": "Replace seal"},
            format="json",
        )
        self.assertEqual(mwo.status_code, 201, mwo.content)
        issued_m = self.client.post(
            f"/api/finance/maintenance-orders/{mwo.data['id']}/issue-part/",
            {"item": item.id, "qty": "1", "warehouse": wh.id},
            format="json",
        )
        self.assertEqual(issued_m.status_code, 200, issued_m.content)
        self.assertEqual(issued_m.data["status"], "in_progress")
        self.assertEqual(Decimal(issued_m.data["cost"]), Decimal("10.00"))
        self.assertEqual(len(issued_m.data["parts"]), 1)
        self.assertEqual(
            StockLevel.objects.get(item=item, warehouse=wh).qty, Decimal("2")
        )
