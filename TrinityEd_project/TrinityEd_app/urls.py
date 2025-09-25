# TrinityEd_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('mentor_dashboard/<int:student_id>/', views.mentor_dashboard, name='mentor_dashboard'),
    path('mentor_dashboard/', views.mentor_dashboard, name='mentor_dashboard'),
    path('attendance/', views.attendance_view, name='attendance'),
    path('performance/', views.performance_view, name='performance'),
    path('fees/', views.fee_status, name='fee_status'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('alerts/mark-read/', views.mark_alert_read, name='mark_alert_read'),
    path('student/<int:student_id>/', views.student, name='student'),  # Corrected URL pattern
    path('progress/', views.progress, name='progress'),
    path('counselling/', views.counselling, name='counselling'),
    path('resources/', views.resources, name='resources'),
    path('students/', views.student_list, name='student_list'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path("chatbot_api/", views.chatbot_api, name="chatbot_api"),
    path('get_gemini_key/', views.get_gemini_key, name='get_gemini_key'),
    path('cancel-session/<int:session_id>/', views.cancel_session, name='cancel_session'),
]