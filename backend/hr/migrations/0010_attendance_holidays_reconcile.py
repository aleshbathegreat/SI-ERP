from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0009_enterprise_attendance"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancepolicy",
            name="auto_apply_leave",
            field=models.BooleanField(
                default=True,
                help_text="Mark attendance on_leave when leave is approved",
            ),
        ),
        migrations.AddField(
            model_name="attendancepolicy",
            name="auto_apply_holiday",
            field=models.BooleanField(
                default=True,
                help_text="Mark attendance holiday from calendar / weekends",
            ),
        ),
        migrations.AddField(
            model_name="attendancepolicy",
            name="auto_mark_absent",
            field=models.BooleanField(
                default=True,
                help_text="On reconcile, mark missing punches as absent for non-exempt staff",
            ),
        ),
        migrations.AddField(
            model_name="attendancepolicy",
            name="weekend_days",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Weekday numbers treated as weekend (0=Mon … 6=Sun). Default Sat+Sun.",
            ),
        ),
        migrations.CreateModel(
            name="AttendanceHoliday",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=128)),
                ("holiday_date", models.DateField()),
                (
                    "is_optional",
                    models.BooleanField(
                        default=False,
                        help_text="Optional holiday — does not auto-mark unless opted",
                    ),
                ),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
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
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_holidays",
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
                "ordering": ["holiday_date"],
                "unique_together": {("organization", "holiday_date", "name")},
            },
        ),
    ]
