from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0002_warehouses_and_item_enhancements"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorder",
            name="warehouse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchase_orders",
                to="ops.warehouse",
            ),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="warehouse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sales_orders",
                to="ops.warehouse",
            ),
        ),
        migrations.AddField(
            model_name="stockmovement",
            name="purchase_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements",
                to="ops.purchaseorder",
            ),
        ),
        migrations.AddField(
            model_name="stockmovement",
            name="sales_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements",
                to="ops.salesorder",
            ),
        ),
        migrations.CreateModel(
            name="PurchaseOrderLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=1, max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("qty_received", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_order_lines",
                        to="ops.item",
                    ),
                ),
                (
                    "purchase_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="ops.purchaseorder",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="purchase_order_lines",
                        to="ops.warehouse",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SalesOrderLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("qty", models.DecimalField(decimal_places=3, default=1, max_digits=14)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("qty_delivered", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sales_order_lines",
                        to="ops.item",
                    ),
                ),
                (
                    "sales_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="ops.salesorder",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sales_order_lines",
                        to="ops.warehouse",
                    ),
                ),
            ],
        ),
    ]
