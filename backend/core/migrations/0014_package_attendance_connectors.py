from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_email_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionpackage",
            name="max_attendance_devices",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Max attendance devices for tenants on this package (0 = none)",
            ),
        ),
        migrations.AddField(
            model_name="subscriptionpackage",
            name="attendance_connectors",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Allowed connector keys from catalog; use ["*"] for all',
            ),
        ),
    ]
