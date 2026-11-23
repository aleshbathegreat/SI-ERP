from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0009_account_types"),
        ("ops", "0004_enterprise_sales_procurement"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendor",
            name="city",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="vendor",
            name="code",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="vendor",
            name="contact_person",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="vendor",
            name="country",
            field=models.CharField(blank=True, default="Pakistan", max_length=80),
        ),
        migrations.AddField(
            model_name="vendor",
            name="credit_limit",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="vendor",
            name="currency",
            field=models.CharField(default="PKR", max_length=8),
        ),
        migrations.AddField(
            model_name="vendor",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="vendor",
            name="payment_terms_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="vendorinvoice",
            name="purchase_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vendor_invoices",
                to="ops.purchaseorder",
            ),
        ),
    ]
