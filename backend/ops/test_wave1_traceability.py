from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from finance.models import (
    Account,
    BankAccount,
    ChequeRegister,
    CustomerInvoice,
    EInvoiceSubmission,
    FxRate,
    IntercompanyPartner,
    IntercompanyTxn,
    TaxReturn,
    Vendor,
    VendorInvoice,
)
from ops.models import (
    Customer,
    CustomerContract,
    Item,
    LotBatch,
    PurchaseOrder,
    PurchaseOrderLine,
    SerialNumber,
    StockMovement,
    Warehouse,
)


class Wave1TraceabilityFinanceTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme2",
            ntn="1234567-8",
            strn="3277876123456",
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
        self.wh = Warehouse.objects.create(organization=self.org, code="W1", name="Main")
        self.vendor = Vendor.objects.create(organization=self.org, name="V1")
        self.customer = Customer.objects.create(
            organization=self.org, code="C1", name="Cust", ntn="999"
        )

    def _item(self, **kw):
        return Item.objects.create(
            organization=self.org,
            sku=kw.pop("sku", "SKU1"),
            name="Widget",
            default_warehouse=self.wh,
            **kw,
        )

    def _po(self, item, qty="10"):
        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_no="PO-1",
            vendor=self.vendor,
            order_date=date.today(),
            status=PurchaseOrder.Status.APPROVED,
            warehouse=self.wh,
        )
        line = PurchaseOrderLine.objects.create(
            purchase_order=po, item=item, qty=Decimal(qty), unit_price=Decimal("5")
        )
        return po, line

    # ---- traceability ----------------------------------------------------
    def test_grn_requires_batch_then_updates_lot(self):
        item = self._item(track_batch=True)
        po, line = self._po(item)
        r = self.client.post(f"/api/procurement/orders/{po.id}/receive/", {}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(StockMovement.objects.count(), 0)
        r = self.client.post(
            f"/api/procurement/orders/{po.id}/receive/",
            {"lines": [{"id": line.id, "qty": 10, "batch_no": "B-001"}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        lot = LotBatch.objects.get(item=item, batch_no="B-001")
        self.assertEqual(lot.qty, Decimal("10"))
        mov = StockMovement.objects.get(item=item)
        self.assertEqual(mov.lot_id, lot.id)
        self.assertEqual(mov.batch_no, "B-001")

    def test_grn_serial_and_manual_issue(self):
        item = self._item(sku="SER1", track_serial=True)
        po, line = self._po(item, qty="2")
        r = self.client.post(
            f"/api/procurement/orders/{po.id}/receive/",
            {"lines": [{"id": line.id, "qty": 2, "serial_nos": ["S1"]}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post(
            f"/api/procurement/orders/{po.id}/receive/",
            {"lines": [{"id": line.id, "qty": 2, "serial_nos": ["S1", "S2"]}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(SerialNumber.objects.filter(item=item, status="available").count(), 2)
        # manual issue of S1
        r = self.client.post(
            "/api/inventory/movements/",
            {
                "item": item.id,
                "warehouse": self.wh.id,
                "movement_date": str(date.today()),
                "qty": -1,
                "reason": "issue",
                "serial_no": "S1",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(SerialNumber.objects.get(item=item, serial_no="S1").status, "issued")
        # issuing S1 again must fail
        r = self.client.post(
            "/api/inventory/movements/",
            {
                "item": item.id,
                "warehouse": self.wh.id,
                "movement_date": str(date.today()),
                "qty": -1,
                "reason": "issue",
                "serial_no": "S1",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)

    def test_item_label(self):
        item = self._item(sku="LBL1", barcode="")
        r = self.client.get(f"/api/inventory/items/{item.id}/label/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["barcode"], "LBL1")
        self.assertEqual(r.data["sku"], "LBL1")

    # ---- FBR -------------------------------------------------------------
    def test_einvoice_auto_draft_and_sandbox_submit(self):
        inv = CustomerInvoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-1",
            invoice_date=date.today(),
            amount=Decimal("1000"),
            tax_amount=Decimal("180"),
            status=CustomerInvoice.Status.DRAFT,
        )
        self.assertEqual(EInvoiceSubmission.objects.count(), 0)
        inv.status = CustomerInvoice.Status.APPROVED
        inv.save()
        sub = EInvoiceSubmission.objects.get(ar_invoice=inv)
        self.assertEqual(sub.fbr_status, "draft")
        self.assertEqual(sub.payload_json["seller"]["ntn"], "1234567-8")
        with override_settings(FBR_API_URL=""):
            r = self.client.post(f"/api/finance/e-invoices/{sub.id}/submit/")
        self.assertEqual(r.status_code, 200, r.content)
        sub.refresh_from_db()
        self.assertEqual(sub.fbr_status, "submitted")
        self.assertTrue(sub.provider_ref.startswith("sandbox:"))
        self.assertEqual(sub.mode, "sandbox")
        self.assertFalse(sub.response_json["transmitted"])

    # ---- tax returns -----------------------------------------------------
    def test_tax_return_generate(self):
        today = date.today()
        CustomerInvoice.objects.create(
            organization=self.org,
            customer=self.customer,
            invoice_no="INV-T",
            invoice_date=today,
            amount=Decimal("1000"),
            tax_amount=Decimal("180"),
            status=CustomerInvoice.Status.APPROVED,
        )
        r = self.client.post(
            "/api/finance/tax-returns/generate/",
            {
                "return_type": "sales_tax",
                "period_start": str(today.replace(day=1)),
                "period_end": str(today),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["totals"]["tax_total"], "180.00")
        self.assertEqual(len(r.data["lines"]), 1)
        VendorInvoice.objects.create(
            organization=self.org,
            vendor=self.vendor,
            invoice_no="V-1",
            invoice_date=today,
            amount=Decimal("500"),
            wht_amount=Decimal("50"),
            status=VendorInvoice.Status.APPROVED,
        )
        r = self.client.post(
            "/api/finance/tax-returns/generate/",
            {
                "return_type": "wht",
                "period_start": str(today.replace(day=1)),
                "period_end": str(today),
            },
            format="json",
        )
        self.assertEqual(r.data["totals"]["tax_total"], "50.00")
        tr = TaxReturn.objects.get(pk=r.data["id"])
        r = self.client.post(f"/api/finance/tax-returns/{tr.id}/file/", {}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.post(f"/api/finance/tax-returns/{tr.id}/regenerate/")
        self.assertEqual(r.status_code, 400)

    # ---- reports ---------------------------------------------------------
    def test_reports(self):
        r = self.client.get("/api/finance/reports/")
        self.assertEqual(r.status_code, 200, r.content)
        for k in ("ar_ageing", "stock_valuation", "wht_register", "payroll_register"):
            self.assertIn(k, r.data)
        r = self.client.get("/api/finance/reports/run/?report=ar_ageing&export=xlsx")
        self.assertEqual(r.status_code, 200, getattr(r, "content", b"")[:200])
        r = self.client.post(
            "/api/finance/saved-reports/",
            {"name": "My AR", "report_key": "ar_ageing", "params": {}},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)

    # ---- finance stubs ---------------------------------------------------
    def test_cheque_clear_and_bounce(self):
        bank = BankAccount.objects.create(
            organization=self.org,
            name="HBL",
            bank_name="HBL",
            account_no="1",
            current_balance=Decimal("1000"),
        )
        chq = ChequeRegister.objects.create(
            organization=self.org,
            bank_account=bank,
            cheque_no="100",
            payee="X",
            amount=Decimal("300"),
            cheque_date=date.today(),
        )
        r = self.client.post(f"/api/finance/cheques/{chq.id}/clear/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        bank.refresh_from_db()
        self.assertEqual(bank.current_balance, Decimal("700.00"))
        self.assertIsNotNone(r.data["gl_journal"])
        r = self.client.post(
            f"/api/finance/cheques/{chq.id}/bounce/", {"reason": "NSF"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        bank.refresh_from_db()
        self.assertEqual(bank.current_balance, Decimal("1000.00"))
        chq.refresh_from_db()
        self.assertEqual(chq.status, "bounced")

    def test_intercompany_post(self):
        ar = Account.objects.create(
            organization=self.org, code="1300", name="IC AR", account_type="asset"
        )
        p = IntercompanyPartner.objects.create(
            organization=self.org, code="P1", name="Sister", receivable_account=ar
        )
        txn = IntercompanyTxn.objects.create(
            organization=self.org,
            partner=p,
            date=date.today(),
            amount=Decimal("250"),
            direction="receivable",
        )
        r = self.client.post(f"/api/finance/intercompany-txns/{txn.id}/post/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        txn.refresh_from_db()
        self.assertEqual(txn.status, "posted")
        self.assertEqual(txn.gl_journal.lines.count(), 2)

    def test_fx_rate_helper(self):
        from finance.fx import get_rate

        FxRate.objects.create(
            organization=self.org,
            currency_from="USD",
            currency_to="PKR",
            rate=Decimal("280"),
            rate_date=date.today() - timedelta(days=1),
        )
        self.assertEqual(get_rate(self.org, "USD", "PKR", date.today()), Decimal("280"))
        self.assertEqual(get_rate(self.org, "PKR", "PKR", date.today()), Decimal("1"))
        self.assertIsNotNone(get_rate(self.org, "PKR", "USD", date.today()))
        self.assertIsNone(get_rate(self.org, "EUR", "PKR", date.today()))

    def test_bill_due_contracts(self):
        from core.jobs import bill_due_customer_contracts

        CustomerContract.objects.create(
            organization=self.org,
            customer=self.customer,
            name="Retainer",
            start_date=date.today() - timedelta(days=40),
            amount=Decimal("100"),
            next_bill_date=date.today() - timedelta(days=35),
        )
        stats = bill_due_customer_contracts()
        self.assertGreaterEqual(stats["invoices"], 2, stats)
        self.assertFalse(stats["errors"], stats)
        self.assertEqual(
            CustomerInvoice.objects.filter(organization=self.org).count(), stats["invoices"]
        )
