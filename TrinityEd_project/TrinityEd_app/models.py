from django.db import models
from accounts.models import User  # For linking to Django's User model

class Student(models.Model):
    """
    Model to store student information and at-risk status predicted by ML.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # Link to Django User
    name = models.CharField(max_length=100)
    attendance_percentage = models.FloatField(default=0.0)  # e.g., 85.5
    average_score = models.FloatField(default=0.0)  # e.g., 75.0
    is_at_risk = models.BooleanField(default=False)  # Updated via ML prediction
    enrollment_date = models.DateField(auto_now_add=True)  # When the student enrolled

    def __str__(self):
        return self.name

class Attendance(models.Model):
    """
    Model to store attendance records for students.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    week = models.CharField(max_length=10, choices=[(f"Week {i}", f"Week {i}") for i in range(1, 5)])  # e.g., Week 1, Week 2
    percentage = models.FloatField(default=0.0)  # Attendance percentage for the week
    recorded_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.week} ({self.percentage}%)"

class Performance(models.Model):
    """
    Model to store performance records (test scores) for students.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    test_name = models.CharField(max_length=50)  # e.g., Test 1, Test 2
    score = models.FloatField(default=0.0)  # Test score
    test_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.test_name} ({self.score})"

class Fee(models.Model):
    """
    Model to store fee details for students.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)  # Total fee amount
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Amount paid
    pending = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Amount pending
    due_date = models.DateField(null=True, blank=True)  # Fee due date
    is_overdue = models.BooleanField(default=False)  # Flag for overdue status

    def __str__(self):
        return f"{self.student.name} - Pending: {self.pending}"



class Alert(models.Model):
    """
    Model to store alert notifications for students or system events.
    """
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
        return self.title