import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0012_fx_cheques_intercompany"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetDepreciationLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("run_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="depreciation_lines", to="finance.fixedasset")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_depreciation_lines", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-run_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="FbrInvoiceSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("invoice_type", models.CharField(choices=[("ar", "AR"), ("ap", "AP")], default="ar", max_length=8)),
                ("local_invoice_id", models.CharField(max_length=64)),
                ("fbr_invoice_no", models.CharField(blank=True, default="", max_length=64)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("queued", "Queued"), ("submitted", "Submitted"), ("accepted", "Accepted"), ("rejected", "Rejected")], default="draft", max_length=20)),
                ("payload_json", models.TextField(blank=True, default="")),
                ("response_json", models.TextField(blank=True, default="")),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fbr_submissions", to="core.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
    ]
