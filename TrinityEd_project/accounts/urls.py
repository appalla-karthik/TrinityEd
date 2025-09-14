from django.contrib.auth.views import PasswordResetView
from django.urls import path
from .views import CustomLoginView, SignUpView, custom_logout,LogoutView
urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView, name='logout'),
    path('custom-logout/', custom_logout, name='custom_logout'),
    path('forgot-password/', PasswordResetView.as_view(template_name='accounts/password_reset.html'), name='forgot_password'),
]