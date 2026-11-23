import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0014_package_attendance_connectors"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("connector_key", models.CharField(db_index=True, max_length=64)),
                ("display_name", models.CharField(blank=True, max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("disconnected", "Not configured"),
                            ("configured", "Configured"),
                            ("active", "Active"),
                            ("error", "Error"),
                            ("disabled", "Disabled"),
                        ],
                        default="disconnected",
                        max_length=20,
                    ),
                ),
                ("is_enabled", models.BooleanField(default=False)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("secrets", models.JSONField(blank=True, default=dict)),
                ("last_tested_at", models.DateTimeField(blank=True, null=True)),
                ("last_test_ok", models.BooleanField(blank=True, null=True)),
                ("last_test_message", models.CharField(blank=True, default="", max_length=512)),
                ("last_error", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
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
                        related_name="integration_connections",
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
                "ordering": ["connector_key"],
                "unique_together": {("organization", "connector_key")},
            },
        ),
    ]
