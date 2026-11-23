from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0005_activity_calendar"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="external_events",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
