from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0011_enterprise_hr_lifecycle"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentTypeDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=32)),
                ("name", models.CharField(max_length=128)),
                ("is_required", models.BooleanField(default=False)),
                ("requires_expiry", models.BooleanField(default=False)),
                ("warn_days_before_expiry", models.PositiveIntegerField(default=30)),
                (
                    "blocks_payroll_if_missing",
                    models.BooleanField(
                        default=False,
                        help_text="If required and missing/expired, flag employee for payroll hold",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort", models.PositiveSmallIntegerField(default=100)),
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
                        related_name="document_types",
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
            options={"ordering": ["sort", "code"], "unique_together": {("organization", "code")}},
        ),
        migrations.CreateModel(
            name="TrainingCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=32)),
                ("title", models.CharField(max_length=128)),
                ("provider", models.CharField(blank=True, default="", max_length=128)),
                ("category", models.CharField(blank=True, default="general", max_length=64)),
                ("duration_hours", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("is_mandatory", models.BooleanField(default=False)),
                (
                    "validity_months",
                    models.PositiveIntegerField(
                        default=0, help_text="0 = no expiry; else certificate validity"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True, default="")),
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
                        related_name="training_courses",
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
            options={"ordering": ["code"], "unique_together": {("organization", "code")}},
        ),
        migrations.CreateModel(
            name="JobHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("hire", "Hire / joining"),
                            ("promotion", "Promotion"),
                            ("transfer", "Transfer"),
                            ("salary_revision", "Salary revision"),
                            ("manager_change", "Manager change"),
                            ("status_change", "Status change"),
                            ("contract_change", "Contract change"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=32,
                    ),
                ),
                ("effective_date", models.DateField()),
                ("from_department", models.CharField(blank=True, default="", max_length=160)),
                ("to_department", models.CharField(blank=True, default="", max_length=160)),
                ("from_designation", models.CharField(blank=True, default="", max_length=160)),
                ("to_designation", models.CharField(blank=True, default="", max_length=160)),
                ("from_salary", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("to_salary", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("from_status", models.CharField(blank=True, default="", max_length=32)),
                ("to_status", models.CharField(blank=True, default="", max_length=32)),
                ("reason", models.TextField(blank=True, default="")),
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
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_history",
                        to="hr.employee",
                    ),
                ),
                (
                    "from_manager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="hr.employee",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_history",
                        to="core.organization",
                    ),
                ),
                (
                    "to_manager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="hr.employee",
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
            options={"ordering": ["-effective_date", "-id"]},
        ),
        migrations.AddField(
            model_name="employeedocument",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="employeedocument",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="achievements",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="development_plan",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="review_period_end",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="review_period_start",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="review_type",
            field=models.CharField(
                choices=[
                    ("annual", "Annual"),
                    ("mid_year", "Mid-year"),
                    ("probation", "Probation"),
                    ("pip", "PIP"),
                    ("project", "Project"),
                ],
                default="annual",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="reviewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviews_given",
                to="hr.employee",
            ),
        ),
        migrations.AddField(
            model_name="performancereview",
            name="self_rating",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="certificate_expires_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="certificate_file",
            field=models.FileField(blank=True, null=True, upload_to="hr/training/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="certificate_no",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="cost",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="enrollments",
                to="hr.trainingcourse",
            ),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="hours",
            field=models.DecimalField(decimal_places=1, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name="trainingrecord",
            name="score",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="trainingrecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("planned", "Planned"),
                    ("in_progress", "In progress"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                    ("failed", "Failed"),
                ],
                default="planned",
                max_length=32,
            ),
        ),
    ]
