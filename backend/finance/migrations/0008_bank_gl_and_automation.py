from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0007_asset_assign_repair"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankaccount",
            name="gl_account",
            field=models.ForeignKey(
                blank=True,
                help_text="Linked cash/bank GL account for payment auto-posting",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bank_accounts",
                to="finance.account",
            ),
        ),
    ]
