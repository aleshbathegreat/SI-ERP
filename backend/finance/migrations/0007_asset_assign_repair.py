# Generated manually for fixed-asset assignment + repair tracking

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0006_bank_recon_sync"),
        ("hr", "0007_employee_tax_attendance_flags"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="fixedasset",
            name="assigned_employee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_assets",
                to="hr.employee",
            ),
        ),
        migrations.AlterField(
            model_name="fixedasset",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("in_repair", "In repair"),
                    ("idle", "Idle"),
                    ("disposed", "Disposed"),
                ],
                default="active",
                max_length=32,
            ),
        ),
        migrations.AlterModelOptions(
            name="fixedasset",
            options={"ordering": ["asset_code"]},
        ),
        migrations.CreateModel(
            name="AssetRepair",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("request_no", models.CharField(max_length=64)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("approved", "Approved"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="requested",
                        max_length=32,
                    ),
                ),
                ("requested_on", models.DateField(blank=True, null=True)),
                ("completed_on", models.DateField(blank=True, null=True)),
                (
                    "cost",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                ("vendor_name", models.CharField(blank=True, max_length=128)),
                ("notes", models.TextField(blank=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="repairs",
                        to="finance.fixedasset",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asset_repairs",
                        to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-requested_on", "-id"],
                "unique_together": {("organization", "request_no")},
            },
        ),
    ]
