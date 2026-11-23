import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ops", "0005_quotes_and_grn"),
        ("finance", "0011_customer_invoice"),
    ]

    operations = [
        migrations.CreateModel(
            name="PurchaseRequisition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("pr_no", models.CharField(max_length=64)),
                ("request_date", models.DateField()),
                ("required_date", models.DateField(blank=True, null=True)),
                ("department", models.CharField(blank=True, default="", max_length=120)),
                ("currency", models.CharField(default="PKR", max_length=8)),
                ("estimated_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("converted", "Converted"), ("cancelled", "Cancelled")], default="draft", max_length=20)),
                ("notes", models.TextField(blank=True, default="")),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_requisitions_approved", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchase_requisitions", to="core.organization")),
                ("preferred_vendor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_requisitions", to="finance.vendor")),
                ("purchase_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_requisitions", to="ops.purchaseorder")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_requisitions_requested", to=settings.AUTH_USER_MODEL)),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_requisitions_submitted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_requisitions", to="ops.warehouse")),
            ],
            options={"ordering": ["-request_date", "-id"]},
        ),
        migrations.CreateModel(
            name="PurchaseRequisitionLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=Decimal("1"), max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pr_lines", to="ops.item")),
                ("requisition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="ops.purchaserequisition")),
            ],
        ),
        migrations.CreateModel(
            name="DeliveryNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("dn_no", models.CharField(max_length=64)),
                ("delivery_date", models.DateField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")], default="posted", max_length=20)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="delivery_notes", to="ops.customer")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("delivered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="delivery_notes_delivered", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="delivery_notes", to="core.organization")),
                ("sales_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="delivery_notes", to="ops.salesorder")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="delivery_notes", to="ops.warehouse")),
            ],
            options={"ordering": ["-delivery_date", "-id"]},
        ),
        migrations.CreateModel(
            name="DeliveryNoteLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("delivery_note", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="ops.deliverynote")),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dn_lines", to="ops.item")),
                ("sales_order_line", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dn_lines", to="ops.salesorderline")),
                ("stock_movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dn_lines", to="ops.stockmovement")),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dn_lines", to="ops.warehouse")),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="purchaserequisition",
            unique_together={("organization", "pr_no")},
        ),
        migrations.AlterUniqueTogether(
            name="deliverynote",
            unique_together={("organization", "dn_no")},
        ),
    ]
