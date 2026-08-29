from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("website", "0008_consultation_submission_type")]
    operations = [
        migrations.AlterField(
            model_name="websitesettings",
            name="company_name",
            field=models.CharField(default="Geeta ForgeTech", max_length=150),
        ),
    ]
