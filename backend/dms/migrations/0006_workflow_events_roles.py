import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_role_soft_delete"),
        ("dms", "0005_workflow_cases"),
    ]

    operations = [
        migrations.AddField(
            model_name="workflowcase",
            name="context",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="workflowtransition",
            name="allowed_roles",
            field=models.ManyToManyField(
                blank=True, related_name="workflow_transitions", to="accounts.role"
            ),
        ),
        migrations.CreateModel(
            name="WorkflowTransitionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("event", models.CharField(choices=[
                    ("record.created", "Record created"),
                    ("record.updated", "Record updated"),
                    ("record.submitted", "Record submitted"),
                    ("record.approved", "Record approved"),
                    ("record.rejected", "Record rejected"),
                    ("record.posted", "Record posted"),
                ], max_length=40)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dms_workflow_transition_events", to="core.organization")),
                ("transition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trigger_events", to="dms.workflowtransition")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transition_events", to="dms.workflowdefinition")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="workflowtransitionevent",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_deleted=False),
                fields=("transition", "event"),
                name="uniq_workflow_transition_event",
            ),
        ),
        migrations.CreateModel(
            name="WorkflowTransitionField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=40)),
                ("label", models.CharField(max_length=80)),
                ("field_type", models.CharField(choices=[("text", "Text"), ("number", "Number"), ("date", "Date")], default="text", max_length=20)),
                ("required", models.BooleanField(default=False)),
                ("help_text", models.CharField(blank=True, default="", max_length=180)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dms_workflow_transition_fields", to="core.organization")),
                ("transition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="dms.workflowtransition")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transition_fields", to="dms.workflowdefinition")),
            ],
            options={"ordering": ["id"]},
        ),
    ]
