# TrinityEd_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User
from .models import Attendance,Student

@receiver(post_save, sender=User)
def create_student_for_user(sender, instance, created, **kwargs):
    """
    Automatically create/update a Student object 
    whenever a User with role='student' is saved.
    """
    if instance.role == 'student':
        Student.objects.update_or_create(
            user=instance,
            defaults={
                "name": instance.get_full_name() or instance.username,
            }
        )
