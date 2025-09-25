from django.db import migrations, models

def set_is_mentor(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='mentor').update(is_mentor=True)

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_user_enrollment_no'),  # Replace with the previous migration name
    ]

    operations = [
        migrations.AddField(
            model_name='User',
            name='is_mentor',
            field=models.BooleanField(default=False, help_text='Designates whether this user is a mentor.'),
        ),
        migrations.RunPython(set_is_mentor, reverse_code=migrations.RunPython.noop),
    ]