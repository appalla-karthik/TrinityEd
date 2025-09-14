from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Alert


# Home page
def home(request):
    return render(request, 'home.html')


# Mentor Dashboard
def mentor_dashboard(request):
    context = {
        "total_students": 120,
        "at_risk": 15,
        "alerts_sent": 45,
        "alerts": [
            {"student": "Student A", "issue": "Low Attendance (65%)", "status": "Critical"},
            {"student": "Student B", "issue": "Fee Pending", "status": "Warning"},
            {"student": "Student C", "issue": "Consistent Poor Performance", "status": "Critical"},
        ],
    }
    return render(request, "mentor_dashboard.html", context)


# Attendance page
def attendance_view(request):
    return render(request, 'attendance.html')


# Performance page
def performance_view(request):
    return render(request, 'performance.html')


# Fee Status page
def fee_status(request):
    students = [
        {'name': 'Student A', 'total_fee': 50000, 'paid': 45000, 'pending': 5000, 'due_date': '2025-09-20'},
        {'name': 'Student B', 'total_fee': 60000, 'paid': 60000, 'pending': 0, 'due_date': '-'},
        {'name': 'Student C', 'total_fee': 45000, 'paid': 30000, 'pending': 15000, 'due_date': '2025-09-18'},
    ]

    total_collected = sum(s['paid'] for s in students)
    total_pending = sum(s['pending'] for s in students)
    due_soon = sum(
        1 for s in students
        if s['due_date'] != '-' and date.fromisoformat(s['due_date']) <= date.today() + timedelta(days=7)
    )

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    fee_collected = [40000, 50000, 45000, 60000, 55000, 65000]

    context = {
        'students': students,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'due_soon': due_soon,
        'months': months,
        'fee_collected': fee_collected
    }
    return render(request, 'feestatus.html', context)


# Alerts page
def alerts_view(request):
    # Fetch alerts from DB (or fallback to sample if DB empty)
    alerts_list = Alert.objects.all().order_by('-timestamp')

    if not alerts_list.exists():
        # Sample alerts fallback
        alerts_list = [
            {"title": "Fee Pending Reminder", "description": "Student Raj has pending fees of ₹5000. Due date: 20-Sep-2025.", "type": "warning", "icon": "warning", "timestamp": "Just now"},
            {"title": "New Attendance Alert", "description": "Attendance for class 10-B is below 75%.", "type": "info", "icon": "info", "timestamp": "Just now"},
            {"title": "Overdue Fee Alert", "description": "Student Priya's fee is overdue by 15 days.", "type": "danger", "icon": "error", "timestamp": "Just now"},
            {"title": "Event Notification", "description": "Science fair scheduled on 25-Sep-2025.", "type": "info", "icon": "notifications", "timestamp": "Just now"},
        ]

    context = {"alerts": alerts_list}
    return render(request, "alerts.html", context)


# Mark alert as read (AJAX)
@csrf_exempt
def mark_alert_read(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            alert_id = data.get('id')
            alert = Alert.objects.get(id=alert_id)
            alert.is_read = True
            alert.save()
            return JsonResponse({'status': 'success'})
        except Alert.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Alert not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# Student Dashboard
@login_required
def student(request):
    user = request.user

    attendance_weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    attendance_values = [85, 78, 90, 70] if user.is_student else [0, 0, 0, 0]
    latest_attendance = attendance_values[-1] if attendance_values else 0

    score_tests = ["Test 1", "Test 2", "Test 3"]
    score_values = [75, 82, 68] if user.is_student else [0, 0, 0]
    avg_score = sum(score_values) / len(score_values) if score_values else 0

    context = {
        "student_name": user.get_full_name() or user.username,
        "attendance": latest_attendance,
        "avg_score": round(avg_score, 2),
        "fee_status": "Partial",
        "dropout_risk": "Medium",
        "role": user.role,
        "attendance_weeks": json.dumps(attendance_weeks),  # Ensure proper JSON
        "attendance_values": json.dumps(attendance_values),
        "score_tests": json.dumps(score_tests),
        "score_values": json.dumps(score_values),
        "messages": [
            f"⚠️ Your attendance dropped below {latest_attendance}%. Please contact your mentor." if latest_attendance < 80 and user.is_student else "",
            "✅ Good improvement in Science this week!" if score_values[-1] > 70 and user.is_student else ""
        ]
    }
    context["messages"] = [msg for msg in context["messages"] if msg]

    return render(request, "student.html", context)

# Progress Page
def progress(request):
    return render(request, "progress.html")


# Counselling Page
def counselling(request):
    return render(request, "counselling.html")


# Resources Page
def resources(request):
    return render(request, "resources.html")
