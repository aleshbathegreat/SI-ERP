import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0018_maintenance_parts"),
        ("projects", "0002_timeentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="timeentry",
            name="customer_invoice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="time_entries",
                to="finance.customerinvoice",
            ),
        ),
    ]
