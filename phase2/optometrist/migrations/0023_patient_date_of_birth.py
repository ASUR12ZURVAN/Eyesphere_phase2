from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("optometrist", "0022_merge_20260826_1850"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
    ]
