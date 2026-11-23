from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from ops.models import (
    Customer,
    Item,
    SalesOrder,
    SalesOrderLine,
    StockLevel,
    StockLevelBin,
    Warehouse,
)


class Wave2WmsDmsTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme W2",
            code="acmew2",
            ntn="1234567-8",
            strn="3277876123456",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("ownerw2", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.wh = Warehouse.objects.create(organization=self.org, code="W1", name="Main")
        self.customer = Customer.objects.create(
            organization=self.org, code="C1", name="Cust"
        )
        self.item = Item.objects.create(
            organization=self.org, sku="S1", name="Widget", default_warehouse=self.wh
        )
        StockLevel.objects.create(
            organization=self.org, warehouse=self.wh, item=self.item, qty=Decimal("20")
        )

    def test_bins_unique_and_pick_confirm(self):
        r = self.client.post(
            "/api/inventory/bins/",
            {"warehouse": self.wh.id, "code": "A-01", "name": "Aisle A", "aisle": "A"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        bin_id = r.json()["id"]
        dup = self.client.post(
            "/api/inventory/bins/",
            {"warehouse": self.wh.id, "code": "A-01"},
            format="json",
        )
        self.assertEqual(dup.status_code, 400)

        r = self.client.post(
            f"/api/inventory/bins/{bin_id}/put-away/",
            {"item": self.item.id, "qty": "12"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        over = self.client.post(
            f"/api/inventory/bins/{bin_id}/put-away/",
            {"item": self.item.id, "qty": "9"},
            format="json",
        )
        self.assertEqual(over.status_code, 400)

        so = SalesOrder.objects.create(
            organization=self.org,
            order_no="SO-W2",
            customer=self.customer,
            warehouse=self.wh,
            order_date=date.today(),
            status=SalesOrder.Status.CONFIRMED,
        )
        SalesOrderLine.objects.create(
            sales_order=so, item=self.item, qty=Decimal("5"), unit_price=Decimal("10")
        )
        r = self.client.post(
            "/api/inventory/pick-lists/create-from-order/",
            {"sales_order": so.id},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        pl = r.json()
        self.assertEqual(pl["status"], "draft")
        self.assertEqual(pl["lines"][0]["bin"], bin_id)

        r = self.client.post(f"/api/inventory/pick-lists/{pl['id']}/confirm/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "done")
        self.assertEqual(Decimal(r.json()["lines"][0]["picked_qty"]), Decimal("5"))
        self.assertTrue(r.json()["delivery_note"])
        self.assertTrue(r.json()["delivery_note_no"])
        self.assertEqual(
            StockLevelBin.objects.get(bin_id=bin_id, item=self.item).qty, Decimal("7")
        )
        # Same confirm posts the delivery, so warehouse on-hand drops with the bin.
        self.assertEqual(
            StockLevel.objects.get(warehouse=self.wh, item=self.item).qty, Decimal("15")
        )
        so.refresh_from_db()
        self.assertEqual(so.status, SalesOrder.Status.DELIVERED)
        again = self.client.post(
            f"/api/inventory/pick-lists/{pl['id']}/confirm/", {}, format="json"
        )
        self.assertEqual(again.status_code, 400)

    def test_posted_delivery_pick_does_not_move_stock_again(self):
        r = self.client.post(
            "/api/inventory/bins/",
            {"warehouse": self.wh.id, "code": "A-01"},
            format="json",
        )
        bin_id = r.json()["id"]
        self.client.post(
            f"/api/inventory/bins/{bin_id}/put-away/",
            {"item": self.item.id, "qty": "12"},
            format="json",
        )
        so = SalesOrder.objects.create(
            organization=self.org,
            order_no="SO-DN",
            customer=self.customer,
            warehouse=self.wh,
            order_date=date.today(),
            status=SalesOrder.Status.CONFIRMED,
        )
        SalesOrderLine.objects.create(
            sales_order=so, item=self.item, qty=Decimal("5"), unit_price=Decimal("10")
        )
        delivered = self.client.post(
            f"/api/sales/orders/{so.id}/deliver/", {}, format="json"
        )
        self.assertEqual(delivered.status_code, 200, delivered.content)
        dn_id = delivered.json()["dn_id"]
        self.assertEqual(
            StockLevel.objects.get(warehouse=self.wh, item=self.item).qty, Decimal("15")
        )
        self.assertEqual(
            StockLevelBin.objects.get(bin_id=bin_id, item=self.item).qty, Decimal("7")
        )
        created = self.client.post(
            "/api/inventory/pick-lists/create-from-order/",
            {"delivery_note": dn_id},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        confirmed = self.client.post(
            f"/api/inventory/pick-lists/{created.json()['id']}/confirm/",
            {},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertEqual(confirmed.json()["delivery_note"], dn_id)
        self.assertEqual(
            StockLevel.objects.get(warehouse=self.wh, item=self.item).qty, Decimal("15")
        )
        self.assertEqual(
            StockLevelBin.objects.get(bin_id=bin_id, item=self.item).qty, Decimal("7")
        )

    def test_grn_putaway_suggests_receiving_bin(self):
        from finance.models import Vendor
        from ops.models import PurchaseOrder, PurchaseOrderLine

        StockLevel.objects.filter(item=self.item, warehouse=self.wh).update(qty=Decimal("0"))
        vendor = Vendor.objects.create(organization=self.org, name="Vendor")
        recv = self.client.post(
            "/api/inventory/bins/",
            {"warehouse": self.wh.id, "code": "RECV", "name": "Dock"},
            format="json",
        ).json()["id"]
        self.client.post(
            "/api/inventory/bins/",
            {"warehouse": self.wh.id, "code": "BULK"},
            format="json",
        )
        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_no="PO-WMS",
            vendor=vendor,
            warehouse=self.wh,
            order_date=date.today(),
            status=PurchaseOrder.Status.APPROVED,
        )
        PurchaseOrderLine.objects.create(
            purchase_order=po, item=self.item, qty=Decimal("6"), unit_price=Decimal("4")
        )
        received = self.client.post(
            f"/api/procurement/orders/{po.id}/receive/",
            {"warehouse": self.wh.id},
            format="json",
        )
        self.assertEqual(received.status_code, 200, received.content)
        self.assertEqual(received.json()["putaway_pending"], 1)
        grn_id = received.json()["grn_id"]
        plan = self.client.get(f"/api/procurement/receipts/{grn_id}/put-away/")
        self.assertEqual(plan.status_code, 200, plan.content)
        row = plan.json()["lines"][0]
        self.assertEqual(row["suggested_bin"], recv)
        self.assertEqual(Decimal(row["qty"]), Decimal("6"))
        applied = self.client.patch(
            f"/api/procurement/receipts/{grn_id}/put-away/",
            {"lines": [{"line_id": row["line_id"], "bin": recv, "qty": "6"}]},
            format="json",
        )
        self.assertEqual(applied.status_code, 200, applied.content)
        self.assertEqual(Decimal(applied.json()["lines"][0]["qty"]), Decimal("0"))
        self.assertEqual(
            StockLevelBin.objects.get(bin_id=recv, item=self.item).qty, Decimal("6")
        )
        self.assertEqual(
            StockLevel.objects.get(warehouse=self.wh, item=self.item).qty, Decimal("6")
        )
        again = self.client.patch(
            f"/api/procurement/receipts/{grn_id}/put-away/",
            {"lines": [{"line_id": row["line_id"], "bin": recv, "qty": "1"}]},
            format="json",
        )
        self.assertEqual(again.status_code, 400)

    def _approved_po(self, qty, po_no="PO-QC"):
        from finance.models import Vendor
        from ops.models import PurchaseOrder, PurchaseOrderLine

        StockLevel.objects.filter(item=self.item, warehouse=self.wh).update(qty=Decimal("0"))
        vendor = Vendor.objects.create(organization=self.org, name=f"V-{po_no}")
        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_no=po_no,
            vendor=vendor,
            warehouse=self.wh,
            order_date=date.today(),
            status=PurchaseOrder.Status.APPROVED,
        )
        PurchaseOrderLine.objects.create(
            purchase_order=po, item=self.item, qty=Decimal(qty), unit_price=Decimal("4")
        )
        received = self.client.post(
            f"/api/procurement/orders/{po.id}/receive/",
            {"warehouse": self.wh.id},
            format="json",
        )
        self.assertEqual(received.status_code, 200, received.content)
        return received.json()["grn_id"]

    def _confirmed_so(self, qty, order_no):
        so = SalesOrder.objects.create(
            organization=self.org,
            order_no=order_no,
            customer=self.customer,
            warehouse=self.wh,
            order_date=date.today(),
            status=SalesOrder.Status.CONFIRMED,
        )
        SalesOrderLine.objects.create(
            sales_order=so, item=self.item, qty=Decimal(qty), unit_price=Decimal("10")
        )
        return so

    def test_qc_hold_blocks_delivery_until_pass(self):
        grn_id = self._approved_po("6", "PO-QC1")
        level = StockLevel.objects.get(warehouse=self.wh, item=self.item)
        self.assertEqual(level.qty, Decimal("6"))
        self.assertEqual(level.qty_qc_hold, Decimal("6"))
        so = self._confirmed_so("4", "SO-QC1")
        blocked = self.client.post(f"/api/sales/orders/{so.id}/deliver/", {}, format="json")
        self.assertEqual(blocked.status_code, 400, blocked.content)
        released = self.client.patch(
            f"/api/procurement/receipts/{grn_id}/",
            {"qc_status": "passed"},
            format="json",
        )
        self.assertEqual(released.status_code, 200, released.content)
        self.assertEqual(released.json()["qc_status"], "passed")
        self.assertEqual(Decimal(released.json()["hold_qty"]), Decimal("0"))
        delivered = self.client.post(f"/api/sales/orders/{so.id}/deliver/", {}, format="json")
        self.assertEqual(delivered.status_code, 200, delivered.content)
        level.refresh_from_db()
        self.assertEqual(level.qty, Decimal("2"))
        self.assertEqual(level.qty_qc_hold, Decimal("0"))

    def test_failed_inspection_quarantines_and_scrap_removes_stock(self):
        grn_id = self._approved_po("6", "PO-QC2")
        failed = self.client.post(
            "/api/qms/inspections/",
            {
                "item": self.item.id,
                "grn": grn_id,
                "result": "fail",
                "qty_inspected": "6",
                "qty_rejected": "6",
            },
            format="json",
        )
        self.assertEqual(failed.status_code, 201, failed.content)
        so = self._confirmed_so("1", "SO-QC2")
        blocked = self.client.post(f"/api/sales/orders/{so.id}/deliver/", {}, format="json")
        self.assertEqual(blocked.status_code, 400, blocked.content)
        ncr = self.client.post(
            f"/api/qms/inspections/{failed.json()['id']}/create-ncr/", {}, format="json"
        )
        self.assertEqual(ncr.status_code, 201, ncr.content)
        closed = self.client.post(
            f"/api/qms/ncrs/{ncr.json()['ncr']}/close/",
            {"disposition": "scrap"},
            format="json",
        )
        self.assertEqual(closed.status_code, 200, closed.content)
        level = StockLevel.objects.get(warehouse=self.wh, item=self.item)
        self.assertEqual(level.qty, Decimal("0"))
        self.assertEqual(level.qty_qc_hold, Decimal("0"))

    def test_conditional_inspection_releases_accepted_qty_only(self):
        grn_id = self._approved_po("10", "PO-QC3")
        created = self.client.post(
            "/api/qms/inspections/",
            {
                "item": self.item.id,
                "grn": grn_id,
                "result": "conditional",
                "qty_inspected": "10",
                "qty_rejected": "4",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        level = StockLevel.objects.get(warehouse=self.wh, item=self.item)
        self.assertEqual(level.qty, Decimal("10"))
        self.assertEqual(level.qty_qc_hold, Decimal("4"))
        so = self._confirmed_so("6", "SO-QC3")
        delivered = self.client.post(f"/api/sales/orders/{so.id}/deliver/", {}, format="json")
        self.assertEqual(delivered.status_code, 200, delivered.content)
        extra = self._confirmed_so("1", "SO-QC3B")
        blocked = self.client.post(f"/api/sales/orders/{extra.id}/deliver/", {}, format="json")
        self.assertEqual(blocked.status_code, 400, blocked.content)
        level.refresh_from_db()
        self.assertEqual(level.qty, Decimal("4"))
        self.assertEqual(level.qty_qc_hold, Decimal("4"))

    def test_dms_folder_document_lifecycle(self):
        import tempfile

        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            r = self.client.post(
                "/api/dms/folders/", {"name": "Policies"}, format="json"
            )
            self.assertEqual(r.status_code, 201, r.content)
            fid = r.json()["id"]
            r = self.client.post(
                "/api/dms/documents/",
                {
                    "title": "Handbook",
                    "folder": fid,
                    "category": "policy",
                    "file": SimpleUploadedFile("a.txt", b"v1"),
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 201, r.content)
            doc = r.json()
            self.assertEqual(doc["version"], 1)
            self.assertEqual(doc["status"], "draft")
            r = self.client.post(f"/api/dms/documents/{doc['id']}/publish/")
            self.assertEqual(r.json()["status"], "published")
            r = self.client.post(
                f"/api/dms/documents/{doc['id']}/new-version/",
                {"file": SimpleUploadedFile("b.txt", b"v2")},
                format="multipart",
            )
            self.assertEqual(r.status_code, 200, r.content)
            self.assertEqual(r.json()["version"], 2)
            self.assertEqual(len(r.json()["versions"]), 2)
            r = self.client.post(f"/api/dms/documents/{doc['id']}/archive/")
            self.assertEqual(r.json()["status"], "archived")
