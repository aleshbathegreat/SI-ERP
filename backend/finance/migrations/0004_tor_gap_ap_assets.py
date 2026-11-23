from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0003_production_hardening"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendorinvoice",
            name="attachment",
            field=models.FileField(
                blank=True, null=True, upload_to="ap/invoices/%Y/%m/"
            ),
        ),
        migrations.AddField(
            model_name="vendorinvoice",
            name="payment_ref",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="vendorinvoice",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="vendorinvoice",
            name="paid_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="fixedasset",
            name="accumulated_depreciation",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="fixedasset",
            name="disposed_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fixedasset",
            name="disposal_proceeds",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
