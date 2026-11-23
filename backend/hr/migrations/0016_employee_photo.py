from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0015_attendance_regularization"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="employee-photos/"),
        ),
    ]
