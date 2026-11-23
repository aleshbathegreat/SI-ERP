from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0003_enterprise_qualification"),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Low"),
                    ("normal", "Normal"),
                    ("high", "High"),
                    ("urgent", "Urgent"),
                ],
                default="normal",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="lead",
            name="campaign",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="lead",
            name="medium",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="lead",
            name="lost_reason",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Low"),
                    ("normal", "Normal"),
                    ("high", "High"),
                    ("urgent", "Urgent"),
                ],
                default="normal",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="won_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="lost_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="activity",
            name="outcome",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
