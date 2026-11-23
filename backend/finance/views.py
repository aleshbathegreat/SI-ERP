from datetime import date as date_cls
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin
from core.workflow import WorkflowActionsMixin
from finance.bank_csv import parse_bank_statement_csv, read_upload_text
from finance.models import (
    Account,
    AccountType,
    AssetDepreciationLine,
    AssetDepreciationRun,
    AssetRepair,
    BankAccount,
    BankReconciliation,
    BankStatementLine,
    Budget,
    ChequeRegister,
    CostCenter,
    Currency,
    CustomerInvoice,
    EInvoiceSubmission,
    FbrInvoiceSubmission,
    FixedAsset,
    FxRate,
    IntercompanyPartner,
    IntercompanyTxn,
    Investment,
    JournalEntry,
    MaintenanceWorkOrder,
    PmSchedule,
    TaxCode,
    Vendor,
    VendorInvoice,
    ensure_default_account_types,
    ensure_default_currencies,
)
from finance.serializers import (
    AccountSerializer,
    AccountTypeSerializer,
    AssetDepreciationLineSerializer,
    AssetDepreciationRunSerializer,
    AssetRepairSerializer,
    BankAccountSerializer,
    BankReconciliationSerializer,
    BudgetSerializer,
    ChequeRegisterSerializer,
    CostCenterSerializer,
    CurrencySerializer,
    CustomerInvoiceSerializer,
    EInvoiceSubmissionSerializer,
    FbrInvoiceSubmissionSerializer,
    FixedAssetSerializer,
    FxRateSerializer,
    IntercompanyPartnerSerializer,
    IntercompanyTxnSerializer,
    InvestmentSerializer,
    JournalEntrySerializer,
    MaintenanceWorkOrderSerializer,
    PmScheduleSerializer,
    TaxCodeSerializer,
    VendorInvoiceSerializer,
    VendorSerializer,
)


class AccountTypeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer
    search_fields = ("code", "name")
    filterset_fields = ("statement_class", "is_active", "is_system")
    rbac_module = "finance.accounts"

    def get_queryset(self):
        from core.access import user_organization

        qs = super().get_queryset()
        org = user_organization(self.request.user)
        if org:
            ensure_default_account_types(org)
        return qs

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System account types cannot be deleted.")
        if Account.objects.filter(
            organization=instance.organization, account_type=instance.code
        ).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Account type is in use by GL accounts.")
        return super().perform_destroy(instance)


class AccountViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Account.objects.select_related("organization", "parent")
    serializer_class = AccountSerializer
    search_fields = ("code", "name")
    filterset_fields = ("account_type", "is_active")
    rbac_module = "finance.accounts"

    def get_queryset(self):
        from core.access import user_organization

        org = user_organization(self.request.user)
        if org:
            ensure_default_account_types(org)
        return super().get_queryset()


class CostCenterViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_active",)
    rbac_module = "finance.cost_centers"


class VendorViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    search_fields = ("name", "ntn", "email")
    filterset_fields = ("is_active",)
    rbac_module = "finance.vendors"


class JournalEntryViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = JournalEntry.objects.prefetch_related("lines").all()
    serializer_class = JournalEntrySerializer
    filterset_fields = ("status",)
    search_fields = ("reference", "narration")
    rbac_module = "finance.journals"
    workflow_allow_post = True

    def perform_destroy(self, instance):
        if instance.status == "posted":
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Posted journals cannot be deleted.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        """Create a posted reversing voucher (swap debit/credit)."""
        from datetime import date as date_cls

        from finance.gl_automation import reverse_journal

        je = self.get_object()
        if je.status != "posted":
            return Response({"detail": "Only posted journals can be reversed"}, status=400)
        raw = request.data.get("entry_date")
        entry_date = None
        if raw:
            try:
                entry_date = date_cls.fromisoformat(str(raw)[:10])
            except ValueError:
                return Response({"detail": "Invalid entry_date"}, status=400)
        try:
            rev = reverse_journal(journal=je, user=request.user, entry_date=entry_date)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
        return Response(
            {
                "original_id": je.id,
                "reversal": self.get_serializer(rev).data,
            }
        )


class BudgetViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = Budget.objects.select_related("cost_center")
    serializer_class = BudgetSerializer
    search_fields = ("name",)
    filterset_fields = ("status", "fiscal_year")
    rbac_module = "finance.budgets"
    workflow_approve_to = "approved"
    workflow_reject_to = "draft"


class VendorInvoiceViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = VendorInvoice.objects.select_related("vendor", "purchase_order")
    serializer_class = VendorInvoiceSerializer
    search_fields = ("invoice_no", "description", "purchase_order__po_no")
    filterset_fields = ("status", "vendor", "purchase_order")
    rbac_module = "finance.invoices"

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Post AP accrual JE before status becomes approved."""
        from django.db import transaction
        from finance.gl_automation import post_ap_invoice_accrual

        obj = self.get_object()
        if self._period_locked(obj):
            return Response({"detail": "Accounting period is locked."}, status=400)
        blocked = self._sod_block_self_approve(obj)
        if blocked:
            return blocked
        current = getattr(obj, self.workflow_status_field)
        allowed = {self.workflow_submit_to, "pending", "processing", "submitted"}
        if current not in allowed:
            return Response(
                {"detail": f"Cannot approve from status '{current}'"}, status=400
            )
        try:
            with transaction.atomic():
                je = post_ap_invoice_accrual(invoice=obj, user=request.user)
                extra = {}
                if hasattr(obj, "approved_by_id"):
                    extra["approved_by"] = request.user
                resp = self._set_status(
                    obj, self.workflow_approve_to, "approve", extra
                )
                data = resp.data
                data["gl_journal_id"] = je.id
                data["gl_journal_ref"] = je.reference
                return Response(data)
        except Exception as e:
            return Response(
                {"detail": f"Approve blocked — GL accrual failed: {e}"},
                status=400,
            )

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        from django.db import transaction
        from finance.gl_automation import post_ap_payment

        inv = self.get_object()
        if inv.status != "approved":
            return Response(
                {"detail": "Only approved invoices can be paid"}, status=400
            )
        bank_id = request.data.get("bank_account")
        if not bank_id:
            return Response(
                {"detail": "bank_account is required to post payment to GL"},
                status=400,
            )
        bank = BankAccount.objects.filter(
            organization=inv.organization, id=bank_id, is_active=True
        ).first()
        if not bank:
            return Response({"detail": "Bank account not found"}, status=400)
        ref = (request.data.get("payment_ref") or "").strip()
        net = Decimal(str(inv.amount or 0)) - Decimal(str(inv.wht_amount or 0))
        raw_amt = request.data.get("paid_amount")
        amount = Decimal(str(raw_amt if raw_amt not in (None, "") else net))
        try:
            with transaction.atomic():
                inv.payment_ref = ref
                inv.paid_amount = amount
                inv.paid_at = timezone.now()
                inv.save(
                    update_fields=[
                        "payment_ref",
                        "paid_amount",
                        "paid_at",
                        "updated_at",
                    ]
                )
                je = post_ap_payment(invoice=inv, bank=bank, user=request.user)
                inv.status = VendorInvoice.Status.PAID
                inv.save(update_fields=["status", "updated_at"])
        except Exception as e:
            return Response(
                {"detail": f"Payment not recorded — GL post failed: {e}"},
                status=400,
            )
        data = self.get_serializer(inv).data
        data["gl_journal_id"] = je.id
        data["gl_journal_ref"] = je.reference
        return Response(data)


class CustomerInvoiceViewSet(
    WorkflowActionsMixin, BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = CustomerInvoice.objects.select_related("customer", "sales_order")
    serializer_class = CustomerInvoiceSerializer
    search_fields = ("invoice_no", "description", "customer__name", "customer__code")
    filterset_fields = ("status", "customer", "sales_order")
    rbac_module = "sales.invoices"
    workflow_reject_to = "draft"

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Post AR accrual JE before status becomes approved."""
        from django.db import transaction
        from finance.gl_automation import post_ar_invoice_accrual

        obj = self.get_object()
        if self._period_locked(obj):
            return Response({"detail": "Accounting period is locked."}, status=400)
        blocked = self._sod_block_self_approve(obj)
        if blocked:
            return blocked
        current = getattr(obj, self.workflow_status_field)
        allowed = {self.workflow_submit_to, "pending", "processing", "submitted"}
        if current not in allowed:
            return Response(
                {"detail": f"Cannot approve from status '{current}'"}, status=400
            )
        try:
            with transaction.atomic():
                je = post_ar_invoice_accrual(invoice=obj, user=request.user)
                extra = {}
                if hasattr(obj, "approved_by_id"):
                    extra["approved_by"] = request.user
                resp = self._set_status(
                    obj, self.workflow_approve_to, "approve", extra
                )
                data = resp.data
                data["gl_journal_id"] = je.id
                data["gl_journal_ref"] = je.reference
                return Response(data)
        except Exception as e:
            return Response(
                {"detail": f"Approve blocked — GL accrual failed: {e}"},
                status=400,
            )

    @action(detail=False, methods=["get"], url_path="aging")
    def aging(self, request):
        """AR open-invoice aging buckets by customer (sales.credit)."""
        from datetime import date as date_cls
        from collections import defaultdict

        from core.access import user_organization

        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        today = timezone.localdate()
        as_of_raw = request.query_params.get("as_of")
        if as_of_raw:
            try:
                today = date_cls.fromisoformat(str(as_of_raw)[:10])
            except ValueError:
                return Response({"detail": "Invalid as_of date"}, status=400)

        qs = (
            CustomerInvoice.objects.filter(
                organization=org,
                is_deleted=False,
                status__in=[
                    CustomerInvoice.Status.APPROVED,
                    CustomerInvoice.Status.SUBMITTED,
                ],
            )
            .select_related("customer")
            .order_by("customer__name", "due_date")
        )
        buckets = ("current", "1_30", "31_60", "61_90", "90_plus")
        by_customer: dict = defaultdict(
            lambda: {
                "customer_id": None,
                "customer_code": "",
                "customer_name": "",
                "current": Decimal("0"),
                "1_30": Decimal("0"),
                "31_60": Decimal("0"),
                "61_90": Decimal("0"),
                "90_plus": Decimal("0"),
                "total": Decimal("0"),
                "invoices": [],
            }
        )
        for inv in qs:
            due = inv.due_date or inv.invoice_date
            days = (today - due).days if due else 0
            open_amt = (
                Decimal(str(inv.amount or 0))
                + Decimal(str(inv.tax_amount or 0))
                - Decimal(str(inv.paid_amount or 0))
            )
            if open_amt <= 0:
                continue
            if days <= 0:
                bucket = "current"
            elif days <= 30:
                bucket = "1_30"
            elif days <= 60:
                bucket = "31_60"
            elif days <= 90:
                bucket = "61_90"
            else:
                bucket = "90_plus"
            key = inv.customer_id
            row = by_customer[key]
            row["customer_id"] = inv.customer_id
            row["customer_code"] = inv.customer.code
            row["customer_name"] = inv.customer.name
            row[bucket] += open_amt
            row["total"] += open_amt
            row["invoices"].append(
                {
                    "id": inv.id,
                    "invoice_no": inv.invoice_no,
                    "invoice_date": str(inv.invoice_date),
                    "due_date": str(due) if due else None,
                    "days_past_due": days,
                    "bucket": bucket,
                    "open_amount": str(open_amt.quantize(Decimal("0.01"))),
                }
            )

        customers = []
        totals = {b: Decimal("0") for b in buckets}
        totals["total"] = Decimal("0")
        for row in by_customer.values():
            for b in buckets:
                totals[b] += row[b]
                row[b] = str(row[b].quantize(Decimal("0.01")))
            totals["total"] += row["total"]
            row["total"] = str(Decimal(row["total"]).quantize(Decimal("0.01")))
            customers.append(row)
        customers.sort(key=lambda r: r["customer_name"] or "")
        return Response(
            {
                "as_of": str(today),
                "buckets": list(buckets),
                "customers": customers,
                "totals": {k: str(v.quantize(Decimal("0.01"))) for k, v in totals.items()},
            }
        )

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        from django.db import transaction
        from finance.gl_automation import post_ar_receipt

        inv = self.get_object()
        if inv.status != "approved":
            return Response(
                {"detail": "Only approved AR invoices can receive payment"},
                status=400,
            )
        bank_id = request.data.get("bank_account")
        if not bank_id:
            return Response(
                {"detail": "bank_account is required to post receipt to GL"},
                status=400,
            )
        bank = BankAccount.objects.filter(
            organization=inv.organization, id=bank_id, is_active=True
        ).first()
        if not bank:
            return Response({"detail": "Bank account not found"}, status=400)
        ref = (request.data.get("payment_ref") or "").strip()
        gross = Decimal(str(inv.amount or 0)) + Decimal(str(inv.tax_amount or 0))
        raw_amt = request.data.get("paid_amount")
        amount = Decimal(str(raw_amt if raw_amt not in (None, "") else gross))
        try:
            with transaction.atomic():
                inv.payment_ref = ref
                inv.paid_amount = amount
                inv.paid_at = timezone.now()
                inv.save(
                    update_fields=[
                        "payment_ref",
                        "paid_amount",
                        "paid_at",
                        "updated_at",
                    ]
                )
                je = post_ar_receipt(invoice=inv, bank=bank, user=request.user)
                inv.status = CustomerInvoice.Status.PAID
                inv.save(update_fields=["status", "updated_at"])
                if inv.sales_order_id and inv.sales_order.status != "invoiced":
                    so = inv.sales_order
                    so.status = "invoiced"
                    so.save(update_fields=["status", "updated_at"])
        except Exception as e:
            return Response(
                {"detail": f"Receipt not recorded — GL post failed: {e}"},
                status=400,
            )
        data = self.get_serializer(inv).data
        data["gl_journal_ref"] = je.reference
        return Response(data)


class BankAccountViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BankAccount.objects.select_related("gl_account").all()
    serializer_class = BankAccountSerializer
    search_fields = ("name", "bank_name", "account_no")
    filterset_fields = ("is_active", "currency")
    rbac_module = "finance.banks"


class BankReconciliationViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BankReconciliation.objects.select_related("bank_account")
    serializer_class = BankReconciliationSerializer
    filterset_fields = ("status", "bank_account")
    search_fields = ("notes", "bank_account__name", "bank_account__account_no")
    rbac_module = "finance.banks"

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """Mark reconciliation closed and sync bank account balance / last_reconciled."""
        from decimal import Decimal

        from finance.models import BankStatementLine
        from finance.serializers import _sync_bank_from_reconciliation

        recon = self.get_object()
        force = str(request.data.get("force") or "").lower() in ("1", "true", "yes")
        diff = abs(Decimal(recon.statement_balance or 0) - Decimal(recon.book_balance or 0))
        unmatched = BankStatementLine.objects.filter(
            reconciliation=recon, matched=False
        ).count()
        if not force and (diff >= Decimal("0.01") or unmatched):
            return Response(
                {
                    "detail": (
                        f"Cannot close: difference {diff:.2f} and {unmatched} unmatched line(s). "
                        "Match lines / fix balances, or pass force=true."
                    ),
                    "difference": float(diff),
                    "unmatched": unmatched,
                },
                status=400,
            )
        recon.status = BankReconciliation.Status.CLOSED
        recon.save(update_fields=["status", "updated_at"])
        _sync_bank_from_reconciliation(recon)
        return Response(self.get_serializer(recon).data)

    @action(detail=True, methods=["post"], url_path="upload-csv")
    def upload_csv(self, request, pk=None):
        """Upload bank statement CSV into BankStatementLine rows for this reconciliation."""
        recon = self.get_object()
        raw = read_upload_text(request)
        if not raw.strip():
            return Response(
                {"detail": "CSV file required (multipart field 'file' or body 'csv')"},
                status=400,
            )
        rows, errors = parse_bank_statement_csv(raw)
        if not rows:
            return Response(
                {"detail": errors[0] if errors else "No rows imported", "errors": errors},
                status=400,
            )
        created = 0
        for row in rows:
            BankStatementLine.objects.create(
                organization=recon.organization,
                bank_account=recon.bank_account,
                reconciliation=recon,
                txn_date=row["txn_date"],
                description=row["description"],
                amount=row["amount"],
                reference=row.get("reference") or "",
                created_by=request.user,
            )
            created += 1
        return Response(
            {
                "created": created,
                "skipped_errors": errors,
                "bank_account": recon.bank_account_id,
                "reconciliation": recon.id,
            }
        )


class InvestmentViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Investment.objects.all()
    serializer_class = InvestmentSerializer
    search_fields = ("name", "instrument_type", "fund_tag")
    rbac_module = "finance.treasury"


class FixedAssetViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = FixedAsset.objects.select_related("assigned_employee")
    serializer_class = FixedAssetSerializer
    search_fields = (
        "asset_code",
        "name",
        "category",
        "location",
        "custodian",
        "assigned_employee__employee_code",
        "assigned_employee__first_name",
        "assigned_employee__last_name",
    )
    filterset_fields = ("status", "category", "assigned_employee", "location")
    rbac_module = "finance.assets"

    def get_queryset(self):
        from django.db.models import Count, Q

        qs = super().get_queryset()
        return qs.annotate(
            _open_repair_count=Count(
                "repairs",
                filter=Q(
                    repairs__is_deleted=False,
                    repairs__status__in=(
                        AssetRepair.Status.REQUESTED,
                        AssetRepair.Status.APPROVED,
                        AssetRepair.Status.IN_PROGRESS,
                    ),
                ),
            )
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign asset to an employee and/or location (custodian label optional)."""
        from hr.models import Employee

        asset = self.get_object()
        if asset.status == FixedAsset.Status.DISPOSED:
            return Response({"detail": "Cannot assign a disposed asset"}, status=400)

        data = request.data or {}
        update_fields = ["updated_at"]

        if "assigned_employee" in data:
            raw = data.get("assigned_employee")
            if raw in (None, "", 0, "0"):
                asset.assigned_employee = None
            else:
                emp = Employee.objects.filter(
                    pk=raw, organization=asset.organization, is_deleted=False
                ).first()
                if not emp:
                    return Response(
                        {"detail": "Employee not found in this organization"},
                        status=400,
                    )
                asset.assigned_employee = emp
                if not data.get("custodian"):
                    asset.custodian = emp.full_name
                    update_fields.append("custodian")
            update_fields.append("assigned_employee")

        if "location" in data:
            asset.location = str(data.get("location") or "")[:128]
            update_fields.append("location")

        if "custodian" in data and data.get("custodian") is not None:
            asset.custodian = str(data.get("custodian") or "")[:128]
            if "custodian" not in update_fields:
                update_fields.append("custodian")

        asset.save(update_fields=list(dict.fromkeys(update_fields)))
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        """QR sticker payload + absolute deep-link URL for printing."""
        asset = self.get_object()
        ser = self.get_serializer(asset)
        return Response(
            {
                "asset_code": asset.asset_code,
                "name": asset.name,
                "qr_payload": ser.data.get("qr_payload"),
                "qr_url": ser.data.get("qr_url"),
                "path": f"/finance/assets/{asset.id}",
            }
        )

    @action(detail=True, methods=["post"])
    def depreciate(self, request, pk=None):
        """Monthly straight-line slice (cost×rate/100/12) + GL post + log line."""
        from finance.gl_automation import post_depreciation

        asset = self.get_object()
        if asset.status != FixedAsset.Status.ACTIVE:
            return Response({"detail": "Asset not active"}, status=400)
        rate = Decimal(str(asset.depreciation_rate or 0))
        cost = Decimal(str(asset.purchase_cost or 0))
        book = Decimal(str(asset.book_value or cost))
        if rate <= 0 or (cost <= 0 and book <= 0):
            return Response({"detail": "Set purchase_cost and depreciation_rate"}, status=400)
        base = cost if cost > 0 else book
        amount = (base * rate / Decimal("100") / Decimal("12")).quantize(Decimal("0.01"))
        if amount > book:
            amount = book
        if amount <= 0:
            return Response({"detail": "Nothing left to depreciate"}, status=400)
        asset.accumulated_depreciation = (
            Decimal(str(asset.accumulated_depreciation or 0)) + amount
        )
        asset.book_value = book - amount
        asset.save(
            update_fields=[
                "accumulated_depreciation",
                "book_value",
                "updated_at",
            ]
        )
        AssetDepreciationLine.objects.create(
            organization_id=asset.organization_id,
            asset=asset,
            run_date=timezone.localdate(),
            amount=amount,
            notes=str(request.data.get("notes") or "Monthly straight-line depreciation"),
            created_by=request.user,
            updated_by=request.user,
        )
        je = None
        try:
            je = post_depreciation(asset=asset, amount=amount, user=request.user)
        except Exception as e:
            return Response(
                {
                    "detail": f"Asset updated but GL post failed: {e}",
                    "depreciation": str(amount),
                    "book_value": str(asset.book_value),
                },
                status=400,
            )
        return Response(
            {
                "depreciation": str(amount),
                "book_value": str(asset.book_value),
                "accumulated_depreciation": str(asset.accumulated_depreciation),
                "gl_journal_id": je.id if je else None,
                "gl_journal_ref": je.reference if je else None,
            }
        )

    @action(detail=True, methods=["post"])
    def dispose(self, request, pk=None):
        from datetime import date as date_cls

        asset = self.get_object()
        proceeds = Decimal(str(request.data.get("proceeds") or 0))
        raw = request.data.get("disposed_on")
        if raw:
            try:
                on = date_cls.fromisoformat(str(raw)[:10])
            except ValueError:
                return Response({"detail": "Invalid disposed_on (YYYY-MM-DD)"}, status=400)
        else:
            on = date_cls.today()
        asset.status = FixedAsset.Status.DISPOSED
        asset.disposed_on = on
        asset.disposal_date = on
        asset.disposal_proceeds = proceeds
        asset.disposal_amount = proceeds
        asset.book_value = Decimal("0")
        asset.save(
            update_fields=[
                "status",
                "disposed_on",
                "disposal_date",
                "disposal_proceeds",
                "disposal_amount",
                "book_value",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(asset).data)


class AssetRepairViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetRepair.objects.select_related("asset")
    serializer_class = AssetRepairSerializer
    search_fields = ("request_no", "title", "vendor_name", "asset__asset_code", "asset__name")
    filterset_fields = ("status", "asset")
    rbac_module = "finance.assets"


class PmScheduleViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PmSchedule.objects.select_related("asset")
    serializer_class = PmScheduleSerializer
    search_fields = ("title", "asset__asset_code", "asset__name")
    filterset_fields = ("asset", "active")
    rbac_module = "finance.maintenance"

    @action(detail=False, methods=["post"], url_path="generate-due")
    def generate_due(self, request):
        from core.access import user_organization
        from finance.maintenance import generate_due_work_orders

        org = user_organization(request.user)
        if org is None:
            return Response({"detail": "No organization."}, status=400)
        created, skipped = generate_due_work_orders(org, user=request.user)
        return Response(
            {
                "created": len(created),
                "skipped": skipped,
                "work_orders": MaintenanceWorkOrderSerializer(
                    created, many=True, context=self.get_serializer_context()
                ).data,
            },
            status=201 if created else 200,
        )


class MaintenanceWorkOrderViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = MaintenanceWorkOrder.objects.select_related(
        "asset", "pm_schedule", "assigned_to"
    ).prefetch_related("parts__item", "parts__warehouse")
    serializer_class = MaintenanceWorkOrderSerializer
    search_fields = ("mwo_no", "title", "asset__asset_code", "asset__name")
    filterset_fields = ("status", "asset", "assigned_to", "pm_schedule")
    rbac_module = "finance.maintenance"

    @property
    def rbac_action(self):
        if getattr(self, "action", None) in ("start", "complete", "cancel", "issue_part"):
            return "change"
        return None

    def _transition(self, request, allowed_from, to_status, label):
        mwo = self.get_object()
        if mwo.status not in allowed_from:
            return Response(
                {"detail": f"Cannot {label} a {mwo.status} work order."}, status=400
            )
        if to_status == MaintenanceWorkOrder.Status.DONE:
            from finance.maintenance import mark_done

            raw = request.data.get("completed_date")
            done_on = None
            if raw:
                try:
                    done_on = date_cls.fromisoformat(str(raw)[:10])
                except ValueError:
                    return Response(
                        {"detail": "Invalid completed_date (YYYY-MM-DD)"}, status=400
                    )
            if request.data.get("cost") not in (None, ""):
                try:
                    mwo.cost = Decimal(str(request.data["cost"]))
                except Exception:
                    return Response({"detail": "Invalid cost."}, status=400)
                mwo.save(update_fields=["cost", "updated_at"])
            mark_done(mwo, user=request.user, done_on=done_on)
        else:
            mwo.status = to_status
            mwo.updated_by = request.user
            mwo.save(update_fields=["status", "updated_by", "updated_at"])
        mwo.refresh_from_db()
        return Response(self.get_serializer(mwo).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        S = MaintenanceWorkOrder.Status
        return self._transition(request, (S.OPEN, S.SCHEDULED), S.IN_PROGRESS, "start")

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        S = MaintenanceWorkOrder.Status
        return self._transition(
            request, (S.OPEN, S.SCHEDULED, S.IN_PROGRESS), S.DONE, "complete"
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        S = MaintenanceWorkOrder.Status
        return self._transition(
            request, (S.OPEN, S.SCHEDULED, S.IN_PROGRESS), S.CANCELLED, "cancel"
        )

    @action(detail=True, methods=["post"], url_path="issue-part")
    def issue_part(self, request, pk=None):
        from decimal import Decimal

        from core.access import user_organization
        from finance.models import MaintenancePart
        from ops.parts_issue import issue_spare
        from rest_framework.exceptions import ValidationError

        mwo = self.get_object()
        if mwo.status in (
            MaintenanceWorkOrder.Status.DONE,
            MaintenanceWorkOrder.Status.CANCELLED,
        ):
            raise ValidationError(f"Cannot issue parts on a {mwo.status} work order.")
        from django.db import transaction

        with transaction.atomic():
            org = user_organization(request.user)
            issued = issue_spare(
                org=org,
                item_id=request.data.get("item"),
                qty=request.data.get("qty"),
                warehouse_id=request.data.get("warehouse"),
                user=request.user,
                reference=mwo.mwo_no,
                notes=f"Maintenance {mwo.mwo_no}",
            )
            qty = Decimal(str(request.data.get("qty")))
            MaintenancePart.objects.create(
                organization=org,
                work_order=mwo,
                item=issued["item"],
                warehouse=issued["warehouse"],
                qty=qty,
                unit_cost=issued["unit_cost"],
                stock_movement=issued["movement"],
            )
            part_cost = (qty * (issued["unit_cost"] or 0)).quantize(Decimal("0.01"))
            mwo.cost = (mwo.cost or 0) + part_cost
            fields = ["cost", "updated_by", "updated_at"]
            mwo.updated_by = request.user
            if mwo.status in (
                MaintenanceWorkOrder.Status.OPEN,
                MaintenanceWorkOrder.Status.SCHEDULED,
            ):
                mwo.status = MaintenanceWorkOrder.Status.IN_PROGRESS
                fields.append("status")
            mwo.save(update_fields=fields)
        mwo.refresh_from_db()
        return Response(self.get_serializer(mwo).data)


class TaxCodeViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaxCode.objects.all()
    serializer_class = TaxCodeSerializer
    search_fields = ("code", "name")
    filterset_fields = ("tax_type", "is_active")
    rbac_module = "finance.tax"


class AssetDepreciationLineViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = AssetDepreciationLine.objects.select_related("asset")
    serializer_class = AssetDepreciationLineSerializer
    filterset_fields = ("asset", "run_date")
    rbac_module = "finance.assets"


class AssetDepreciationRunViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = AssetDepreciationRun.objects.all()
    serializer_class = AssetDepreciationRunSerializer
    filterset_fields = ("status", "period_year", "period_month")
    search_fields = ("notes",)
    rbac_module = "finance.assets"

    @action(detail=True, methods=["post"], url_path="post")
    def post_run(self, request, pk=None):
        from finance.gl_automation import post_depreciation

        run = self.get_object()
        if run.status == AssetDepreciationRun.Status.POSTED:
            return Response({"detail": "Already posted."}, status=400)
        posted = 0
        errors = []
        assets = FixedAsset.objects.filter(
            organization=run.organization,
            is_deleted=False,
            status=FixedAsset.Status.ACTIVE,
            cip_flag=False,
        )
        for asset in assets:
            rate = Decimal(str(asset.depreciation_rate or 0))
            cost = Decimal(str(asset.purchase_cost or 0))
            if rate <= 0 or cost <= 0:
                continue
            amount = (cost * rate / Decimal("100") / Decimal("12")).quantize(
                Decimal("0.01")
            )
            book = Decimal(str(asset.book_value or cost))
            if amount > book:
                amount = book
            if amount <= 0:
                continue
            asset.accumulated_depreciation = (
                Decimal(str(asset.accumulated_depreciation or 0)) + amount
            )
            asset.book_value = book - amount
            asset.save(
                update_fields=[
                    "accumulated_depreciation",
                    "book_value",
                    "updated_at",
                ]
            )
            AssetDepreciationLine.objects.create(
                organization=run.organization,
                asset=asset,
                run_date=timezone.localdate(),
                amount=amount,
                notes=f"Dep run {run.period_year}-{run.period_month:02d}",
                created_by=request.user,
                updated_by=request.user,
            )
            try:
                post_depreciation(asset=asset, amount=amount, user=request.user)
            except Exception as e:
                errors.append(f"{asset.asset_code}: {e}")
            posted += 1
        run.status = AssetDepreciationRun.Status.POSTED
        run.posted_at = timezone.now()
        run.save(update_fields=["status", "posted_at", "updated_at"])
        return Response(
            {
                "posted_assets": posted,
                "errors": errors,
                "run": self.get_serializer(run).data,
            }
        )


class EInvoiceSubmissionViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = EInvoiceSubmission.objects.select_related(
        "ar_invoice", "ar_invoice__customer"
    )
    serializer_class = EInvoiceSubmissionSerializer
    search_fields = ("fbr_invoice_no", "ar_invoice__invoice_no")
    filterset_fields = ("fbr_status", "ar_invoice")
    rbac_module = "finance.einvoice"

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """Build PK-style payload and submit (sandbox unless FBR_API_URL is set)."""
        from finance.fbr import submit_einvoice

        obj = self.get_object()
        try:
            submit_einvoice(obj, user=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        data = self.get_serializer(obj).data
        if obj.fbr_status == EInvoiceSubmission.FbrStatus.REJECTED:
            return Response(
                {"detail": obj.error_message or "FBR submission failed", **data},
                status=502,
            )
        return Response(data)

    @action(detail=True, methods=["get"], url_path="payload")
    def payload(self, request, pk=None):
        """Preview the payload that would be submitted."""
        from finance.fbr import build_payload

        obj = self.get_object()
        return Response(build_payload(obj.ar_invoice))


class FbrInvoiceSubmissionViewSet(
    OrgScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet
):
    """DEPRECATED legacy table — read-only. Use /finance/e-invoices/."""

    queryset = FbrInvoiceSubmission.objects.all()
    serializer_class = FbrInvoiceSubmissionSerializer
    search_fields = ("local_invoice_id", "fbr_invoice_no")
    filterset_fields = ("invoice_type", "status")
    rbac_module = "finance.einvoice"


class CurrencyViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_active", "code")
    rbac_module = "finance.fx"

    def initial(self, request, *args, **kwargs):
        from accounts.rbac import can

        if request.method in ("GET", "HEAD", "OPTIONS"):
            self.rbac_module = ""
        else:
            action = {"POST": "add", "DELETE": "delete"}.get(request.method, "change")
            for module in ("finance.fx", "finance.vendors"):
                if can(request.user, module, action):
                    self.rbac_module = module
                    break
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        from core.access import user_organization

        org = user_organization(self.request.user)
        if org:
            ensure_default_currencies(org)
        return super().get_queryset()


class FxRateViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = FxRate.objects.all()
    serializer_class = FxRateSerializer
    search_fields = ("currency_from", "currency_to")
    filterset_fields = ("currency_from", "currency_to", "rate_date")
    rbac_module = "finance.fx"


class ChequeRegisterViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ChequeRegister.objects.select_related("bank_account")
    serializer_class = ChequeRegisterSerializer
    search_fields = ("cheque_no", "payee")
    filterset_fields = ("status", "bank_account", "is_pdc")
    rbac_module = "finance.cheques"

    @staticmethod
    def _flag(request, key, default=True):
        raw = (request.data or {}).get(key)
        if raw is None:
            return default
        return str(raw).lower() in ("1", "true", "yes", "on")

    @action(detail=True, methods=["post"], url_path="clear")
    def clear(self, request, pk=None):
        """Issued cheque cleared by bank: reduce bank balance, post Dr AP / Cr Bank."""
        from django.db import transaction
        from rest_framework.exceptions import ValidationError

        from finance.gl_automation import post_cheque_clearing

        chq = self.get_object()
        if chq.status != ChequeRegister.Status.ISSUED:
            raise ValidationError(f"Only issued cheques can be cleared (now {chq.status}).")
        raw = (request.data or {}).get("cleared_date")
        try:
            cleared = date_cls.fromisoformat(str(raw)[:10]) if raw else timezone.localdate()
        except ValueError:
            raise ValidationError("Invalid cleared_date (YYYY-MM-DD).")
        try:
            with transaction.atomic():
                chq.cleared_date = cleared
                chq.status = ChequeRegister.Status.CLEARED
                je = post_cheque_clearing(
                    cheque=chq,
                    user=request.user,
                    post_journal=self._flag(request, "post_journal", True),
                )
                chq.gl_journal = je
                chq.updated_by = request.user
                chq.save()
        except ValueError as e:
            raise ValidationError(str(e))
        data = self.get_serializer(chq).data
        data["gl_journal_ref"] = chq.gl_journal.reference if chq.gl_journal_id else None
        return Response(data)

    @action(detail=True, methods=["post"], url_path="bounce")
    def bounce(self, request, pk=None):
        """Bounce a cheque; if it had cleared, restore bank balance and reverse the JE."""
        from django.db import transaction
        from rest_framework.exceptions import ValidationError

        from finance.gl_automation import post_cheque_bounce_reversal

        chq = self.get_object()
        if chq.status not in (
            ChequeRegister.Status.ISSUED,
            ChequeRegister.Status.CLEARED,
        ):
            raise ValidationError(f"Cannot bounce a {chq.status} cheque.")
        was_cleared = chq.status == ChequeRegister.Status.CLEARED
        try:
            with transaction.atomic():
                if was_cleared:
                    post_cheque_bounce_reversal(cheque=chq, user=request.user)
                chq.status = ChequeRegister.Status.BOUNCED
                chq.bounced_date = timezone.localdate()
                chq.bounce_reason = str((request.data or {}).get("reason") or "")[:255]
                chq.updated_by = request.user
                chq.save()
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(self.get_serializer(chq).data)


class IntercompanyPartnerViewSet(
    BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = IntercompanyPartner.objects.select_related(
        "receivable_account", "payable_account"
    )
    serializer_class = IntercompanyPartnerSerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_active", "currency")
    rbac_module = "finance.intercompany"


class IntercompanyTxnViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = IntercompanyTxn.objects.select_related("partner")
    serializer_class = IntercompanyTxnSerializer
    search_fields = ("reference", "notes")
    filterset_fields = ("partner", "direction", "status")
    rbac_module = "finance.intercompany"

    @action(detail=True, methods=["post"], url_path="post")
    def post_txn(self, request, pk=None):
        """Post IC txn to GL using the partner's receivable / payable account."""
        from django.db import transaction
        from rest_framework.exceptions import ValidationError

        from finance.gl_automation import post_intercompany_txn

        txn = self.get_object()
        if txn.status == IntercompanyTxn.Status.POSTED:
            raise ValidationError("Already posted.")
        try:
            with transaction.atomic():
                je = post_intercompany_txn(txn=txn, user=request.user)
                txn.gl_journal = je
                txn.status = IntercompanyTxn.Status.POSTED
                txn.updated_by = request.user
                txn.save()
        except ValueError as e:
            raise ValidationError(str(e))
        data = self.get_serializer(txn).data
        data["gl_journal_ref"] = je.reference
        return Response(data)


class FinanceReportsView(APIView):
    """TB, P&L, balance sheet, cash, AP ageing + KPI snapshot."""

    rbac_module = "finance.reports"

    def get(self, request):
        from datetime import date

        from core.access import user_organization
        from django.db.models import Sum
        from finance.reporting import (
            ap_ageing,
            ar_ageing,
            balance_sheet,
            budget_vs_actual,
            cash_flow,
            cash_position,
            income_statement,
            payroll_register_summary,
            refresh_budget_utilized,
            stock_valuation,
            trial_balance,
            wht_register,
        )

        org = user_organization(request.user)
        if not org:
            return Response({})
        as_of_raw = request.query_params.get("as_of")
        year = request.query_params.get("year")
        as_of = None
        if as_of_raw:
            try:
                as_of = date.fromisoformat(as_of_raw)
            except ValueError:
                as_of = None
        fy = int(year) if year else (as_of.year if as_of else date.today().year)
        refresh_budget_utilized(org, fy)
        return Response(
            {
                "accounts": Account.objects.filter(organization=org).count(),
                "vendors": Vendor.objects.filter(organization=org).count(),
                "open_journals": JournalEntry.objects.filter(
                    organization=org, status__in=["draft", "submitted", "approved"]
                ).count(),
                "budget_total": Budget.objects.filter(organization=org).aggregate(
                    s=Sum("amount")
                )["s"]
                or 0,
                "budget_utilized": Budget.objects.filter(organization=org).aggregate(
                    s=Sum("utilized")
                )["s"]
                or 0,
                "budget_vs_actual": budget_vs_actual(org, fiscal_year=fy),
                "ap_open": VendorInvoice.objects.filter(
                    organization=org, status__in=["draft", "submitted", "approved"]
                ).count(),
                "assets": FixedAsset.objects.filter(organization=org).count(),
                "investments": Investment.objects.filter(organization=org).count(),
                "trial_balance": trial_balance(org, as_of=as_of),
                "income_statement": income_statement(org, year=fy),
                "balance_sheet": balance_sheet(org, as_of=as_of),
                "cash_position": cash_position(org),
                "cash_flow": cash_flow(org, year=fy),
                "ap_ageing": ap_ageing(org, as_of=as_of),
                "ar_ageing": ar_ageing(org, as_of=as_of),
                "stock_valuation": stock_valuation(org),
                "wht_register": wht_register(
                    org, date_from=date(fy, 1, 1), date_to=as_of or date(fy, 12, 31)
                ),
                "payroll_register": payroll_register_summary(org, year=fy),
            }
        )
