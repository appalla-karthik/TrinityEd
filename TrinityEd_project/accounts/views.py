# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import User
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib import messages
from django.conf import settings

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        user = self.request.user
        if next_url and 'mentor_dashboard' in next_url:
            from urllib.parse import urlparse, parse_qs
            path = urlparse(next_url).path
            if '/mentor_dashboard/' in path:
                student_id = path.split('/mentor_dashboard/')[-1].split('/')[0]
                try:
                    student_id = int(student_id)
                    return reverse_lazy('mentor_dashboard', kwargs={'student_id': student_id})
                except (ValueError, IndexError):
                    pass  # Fall back to default redirect
        if user.is_student:
            return reverse_lazy('student', kwargs={'student_id': user.student.id}) if hasattr(user, 'student') else reverse_lazy('home')
        elif user.is_mentor or user.is_admin_user:
            return reverse_lazy('mentor_dashboard')
        return reverse_lazy('home')
    
class SignUpView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def get_success_url(self):
        user = self.object
        if user.is_student:
            return reverse_lazy('student', kwargs={'student_id': user.student.id}) if hasattr(user, 'student') else reverse_lazy('home')
        elif user.is_mentor or user.is_admin_user:
            return reverse_lazy('mentor_dashboard', kwargs={'student_id': user.id})
        return reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)  # Automatically log in the user after signup

        # Send welcome email
        subject = 'Welcome to TrinityEd'
        context = {
            'first_name': user.first_name or user.username,
            'role': user.get_role_display(),
            'request': self.request,  # Pass request for dynamic URL
        }
        html_message = render_to_string('accounts/email/welcome_email.html', context)
        plain_message = strip_tags(html_message)
        from_email = settings.EMAIL_HOST_USER
        to = [user.email]  # Send to the user's email

        try:
            send_mail(subject, plain_message, from_email, to, html_message=html_message, fail_silently=False)
            messages.success(self.request, f'Welcome, {user.first_name or user.username}! An email has been sent to {user.email}.')
        except Exception as e:
            messages.error(self.request, f'Welcome, {user.first_name or user.username}! Failed to send welcome email: {str(e)}')

        return response

def custom_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))

def LogoutView(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))