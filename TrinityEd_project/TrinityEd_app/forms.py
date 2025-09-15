# TrinityEd_app/forms.py
from django import forms
from django.contrib.auth import get_user_model
from TrinityEd_app.models import Student

User = get_user_model()

class StudentForm(forms.ModelForm):
    enrollment_no = forms.CharField(max_length=20, required=False, help_text="Enter enrollment number for the student.")

    class Meta:
        model = Student
        fields = ['user']  # Only user field from Student model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logged_in_students = User.objects.filter(last_login__isnull=False, role='student')
        existing_student_ids = Student.objects.values_list('user_id', flat=True)
        eligible_users = logged_in_students.exclude(id__in=existing_student_ids)
        self.fields['user'].queryset = eligible_users

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        # Update the related User model's enrollment_no
        if self.cleaned_data.get('enrollment_no'):
            instance.user.enrollment_no = self.cleaned_data['enrollment_no']
            instance.user.save()
        return instance