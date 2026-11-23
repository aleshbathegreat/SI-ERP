from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ops", "0003_order_lines_and_stock_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="city",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="customer",
            name="contact_person",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="customer",
            name="country",
            field=models.CharField(blank=True, default="Pakistan", max_length=80),
        ),
        migrations.AddField(
            model_name="customer",
            name="credit_limit",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="customer",
            name="currency",
            field=models.CharField(default="PKR", max_length=8),
        ),
        migrations.AddField(
            model_name="customer",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="customer",
            name="payment_terms_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="customer_po",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="expected_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="payment_terms_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="shipping_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sales_orders_submitted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="tax_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchase_orders_approved",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="payment_terms_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchase_orders_submitted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="tax_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="vendor_ref",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
