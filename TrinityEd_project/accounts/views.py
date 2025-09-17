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

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.is_student:
            return reverse_lazy('student_dashboard')
        elif user.is_mentor or user.is_admin_user:
            return reverse_lazy('mentor_dashboard')
        return reverse_lazy('student_dashboard')

class SignUpView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        
        # Send welcome email
        subject = 'Welcome to TrinityEd - Your Account Has Been Created!'
        html_message = render_to_string('accounts/email/welcome_email.html', {
            'user': user,
            'first_name': user.first_name,
            'role': user.get_role_display(),
        })
        plain_message = strip_tags(html_message)
        from_email = 'godanishubham30@gmail.com'
        to_email = user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
        )
        
        login(self.request, self.object)
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        user = self.object
        if user.is_student:
            return reverse_lazy('student_dashboard')
        elif user.is_mentor or user.is_admin_user:
            return reverse_lazy('mentor_dashboard')
        return reverse_lazy('student_dashboard')

def custom_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))

def LogoutView(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))