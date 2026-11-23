import django.db.models.deletion
from django.db import migrations, models


def seed_units(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Unit = apps.get_model("ops", "UnitOfMeasure")
    Item = apps.get_model("ops", "Item")
    defaults = (
        ("ea", "Each", 10),
        ("pcs", "Pieces", 20),
        ("kg", "Kilogram", 30),
        ("g", "Gram", 40),
        ("l", "Litre", 50),
        ("ml", "Millilitre", 60),
        ("m", "Metre", 70),
        ("hr", "Hour", 80),
        ("day", "Day", 90),
        ("box", "Box", 100),
        ("pack", "Pack", 110),
        ("set", "Set", 120),
        ("ton", "Tonne", 130),
    )
    for org in Organization.objects.all():
        for code, name, sort in defaults:
            Unit.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "is_active": True, "sort": sort},
            )
        seen = set()
        for raw in Item.objects.filter(organization=org).values_list("unit", flat=True):
            code = str(raw or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            Unit.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"name": code, "is_active": True, "sort": 200},
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0014_qc_hold"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitOfMeasure",
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
                        related_name="units_of_measure",
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
        migrations.RunPython(seed_units, noop_reverse),
    ]
