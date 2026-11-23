from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_chat"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="chat/%Y/%m/"),
        ),
    ]
