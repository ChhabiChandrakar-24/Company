from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("website", "0007_terms_and_conditions")]
    operations = [
        migrations.AlterField(
            model_name="websitesubmission",
            name="submission_type",
            field=models.CharField(
                choices=[("contact", "Contact"), ("consultation", "Consultation"), ("career", "Career"), ("newsletter", "Newsletter")],
                default="contact",
                max_length=20,
            ),
        ),
    ]
