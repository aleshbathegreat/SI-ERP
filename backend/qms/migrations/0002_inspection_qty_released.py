from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("qms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="qualityinspection",
            name="qty_released",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Quantity this inspection has released from QC hold.",
                max_digits=14,
            ),
        ),
    ]
