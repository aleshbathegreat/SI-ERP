from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0013_wave2_wms_bins_picklists"),
    ]

    operations = [
        migrations.AddField(
            model_name="stocklevel",
            name="qty_qc_hold",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Quantity received but not available until QC releases it.",
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="goodsreceiptline",
            name="qty_on_hold",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14),
        ),
    ]
