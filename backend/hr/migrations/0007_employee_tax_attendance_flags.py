from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0006_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="is_attendance_free",
            field=models.BooleanField(
                default=False,
                help_text="Skip attendance/unpaid-leave proration on payroll runs",
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="is_tax_free",
            field=models.BooleanField(
                default=False,
                help_text="Skip income tax on payroll runs for this employee",
            ),
        ),
    ]
