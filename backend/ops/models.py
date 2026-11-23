from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from core.models import AuditModel, Organization
from finance.models import Vendor


class Customer(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="customers"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    ntn = models.CharField(max_length=32, blank=True, default="")
    address = models.TextField(blank=True, default="")
    contact_person = models.CharField(max_length=120, blank=True, default="")
    payment_terms_days = models.PositiveIntegerField(default=30)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=80, blank=True, default="Pakistan")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} · {self.name}"


class Warehouse(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="warehouses"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default and not self.is_deleted:
            Warehouse.objects.filter(organization_id=self.organization_id, is_deleted=False).exclude(
                pk=self.pk
            ).update(is_default=False)


class UnitOfMeasure(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="units_of_measure"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    sort = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["sort", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


DEFAULT_UNITS = (
    ("ea", "Each", 10),
    ("pcs", "Pieces", 20),
    ("kg", "Kilogram", 30),
    ("g", "Gram", 40),
    ("l", "Litre", 50),
    ("ml", "Millilitre", 60),
    ("m", "Metre", 70),
    ("hr", "Hour", 80),
    ("day", "Day", 90),
    ("box", "Box", 100),
    ("pack", "Pack", 110),
    ("set", "Set", 120),
    ("ton", "Tonne", 130),
)


class Item(AuditModel):
    class ItemType(models.TextChoices):
        STOCKABLE = "stockable", "Stockable"
        CONSUMABLE = "consumable", "Consumable"
        SERVICE = "service", "Service"

    class Valuation(models.TextChoices):
        AVERAGE = "average", "Average cost"
        FIFO = "fifo", "FIFO"
        STANDARD = "standard", "Standard cost"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="inventory_items"
    )
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=64, blank=True, default="")
    category = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    unit = models.CharField(max_length=32, default="ea")
    item_type = models.CharField(
        max_length=20, choices=ItemType.choices, default=ItemType.STOCKABLE
    )
    valuation_method = models.CharField(
        max_length=20, choices=Valuation.choices, default=Valuation.AVERAGE
    )
    default_warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_items",
    )
    qty_on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    max_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sales_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "sku")
        ordering = ["sku"]

    def __str__(self):
        return f"{self.sku} · {self.name}"


def ensure_default_units(organization) -> list[str]:
    created = []
    for code, name, sort in DEFAULT_UNITS:
        if UnitOfMeasure.all_objects.filter(organization=organization, code=code).exists():
            continue
        UnitOfMeasure.objects.create(
            organization=organization,
            code=code,
            name=name,
            is_active=True,
            sort=sort,
        )
        created.append(code)
    for raw in (
        Item.objects.filter(organization=organization)
        .values_list("unit", flat=True)
        .distinct()
    ):
        code = str(raw or "").strip()
        if not code or UnitOfMeasure.all_objects.filter(organization=organization, code=code).exists():
            continue
        UnitOfMeasure.objects.create(
            organization=organization,
            code=code,
            name=code,
            is_active=True,
            sort=200,
        )
        created.append(code)
    return created


