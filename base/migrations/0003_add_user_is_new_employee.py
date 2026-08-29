from django.db import migrations, models

def add_is_new_employee(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    
    # Check if the column is_new_employee already exists in the auth_user table
    with schema_editor.connection.cursor() as cursor:
        columns = [col.name for col in schema_editor.connection.introspection.get_table_description(cursor, 'auth_user')]
    
    if 'is_new_employee' not in columns:
        field = models.BooleanField(default=False)
        field.set_attributes_from_name('is_new_employee')
        schema_editor.add_field(User, field)

def remove_is_new_employee(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    field = models.BooleanField(default=False)
    field.set_attributes_from_name('is_new_employee')
    try:
        schema_editor.remove_field(User, field)
    except Exception:
        pass

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('base', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(add_is_new_employee, reverse_code=remove_is_new_employee),
    ]
