import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0007_tier1_ops"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LotBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("batch_no", models.CharField(max_length=64)),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("qty", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lot_batches", to="ops.item")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lot_batches", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lot_batches", to="ops.warehouse")),
            ],
            options={
                "ordering": ["-id"],
                "unique_together": {("organization", "item", "batch_no", "warehouse")},
            },
        ),
        migrations.CreateModel(
            name="CustomerContract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=255)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("billing_frequency", models.CharField(choices=[("monthly", "Monthly"), ("quarterly", "Quarterly"), ("yearly", "Yearly")], default="monthly", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("next_bill_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("ended", "Ended")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ar_contracts", to="ops.customer")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_contracts", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.CreateModel(
            name="ItemLot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("lot_no", models.CharField(max_length=64)),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("qty_on_hand", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lots", to="ops.item")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="item_lots", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-id"],
                "unique_together": {("organization", "item", "lot_no")},
            },
        ),
        migrations.CreateModel(
            name="SerialNumber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("serial_no", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("available", "Available"), ("allocated", "Allocated"), ("sold", "Sold"), ("scrapped", "Scrapped")], default="available", max_length=20)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="serials", to="ops.item")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="serial_numbers", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="serials", to="ops.warehouse")),
            ],
            options={
                "ordering": ["-id"],
                "unique_together": {("organization", "serial_no")},
            },
        ),
    ]