class StockLevel(AuditModel):
    """On-hand quantity of an item in a warehouse."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_levels"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="stock_levels"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_levels")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_qc_hold = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        help_text="Quantity received but not available until QC releases it.",
    )

    class Meta:
        unique_together = ("warehouse", "item")
        ordering = ["warehouse__code", "item__sku"]

    def __str__(self):
        return f"{self.warehouse.code}/{self.item.sku}: {self.qty}"


class StockMovement(AuditModel):
    class Reason(models.TextChoices):
        RECEIPT = "receipt", "Goods receipt"
        ISSUE = "issue", "Issue / consumption"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN = "return", "Return"
        TRANSFER = "transfer", "Warehouse transfer"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_movements"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="inbound_transfers",
    )
    purchase_order = models.ForeignKey(
        "PurchaseOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    sales_order = models.ForeignKey(
        "SalesOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    movement_date = models.DateField()
    qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Positive = inbound, negative = outbound; transfers use positive qty",
    )
    reason = models.CharField(
        max_length=20, choices=Reason.choices, default=Reason.ADJUSTMENT
    )
    reference = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    lot = models.ForeignKey(
        "LotBatch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )
    batch_no = models.CharField(max_length=64, blank=True, default="")
    serial = models.ForeignKey(
        "SerialNumber",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )

    class Meta:
        ordering = ["-movement_date", "-id"]

    def _apply_trace(self):
        """Best-effort update of lot qty / serial status after a movement posts."""
        qty = self.qty or Decimal("0")
        if self.lot_id:
            lot = LotBatch.objects.select_for_update().filter(pk=self.lot_id).first()
            if lot:
                if self.reason == self.Reason.TRANSFER and self.to_warehouse_id:
                    amount = abs(qty)
                    lot.qty = (lot.qty or Decimal("0")) - amount
                    lot.save(update_fields=["qty", "updated_at"])
                    dest, _ = LotBatch.objects.select_for_update().get_or_create(
                        organization_id=self.organization_id,
                        item_id=self.item_id,
                        batch_no=lot.batch_no,
                        warehouse_id=self.to_warehouse_id,
                        defaults={"expiry_date": lot.expiry_date, "qty": Decimal("0")},
                    )
                    dest.qty = (dest.qty or Decimal("0")) + amount
                    dest.save(update_fields=["qty", "updated_at"])
                else:
                    lot.qty = (lot.qty or Decimal("0")) + qty
                    lot.save(update_fields=["qty", "updated_at"])
        if self.serial_id:
            sn = SerialNumber.objects.select_for_update().filter(pk=self.serial_id).first()
            if sn:
                if self.reason == self.Reason.TRANSFER and self.to_warehouse_id:
                    sn.warehouse_id = self.to_warehouse_id
                    sn.save(update_fields=["warehouse", "updated_at"])
                elif qty > 0:
                    sn.status = SerialNumber.Status.AVAILABLE
                    sn.warehouse_id = self.warehouse_id or sn.warehouse_id
                    sn.save(update_fields=["status", "warehouse", "updated_at"])
                else:
                    sn.status = SerialNumber.Status.ISSUED
                    sn.save(update_fields=["status", "updated_at"])

    @staticmethod
    def _adjust_level(org_id, warehouse_id, item_id, delta, user=None):
        level, _ = StockLevel.objects.select_for_update().get_or_create(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            item_id=item_id,
            defaults={"qty": Decimal("0")},
        )
        level.qty = (level.qty or Decimal("0")) + delta
        level.save(update_fields=["qty", "updated_at"])
        return level

    def apply_to_item(self):
        item = Item.objects.select_for_update().get(pk=self.item_id)
        qty = self.qty or Decimal("0")

        if self.reason == self.Reason.TRANSFER:
            if not self.warehouse_id or not self.to_warehouse_id:
                raise ValueError("Transfer requires source and destination warehouse.")
            if self.warehouse_id == self.to_warehouse_id:
                raise ValueError("Source and destination warehouse must differ.")
            amount = abs(qty)
            self._adjust_level(
                self.organization_id, self.warehouse_id, self.item_id, -amount
            )
            self._adjust_level(
                self.organization_id, self.to_warehouse_id, self.item_id, amount
            )
            # Org total unchanged for warehouse transfers
            self._apply_trace()
            return

        if self.warehouse_id:
            self._adjust_level(
                self.organization_id, self.warehouse_id, self.item_id, qty
            )

        if item.item_type != Item.ItemType.SERVICE:
            item.qty_on_hand = (item.qty_on_hand or Decimal("0")) + qty
            item.save(update_fields=["qty_on_hand", "updated_at"])
        self._apply_trace()


class SalesOrder(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        DELIVERED = "delivered", "Delivered"
        INVOICED = "invoiced", "Invoiced"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_orders"
    )
    order_no = models.CharField(max_length=64)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_orders",
    )
    order_date = models.DateField()
    expected_date = models.DateField(null=True, blank=True)
    customer_po = models.CharField(max_length=64, blank=True, default="")
    payment_terms_days = models.PositiveIntegerField(default=30)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True, default="")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_orders_submitted",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_orders",
    )

    class Meta:
        unique_together = ("organization", "order_no")
        ordering = ["-order_date", "-id"]

    @property
    def subtotal(self):
        total = Decimal("0")
        for line in self.lines.all():
            total += (line.qty or Decimal("0")) * (line.unit_price or Decimal("0"))
        return total.quantize(Decimal("0.01"))

    def recompute_amount(self):
        sub = self.subtotal
        disc = self.discount_amount or Decimal("0")
        tax = self.tax_amount or Decimal("0")
        self.amount = (sub - disc + tax).quantize(Decimal("0.01"))
        self.save(update_fields=["amount", "updated_at"])


class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="sales_order_lines"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    qty_delivered = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_order_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class PurchaseOrder(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="purchase_orders"
    )
    po_no = models.CharField(max_length=64)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders",
    )
    order_date = models.DateField()
    expected_date = models.DateField(null=True, blank=True)
    vendor_ref = models.CharField(max_length=64, blank=True, default="")
    payment_terms_days = models.PositiveIntegerField(default=30)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders_submitted",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders_approved",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders",
    )

    class Meta:
        unique_together = ("organization", "po_no")
        ordering = ["-order_date", "-id"]

    @property
    def subtotal(self):
        total = Decimal("0")
        for line in self.lines.all():
            total += (line.qty or Decimal("0")) * (line.unit_price or Decimal("0"))
        return total.quantize(Decimal("0.01"))

    def recompute_amount(self):
        sub = self.subtotal
        disc = self.discount_amount or Decimal("0")
        tax = self.tax_amount or Decimal("0")
        self.amount = (sub - disc + tax).quantize(Decimal("0.01"))
        self.save(update_fields=["amount", "updated_at"])


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="purchase_order_lines"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    qty_received = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_order_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class SalesQuotation(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        CONVERTED = "converted", "Converted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_quotations"
    )
    quote_no = models.CharField(max_length=64)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="quotations"
    )
    quote_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=30)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    sales_order = models.ForeignKey(
        SalesOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_quotations",
    )
    opportunity = models.ForeignKey(
        "crm.Opportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quotations",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_quotations",
    )

    class Meta:
        unique_together = ("organization", "quote_no")
        ordering = ["-quote_date", "-id"]

    @property
    def subtotal(self):
        total = Decimal("0")
        for line in self.lines.all():
            total += (line.qty or Decimal("0")) * (line.unit_price or Decimal("0"))
        return total.quantize(Decimal("0.01"))

    def recompute_amount(self):
        sub = self.subtotal
        disc = self.discount_amount or Decimal("0")
        tax = self.tax_amount or Decimal("0")
        self.amount = (sub - disc + tax).quantize(Decimal("0.01"))
        self.save(update_fields=["amount", "updated_at"])


class SalesQuotationLine(models.Model):
    quotation = models.ForeignKey(
        SalesQuotation, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="quotation_lines"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class GoodsReceipt(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    class QcStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="goods_receipts"
    )
    grn_no = models.CharField(max_length=64)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts"
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="goods_receipts"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="goods_receipts",
    )
    receipt_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.POSTED
    )
    qc_status = models.CharField(
        max_length=20, choices=QcStatus.choices, default=QcStatus.PENDING
    )
    notes = models.TextField(blank=True, default="")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="goods_receipts_received",
    )

    class Meta:
        unique_together = ("organization", "grn_no")
        ordering = ["-receipt_date", "-id"]


class GoodsReceiptLine(models.Model):
    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE, related_name="lines"
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grn_lines",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="grn_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_on_hold = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grn_lines",
    )
    stock_movement = models.ForeignKey(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grn_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class PurchaseRequisition(AuditModel):
    """Internal demand document — approve then convert to PO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        CONVERTED = "converted", "Converted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="purchase_requisitions"
    )
    pr_no = models.CharField(max_length=64)
    request_date = models.DateField()
    required_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=120, blank=True, default="")
    preferred_vendor = models.ForeignKey(
        Vendor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_requisitions",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_requisitions",
    )
    currency = models.CharField(max_length=8, default="PKR")
    estimated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    purchase_order = models.ForeignKey(
        "PurchaseOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_requisitions",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_requisitions_requested",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_requisitions_submitted",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_requisitions_approved",
    )

    class Meta:
        unique_together = ("organization", "pr_no")
        ordering = ["-request_date", "-id"]

    @property
    def subtotal(self):
        total = Decimal("0")
        for line in self.lines.all():
            total += (line.qty or Decimal("0")) * (line.unit_price or Decimal("0"))
        return total.quantize(Decimal("0.01"))

    def recompute_amount(self):
        self.estimated_amount = self.subtotal
        self.save(update_fields=["estimated_amount", "updated_at"])


