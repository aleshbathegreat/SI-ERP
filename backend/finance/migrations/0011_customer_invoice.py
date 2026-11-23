import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finance", "0010_vendor_enterprise_po_link"),
        ("ops", "0005_quotes_and_grn"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerInvoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("invoice_no", models.CharField(max_length=64)),
                ("invoice_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("paid", "Paid"), ("rejected", "Rejected")], default="draft", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("payment_ref", models.CharField(blank=True, default="", max_length=64)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ar_invoices", to="ops.customer")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_invoices", to="core.organization")),
                ("sales_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_invoices", to="ops.salesorder")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-invoice_date"], "unique_together": {("organization", "invoice_no")}},
        ),
    ]
