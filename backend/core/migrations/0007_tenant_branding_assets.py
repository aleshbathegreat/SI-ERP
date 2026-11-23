from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_tenant_custom_domains"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="brand_tagline",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Short line under brand name (login, shell)",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="brand_secondary_color",
            field=models.CharField(blank=True, default="#C45C26", max_length=16),
        ),
        migrations.AddField(
            model_name="organization",
            name="brand_logo",
            field=models.ImageField(
                blank=True,
                help_text="Primary logo (light backgrounds)",
                null=True,
                upload_to="branding/logos/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="brand_logo_dark",
            field=models.ImageField(
                blank=True,
                help_text="Optional logo for dark UI; falls back to brand_logo",
                null=True,
                upload_to="branding/logos/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="brand_favicon",
            field=models.ImageField(
                blank=True,
                help_text="Browser tab icon (PNG/ICO/SVG)",
                null=True,
                upload_to="branding/favicons/%Y/%m/",
            ),
        ),
    ]
