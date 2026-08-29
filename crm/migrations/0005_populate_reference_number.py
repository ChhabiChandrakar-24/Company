from django.db import migrations, models

def generate_reference_numbers(apps, schema_editor):
    Inquiry = apps.get_model('crm', 'Inquiry')
    for inquiry in Inquiry.objects.all():
        if not inquiry.reference_number:
            inquiry.reference_number = f"INV-{inquiry.id}"
            inquiry.save(update_fields=['reference_number'])

class Migration(migrations.Migration):
    dependencies = [
        ('crm', '0004_inquiry_reference_number_alter_inquiry_status'),
    ]
    operations = [
        migrations.RunPython(generate_reference_numbers, reverse_code=migrations.RunPython.noop),
    ]