class PurchaseRequisitionLine(models.Model):
    requisition = models.ForeignKey(
        PurchaseRequisition, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="pr_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class DeliveryNote(AuditModel):
    """Formal outbound dispatch document against a sales order."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="delivery_notes"
    )
    dn_no = models.CharField(max_length=64)
    sales_order = models.ForeignKey(
        SalesOrder, on_delete=models.PROTECT, related_name="delivery_notes"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="delivery_notes"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_notes",
    )
    delivery_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.POSTED
    )
    notes = models.TextField(blank=True, default="")
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_notes_delivered",
    )

    class Meta:
        unique_together = ("organization", "dn_no")
        ordering = ["-delivery_date", "-id"]


class DeliveryNoteLine(models.Model):
    delivery_note = models.ForeignKey(
        DeliveryNote, on_delete=models.CASCADE, related_name="lines"
    )
    sales_order_line = models.ForeignKey(
        SalesOrderLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dn_lines",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="dn_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dn_lines",
    )
    stock_movement = models.ForeignKey(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dn_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))

class VendorRFQ(AuditModel):
    """Request for quotation to vendors — award creates a draft PO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        AWARDED = "awarded", "Awarded"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vendor_rfqs"
    )
    rfq_no = models.CharField(max_length=64)
    rfq_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendor_rfqs",
    )
    currency = models.CharField(max_length=8, default="PKR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    awarded_vendor = models.ForeignKey(
        Vendor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="awarded_rfqs",
    )
    purchase_order = models.ForeignKey(
        "PurchaseOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_rfqs",
    )

    class Meta:
        unique_together = ("organization", "rfq_no")
        ordering = ["-rfq_date", "-id"]


