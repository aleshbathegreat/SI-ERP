import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0007_tenant_branding_assets"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="grace_days",
            field=models.PositiveIntegerField(
                default=7,
                help_text="Days after trial/subscription end before hard lock (past_due → canceled)",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="last_dunning_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="SaaSInvoice",
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
                ("invoice_no", models.CharField(max_length=32, unique=True)),
                ("plan_code", models.CharField(blank=True, default="", max_length=32)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                (
                    "amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "tax_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "total",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                ("currency", models.CharField(default="PKR", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("sent", "Sent"),
                            ("paid", "Paid"),
                            ("overdue", "Overdue"),
                            ("void", "Void"),
                        ],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("issue_date", models.DateField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saas_invoices_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saas_invoices",
                        to="core.organization",
                    ),
                ),
                (
                    "package",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invoices",
                        to="core.subscriptionpackage",
                    ),
                ),
                (
                    "payment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invoices",
                        to="core.subscriptionpayment",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="SupportTicket",
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
                ("ticket_no", models.CharField(max_length=32, unique=True)),
                ("subject", models.CharField(max_length=200)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("billing", "Billing"),
                            ("technical", "Technical"),
                            ("sales", "Sales"),
                            ("general", "General"),
                        ],
                        default="general",
                        max_length=16,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("normal", "Normal"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="normal",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("in_progress", "In progress"),
                            ("waiting", "Waiting on tenant"),
                            ("resolved", "Resolved"),
                            ("closed", "Closed"),
                        ],
                        default="open",
                        max_length=16,
                    ),
                ),
                ("last_message_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assignee",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tickets_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tickets_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_tickets",
                        to="core.organization",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.CreateModel(
            name="SupportTicketMessage",
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
                ("body", models.TextField()),
                (
                    "is_internal",
                    models.BooleanField(
                        default=False,
                        help_text="Internal platform note — hidden from tenant users",
                    ),
                ),
                ("is_from_platform", models.BooleanField(default=False)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ticket_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="core.supportticket",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="PlatformStaff",
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
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("owner", "Platform owner"),
                            ("finance", "Finance team"),
                            ("sales", "Sales team"),
                            ("support", "Support team"),
                            ("technical", "Technical team"),
                        ],
                        default="support",
                        max_length=16,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("title", models.CharField(blank=True, default="", max_length=128)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="platform_staff",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["role", "user__username"]},
        ),
    ]
