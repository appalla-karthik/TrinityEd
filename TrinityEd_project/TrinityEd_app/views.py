from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import joblib
from django.db.models import Avg, Max, Min
import numpy as np
from TrinityEd_app.models import Alert, Student, Attendance, Performance

# Home page
def home(request):
    return render(request, 'home.html')

# Mentor Dashboard
@login_required
def mentor_dashboard(request):
    # Load the ML model
    model_path = 'ml_models/at_risk_model.pkl'
    try:
        model = joblib.load(model_path)
    except FileNotFoundError:
        return render(request, 'mentor_dashboard.html', {'error': 'ML model not found. Re-run train_ml_model.py.'})

    # Get all students
    students = Student.objects.all()

    # Predict at-risk for each student and update
    at_risk_count = 0
    for student in students:
        features = np.array([[student.attendance_percentage, student.average_score]])
        prediction = model.predict(features)[0]
        student.is_at_risk = bool(prediction)
        student.save()
        if student.is_at_risk:
            at_risk_count += 1
            if not Alert.objects.filter(title=f"At-Risk Alert for {student.name}").exists():
                Alert.objects.create(
                    title=f"At-Risk Alert for {student.name}",
                    description=f"Low performance indicators detected (Attendance: {student.attendance_percentage}%, Score: {student.average_score}%).",
                    type='danger',
                    icon='warning'
                )

    # Other stats
    total_students = students.count()
    alerts_sent = Alert.objects.filter(is_read=False).count()

    # Prepare dynamic alerts list
    alerts = [
        {"student": student.name, "issue": f"Low Attendance ({student.attendance_percentage}%)", "status": "Critical"}
        for student in students if student.is_at_risk
    ][:3]

    # Dynamic chart data
    attendance_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']
    attendance_data = []
    for week in attendance_labels:
        week_attendance = Attendance.objects.filter(week=week).aggregate(avg=Avg('percentage'))['avg'] or 0
        attendance_data.append(week_attendance)

    performance_subjects = ['Math', 'Science', 'English', 'History']
    performance_data = []
    for subject in performance_subjects:
        subject_scores = Performance.objects.filter(test_name=subject).aggregate(avg=Avg('score'))['avg'] or 0
        performance_data.append(subject_scores)

    context = {
        "total_students": total_students,
        "at_risk": at_risk_count,
        "alerts_sent": alerts_sent,
        "alerts": alerts,
        "attendance_labels": json.dumps(attendance_labels),
        "attendance_data": json.dumps(attendance_data),
        "performance_subjects": json.dumps(performance_subjects),
        "performance_data": json.dumps(performance_data),
    }
    return render(request, "mentor_dashboard.html", context)

# Attendance page
@login_required
def attendance_view(request):
    # Get all students
    students = Student.objects.all()

    # Calculate total students
    total_students = students.count()

    # Calculate average attendance
    avg_attendance = Attendance.objects.aggregate(avg=Avg('percentage'))['avg'] or 0

    # Count at-risk students (using ML prediction or threshold, e.g., <70%)
    at_risk_students = Student.objects.filter(is_at_risk=True).count()

    # Fetch attendance data for student cards and table
    student_attendance = []
    for student in students:
        latest_attendance = Attendance.objects.filter(student=student).order_by('-recorded_date').first()
        attendance_percent = latest_attendance.percentage if latest_attendance else student.attendance_percentage
        student_attendance.append({
            'name': student.name,
            'class_name': f"Class {student.id % 2 + 1}",  # Simple class assignment (1 or 2 based on ID)
            'attendance': attendance_percent,
            'status': 'At Risk' if attendance_percent < 70 else 'Average' if attendance_percent < 80 else 'Good'
        })

    # Chart data: Average attendance per class (simulated classes 1-4)
    class_attendance = {}
    for student in students:
        latest_attendance = Attendance.objects.filter(student=student).order_by('-recorded_date').first()
        attendance = latest_attendance.percentage if latest_attendance else student.attendance_percentage
        class_name = f"Class {student.id % 4 + 1}"  # Distribute across 4 classes
        class_attendance[class_name] = class_attendance.get(class_name, []) + [attendance]
    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [sum(class_attendance.get(f"Class {i}", [0])) / len(class_attendance.get(f"Class {i}", [1])) for i in range(1, 5)]

    # Prepare context
    context = {
        'total_students': total_students,
        'avg_attendance': round(avg_attendance, 2) if avg_attendance else 0,
        'at_risk_students': at_risk_students,
        'student_attendance': student_attendance,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'attendance.html', context)