class VendorRFQLine(models.Model):
    rfq = models.ForeignKey(VendorRFQ, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="rfq_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)

    @property
    def line_total(self):
        return Decimal("0")


class VendorRFQQuote(AuditModel):
    """A vendor's bid against an RFQ."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vendor_rfq_quotes"
    )
    rfq = models.ForeignKey(VendorRFQ, on_delete=models.CASCADE, related_name="quotes")
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="rfq_quotes"
    )
    quote_date = models.DateField()
    notes = models.TextField(blank=True, default="")
    is_winning = models.BooleanField(default=False)

    class Meta:
        unique_together = ("rfq", "vendor")
        ordering = ["-quote_date", "-id"]


class VendorRFQQuoteLine(models.Model):
    quote = models.ForeignKey(
        VendorRFQQuote, on_delete=models.CASCADE, related_name="lines"
    )
    rfq_line = models.ForeignKey(
        VendorRFQLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quote_lines",
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="rfq_quote_lines"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class SalesReturn(AuditModel):
    """RMA / customer return — posts credit stock receipt."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_returns"
    )
    rma_no = models.CharField(max_length=64)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="sales_returns"
    )
    sales_order = models.ForeignKey(
        SalesOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_returns",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_returns",
    )
    return_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    # Optional link for a future AR credit note
    ar_credit_invoice = models.ForeignKey(
        "finance.CustomerInvoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_returns",
    )

    class Meta:
        unique_together = ("organization", "rma_no")
        ordering = ["-return_date", "-id"]


class SalesReturnLine(models.Model):
    sales_return = models.ForeignKey(
        SalesReturn, on_delete=models.CASCADE, related_name="lines"
    )
    sales_order_line = models.ForeignKey(
        SalesOrderLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="return_lines",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="sales_return_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_return_lines",
    )
    stock_movement = models.ForeignKey(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_return_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class PurchaseReturn(AuditModel):
    """Vendor return — issues stock out."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="purchase_returns"
    )
    pret_no = models.CharField(max_length=64)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="purchase_returns"
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_returns",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_returns",
    )
    return_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    ap_credit_invoice = models.ForeignKey(
        "finance.VendorInvoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_returns",
    )

    class Meta:
        unique_together = ("organization", "pret_no")
        ordering = ["-return_date", "-id"]


class PurchaseReturnLine(models.Model):
    purchase_return = models.ForeignKey(
        PurchaseReturn, on_delete=models.CASCADE, related_name="lines"
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="return_lines",
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="purchase_return_lines"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_return_lines",
    )
    stock_movement = models.ForeignKey(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_return_lines",
    )

    @property
    def line_total(self):
        return (self.qty or Decimal("0")) * (self.unit_price or Decimal("0"))


class PriceList(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="price_lists"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="price_lists",
    )
    currency = models.CharField(max_length=8, default="PKR")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]


class PriceListItem(models.Model):
    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name="items"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="price_list_items")
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("price_list", "item")


class Stocktake(AuditModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stocktakes"
    )
    st_no = models.CharField(max_length=64)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="stocktakes"
    )
    count_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("organization", "st_no")
        ordering = ["-count_date", "-id"]


class StocktakeLine(models.Model):
    stocktake = models.ForeignKey(
        Stocktake, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="stocktake_lines")
    system_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    counted_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    stock_movement = models.ForeignKey(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stocktake_lines",
    )

    @property
    def variance(self):
        return (self.counted_qty or Decimal("0")) - (self.system_qty or Decimal("0"))


class LandedCost(AuditModel):
    """Freight/duty allocation into GRN item unit costs."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="landed_costs"
    )
    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.PROTECT, related_name="landed_costs"
    )
    freight_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    duty_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    @property
    def total_charges(self):
        return (
            (self.freight_amount or Decimal("0"))
            + (self.duty_amount or Decimal("0"))
            + (self.other_amount or Decimal("0"))
        ).quantize(Decimal("0.01"))


