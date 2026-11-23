import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_notification_read"),
        ("hr", "0004_production_hardening"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="leavetype",
            name="allow_carry_forward",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="allow_encashment",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="employeedocument",
            name="file",
            field=models.FileField(
                blank=True, null=True, upload_to="hr/documents/%Y/%m/"
            ),
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year", models.PositiveIntegerField()),
                (
                    "opening",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "accrued",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "used",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "encashed",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "carried_forward",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leave_balances",
                        to="hr.employee",
                    ),
                ),
                (
                    "leave_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="balances",
                        to="hr.leavetype",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leave_balances",
                        to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-year", "leave_type__code"],
                "unique_together": {("employee", "leave_type", "year")},
            },
        ),
    ]
