from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MaxValueValidator, MinValueValidator
from accounts.models import User
from datetime import date

# ----------------- Student -----------------
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    grade = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    attendance_percentage = models.FloatField(default=0.0, validators=[MaxValueValidator(100.0)])
    average_score = models.FloatField(default=0.0, validators=[MaxValueValidator(10.0)])
    is_at_risk = models.BooleanField(default=False)
    enrollment_date = models.DateField(auto_now_add=True)
    enrollment_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    course = models.CharField(max_length=100, default="Default Course")
    year = models.IntegerField(default=1)
    credits_earned = models.IntegerField(default=0)
    total_credits = models.IntegerField(default=0)
    incidents_count = models.IntegerField(default=0)

    # ✅ Editable fields
    area_of_interest = models.TextField(blank=True, null=True, help_text="Student's academic/career interests")
    need_counselling = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")],
        default="no",
        help_text="Does the student need counselling?"
    )

    def __str__(self):
        return self.name or (self.user.username if self.user else "Unknown Student")


# Automatically create sample data for new students
@receiver(post_save, sender=Student)
def create_sample_data_for_student(sender, instance, created, **kwargs):
    if created:
        Performance.objects.create(student=instance, test_name="Initial Test", subject="Math", score=80)
        Attendance.objects.create(student=instance, date=date.today(), status="Present", percentage=100)


# ----------------- Attendance -----------------
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[("Present", "Present"), ("Absent", "Absent")])
    percentage = models.FloatField(default=0.0, validators=[MaxValueValidator(100.0)])

    def __str__(self):
        return f"{self.student.name if self.student else 'Unknown'} - {self.date} ({self.status})"

    @property
    def week_number(self):
        return self.date.isocalendar()[1] if self.date else None

    @property
    def recorded_date(self):
        return self.date


# ----------------- Performance -----------------
class Performance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='performances')
    test_name = models.CharField(max_length=100)
    subject = models.CharField(max_length=50)
    score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_score = models.FloatField(default=100.0, validators=[MinValueValidator(1)])
    percentage = models.FloatField(default=0.0)
    test_date = models.DateField(default=date.today)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-test_date']

    def save(self, *args, **kwargs):
        if self.max_score > 0:
            self.percentage = round((self.score / self.max_score) * 100, 2)
        super().save(*args, **kwargs)

    @property
    def grade(self):
        if self.percentage >= 90:
            return 'A+'
        elif self.percentage >= 80:
            return 'A'
        elif self.percentage >= 70:
            return 'B'
        elif self.percentage >= 60:
            return 'C'
        elif self.percentage >= 50:
            return 'D'
        else:
            return 'F'

    def __str__(self):
        return f"{self.student.name} - {self.test_name} ({self.score}/{self.max_score})"


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
    message = models.TextField(null=True, blank=True)
    description = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    icon = models.CharField(max_length=50, default='notifications')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')

    def __str__(self):
        return self.title or "Alert"


# ----------------- Progress -----------------
class Progress(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='progress_data')
    gpa_labels = models.JSONField(default=list, blank=True)
    gpa_data = models.JSONField(default=list, blank=True)
    attendance_labels = models.JSONField(default=list, blank=True)
    attendance_data = models.JSONField(default=list, blank=True)
    subject_labels = models.JSONField(default=list, blank=True)
    subject_data = models.JSONField(default=list, blank=True)
    grade_summary = models.JSONField(default=list, blank=True)
    incidents_count = models.PositiveIntegerField(default=0)
    incident_list = models.JSONField(default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.name} Progress"


# ----------------- CounsellingSession -----------------
class CounsellingSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    mentor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'mentor'}
    )
    scheduled_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
        default='pending'
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.scheduled_time.date() if self.scheduled_time else 'Not Scheduled'} ({self.status})"
