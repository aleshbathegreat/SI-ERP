from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="currency",
            field=models.CharField(
                default="PKR",
                help_text="Default tenant currency for payroll and finance",
                max_length=3,
            ),
        ),
    ]
