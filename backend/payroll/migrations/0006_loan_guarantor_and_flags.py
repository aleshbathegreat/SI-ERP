import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0007_employee_tax_attendance_flags"),
        ("payroll", "0005_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeloan",
            name="guarantor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="guaranteed_loans",
                to="hr.employee",
            ),
        ),
    ]
