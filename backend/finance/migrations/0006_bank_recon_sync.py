# Generated manually for bank account / reconciliation sync + CSV reference

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0005_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankaccount",
            name="current_balance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="bankaccount",
            name="last_reconciled",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bankstatementline",
            name="reference",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
