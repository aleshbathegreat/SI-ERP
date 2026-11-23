from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_notification_read"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionpackage",
            name="core_module_keys",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Always-on shell modules; empty = platform default core set",
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionpackage",
            name="module_keys",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Assignable TOR modules (finance.*/hr.*/payroll.*/billing)",
            ),
        ),
    ]
