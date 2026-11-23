from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from finance.models import (
    Account,
    AccountType,
    AssetDepreciationLine,
    AssetDepreciationRun,
    AssetRepair,
    BankAccount,
    BankReconciliation,
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
    JournalLine,
    MaintenanceWorkOrder,
    PmSchedule,
    TaxCode,
    Vendor,
    VendorInvoice,
    ensure_default_currencies,
)

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


class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = "__all__"
        read_only_fields = RO

    def validate_code(self, value):
        return (value or "").strip().lower().replace(" ", "_")

    def update(self, instance, validated_data):
        if instance.is_system:
            validated_data.pop("code", None)
            validated_data.pop("is_system", None)
        return super().update(instance, validated_data)


class AccountSerializer(serializers.ModelSerializer):
    code = serializers.CharField(max_length=32, allow_blank=True, trim_whitespace=True)
    name = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=True)

    class Meta:
        model = Account
        fields = "__all__"
        read_only_fields = RO

    def validate_code(self, value):
        return (value or "").strip()

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else validated_data.get("organization")
        if org and not (validated_data.get("code") or "").strip():
            ensure_doc_no(validated_data, "code", org, kind="gl", model=Account)
        return super().create(validated_data)

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Account name is required.")
        return name

    def validate_account_type(self, value):
        from finance.models import ensure_default_account_types

        code = (value or "").strip()
        if not code:
            raise serializers.ValidationError("Account type is required")
        request = self.context.get("request")
        org = None
        if request:
            from core.access import user_organization

            org = user_organization(request.user)
        if self.instance is not None:
            org = org or self.instance.organization
        if org:
            ensure_default_account_types(org)
            if not AccountType.objects.filter(
                organization=org, code=code, is_active=True, is_deleted=False
            ).exists():
                raise serializers.ValidationError(
                    f"Unknown or inactive account type '{code}'. Add it under Account types."
                )
        return code

    def to_representation(self, instance):
        data = super().to_representation(instance)
        at = AccountType.objects.filter(
            organization_id=instance.organization_id, code=instance.account_type
        ).first()
        data["account_type_name"] = at.name if at else instance.account_type
        data["statement_class"] = instance.statement_class
        return data


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = "__all__"
        read_only_fields = RO

    def validate(self, attrs):
        request = self.context.get("request")
        org = None
        if request and request.user.is_authenticated:
            from core.access import user_organization

            org = user_organization(request.user)
        if self.instance is not None:
            org = org or self.instance.organization
        code = str(attrs.get("code", getattr(self.instance, "code", "")) or "").strip()
        if code and org:
            clash = CostCenter.all_objects.filter(organization=org, code=code, is_deleted=False)
            if self.instance is not None and self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"code": f"Code {code} is already used. Choose a different code."}
                )
        if "code" in attrs:
            attrs["code"] = code
        return attrs


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"
        read_only_fields = RO

    def validate_code(self, value):
        code = str(value or "").strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise serializers.ValidationError("Use a 3-letter code such as PKR or USD.")
        return code

    def validate_name(self, value):
        name = str(value or "").strip()
        if not name:
            raise serializers.ValidationError("Enter the currency name.")
        return name

    def validate(self, attrs):
        attrs = super().validate(attrs)
        code = attrs.get("code", getattr(self.instance, "code", ""))
        request = self.context.get("request")
        from core.access import user_organization

        org = user_organization(request.user) if request else None
        if org and code:
            clash = Currency.all_objects.filter(organization=org, code=code, is_deleted=False)
            if self.instance is not None and self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"code": f"Code {code} is already used. Choose a different code."}
                )
        return attrs


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"
        read_only_fields = RO

    def validate_currency(self, value):
        return str(value or "PKR").strip().upper()[:8] or "PKR"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "currency" not in attrs and self.instance is not None:
            return attrs
        code = attrs.get("currency") or "PKR"
        attrs["currency"] = code
        request = self.context.get("request")
        from core.access import user_organization

        org = user_organization(request.user) if request else None
        if org:
            ensure_default_currencies(org)
            active = Currency.objects.filter(
                organization=org, code=code, is_active=True
            ).exists()
            unchanged = (
                self.instance is not None
                and str(self.instance.currency or "").strip().upper() == code
            )
            if not active and not unchanged:
                raise serializers.ValidationError(
                    {
                        "currency": (
                            f"{code} is not in the currency list. "
                            "Add it under Currencies, then choose it here."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org and not validated_data.get("code"):
            ensure_doc_no(validated_data, "code", org, kind="vendor", model=Vendor)
        return super().create(validated_data)


class JournalLineSerializer(serializers.ModelSerializer):
    cost_center_label = serializers.SerializerMethodField()

    class Meta:
        model = JournalLine
        fields = (
            "id",
            "account",
            "cost_center",
            "cost_center_label",
            "debit",
            "credit",
            "description",
        )
        read_only_fields = ("cost_center_label",)

    def get_cost_center_label(self, obj):
        cc_id = getattr(obj, "cost_center_id", None)
        if not cc_id:
            return ""
        cc = CostCenter.all_objects.filter(pk=cc_id).only("code", "name").first()
        if not cc:
            return ""
        code = (cc.code or "").strip()
        name = (cc.name or "").strip()
        if code and name and code.casefold() != name.casefold():
            return f"{code} — {name}"
        return name or code


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, required=False)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    balanced = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = (
            "id",
            "organization",
            "entry_date",
            "reference",
            "narration",
            "status",
            "lines",
            "total_debit",
            "total_credit",
            "balanced",
            "created_at",
        )
        read_only_fields = (
            "organization",
            "status",
            "total_debit",
            "total_credit",
            "balanced",
            "created_at",
        )

    def get_total_debit(self, obj):
        return float(sum((l.debit or 0) for l in obj.lines.all()))

    def get_total_credit(self, obj):
        return float(sum((l.credit or 0) for l in obj.lines.all()))

    def get_balanced(self, obj):
        return abs(self.get_total_debit(obj) - self.get_total_credit(obj)) < 0.005

    def _assert_balanced_lines(self, lines_data):
        debit = sum(float(l.get("debit") or 0) for l in lines_data)
        credit = sum(float(l.get("credit") or 0) for l in lines_data)
        if abs(debit - credit) >= 0.005:
            raise serializers.ValidationError(
                {"lines": f"Journal is out of balance (debit {debit:.2f} ≠ credit {credit:.2f})."}
            )

    def validate(self, attrs):
        if self.instance is None:
            raw = self.initial_data.get("lines") if hasattr(self, "initial_data") else None
            if not raw:
                raise serializers.ValidationError(
                    {"lines": "Add at least two journal lines (debit and credit)."}
                )
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        lines_data = validated_data.pop("lines", [])
        validated_data.pop("status", None)
        if len(lines_data) < 2:
            raise serializers.ValidationError(
                {"lines": "Journal needs at least two lines for double-entry."}
            )
        self._assert_balanced_lines(lines_data)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            # Auto voucher no. into reference when blank (JE-YYYY-#####)
            ensure_doc_no(
                validated_data, "reference", org, kind="journal", model=JournalEntry
            )
        journal = JournalEntry.objects.create(status="draft", **validated_data)
        for line in lines_data:
            JournalLine.objects.create(journal=journal, **line)
        return journal

    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status == "posted":
            raise serializers.ValidationError(
                {"detail": "Posted journals are immutable. Reverse with a new adjusting entry."}
            )
        if instance.status not in ("draft", "rejected"):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot edit a {instance.status} journal. "
                        "Use workflow actions, or reject back to draft."
                    )
                }
            )
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            if len(lines_data) < 2:
                raise serializers.ValidationError(
                    {"lines": "Journal needs at least two lines for double-entry."}
                )
            self._assert_balanced_lines(lines_data)
            instance.lines.all().delete()
            for line in lines_data:
                JournalLine.objects.create(journal=instance, **line)
        return instance


