from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Avg, Max, Min
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import User
import json
from django.shortcuts import render



from TrinityEd_app.utils.ai_insights import AIInsightsGenerator
from TrinityEd_app.utils.ml_models import MLPredictor
from TrinityEd_app.utils.risk_calculator import RiskCalculator
import joblib
import numpy as np
from TrinityEd_app.models import Alert, Student, Attendance, Performance
from TrinityEd_app.forms import StudentForm  # make sure this exists


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

User = get_user_model()

# ------------------- Student Management -------------------

@login_required
def add_student(request):
    # Logged-in users with role='student'
    logged_in_students = User.objects.filter(last_login__isnull=False, role='student')
    existing_student_ids = Student.objects.values_list('user_id', flat=True)
    eligible_users = logged_in_students.exclude(id__in=existing_student_ids)

    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('learner_list')
    else:
        form = StudentForm()
        form.fields['user'].queryset = eligible_users

    return render(request, "add_student.html", {"form": form})


@login_required
def studnet_list(request):
    # Sirf un Learners ko lo jinka linked User student hai
    learners = User.objects.select_related("user").filter(user__role="student")
    return render(
        request,
        "student_list.html",   # 👈 full path dena zaroori hai
        {"students": learners}
    )


@login_required
def learner_detail(request, pk):
    learner = get_object_or_404(User, pk=pk)
    return render(request, "learner_detail.html", {"learner": learner})


# ------------------- Dashboards -------------------


def home(request):
    return render(request, 'home.html')




def mentor_dashboard(request):
    try:
        risk_calculator = RiskCalculator()
        risk_data = risk_calculator.calculate_all_risks()

        # Add hyphenated risk_level to risk_data
        risk_data_dict = risk_data.to_dict('records')
        for student in risk_data_dict:
            student['risk_level_hyphenated'] = student['risk_level'].lower().replace(' ', '-')

        ai_insights = AIInsightsGenerator()  # Adjusted per latest ai_insights.py
        insights = ai_insights.generate_insights()

        # Example data; replace with real queries
        attendance_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        attendance_data = [95, 92, 90, 88]
        performance_subjects = ['Math', 'Science', 'English']
        performance_data = [85, 78, 82]
        alerts = [
            {'student': 'John Doe', 'issue': 'Low attendance (<70%)'},
            {'student': 'Jane Smith', 'issue': 'GPA dropped below 2.0'}
        ]

        context = {
            'risk_data': risk_data_dict,
            'insights': insights,
            'attendance_labels': json.dumps(attendance_labels),
            'attendance_data': json.dumps(attendance_data),
            'performance_subjects': json.dumps(performance_subjects),
            'performance_data': json.dumps(performance_data),
            'total_students': len(risk_data),
            'at_risk': sum(1 for row in risk_data_dict if row['risk_level'] in ['Very High', 'High']),
            'alerts_sent': len(alerts),
            'alerts': alerts
        }
        return render(request, 'mentor_dashboard.html', context)
    except Exception as e:
        print(f"Error in mentor_dashboard: {e}")
        return render(request, 'mentor_dashboard.html', {})
# ------------------- Attendance -------------------

@login_required
def attendance_view(request):
    students = Student.objects.all()
    total_students = students.count()
    avg_attendance = Attendance.objects.aggregate(avg=Avg('percentage'))['avg'] or 0
    at_risk_students = Student.objects.filter(is_at_risk=True).count()

    student_attendance = []
    class_attendance = {}
    for student in students:
        latest_att = Attendance.objects.filter(student=student).order_by('-date').first()
        attendance_percent = latest_att.percentage if latest_att else student.attendance_percentage
        student_attendance.append({
            'name': student.user.username if student.user else student.name,  # Fallback to student.name
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
    top_student = Student.objects.order_by('-average_score').first()
    top_student_name = top_student.user.username if top_student else 'N/A'
    needs_improvement = Student.objects.filter(average_score__lt=70).count()

    highest_score = Performance.objects.aggregate(max_score=Max('score'))['max_score'] or 0
    lowest_score = Performance.objects.aggregate(min_score=Min('score'))['min_score'] or 0

    class_performance = {}
    for student in students:
        class_name = f"Class {student.id % 4 + 1}"
        class_performance[class_name] = class_performance.get(class_name, []) + [student.average_score]

    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [sum(class_performance.get(f"Class {i}", [0])) / len(class_performance.get(f"Class {i}", [1])) for i in range(1, 5)]

    good_count = Student.objects.filter(average_score__gte=80).count()
    average_count = Student.objects.filter(average_score__gte=70, average_score__lt=80).count()
    needs_improvement_count = Student.objects.filter(average_score__lt=70).count()

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
            continue  # skip prediction errors safely

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
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# ------------------- Student Dashboard -------------------

@login_required
def student(request):
    user = request.user
    attendance_weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    attendance_values = [a.percentage for a in Attendance.objects.filter(student__user=user).order_by('week')] if user.is_student else [0,0,0,0]
    latest_attendance = attendance_values[-1] if attendance_values else 0

    performance_data = Performance.objects.filter(student__user=user).order_by('test_date')
    score_values = [p.score for p in performance_data] if performance_data.exists() else [0,0,0]
    while len(score_values) < 3: score_values.append(0)
    avg_score = sum(score_values)/len(score_values) if score_values else 0
    is_at_risk = latest_attendance < 75 or avg_score < 70

    messages = []
    if latest_attendance < 80: messages.append(f"⚠️ Your attendance dropped below {latest_attendance}%.")
    if score_values[-1] > 70: messages.append("✅ Good improvement in recent test!")

    context = {
        "student_name": user.get_full_name() or user.username,
        "attendance": latest_attendance,
        "avg_score": round(avg_score,2),
        "dropout_risk": "High" if is_at_risk else "Low",
        "role": user.role,
        "attendance_weeks": json.dumps(attendance_weeks),
        "attendance_values": json.dumps(attendance_values[:4]),
        "score_tests": json.dumps(["Test 1","Test 2","Test 3"]),
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

# TrinityEd_app/views.py
from django.shortcuts import render
from .models import Student

def student_list(request):   # ❌ 'studnet_list' se ❌
    students = Student.objects.all()
    return render(request, 'student_list.html', {'students': students})
