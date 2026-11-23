from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0004_pipeline_board"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="starts_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="activity",
            name="ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="activity",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
