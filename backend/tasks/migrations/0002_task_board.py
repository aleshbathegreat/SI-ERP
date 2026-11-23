from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_tasks"),
    ]

    operations = [
        migrations.AddField(
            model_name="worktask",
            name="checklist",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="worktask",
            name="due_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="worktask",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Low"),
                    ("medium", "Medium"),
                    ("high", "High"),
                    ("urgent", "Urgent"),
                ],
                default="medium",
                max_length=8,
            ),
        ),
        migrations.AlterField(
            model_name="worktask",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "To do"),
                    ("in_progress", "In progress"),
                    ("in_review", "In review"),
                    ("done", "Done"),
                ],
                default="open",
                max_length=12,
            ),
        ),
    ]
