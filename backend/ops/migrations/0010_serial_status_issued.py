from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0009_enterprise_packs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="serialnumber",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("issued", "Issued"),
                    ("scrapped", "Scrapped"),
                ],
                default="available",
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="serialnumber",
            unique_together={("organization", "item", "serial_no")},
        ),
        migrations.AlterModelOptions(
            name="serialnumber",
            options={"ordering": ["serial_no"]},
        ),
    ]
