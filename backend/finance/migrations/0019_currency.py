import django.db.models.deletion
from django.db import migrations, models


def seed_currencies(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Currency = apps.get_model("finance", "Currency")
    defaults = (
        ("PKR", "Pakistani Rupee", 10),
        ("USD", "US Dollar", 20),
        ("EUR", "Euro", 30),
        ("GBP", "British Pound", 40),
        ("AED", "UAE Dirham", 50),
        ("SAR", "Saudi Riyal", 60),
        ("CNY", "Chinese Yuan", 70),
        ("INR", "Indian Rupee", 80),
    )
    for org in Organization.objects.all():
        for code, name, sort in defaults:
            Currency.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "is_active": True, "sort": sort},
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0018_maintenance_parts"),
    ]

    operations = [
        migrations.CreateModel(
            name="Currency",
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
                ("code", models.CharField(max_length=8)),
                ("name", models.CharField(max_length=128)),
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
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to="auth.user",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="currencies",
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
            ],
            options={
                "ordering": ["sort", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
        migrations.RunPython(seed_currencies, noop_reverse),
    ]