class BudgetSerializer(serializers.ModelSerializer):
    cost_center_name = serializers.CharField(source="cost_center.name", read_only=True)

    class Meta:
        model = Budget
        fields = "__all__"
        read_only_fields = RO

    def validate_fiscal_year(self, value):
        year = int(value)
        if year < 2000 or year > 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100.")
        return year

    def validate_amount(self, value):
        return Decimal(value or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class VendorInvoiceSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    purchase_order_no = serializers.CharField(
        source="purchase_order.po_no", read_only=True, allow_null=True
    )

    class Meta:
        model = VendorInvoice
        fields = "__all__"
        read_only_fields = list(RO) + ["status", "fx_rate"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["vendor_name"] = getattr(instance.vendor, "name", None)
        data["purchase_order_no"] = (
            getattr(instance.purchase_order, "po_no", None)
            if instance.purchase_order_id
            else None
        )
        data["net_payable"] = float(
            (instance.amount or 0) - (instance.wht_amount or 0)
        )
        if instance.purchase_order_id:
            from ops.match import three_way_match

            data["three_way_match"] = three_way_match(
                instance.purchase_order, invoice_amount=instance.amount
            )
        else:
            data["three_way_match"] = None
        return data

    def validate(self, attrs):
        vendor = attrs.get("vendor") or getattr(self.instance, "vendor", None)
        po = attrs.get("purchase_order", getattr(self.instance, "purchase_order", None))
        if "purchase_order" in attrs and attrs["purchase_order"] is None:
            po = None
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if po is not None:
            if vendor and po.vendor_id != vendor.id:
                raise serializers.ValidationError(
                    {"purchase_order": "Purchase order vendor must match the invoice vendor."}
                )
            if po.status not in ("approved", "received"):
                raise serializers.ValidationError(
                    {
                        "purchase_order": (
                            "Link only approved or received purchase orders."
                        )
                    }
                )
            from ops.match import three_way_match

            match = three_way_match(po, invoice_amount=amount)
            # Soft block only on hard over-receipt / large amount variance without receipt
            if match["status"] == "no_receipt":
                raise serializers.ValidationError(
                    {
                        "purchase_order": (
                            "No goods receipt posted for this PO — receive goods before billing."
                        )
                    }
                )
            attrs["_three_way_match"] = match
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        validated_data.pop("status", None)
        validated_data.pop("_three_way_match", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(
                validated_data, "invoice_no", org, kind="invoice", model=VendorInvoice
            )
        po = validated_data.get("purchase_order")
        if po and not validated_data.get("amount"):
            validated_data["amount"] = po.amount or 0
        if po and not validated_data.get("description"):
            validated_data["description"] = f"AP from PO {po.po_no}"
        validated_data["status"] = "draft"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        validated_data.pop("_three_way_match", None)
        if instance.status == "paid":
            raise serializers.ValidationError(
                {"detail": "Paid invoices are locked. Post a credit note / adjustment instead."}
            )
        if instance.status not in ("draft", "rejected"):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot edit a {instance.status} invoice. "
                        "Use LoA actions or record payment."
                    )
                }
            )
        return super().update(instance, validated_data)


class CustomerInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    sales_order_no = serializers.CharField(
        source="sales_order.order_no", read_only=True, allow_null=True
    )
    net_receivable = serializers.SerializerMethodField()

    class Meta:
        model = CustomerInvoice
        fields = "__all__"
        read_only_fields = list(RO) + ["status", "fx_rate"]

    def get_net_receivable(self, obj):
        return float((obj.amount or 0) + (obj.tax_amount or 0))

    def validate_customer(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError("Customer not in this organization.")
        return value

    def validate(self, attrs):
        so = attrs.get("sales_order", getattr(self.instance, "sales_order", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if so is not None and customer and so.customer_id != customer.id:
            raise serializers.ValidationError(
                {"sales_order": "Sales order customer must match the invoice customer."}
            )
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        validated_data.pop("status", None)
        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        so = validated_data.get("sales_order")
        if so and not validated_data.get("amount"):
            validated_data["amount"] = so.amount or 0
        if so and not validated_data.get("tax_amount"):
            validated_data["tax_amount"] = so.tax_amount or 0
        if so and not validated_data.get("description"):
            validated_data["description"] = f"AR from SO {so.order_no}"
        if so and not (self.initial_data or {}).get("currency"):
            validated_data["currency"] = so.currency or "PKR"
        if org:
            ensure_doc_no(
                validated_data,
                "invoice_no",
                org,
                kind="ar_invoice",
                model=CustomerInvoice,
            )
        validated_data["status"] = "draft"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("status", None)
        if instance.status == "paid":
            raise serializers.ValidationError(
                {"detail": "Paid AR invoices are locked."}
            )
        if instance.status not in ("draft", "rejected"):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot edit a {instance.status} invoice. "
                        "Use LoA actions or record receipt."
                    )
                }
            )
        return super().update(instance, validated_data)


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = "__all__"
        read_only_fields = RO + ("last_reconciled",)

    def create(self, validated_data):
        if "current_balance" not in validated_data or validated_data.get(
            "current_balance"
        ) is None:
            validated_data["current_balance"] = validated_data.get(
                "opening_balance", 0
            )
        return super().create(validated_data)


