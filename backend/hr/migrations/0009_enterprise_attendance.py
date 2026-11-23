import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0008_attendance_devices_connectors"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendancePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("work_start", models.TimeField(default=datetime.time(9, 0))),
                ("work_end", models.TimeField(default=datetime.time(18, 0))),
                ("late_grace_minutes", models.PositiveIntegerField(default=15)),
                ("early_leave_grace_minutes", models.PositiveIntegerField(default=15)),
                ("half_day_minutes", models.PositiveIntegerField(default=240, help_text="Minimum worked minutes to count as half day")),
                ("full_day_minutes", models.PositiveIntegerField(default=480, help_text="Expected full-day worked minutes")),
                ("overtime_after_minutes", models.PositiveIntegerField(default=480, help_text="OT starts after this many worked minutes")),
                ("require_checkout", models.BooleanField(default=True)),
                ("allow_wfh", models.BooleanField(default=True)),
                ("allow_manual_punch", models.BooleanField(default=True)),
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
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_policy",
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
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="work_type",
            field=models.CharField(
                choices=[
                    ("office", "Office"),
                    ("wfh", "Work from home"),
                    ("field", "Field / on-site"),
                    ("half_day", "Half day"),
                ],
                default="office",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="is_half_day",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="late_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="early_leave_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="overtime_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="worked_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="regularize_reason",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("present", "Present"),
                    ("absent", "Absent"),
                    ("late", "Late"),
                    ("early_leave", "Early leave"),
                    ("half_day", "Half day"),
                    ("wfh", "Work from home"),
                    ("on_leave", "On leave"),
                    ("holiday", "Holiday"),
                    ("exempt", "Exempt"),
                    ("exception", "Exception"),
                    ("regularized", "Regularized"),
                ],
                default="present",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="source",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("device", "Device sync"),
                    ("csv", "CSV import"),
                    ("ess", "ESS"),
                    ("system", "System"),
                ],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="is_attendance_free",
            field=models.BooleanField(
                default=False,
                help_text="Attendance-exempt: no check-in/out required; payroll skips attendance/unpaid-leave proration (e.g. directors, field staff)",
            ),
        ),
    ]