class LotBatch(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="lot_batches"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="lot_batches")
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lot_batches",
    )
    batch_no = models.CharField(max_length=64)
    expiry_date = models.DateField(null=True, blank=True)
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        unique_together = ("organization", "item", "batch_no", "warehouse")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.batch_no} · {self.item_id}"


class CustomerContract(AuditModel):
    class BillingFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="customer_contracts"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="ar_contracts"
    )
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    billing_frequency = models.CharField(
        max_length=20,
        choices=BillingFrequency.choices,
        default=BillingFrequency.MONTHLY,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    next_bill_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class ItemLot(AuditModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="item_lots"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="lots")
    lot_no = models.CharField(max_length=64)
    expiry_date = models.DateField(null=True, blank=True)
    qty_on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        unique_together = ("organization", "item", "lot_no")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.lot_no} · {self.item_id}"


class SerialNumber(AuditModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ISSUED = "issued", "Issued"
        SCRAPPED = "scrapped", "Scrapped"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="serial_numbers"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="serials")
    serial_no = models.CharField(max_length=128)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="serials",
    )

    class Meta:
        unique_together = ("organization", "item", "serial_no")
        ordering = ["serial_no"]

    def __str__(self):
        return self.serial_no


class WarehouseBin(AuditModel):
    """Storage location (bin) inside a warehouse (WMS lite)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="warehouse_bins"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="bins"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255, blank=True, default="")
    aisle = models.CharField(max_length=32, blank=True, default="")
    rack = models.CharField(max_length=32, blank=True, default="")
    level = models.CharField(max_length=32, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("warehouse", "code")
        ordering = ["warehouse__code", "code"]

    def __str__(self):
        return f"{self.warehouse.code}/{self.code}"


class StockLevelBin(AuditModel):
    """Bin-level split of a warehouse StockLevel (sub-ledger; warehouse total stays on StockLevel)."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_level_bins"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="bin_stock"
    )
    bin = models.ForeignKey(
        WarehouseBin,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stock",
        help_text="Null = unassigned / default location",
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bin_stock")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        unique_together = ("warehouse", "item", "bin")
        ordering = ["warehouse__code", "item__sku"]

    def __str__(self):
        return f"{self.warehouse.code}/{self.bin.code if self.bin_id else '-'}/{self.item.sku}: {self.qty}"


class PickList(AuditModel):
    """Warehouse pick document created from a sales order or delivery note."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PICKING = "picking", "Picking"
        DONE = "done", "Done"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="pick_lists"
    )
    pick_no = models.CharField(max_length=64)
    sales_order = models.ForeignKey(
        SalesOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pick_lists",
    )
    delivery_note = models.ForeignKey(
        DeliveryNote,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pick_lists",
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="pick_lists"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    picked_at = models.DateTimeField(null=True, blank=True)
    picked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pick_lists_picked",
    )

    class Meta:
        unique_together = ("organization", "pick_no")
        ordering = ["-id"]

    def __str__(self):
        return self.pick_no


class PickListLine(models.Model):
    pick_list = models.ForeignKey(
        PickList, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="pick_lines")
    sales_order_line = models.ForeignKey(
        SalesOrderLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pick_lines",
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    bin = models.ForeignKey(
        WarehouseBin,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pick_lines",
    )
    picked_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        ordering = ["id"]
