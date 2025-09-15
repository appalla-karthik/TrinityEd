from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Avg, Max, Min
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import User
import json
import joblib
import numpy as np
import logging

from TrinityEd_app.utils.ai_insights import AIInsightsGenerator
from TrinityEd_app.utils.ml_models import MLPredictor
from TrinityEd_app.utils.risk_calculator import RiskCalculator
from TrinityEd_app.models import Alert, Student, Attendance, Performance
from TrinityEd_app.forms import StudentForm

logger = logging.getLogger(__name__)
User = get_user_model()

# ------------------- Fee Status -------------------
@login_required
def fee_status(request):
    # Sample student fee data (replace with real DB queries if needed)
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

# ------------------- Student Management -------------------
@login_required
def add_student(request):
    logged_in_students = User.objects.filter(last_login__isnull=False, role='student')
    existing_student_ids = Student.objects.values_list('user_id', flat=True)
    eligible_users = logged_in_students.exclude(id__in=existing_student_ids)

    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentForm()
        form.fields['user'].queryset = eligible_users

    return render(request, "add_student.html", {"form": form})

@login_required
def student_list(request):
    students = Student.objects.all()
    return render(request, "student_list.html", {"students": students})

@login_required
def learner_detail(request, pk):
    learner = get_object_or_404(User, pk=pk)
    return render(request, "learner_detail.html", {"learner": learner})

# ------------------- Dashboards -------------------
def home(request):
    return render(request, 'home.html')

