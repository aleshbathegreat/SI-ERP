from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0010_attendance_holidays_reconcile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="designation",
            name="grade",
            field=models.CharField(
                blank=True, default="", help_text="Band / grade (e.g. G5, M2)", max_length=32
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="employee",
            name="bank_iban",
            field=models.CharField(blank=True, default="", max_length=34),
        ),
        migrations.AddField(
            model_name="employee",
            name="bank_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="employee",
            name="contract_type",
            field=models.CharField(
                choices=[
                    ("permanent", "Permanent"),
                    ("contract", "Contract"),
                    ("intern", "Intern"),
                    ("consultant", "Consultant"),
                ],
                default="permanent",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employee",
            name="emergency_contact_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="employee",
            name="emergency_contact_phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="employee",
            name="eobi_number",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="employee",
            name="gender",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="employee",
            name="marital_status",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="employee",
            name="national_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="CNIC / Emirates ID / Iqama",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="employee",
            name="ntn",
            field=models.CharField(
                blank=True, default="", help_text="Tax NTN", max_length=32
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="work_location",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="accrual_method",
            field=models.CharField(
                choices=[
                    ("annual", "Annual (full / pro-rata on join)"),
                    ("monthly", "Monthly accrual"),
                    ("none", "Manual only"),
                ],
                default="annual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="exclude_holidays",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="exclude_weekends",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="gender_restriction",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional: male / female — blank = all",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="max_carry_forward",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Max days CF at year-end (0 = unlimited when CF allowed)",
                max_digits=6,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="is_half_day",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="SeparationChecklistItem",
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
                ("item_key", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=255)),
                ("is_done", models.BooleanField(default=False)),
                ("done_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
                ("sort", models.PositiveSmallIntegerField(default=100)),
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
                        related_name="separation_checklist_items",
                        to="core.organization",
                    ),
                ),
                (
                    "separation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checklist_items",
                        to="hr.separationrecord",
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
                "ordering": ["sort", "id"],
                "unique_together": {("separation", "item_key")},
            },
        ),
    ]
