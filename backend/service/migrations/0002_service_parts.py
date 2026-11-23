import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0017_pmschedule_maintenanceworkorder"),
        ("ops", "0014_qc_hold"),
        ("service", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicecase",
            name="customer_invoice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="service_cases",
                to="finance.customerinvoice",
            ),
        ),
        migrations.CreateModel(
            name="ServicePart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("qty", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("unit_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parts", to="service.servicecase")),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_parts", to="ops.item")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_parts", to="core.organization")),
                ("stock_movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_parts", to="ops.stockmovement")),
                ("warehouse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_parts", to="ops.warehouse")),
            ],
            options={"ordering": ["id"]},
        ),
    ]
