import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ops", "0004_enterprise_sales_procurement"),
        ("finance", "0010_vendor_enterprise_po_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalesQuotation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("quote_no", models.CharField(max_length=64)),
                ("quote_date", models.DateField()),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("payment_terms_days", models.PositiveIntegerField(default=30)),
                ("discount_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("currency", models.CharField(default="PKR", max_length=8)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("converted", "Converted"), ("expired", "Expired"), ("cancelled", "Cancelled")], default="draft", max_length=20)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotations", to="ops.customer")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sales_quotations", to="core.organization")),
                ("sales_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_quotations", to="ops.salesorder")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-quote_date", "-id"], "unique_together": {("organization", "quote_no")}},
        ),
        migrations.CreateModel(
            name="SalesQuotationLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=1, max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotation_lines", to="ops.item")),
                ("quotation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="ops.salesquotation")),
            ],
        ),
        migrations.CreateModel(
            name="GoodsReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("grn_no", models.CharField(max_length=64)),
                ("receipt_date", models.DateField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")], default="posted", max_length=20)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="goods_receipts", to="core.organization")),
                ("purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="goods_receipts", to="ops.purchaseorder")),
                ("received_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="goods_receipts_received", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="goods_receipts", to="finance.vendor")),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="goods_receipts", to="ops.warehouse")),
            ],
            options={"ordering": ["-receipt_date", "-id"], "unique_together": {("organization", "grn_no")}},
        ),
        migrations.CreateModel(
            name="GoodsReceiptLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("goods_receipt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="ops.goodsreceipt")),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="grn_lines", to="ops.item")),
                ("purchase_order_line", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="grn_lines", to="ops.purchaseorderline")),
                ("stock_movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="grn_lines", to="ops.stockmovement")),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="grn_lines", to="ops.warehouse")),
            ],
        ),
    ]
