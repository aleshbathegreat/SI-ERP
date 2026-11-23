from django.db import migrations, models
import django.db.models.deletion


def seed_account_types(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    AccountType = apps.get_model("finance", "AccountType")
    defaults = (
        ("asset", "Asset", "asset", 10),
        ("liability", "Liability", "liability", 20),
        ("equity", "Equity", "equity", 30),
        ("income", "Income", "income", 40),
        ("expense", "Expense", "expense", 50),
    )
    for org in Organization.objects.all():
        for code, name, stmt, sort in defaults:
            AccountType.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "statement_class": stmt,
                    "is_system": True,
                    "is_active": True,
                    "sort": sort,
                },
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_package_attendance_connectors"),
        ("finance", "0008_bank_gl_and_automation"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountType",
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
                ("code", models.CharField(max_length=32)),
                ("name", models.CharField(max_length=128)),
                (
                    "statement_class",
                    models.CharField(
                        choices=[
                            ("asset", "Asset (Balance sheet)"),
                            ("liability", "Liability (Balance sheet)"),
                            ("equity", "Equity (Balance sheet)"),
                            ("income", "Income (P&L)"),
                            ("expense", "Expense (P&L)"),
                        ],
                        default="expense",
                        help_text="Drives TB / P&L / BS bucketing",
                        max_length=20,
                    ),
                ),
                (
                    "is_system",
                    models.BooleanField(
                        default=False, help_text="Seeded classic types — code locked"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort", models.PositiveSmallIntegerField(default=100)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to="auth.user",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_types",
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
                        to="auth.user",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "ordering": ["sort", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
        migrations.AlterField(
            model_name="account",
            name="account_type",
            field=models.CharField(default="expense", max_length=32),
        ),
        migrations.RunPython(seed_account_types, noop_reverse),
    ]
