# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model with role-based access control and enrollment number.

    Roles:
    - student: Learner/Student
    - mentor: Mentor/Counselor
    - admin: Admin
    """
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('mentor', 'Mentor/Counselor'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profiles/', 
        blank=True, 
        null=True, 
        default='profiles/default.png'
    )
    enrollment_no = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        unique=True, 
        help_text="Enrollment number for students (optional for non-students)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    # ---------------- Role Properties ----------------
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_mentor(self):
        return self.role == 'mentor'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'