def _sync_bank_from_reconciliation(recon: BankReconciliation) -> None:
    """Push statement balance / date onto the linked bank account after reconciling."""
    if recon.status not in (
        BankReconciliation.Status.MATCHED,
        BankReconciliation.Status.CLOSED,
    ):
        return
    bank = recon.bank_account
    bank.current_balance = recon.statement_balance
    bank.last_reconciled = recon.statement_date
    bank.save(update_fields=["current_balance", "last_reconciled", "updated_at"])


class BankReconciliationSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source="bank_account.name", read_only=True)
    bank_account_name = serializers.CharField(
        source="bank_account.name", read_only=True
    )
    bank_account_no = serializers.CharField(
        source="bank_account.account_no", read_only=True
    )
    bank_label = serializers.SerializerMethodField()

    class Meta:
        model = BankReconciliation
        fields = "__all__"
        read_only_fields = RO

    def get_bank_label(self, obj):
        ba = obj.bank_account
        if not ba:
            return ""
        return f"{ba.name} — {ba.bank_name} ({ba.account_no})"

    def validate_bank_account(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError(
                    "Bank account does not belong to this organization."
                )
            if getattr(value, "is_deleted", False):
                raise serializers.ValidationError("Bank account is deleted.")
            if not value.is_active:
                raise serializers.ValidationError("Bank account is inactive.")
        return value

    def create(self, validated_data):
        bank = validated_data.get("bank_account")
        if bank and not validated_data.get("book_balance"):
            validated_data["book_balance"] = (
                bank.current_balance
                if bank.current_balance is not None
                else bank.opening_balance
            )
        recon = super().create(validated_data)
        _sync_bank_from_reconciliation(recon)
        return recon

    def update(self, instance, validated_data):
        recon = super().update(instance, validated_data)
        _sync_bank_from_reconciliation(recon)
        return recon


class InvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = "__all__"
        read_only_fields = RO

    def validate(self, attrs):
        name = str(attrs.get("name", getattr(self.instance, "name", "")) or "").strip()
        kind = str(
            attrs.get("instrument_type", getattr(self.instance, "instrument_type", "")) or ""
        ).strip()
        errors = {}
        if not name:
            errors["name"] = "Enter a name."
        if not kind:
            errors["instrument_type"] = "Choose a kind."
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        maturity = attrs.get("maturity_date", getattr(self.instance, "maturity_date", None))
        if start and maturity and maturity < start:
            errors["maturity_date"] = "This date cannot be before the start date."
        if errors:
            raise serializers.ValidationError(errors)
        if "name" in attrs:
            attrs["name"] = name
        if "instrument_type" in attrs:
            attrs["instrument_type"] = kind
        return attrs


class FixedAssetSerializer(serializers.ModelSerializer):
    assigned_employee_name = serializers.SerializerMethodField()
    qr_payload = serializers.SerializerMethodField()
    qr_url = serializers.SerializerMethodField()
    open_repair_count = serializers.SerializerMethodField()

    class Meta:
        model = FixedAsset
        fields = "__all__"
        read_only_fields = RO

    def get_assigned_employee_name(self, obj):
        emp = obj.assigned_employee
        if not emp:
            return ""
        return f"{emp.employee_code} — {emp.full_name}"

    def _public_asset_path(self, obj):
        return f"/finance/assets/{obj.id}"

    def get_qr_payload(self, obj):
        """Stable sticker payload: org + asset code + deep link path."""
        return (
            f"SIERP-ASSET|{obj.organization_id}|{obj.asset_code}|"
            f"{self._public_asset_path(obj)}"
        )

    def get_qr_url(self, obj):
        request = self.context.get("request")
        path = self._public_asset_path(obj)
        if request:
            # Prefer absolute frontend-style path; API host used as fallback base.
            return request.build_absolute_uri(path)
        return path

    def get_open_repair_count(self, obj):
        annotated = getattr(obj, "_open_repair_count", None)
        if annotated is not None:
            return annotated
        return obj.repairs.exclude(
            status__in=(
                AssetRepair.Status.COMPLETED,
                AssetRepair.Status.CANCELLED,
            )
        ).count()

    def validate_assigned_employee(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError(
                    "Employee does not belong to this organization."
                )
            if getattr(value, "is_deleted", False):
                raise serializers.ValidationError("Employee is deleted.")
        return value

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(
                validated_data, "asset_code", org, kind="asset", model=FixedAsset
            )
        return super().create(validated_data)


class AssetRepairSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source="asset.asset_code", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = AssetRepair
        fields = "__all__"
        read_only_fields = RO

    def validate_asset(self, value):
        request = self.context.get("request")
        if request and value:
            from core.access import user_organization

            org = user_organization(request.user)
            if org and value.organization_id != org.id:
                raise serializers.ValidationError(
                    "Asset does not belong to this organization."
                )
            if getattr(value, "is_deleted", False):
                raise serializers.ValidationError("Asset is deleted.")
        return value

    def create(self, validated_data):
        asset = validated_data.get("asset")
        if asset and not validated_data.get("request_no"):
            validated_data["request_no"] = f"AR-{asset.asset_code}-{asset.repairs.count() + 1}"
        repair = super().create(validated_data)
        if (
            repair.asset_id
            and repair.status
            in (
                AssetRepair.Status.REQUESTED,
                AssetRepair.Status.APPROVED,
                AssetRepair.Status.IN_PROGRESS,
            )
            and repair.asset.status == FixedAsset.Status.ACTIVE
        ):
            repair.asset.status = FixedAsset.Status.IN_REPAIR
            repair.asset.save(update_fields=["status", "updated_at"])
        return repair

    def update(self, instance, validated_data):
        repair = super().update(instance, validated_data)
        asset = repair.asset
        if not asset:
            return repair
        open_statuses = (
            AssetRepair.Status.REQUESTED,
            AssetRepair.Status.APPROVED,
            AssetRepair.Status.IN_PROGRESS,
        )
        has_open = asset.repairs.filter(status__in=open_statuses).exists()
        if has_open and asset.status == FixedAsset.Status.ACTIVE:
            asset.status = FixedAsset.Status.IN_REPAIR
            asset.save(update_fields=["status", "updated_at"])
        elif (
            not has_open
            and asset.status == FixedAsset.Status.IN_REPAIR
            and repair.status
            in (AssetRepair.Status.COMPLETED, AssetRepair.Status.CANCELLED)
        ):
            asset.status = FixedAsset.Status.ACTIVE
            asset.save(update_fields=["status", "updated_at"])
        return repair


def _mnt_user_label(u):
    if not u:
        return ""
    return (u.get_full_name() or u.username or str(u.pk)).strip()


def _mnt_check_org(serializer, attrs):
    from core.access import user_organization

    request = serializer.context.get("request")
    org = user_organization(request.user) if request else None
    if not org:
        return
    asset = attrs.get("asset")
    if asset and (asset.organization_id != org.id or getattr(asset, "is_deleted", False)):
        raise serializers.ValidationError({"asset": "Invalid asset."})
    sch = attrs.get("pm_schedule")
    if sch and sch.organization_id != org.id:
        raise serializers.ValidationError({"pm_schedule": "Invalid PM schedule."})
    assignee = attrs.get("assigned_to")
    if assignee and user_organization(assignee) != org:
        raise serializers.ValidationError({"assigned_to": "Invalid user."})


class PmScheduleSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source="asset.asset_code", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.name", read_only=True, default="")
    is_due = serializers.SerializerMethodField()

    class Meta:
        model = PmSchedule
        fields = "__all__"
        read_only_fields = RO

    def get_is_due(self, obj):
        from datetime import date

        return bool(obj.active and obj.next_due and obj.next_due <= date.today())

    def validate_frequency_days(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError("Frequency must be at least 1 day.")
        return value

    def validate(self, attrs):
        _mnt_check_org(self, attrs)
        return attrs

    def create(self, validated_data):
        from datetime import date, timedelta

        if not validated_data.get("next_due"):
            base = validated_data.get("last_done") or date.today()
            validated_data["next_due"] = base + timedelta(
                days=validated_data.get("frequency_days") or 30
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from datetime import timedelta

        if "next_due" not in validated_data and (
            "last_done" in validated_data or "frequency_days" in validated_data
        ):
            base = validated_data.get("last_done", instance.last_done)
            if base:
                freq = validated_data.get("frequency_days", instance.frequency_days)
                validated_data["next_due"] = base + timedelta(days=freq)
        return super().update(instance, validated_data)


class MaintenanceWorkOrderSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source="asset.asset_code", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.name", read_only=True, default="")
    pm_schedule_title = serializers.CharField(
        source="pm_schedule.title", read_only=True, default=""
    )
    assigned_to_name = serializers.SerializerMethodField()
    parts = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceWorkOrder
        fields = "__all__"
        read_only_fields = RO
        extra_kwargs = {"mwo_no": {"required": False, "allow_blank": True}}

    def get_assigned_to_name(self, obj):
        return _mnt_user_label(obj.assigned_to)

    def get_parts(self, obj):
        return [
            {
                "id": p.id,
                "item": p.item_id,
                "item_sku": p.item.sku,
                "item_name": p.item.name,
                "warehouse": p.warehouse_id,
                "warehouse_code": p.warehouse.code if p.warehouse_id else "",
                "qty": str(p.qty),
                "unit_cost": str(p.unit_cost),
            }
            for p in obj.parts.select_related("item", "warehouse")
        ]

    def validate_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Cost cannot be negative.")
        return value

    def validate(self, attrs):
        _mnt_check_org(self, attrs)
        inst = self.instance
        status = attrs.get("status", inst.status if inst else None)
        if (
            status == MaintenanceWorkOrder.Status.DONE
            and not attrs.get("completed_date")
            and not (inst and inst.completed_date)
        ):
            from datetime import date

            attrs["completed_date"] = date.today()
        return attrs

    def create(self, validated_data):
        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = validated_data.get("organization") or (
            user_organization(request.user) if request else None
        )
        if org:
            ensure_doc_no(
                validated_data, "mwo_no", org, kind="mwo", model=MaintenanceWorkOrder
            )
        mwo = super().create(validated_data)
        if mwo.status == MaintenanceWorkOrder.Status.DONE and mwo.pm_schedule_id:
            from finance.maintenance import roll_schedule_forward

            roll_schedule_forward(mwo.pm_schedule, mwo.completed_date)
        return mwo

    def update(self, instance, validated_data):
        was_done = instance.status == MaintenanceWorkOrder.Status.DONE
        mwo = super().update(instance, validated_data)
        if (
            not was_done
            and mwo.status == MaintenanceWorkOrder.Status.DONE
            and mwo.pm_schedule_id
        ):
            from finance.maintenance import roll_schedule_forward

            roll_schedule_forward(mwo.pm_schedule, mwo.completed_date)
        return mwo


class TaxCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxCode
        fields = "__all__"
        read_only_fields = RO


class AssetDepreciationLineSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(
        source="asset.asset_code", read_only=True, default=""
    )

    class Meta:
        model = AssetDepreciationLine
        fields = "__all__"
        read_only_fields = RO


class AssetDepreciationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDepreciationRun
        fields = "__all__"
        read_only_fields = list(RO) + ["status", "posted_at"]


class EInvoiceSubmissionSerializer(serializers.ModelSerializer):
    invoice_no = serializers.CharField(source="ar_invoice.invoice_no", read_only=True)
    customer_name = serializers.CharField(
        source="ar_invoice.customer.name", read_only=True, default=""
    )

    class Meta:
        model = EInvoiceSubmission
        fields = "__all__"
        read_only_fields = list(RO) + [
            "fbr_status",
            "fbr_invoice_no",
            "provider_ref",
            "mode",
            "error_message",
            "payload_json",
            "response_json",
            "submitted_at",
        ]


class FbrInvoiceSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FbrInvoiceSubmission
        fields = "__all__"
        read_only_fields = RO


class FxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxRate
        fields = "__all__"
        read_only_fields = RO


class ChequeRegisterSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(
        source="bank_account.name", read_only=True, default=""
    )

    class Meta:
        model = ChequeRegister
        fields = "__all__"
        read_only_fields = list(RO) + [
            "cleared_date",
            "bounced_date",
            "bounce_reason",
            "gl_journal",
        ]


class IntercompanyPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntercompanyPartner
        fields = "__all__"
        read_only_fields = RO


class IntercompanyTxnSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source="partner.name", read_only=True, default="")
    partner_code = serializers.CharField(source="partner.code", read_only=True, default="")

    class Meta:
        model = IntercompanyTxn
        fields = "__all__"
        read_only_fields = list(RO) + ["status", "gl_journal"]
