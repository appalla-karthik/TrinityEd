# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('mentor_dashboard', views.mentor_dashboard, name="mentor_dashboard"),
    path('attendance/', views.attendance_view, name='attendance'),
    path('performance/', views.performance_view, name='performance'),
    path('fees/', views.fee_status, name='fee_status'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('alerts/mark-read/', views.mark_alert_read, name='mark_alert_read'),
    path("student1/", views.student, name="student_dashboard"),
    path("progress/", views.progress, name="progress"),
    path("counselling/", views.counselling, name="counselling"),
    path("resources/", views.resources, name="resources"),
    path('students/', views.student_list, name='student_list'),  # Updated to reflect students
]