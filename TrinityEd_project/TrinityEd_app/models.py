from django.db import models

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
        return self.title
