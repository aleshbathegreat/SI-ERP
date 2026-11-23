import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0004_tor_gap_ap_assets"),
        ("payroll", "0003_intl_payroll_and_loans"),
    ]

    operations = [
        migrations.AddField(
            model_name="payrollperiod",
            name="gl_journal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payroll_periods",
                to="finance.journalentry",
            ),
        ),
    ]
