from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0007_employee_tax_attendance_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="source",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("device", "Device sync"),
                    ("csv", "CSV import"),
                    ("ess", "ESS"),
                ],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="connector_key",
            field=models.CharField(default="generic_webhook", max_length=64),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="connection_mode",
            field=models.CharField(
                choices=[
                    ("push_webhook", "Push / webhook"),
                    ("pull_tcp", "Pull / TCP"),
                    ("cloud_api", "Cloud / REST API"),
                    ("csv_import", "CSV import"),
                ],
                default="push_webhook",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="host",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="port",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="username",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="password",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="api_token",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="webhook_secret",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="config",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="last_sync_status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("ok", "Last sync OK"),
                    ("error", "Last sync error"),
                    ("testing", "Testing"),
                ],
                default="idle",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="last_sync_message",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="attendancedevice",
            name="last_error_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="device",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="attendance_records",
                to="hr.attendancedevice",
            ),
        ),
        migrations.AlterModelOptions(
            name="attendancedevice",
            options={"ordering": ["device_id"]},
        ),
    ]
