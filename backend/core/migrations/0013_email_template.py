from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_organization_currency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=128)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("general", "General"),
                            ("workflow", "Workflow / Approvals"),
                            ("hr", "HR / ESS"),
                            ("finance", "Finance"),
                            ("payroll", "Payroll"),
                            ("billing", "Billing"),
                            ("sales", "Sales"),
                            ("procurement", "Procurement"),
                        ],
                        default="general",
                        max_length=32,
                    ),
                ),
                ("subject", models.CharField(max_length=255)),
                ("body_text", models.TextField(help_text="Plain text body. Use {{var}} placeholders.")),
                ("body_html", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
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
                        related_name="email_templates",
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
                "ordering": ["purpose", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
    ]
