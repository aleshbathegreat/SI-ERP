import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0008_saas_ops_enterprise"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationRead",
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
                ("key", models.CharField(db_index=True, max_length=64)),
                (
                    "source_stamp",
                    models.CharField(
                        help_text="Item version when marked read — newer stamp = unread again",
                        max_length=64,
                    ),
                ),
                ("read_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_reads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-read_at"],
                "unique_together": {("user", "key")},
            },
        ),
    ]
