from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0012_organization_currency"),
        ("finance", "0007_asset_assign_repair"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=32)),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("phone", models.CharField(blank=True, default="", max_length=64)),
                ("ntn", models.CharField(blank=True, default="", max_length=32)),
                ("address", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customers", to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name"], "unique_together": {("organization", "code")}},
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("sku", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("unit", models.CharField(default="ea", max_length=32)),
                ("qty_on_hand", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("reorder_level", models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ("unit_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_items", to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["sku"], "unique_together": {("organization", "sku")}},
        ),
        migrations.CreateModel(
            name="SalesOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("order_no", models.CharField(max_length=64)),
                ("order_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("currency", models.CharField(default="PKR", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("confirmed", "Confirmed"),
                            ("delivered", "Delivered"),
                            ("invoiced", "Invoiced"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders", to="ops.customer",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sales_orders", to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-order_date", "-id"], "unique_together": {("organization", "order_no")}},
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("movement_date", models.DateField()),
                ("qty", models.DecimalField(decimal_places=3, help_text="Positive = inbound, negative = outbound", max_digits=14)),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("receipt", "Goods receipt"),
                            ("issue", "Issue / consumption"),
                            ("adjustment", "Adjustment"),
                            ("return", "Return"),
                            ("transfer", "Transfer"),
                        ],
                        default="adjustment",
                        max_length=20,
                    ),
                ),
                ("reference", models.CharField(blank=True, default="", max_length=128)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movements", to="ops.item",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_movements", to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-movement_date", "-id"]},
        ),
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("po_no", models.CharField(max_length=64)),
                ("order_date", models.DateField()),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("currency", models.CharField(default="PKR", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("approved", "Approved"),
                            ("received", "Received"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="purchase_orders", to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vendor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_orders", to="finance.vendor",
                    ),
                ),
            ],
            options={"ordering": ["-order_date", "-id"], "unique_together": {("organization", "po_no")}},
        ),
    ]
