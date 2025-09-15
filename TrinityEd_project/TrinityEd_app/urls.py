from django.urls import path
from . import views

urlpatterns = [
     path('', views.home, name='home'),
     path('mentor_dashboard', views.mentor_dashboard, name="mentor_dashboard"),
     path('attendance/', views.attendance_view, name='attendance'),
     path('performance/', views.performance_view, name='performance'),
     path('fees/', views.fee_status, name='fee_status'),
     path('alerts/', views.alerts_view, name='alerts'),  # <-- fixed here
     path('alerts/mark-read/', views.mark_alert_read, name='mark_alert_read'),
     #rudra
     path("student1/", views.student, name="student_dashboard"),
     path("progress/", views.progress, name="progress"),
     path("counselling/", views.counselling, name="counselling"),
     path("resources/", views.resources, name="resources"),   
     path("learners/", views.learner_list, name="learner_list"),
    path("learners/<int:pk>/", views.learner_detail, name="learner_detail"), 
]
