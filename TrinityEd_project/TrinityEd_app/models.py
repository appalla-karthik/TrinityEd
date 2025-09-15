from django.db import models
from django.conf import settings  # For custom User model
from django.db.models.signals import post_save
from django.dispatch import receiver

# ----------------- Student -----------------
class Student(models.Model):
    """
    Stores student info linked to User for dashboard, attendance, and performance.
    Automatically created when a User with role='student' is added.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # ✅ Use custom User model
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    enrollment_no = models.CharField(max_length=20, blank=True, null=True, unique=True)
    course = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    attendance_percentage = models.FloatField(default=0.0)
    average_score = models.FloatField(default=0.0)
    is_at_risk = models.BooleanField(default=False)
    enrollment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name or "Unnamed Student"

# Automatically create Student when a User with role='student' is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_student_for_user(sender, instance, created, **kwargs):
    if created and getattr(instance, 'role', None) == 'student':
        Student.objects.create(
            user=instance,
            name=getattr(instance, 'get_full_name', lambda: instance.username)(),
            enrollment_no=f"ENR{instance.id}",  # Auto-generate enrollment number
            course="Default Course",
            year=1,
        )

# ----------------- Attendance -----------------
class Attendance(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[("Present", "Present"), ("Absent", "Absent")])
    percentage = models.FloatField(default=0.0)  # Pre-calculated DB field

    def __str__(self):
        return f"{self.student.name if self.student else 'Unknown'} - {self.date} ({self.status})"

    @property
    def week_number(self):
        """Week number for reporting (property, not DB field)."""
        return self.date.isocalendar()[1] if self.date else None

    @property
    def recorded_date(self):
        return self.date

# ----------------- Performance -----------------
class Performance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    test_name = models.CharField(max_length=50)
    score = models.FloatField(default=0.0)
    test_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.test_name} ({self.score})"

# ----------------- Fee -----------------
class Fee(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    pending = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    due_date = models.DateField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name if self.student else 'Unknown'} - Pending: {self.pending}"

# ----------------- Alert -----------------
class Alert(models.Model):
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    icon = models.CharField(max_length=50, default='notifications')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.title or "Alert"