# Performance page
@login_required
def performance_view(request):
    # Get all students
    students = Student.objects.all()

    # Calculate average score
    avg_score = Performance.objects.aggregate(avg=Avg('score'))['avg'] or 0

    # Top student (highest average_score)
    top_student = Student.objects.order_by('-average_score').first()
    top_student_name = top_student.name if top_student else 'N/A'

    # Needs improvement (count of students with average_score < 70)
    needs_improvement = Student.objects.filter(average_score__lt=70).count()

    # Highest and lowest scores from Performance records
    highest_score = Performance.objects.aggregate(max_score=Max('score'))['max_score'] or 0
    lowest_score = Performance.objects.aggregate(min_score=Min('score'))['min_score'] or 0

    # Class-wise average performance (simulate classes 1-4)
    class_performance = {}
    for student in students:
        class_name = f"Class {student.id % 4 + 1}"  # Distribute across 4 classes
        class_performance[class_name] = class_performance.get(class_name, []) + [student.average_score]
    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [sum(class_performance.get(f"Class {i}", [0])) / len(class_performance.get(f"Class {i}", [1])) for i in range(1, 5)]

    # Performance distribution for pie chart (counts of Good, Average, Needs Improvement)
    good_count = Student.objects.filter(average_score__gte=80).count()
    average_count = Student.objects.filter(average_score__gte=70, average_score__lt=80).count()
    needs_improvement_count = Student.objects.filter(average_score__lt=70).count()

    # Prepare context
    context = {
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'top_student': top_student_name,
        'needs_improvement': needs_improvement,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'pie_data': json.dumps([good_count, average_count, needs_improvement_count]),
    }
    return render(request, 'performance.html', context)

# Fee Status page
@login_required
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
@login_required
def alerts_view(request):
    # Load the ML model
    model_path = 'ml_models/at_risk_model.pkl'
    try:
        model = joblib.load(model_path)
    except FileNotFoundError:
        return render(request, 'alerts.html', {'error': 'ML model not found. Re-run train_ml_model.py.'})

    # Get all students and predict, creating alerts if at-risk
    students = Student.objects.all()
    for student in students:
        features = np.array([[student.attendance_percentage, student.average_score]])
        if model.predict(features)[0] == 1 and not Alert.objects.filter(title=f"At-Risk Alert for {student.name}").exists():
            Alert.objects.create(
                title=f"At-Risk Alert for {student.name}",
                description=f"Low performance indicators detected (Attendance: {student.attendance_percentage}%, Score: {student.average_score}%).",
                type='danger',
                icon='warning'
            )

    # Fetch all unread alerts from DB
    alerts_list = Alert.objects.filter(is_read=False).order_by('-timestamp')

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
    user = get_user_model().objects.get(id=request.user.id)

    attendance_weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    attendance_values = [a.percentage for a in Attendance.objects.filter(student__user=user).order_by('week')] if user.is_student else [0, 0, 0, 0]
    latest_attendance = attendance_values[-1] if attendance_values else 0

    score_tests = ["Test 1", "Test 2", "Test 3"]
    performance_data = Performance.objects.filter(student__user=user).order_by('test_date')
    score_values = [p.score for p in performance_data] if performance_data.exists() else [0, 0, 0]
    while len(score_values) < 3:
        score_values.append(0)
    avg_score = sum(score_values) / len(score_values) if score_values else 0

    is_at_risk = latest_attendance < 75 or avg_score < 70

    context = {
        "student_name": user.get_full_name() or user.username,
        "attendance": latest_attendance,
        "avg_score": round(avg_score, 2),
        "fee_status": "Partial",
        "dropout_risk": "High" if is_at_risk else "Low",
        "role": user.role,
        "attendance_weeks": json.dumps(attendance_weeks),
        "attendance_values": json.dumps(attendance_values[:4]),
        "score_tests": json.dumps(score_tests),
        "score_values": json.dumps(score_values[:3]),
        "messages": [
            f"⚠️ Your attendance dropped below {latest_attendance}%. Please contact your mentor." if latest_attendance < 80 and user.is_student else "",
            "✅ Good improvement in Science this week!" if score_values[-1] > 70 and user.is_student else ""
        ]
    }
    context["messages"] = [msg for msg in context["messages"] if msg]

    return render(request, "student.html", context)

# Progress Page
@login_required
def progress(request):
    return render(request, "progress.html")

# Counselling Page
@login_required
def counselling(request):
    return render(request, "counselling.html")

# Resources Page
@login_required
def resources(request):
    return render(request, "resources.html")