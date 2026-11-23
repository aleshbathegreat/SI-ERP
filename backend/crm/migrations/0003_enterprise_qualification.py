from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0002_lead_converted_customer_lead_converted_opportunity_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="industry",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="lead",
            name="rating",
            field=models.CharField(
                choices=[("cold", "Cold"), ("warm", "Warm"), ("hot", "Hot")],
                default="warm",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="lead",
            name="score",
            field=models.PositiveSmallIntegerField(
                default=50,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddField(
            model_name="lead",
            name="next_follow_up",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="lead",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="next_step",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="competitor",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="activity",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="activity",
            name="priority",
            field=models.CharField(
                choices=[("low", "Low"), ("normal", "Normal"), ("high", "High")],
                default="normal",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="activity",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="crm_activities_owned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="type",
            field=models.CharField(
                choices=[
                    ("call", "Call"),
                    ("email", "Email"),
                    ("meeting", "Meeting"),
                    ("task", "Task"),
                    ("note", "Note"),
                ],
                default="call",
                max_length=20,
            ),
        ),
    ]
