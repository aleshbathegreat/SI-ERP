import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dms", "0004_document_workflow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="workflowdefinition",
            name="applies_to",
            field=models.CharField(
                choices=[
                    ("dms.documents", "Documents"),
                    ("finance.journals", "Journals"),
                    ("finance.budgets", "Budgets"),
                    ("finance.invoices", "Vendor invoices"),
                    ("sales.invoices", "Customer invoices"),
                    ("sales.orders", "Sales orders"),
                    ("procurement.requisitions", "Purchase requisitions"),
                    ("procurement.orders", "Purchase orders"),
                    ("hr.leaves", "Leave requests"),
                    ("hr.recruitment", "Recruitment"),
                    ("hr.performance", "Performance reviews"),
                    ("payroll.periods", "Payroll periods"),
                    ("payroll.loans", "Employee loans"),
                    ("projects.timesheets", "Timesheets"),
                ],
                default="dms.documents",
                max_length=64,
            ),
        ),
        migrations.CreateModel(
            name="WorkflowCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("module", models.CharField(max_length=64)),
                ("object_id", models.CharField(max_length=64)),
                ("entered_at", models.DateTimeField()),
                ("escalation_due_at", models.DateTimeField(blank=True, null=True)),
                ("escalated", models.BooleanField(default=False)),
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
                    "last_actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dms_workflow_cases_acted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dms_workflow_cases",
                        to="core.organization",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cases",
                        to="dms.workflowstate",
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
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cases",
                        to="dms.workflowdefinition",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.AddConstraint(
            model_name="workflowcase",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_deleted=False),
                fields=("organization", "module", "object_id"),
                name="uniq_open_workflow_case",
            ),
        ),
        migrations.AlterField(
            model_name="workflowhistory",
            name="document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workflow_history",
                to="dms.document",
            ),
        ),
        migrations.AddField(
            model_name="workflowhistory",
            name="case",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="history",
                to="dms.workflowcase",
            ),
        ),
    ]