@login_required
def mentor_dashboard(request, student_id=None):
    # Ensure the user is a mentor
    user = request.user
    if not (user.is_mentor or user.is_admin_user):
        return redirect('home')  # Redirect non-mentors to home

    # Determine if showing a specific student or all students
    if student_id:
        students = Student.objects.filter(id=student_id)  # Queryset for single student
        student = get_object_or_404(Student, id=student_id)
    else:
        student = None
        students = Student.objects.select_related("user").all()  # Queryset for all students

    # Core stats
    total_students = students.count()
    at_risk = students.filter(is_at_risk=True).count()
    alerts_sent = Alert.objects.count() if not student else Alert.objects.filter(student=student).count()

    # Attendance chart (avg by month/week)
    attendance_records = Attendance.objects.filter(student__in=students)[:6]
    attendance_labels = [a.date.strftime("%b %d") for a in attendance_records]
    attendance_data = [a.percentage for a in attendance_records]

    # Performance chart
    if student:
        subjects = Performance.objects.filter(student=student).values_list("subject", flat=True).distinct()
    else:
        subjects = Performance.objects.filter(student__in=students).values_list("subject", flat=True).distinct()
    performance_subjects = list(subjects)
    performance_data = [
        Performance.objects.filter(student__in=students, subject=sub).aggregate(avg=Avg("score"))["avg"] or 0
        for sub in performance_subjects
    ]

    # Risk Assessment + AI Insights
    risk_calc = RiskCalculator()
    ai_insights = AIInsightsGenerator()
    risk_data = risk_calc.calculate_all_risks(students)
    insights = ai_insights.generate_insights()  # Ensure ai_insights.py is updated to handle this

    # Convert complex data to JSON-serializable format
    def safe_json(data):
        if isinstance(data, dict):
            return {k: safe_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [safe_json(item) for item in data]
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            return str(data)  # Fallback for non-serializable types

    # Alerts (recent)
    alerts = Alert.objects.filter(student__in=students).order_by("-timestamp")[:5] if student else Alert.objects.all().order_by("-timestamp")[:5]

    context = {
        "student": student,  # Pass student if specific, None otherwise
        "total_students": total_students,
        "at_risk": at_risk,
        "alerts_sent": alerts_sent,
        "attendance_labels": json.dumps(attendance_labels),
        "attendance_data": json.dumps(attendance_data),
        "performance_subjects": json.dumps(performance_subjects),
        "performance_data": json.dumps(performance_data),
        "risk_data": safe_json(risk_data.to_dict('records')) if not risk_data.empty else [],
        "insights": safe_json(insights),
        "alerts": alerts,
    }
    return render(request, "mentor_dashboard.html", context)

# ------------------- Attendance -------------------
@login_required
def attendance_view(request):
    students = Student.objects.all()
    total_students = students.count()
    avg_attendance = Attendance.objects.aggregate(avg=Avg('percentage'))['avg'] or 0
    at_risk_students = students.filter(is_at_risk=True).count()

    student_attendance = []
    class_attendance = {}
    for student in students:
        latest_att = Attendance.objects.filter(student=student).order_by('-date').first()
        attendance_percent = latest_att.percentage if latest_att else student.attendance_percentage
        student_attendance.append({
            'name': student.user.username if student.user else student.name,
            'class_name': f"Class {student.id % 4 + 1}",
            'attendance': attendance_percent,
            'status': 'At Risk' if attendance_percent < 70 else 'Average' if attendance_percent < 80 else 'Good'
        })
        class_name = f"Class {student.id % 4 + 1}"
        class_attendance[class_name] = class_attendance.get(class_name, []) + [attendance_percent]

    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [sum(class_attendance.get(f"Class {i}", [0])) / len(class_attendance.get(f"Class {i}", [1])) for i in range(1, 5)]

    context = {
        'total_students': total_students,
        'avg_attendance': round(avg_attendance, 2),
        'at_risk_students': at_risk_students,
        'student_attendance': student_attendance,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'attendance.html', context)

# ------------------- Performance -------------------
@login_required
def performance_view(request):
    students = Student.objects.all()
    avg_score = Performance.objects.aggregate(avg=Avg('score'))['avg'] or 0
    top_student = students.order_by('-average_score').first()
    top_student_name = top_student.user.username if top_student else 'N/A'
    needs_improvement = students.filter(average_score__lt=70).count()

    highest_score = Performance.objects.aggregate(max_score=Max('score'))['max_score'] or 0
    lowest_score = Performance.objects.aggregate(min_score=Min('score'))['min_score'] or 0

    class_performance = {}
    for student in students:
        class_name = f"Class {student.id % 4 + 1}"
        class_performance[class_name] = class_performance.get(class_name, []) + [student.average_score]

    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [sum(class_performance.get(f"Class {i}", [0])) / len(class_performance.get(f"Class {i}", [1])) for i in range(1, 5)]

    good_count = students.filter(average_score__gte=80).count()
    average_count = students.filter(average_score__gte=70, average_score__lt=80).count()
    needs_improvement_count = students.filter(average_score__lt=70).count()

    context = {
        'avg_score': round(avg_score, 2),
        'top_student': top_student_name,
        'needs_improvement': needs_improvement,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'pie_data': json.dumps([good_count, average_count, needs_improvement_count]),
    }
    return render(request, 'performance.html', context)

# ------------------- Alerts -------------------
@login_required
def alerts_view(request):
    students = Student.objects.all()
    model_path = 'ml_models/at_risk_model.pkl'
    try:
        data = joblib.load(model_path)
        if isinstance(data, dict):
            model = data.get("model")
            scaler = data.get("scaler")
        else:
            model, scaler = data, None
        if not model:
            raise ValueError("Model missing inside saved file.")
    except Exception as e:
        return render(request, 'alerts.html', {'error': f'ML model error: {e}'})

    for student in students:
        features = np.array([[student.attendance_percentage, student.average_score]])
        if scaler:
            try:
                features = scaler.transform(features)
            except Exception:
                pass

        try:
            if model.predict(features)[0] == 1:
                Alert.objects.get_or_create(
                    student=student,
                    title=f"At-Risk Alert for {student.user.username}",
                    defaults={
                        'description': f"Low performance indicators detected "
                                       f"(Attendance: {student.attendance_percentage}%, "
                                       f"Score: {student.average_score}%).",
                        'type': 'danger',
                        'icon': 'warning'
                    }
                )
        except Exception:
            continue

    alerts_list = Alert.objects.filter(is_read=False).order_by('-timestamp')
    context = {"alerts": alerts_list}
    return render(request, "alerts.html", context)

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
    return JsonResponse({'status': 'error', 'message': 'Invalid request')

# ------------------- Student Dashboard -------------------
@login_required
def student(request):
    user = request.user
    attendance_weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    attendance_values = [a.percentage for a in Attendance.objects.filter(student__user=user).order_by('date')] if user.is_student else [0, 0, 0, 0]
    latest_attendance = attendance_values[-1] if attendance_values else 0

    performance_data = Performance.objects.filter(student__user=user).order_by('test_date')
    score_values = [p.score for p in performance_data] if performance_data.exists() else [0, 0, 0]
    while len(score_values) < 3: score_values.append(0)
    avg_score = sum(score_values) / len(score_values) if score_values else 0
    is_at_risk = latest_attendance < 75 or avg_score < 70

    messages = []
    if latest_attendance < 80: messages.append(f"⚠️ Your attendance dropped below {latest_attendance}%.")
    if score_values[-1] > 70: messages.append("✅ Good improvement in recent test!")

    context = {
        "student_name": user.get_full_name() or user.username,
        "attendance": latest_attendance,
        "avg_score": round(avg_score, 2),
        "dropout_risk": "High" if is_at_risk else "Low",
        "role": user.role,
        "attendance_weeks": json.dumps(attendance_weeks),
        "attendance_values": json.dumps(attendance_values[:4]),
        "score_tests": json.dumps(["Test 1", "Test 2", "Test 3"]),
        "score_values": json.dumps(score_values[:3]),
        "messages": messages
    }
    return render(request, "student.html", context)

# ------------------- Other Pages -------------------
@login_required
def progress(request):
    return render(request, "progress.html")

@login_required
def counselling(request):
    return render(request, "counselling.html")

@login_required
def resources(request):
    return render(request, "resources.html")