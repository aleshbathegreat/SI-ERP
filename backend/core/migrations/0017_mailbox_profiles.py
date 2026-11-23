from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_enterprise_packs"),
        ("crm", "0006_activity_external_events"),
        ("hr", "0014_alter_attendancedevice_connector_key"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantemailprofile",
            name="signature",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="owner_type",
            field=models.CharField(
                choices=[
                    ("shared", "Shared mailbox"),
                    ("user", "Full user"),
                    ("employee", "Employee"),
                ],
                default="shared",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="email_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="employee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="email_profiles",
                to="hr.employee",
            ),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="inbound",
            field=models.CharField(
                choices=[
                    ("none", "Send only"),
                    ("graph", "Microsoft 365 inbox"),
                    ("imap", "IMAP inbox"),
                ],
                default="none",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="imap_host",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="imap_port",
            field=models.PositiveIntegerField(default=993),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="imap_username",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="imap_password",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="tenantemailprofile",
            name="imap_use_ssl",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="tenantemailprofile",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("workflow", "Workflow / Approvals"),
                    ("hr", "HR / ESS"),
                    ("finance", "Finance"),
                    ("payroll", "Payroll"),
                    ("billing", "Billing"),
                    ("crm", "CRM"),
                ],
                default="general",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="MailMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("direction", models.CharField(choices=[("out", "Sent"), ("in", "Received")], max_length=8)),
                ("status", models.CharField(choices=[("sent", "Sent"), ("failed", "Failed"), ("received", "Received")], max_length=16)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                ("body", models.TextField(blank=True, default="")),
                ("from_email", models.EmailField(blank=True, default="", max_length=254)),
                ("to_emails", models.CharField(blank=True, default="", max_length=500)),
                ("message_id", models.CharField(blank=True, db_index=True, default="", max_length=255)),
                ("error", models.TextField(blank=True, default="")),
                ("occurred_at", models.DateTimeField(blank=True, null=True)),
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
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
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
                        related_name="mail_messages",
                        to="core.organization",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="core.tenantemailprofile",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mail_messages",
                        to="crm.lead",
                    ),
                ),
                (
                    "opportunity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mail_messages",
                        to="crm.opportunity",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.AddConstraint(
            model_name="mailmessage",
            constraint=models.UniqueConstraint(
                condition=~models.Q(("message_id", "")),
                fields=("organization", "message_id"),
                name="uniq_org_mail_message_id",
            ),
        ),
    ]
