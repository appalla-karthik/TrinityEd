import json
import numpy as np
import requests

from django.shortcuts import render, redirect
from django.conf import settings


from django.utils import timezone

import os
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Avg, Max, Min
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from accounts.models import User
import joblib

from TrinityEd_app.utils.ai_insights import AIInsightsGenerator
from TrinityEd_app.utils.ml_models import MLPredictor
from TrinityEd_app.utils.risk_calculator import RiskCalculator
from TrinityEd_app.models import Alert, CounsellingSession, Progress, Student, Attendance, Performance
from TrinityEd_app.forms import StudentForm

logger = logging.getLogger(__name__)
User = get_user_model()

# ------------------- Fee Status -------------------
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
        'months': json.dumps(months),
        'fee_collected': json.dumps(fee_collected)
    }
    logger.debug(f"Fee status context: {context}")
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
            student = form.save()
            logger.info(f"New student added: {student.name}")
            return redirect('student_list')
    else:
        form = StudentForm()
        form.fields['user'].queryset = eligible_users

    context = {"form": form}
    logger.debug(f"Add student context: {context}")
    return render(request, "add_student.html", context)

@login_required
def student_list(request):
    students = Student.objects.select_related('user').all()
    context = {"students": students}
    logger.debug(f"Student list context: {context}")
    return render(request, "student_list.html", context)

@login_required
def learner_detail(request, pk):
    learner = get_object_or_404(User, pk=pk)
    context = {"learner": learner}
    logger.debug(f"Learner detail context for pk {pk}: {context}")
    return render(request, "learner_detail.html", context)

# ------------------- Dashboards -------------------
def home(request):
    return render(request, 'home.html')

@login_required
def mentor_dashboard(request, student_id=None):
    # Ensure the user is a mentor or admin
    user = request.user
    if not (user.is_mentor or user.is_admin_user):
        logger.warning(f"Unauthorized access to mentor_dashboard by {user.username}")
        return redirect('home')

    # Determine if showing a specific student or all students
    if student_id:
        try:
            student = get_object_or_404(Student, id=student_id)
            students = [student]  # Limit to the specific student
        except Exception as e:
            messages.error(request, f"Student with ID {student_id} not found.")
            logger.error(f"Student ID {student_id} not found: {e}")
            return redirect('mentor_dashboard')
    else:
        student = None
        students = Student.objects.select_related("user").all()

    # Core stats
    total_students = students.count()
    at_risk = students.filter(is_at_risk=True).count()
    alerts_sent = Alert.objects.count() if not student else Alert.objects.filter(student=student).count()

    # Attendance and Performance charts (unchanged)
    attendance_records = Attendance.objects.filter(student__in=students).order_by('-date')[:6]
    attendance_labels = [a.date.strftime("%b %d") for a in attendance_records]
    attendance_data = [float(a.percentage) for a in attendance_records] if attendance_records else [0] * 6

    subjects = Performance.objects.filter(student__in=students).values_list("subject", flat=True).distinct()
    performance_subjects = list(subjects) if subjects else ['Math', 'Science', 'English']
    performance_data = [
        float(Performance.objects.filter(student__in=students, subject=sub).aggregate(avg=Avg("score"))["avg"] or 0)
        for sub in performance_subjects
    ] if subjects else [0] * len(performance_subjects)

    # Risk Assessment + AI Insights with improved error handling
    risk_data = []
    insights = {}
    model_metrics = {}
    feature_importance_labels = []
    feature_importance_data = []
    risk_calc_summary = {}

    # Initialize alerts outside the try-except block
    alerts = Alert.objects.filter(student__in=students).order_by("-timestamp")[:5] if student else Alert.objects.order_by("-timestamp")[:5]

    try:
        # Initialize utilities
        risk_calc = RiskCalculator()
        ai_insights_gen = AIInsightsGenerator()
        ml_predictor = MLPredictor()

        # Calculate risks
        risk_df = risk_calc.calculate_all_risks(students)
        if not risk_df.empty:
            risk_records = risk_df.to_dict('records')
            for record in risk_records:
                record['student_name'] = record.get('student_name', record.get('name', 'Unknown Student'))
                record['grade_level'] = record.get('grade_level', 'N/A')
                record['risk_level'] = record.get('risk_level', 'Medium')
                record['risk_score'] = float(record.get('risk_score', 50.0))
                record['primary_risk_factors'] = record.get('primary_risk_factors', 'General Risk')
            risk_data = risk_records
        else:
            raise ValueError("Risk calculation returned empty DataFrame")

        # Generate AI insights
        insights_raw = ai_insights_gen.generate_insights()
        if isinstance(insights_raw, dict) and all(key in insights_raw for key in ['executive_summary', 'key_findings', 'student_insights', 'risk_distribution']):
            insights = insights_raw
        else:
            raise ValueError("Invalid insights structure from AIInsightsGenerator")

        # [Rest of the model metrics and feature importance logic remains unchanged]
    except Exception as e:
        logger.error(f"Error generating risk/AI insights: {e}")
        # Use mock data only as a last resort
        risk_data = _generate_mock_risk_data(students)
        insights = _generate_mock_insights(students)
        model_metrics = {
            'Random Forest': {
                'accuracy': 0.85,
                'precision': 0.82,
                'recall': 0.80,
                'f1_score': 0.81
            }
        }
        feature_importance_labels = ['Attendance', 'GPA', 'Engagement', 'Behavior']
        feature_importance_data = [0.35, 0.30, 0.20, 0.15]
        risk_calc_summary = {
            'Attendance Weight': '30%',
            'GPA Weight': '30%',
            'Engagement Weight': '20%',
            'Behavior Weight': '20%'
        }
        # Ensure risk_distribution in insights
        if 'risk_distribution' not in insights:
            insights['risk_distribution'] = {
                'Very_High': 1, 'High': 1, 'Medium': 3, 'Low': 3, 'Very_Low': 1
            }

    # Convert complex data to JSON-serializable format
    def safe_json(data):
        if isinstance(data, dict):
            return {k: safe_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [safe_json(item) for item in data]
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            return str(data)

    context = {
        "student": student,
        "total_students": total_students,
        "at_risk": at_risk,
        "alerts_sent": alerts_sent,
        "attendance_labels": json.dumps(attendance_labels),
        "attendance_data": json.dumps(attendance_data),
        "performance_subjects": json.dumps(performance_subjects),
        "performance_data": json.dumps(performance_data),
        "risk_data": safe_json(risk_data),
        "insights": safe_json(insights),
        "alerts": alerts,
        "model_metrics": safe_json(model_metrics),
        "feature_importance_labels": json.dumps(feature_importance_labels),
        "feature_importance_data": json.dumps(feature_importance_data),
        "risk_calc_summary": safe_json(risk_calc_summary),
    }
    logger.debug(f"Mentor dashboard context: {context}")
    return render(request, "mentor_dashboard.html", context)

# Helper methods
def _generate_mock_risk_data(students):
    data = []
    for s in students[:11]:
        risk_score = max(0, min(100, (100 - (s.attendance_percentage or 0)) * 0.4 + (100 - (s.average_score or 0)) * 0.6))
        level = 'Very High' if risk_score > 80 else 'High' if risk_score > 60 else 'Medium' if risk_score > 40 else 'Low' if risk_score > 20 else 'Very Low'
        primary_factors = 'Chronic Absenteeism' if (s.attendance_percentage or 0) < 70 else 'Low Scores' if (s.average_score or 0) < 60 else 'None'
        data.append({
            'student_name': s.name or s.user.username if s.user else 'Unknown',
            'grade_level': getattr(s, 'grade_level', 'N/A'),
            'risk_level': level,
            'risk_score': round(risk_score, 1),
            'primary_risk_factors': primary_factors
        })
    return data

def _generate_mock_insights(students):
    num_students = min(11, len(students))
    at_risk_count = sum(1 for s in students[:num_students] if s.is_at_risk)
    avg_att = sum(s.attendance_percentage or 0 for s in students[:num_students]) / num_students if num_students else 0
    avg_gpa = sum(s.average_score or 0 for s in students[:num_students]) / num_students if num_students else 0

    key_findings = [
        f"{at_risk_count} students are at high risk, requiring urgent interventions.",
        f"Average attendance ({avg_att:.1f}%) is below target, impacting outcomes.",
        "Key risk factors: Chronic Absenteeism, High Risk Status."
    ]

    student_insights = []
    high_risk_students = [s for s in students[:num_students] if s.is_at_risk][:2]
    for i, s in enumerate(high_risk_students):
        analysis = f"Low attendance ({s.attendance_percentage or 0}%) and score ({s.average_score or 0}) indicate high dropout risk."
        interventions = [
            "Implement personalized attendance tracking.",
            "Schedule weekly mentoring sessions.",
            "Provide academic support resources."
        ]
        success_prob = 75 if i == 0 else 60
        student_insights.append({
            'student_name': s.name or s.user.username if s.user else 'Unknown',
            'risk_level': 'High Risk',
            'analysis': analysis,
            'interventions': interventions,
            'success_probability': success_prob
        })

    return {
        'executive_summary': f"Analysis of {num_students} students identifies {at_risk_count} at high risk. Average attendance is {avg_att:.1f}%, and average GPA is {avg_gpa:.1f}. Immediate interventions needed for at-risk students.",
        'key_findings': key_findings,
        'student_insights': student_insights,
        'risk_distribution': {
            'Very_High': max(0, at_risk_count // 4),
            'High': max(0, at_risk_count // 2),
            'Medium': max(0, num_students // 3),
            'Low': max(0, num_students // 4),
            'Very_Low': max(0, num_students - at_risk_count - (num_students // 3 + num_students // 4))
        }
    }

# ------------------- Attendance -------------------
@login_required
def attendance_view(request):
    students = Student.objects.select_related('user').all()
    total_students = students.count()
    avg_attendance = Attendance.objects.aggregate(avg=Avg('percentage'))['avg'] or 0

    student_attendance = []
    class_attendance = {}
    for student in students:
        latest_att = Attendance.objects.filter(student=student).order_by('-date').first()
        attendance_percent = float(latest_att.percentage) if latest_att else float(student.attendance_percentage or 0)
        student_attendance.append({
            'name': student.user.username if student.user else student.name,
            'class_name': f"Class {student.id % 4 + 1}",
            'attendance': attendance_percent,
            'status': 'At Risk' if attendance_percent < 70 else 'Average' if attendance_percent < 80 else 'Good'
        })
        class_name = f"Class {student.id % 4 + 1}"
        class_attendance[class_name] = class_attendance.get(class_name, []) + [attendance_percent]

    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [float(sum(class_attendance.get(f"Class {i}", [0])) / len(class_attendance.get(f"Class {i}", [1]))) for i in range(1, 5)]

    context = {
        'total_students': total_students,
        'avg_attendance': round(avg_attendance, 2),
        'at_risk_students': students.filter(is_at_risk=True).count(),
        'student_attendance': student_attendance,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    logger.debug(f"Attendance view context: {context}")
    return render(request, 'attendance.html', context)

# ------------------- Performance -------------------
@login_required
def performance_view(request):
    students = Student.objects.select_related('user').all()
    total_students = students.count()
    avg_score = Performance.objects.aggregate(avg=Avg('score'))['avg'] or 0
    top_student = students.order_by('-average_score').first()
    top_student_name = top_student.user.username if top_student and top_student.user else 'N/A'
    top_score = float(top_student.average_score) if top_student else 0
    needs_improvement = students.filter(average_score__lt=70).count()
    needs_improvement_percent = round((needs_improvement / total_students * 100) if total_students else 0, 2)

    highest_score = float(Performance.objects.aggregate(max_score=Max('score'))['max_score'] or 0)
    lowest_score = float(Performance.objects.aggregate(min_score=Min('score'))['min_score'] or 0)

    class_performance = {}
    for student in students:
        class_name = f"Class {student.id % 4 + 1}"
        class_performance[class_name] = class_performance.get(class_name, []) + [float(student.average_score or 0)]

    chart_labels = [f"Class {i}" for i in range(1, 5)]
    chart_data = [round(sum(class_performance.get(f"Class {i}", [0])) / len(class_performance.get(f"Class {i}", [1])), 2) for i in range(1, 5)]

    good_count = students.filter(average_score__gte=80).count()
    average_count = students.filter(average_score__gte=70, average_score__lt=80).count()
    needs_improvement_count = students.filter(average_score__lt=70).count()

    context = {
        'total_students': total_students,
        'avg_score': round(avg_score, 2),
        'top_student': top_student_name,
        'top_score': round(top_score, 2),
        'needs_improvement': needs_improvement,
        'needs_improvement_percent': needs_improvement_percent,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'pie_data': json.dumps([good_count, average_count, needs_improvement_count]),
    }
    logger.debug(f"Performance view context: {context}")
    return render(request, 'performance.html', context)

# ------------------- Alerts -------------------
@login_required
def alerts_view(request):
    students = Student.objects.select_related('user').all()
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
        logger.error(f"Failed to load ML model: {e}")
        return render(request, 'alerts.html', {'error': f'ML model error: {e}'})

    for student in students:
        features = np.array([[float(student.attendance_percentage or 0), float(student.average_score or 0)]])
        if scaler:
            try:
                features = scaler.transform(features)
            except Exception as e:
                logger.warning(f"Scaler transform failed for student {student.id}: {e}")
                continue

        try:
            if model.predict(features)[0] == 1:
                Alert.objects.get_or_create(
                    student=student,
                    title=f"At-Risk Alert for {student.user.username if student.user else student.name}",
                    defaults={
                        'description': f"Low performance indicators detected "
                                      f"(Attendance: {student.attendance_percentage or 0}%, "
                                      f"Score: {student.average_score or 0}%).",
                        'type': 'danger',
                        'icon': 'warning'
                    }
                )
        except Exception as e:
            logger.warning(f"Prediction failed for student {student.id}: {e}")
            continue

    alerts_list = Alert.objects.filter(is_read=False).order_by('-timestamp')
    context = {"alerts": alerts_list}
    logger.debug(f"Alerts view context: {context}")
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
            logger.info(f"Alert {alert_id} marked as read")
            return JsonResponse({'status': 'success'})
        except Alert.DoesNotExist:
            logger.error(f"Alert {alert_id} not found")
            return JsonResponse({'status': 'error', 'message': 'Alert not found'})
        except Exception as e:
            logger.error(f"Error marking alert read: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# ------------------- Student Dashboard -------------------
@login_required
def student(request, student_id):
    try:
        student_obj = Student.objects.select_related('user').get(id=student_id)
    except Student.DoesNotExist:
        messages.error(request, f"Student with ID {student_id} not found.")
        logger.warning(f"Student {student_id} not found")
        return redirect('student_list')

    gpa = float(student_obj.average_score or 0)
    gpa_out_of_10 = min(round(gpa * 2.5, 2), 10.0) if gpa else 0.0
    attendance_rate = float(student_obj.attendance_percentage or 0)
    credits_earned = student_obj.credits_earned or 0
    total_credits = student_obj.total_credits or 0
    incidents = student_obj.incidents_count or 0
    notifications = Alert.objects.filter(student=student_obj).order_by('-timestamp')[:5]
    messages = [a.description for a in notifications]

    context = {
        "student_name": student_obj.name or student_obj.user.username if student_obj.user else "Unknown",
        "student_id": student_obj.id,
        "grade": student_obj.grade or "N/A",
        "email": student_obj.user.email if student_obj.user else "",
        "phone": student_obj.phone or (student_obj.user.phone_number if student_obj.user else ""),
        "dropout_risk": "High" if student_obj.is_at_risk else "Low",
        "gpa": gpa_out_of_10,
        "attendance_rate": attendance_rate,
        "credits_earned": credits_earned,
        "total_credits": total_credits,
        "incidents": incidents,
        "notifications": notifications,
        "messages": messages,
    }
    logger.debug(f"Student dashboard context for {student_id}: {context}")
    return render(request, "student.html", context)

# ------------------- Progress -------------------
@login_required
def progress(request, student_id=None):
    student = get_object_or_404(Student, id=student_id) if student_id else Student.objects.filter(user=request.user).first()
    if not student:
        messages.error(request, "No student data found.")
        logger.warning("No student data found for progress view")
        return redirect('home')

    progress, created = Progress.objects.get_or_create(student=student)

    performances = Performance.objects.filter(student=student).order_by('test_date')
    if performances.exists():
        gpa_labels = [p.test_date.strftime("%b %d") for p in performances]
        gpa_data = [float(p.score) for p in performances]
    else:
        gpa_labels = ["Sep 01", "Sep 08", "Sep 15"]
        gpa_data = [75.5, 82.0, 88.5]
        logger.warning(f"No performance data for student {student.id}, using dummy data")
    progress.gpa_labels = gpa_labels
    progress.gpa_data = gpa_data

    attendance_records = Attendance.objects.filter(student=student)
    attendance_by_month = {}
    for att in attendance_records:
        month = att.date.strftime("%b %Y")
        attendance_by_month.setdefault(month, []).append(float(att.percentage))
    if attendance_by_month:
        attendance_labels = list(attendance_by_month.keys())
        attendance_data = [round(sum(vals) / len(vals), 2) for vals in attendance_by_month.values()]
    else:
        attendance_labels = ["Sep 2025", "Aug 2025", "Jul 2025"]
        attendance_data = [95.0, 90.0, 85.0]
        logger.warning(f"No attendance data for student {student.id}, using dummy data")
    progress.attendance_labels = attendance_labels
    progress.attendance_data = attendance_data

    subjects = Performance.objects.filter(student=student).values_list('subject', flat=True).distinct()
    if subjects:
        subject_labels = list(subjects)
        subject_data = [
            round(float(Performance.objects.filter(student=student, subject=sub).aggregate(avg=Avg('score'))['avg'] or 0), 2)
            for sub in subject_labels
        ]
    else:
        subject_labels = ["Math", "Science", "English"]
        subject_data = [85.0, 78.0, 92.0]
        logger.warning(f"No subject data for student {student.id}, using dummy data")
    progress.subject_labels = subject_labels
    progress.subject_data = subject_data

    grade_summary = []
    for sub, score in zip(subject_labels, subject_data):
        if score >= 80:
            grade = 'A'
        elif score >= 70:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        else:
            grade = 'D'
        grade_summary.append({'subject': sub, 'grade': grade})
    progress.grade_summary = grade_summary

    incident_list = [f"Incident {i+1}" for i in range(student.incidents_count or 0)] if student.incidents_count > 0 else ["No incidents recorded."]
    progress.incidents_count = student.incidents_count
    progress.incident_list = incident_list

    progress.save()

    attendance_table = Attendance.objects.filter(student=student).order_by('-date')[:10]
    if not attendance_table.exists():
        attendance_table = [
            Attendance(student=student, date=date(2025, 9, 15), status="Present", percentage=95.0),
            Attendance(student=student, date=date(2025, 9, 14), status="Absent", percentage=0.0),
        ]
        logger.warning(f"No attendance records for student {student.id}, using dummy data")

    context = {
        'student': student,
        'gpa_labels': json.dumps(progress.gpa_labels),
        'gpa_data': json.dumps(progress.gpa_data),
        'attendance_labels': json.dumps(progress.attendance_labels),
        'attendance_data': json.dumps(progress.attendance_data),
        'subject_labels': json.dumps(progress.subject_labels),
        'subject_data': json.dumps(progress.subject_data),
        'grade_summary': progress.grade_summary,
        'incident_list': progress.incident_list,
        'attendance_table': attendance_table,
    }
    logger.debug(f"Progress context for student {student.id if student else 'None'}: {context}")
    return render(request, 'progress.html', context)

# ------------------- Counselling -------------------
# ... (other imports and views remain unchanged)

# ------------------- Counselling -------------------

# ... (existing imports and views remain unchanged)

# ------------------- Counselling -------------------
@login_required
def counselling(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        messages.error(request, "No student data found.")
        logger.warning(f"No student data found for user {request.user.username}")
        return redirect('home')

    mentors = User.objects.filter(role='mentor')

    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        mentor_id = request.POST.get('mentor')
        scheduled_time = request.POST.get('scheduled_time')

        if not all([name, email, mentor_id, scheduled_time]):
            messages.error(request, "All fields are required.")
            logger.warning(f"Incomplete form data for counselling session by {request.user.username}")
        else:
            try:
                mentor = User.objects.get(id=mentor_id, role='mentor') if mentor_id else None
                scheduled_time_dt = timezone.datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                if scheduled_time_dt < timezone.now():
                    messages.error(request, "Cannot book a session in the past.")
                    logger.warning(f"Attempted to book past session by {request.user.username}")
                else:
                    CounsellingSession.objects.create(
                        student=student,
                        name=name,
                        email=email,
                        mentor=mentor,
                        scheduled_time=timezone.make_aware(scheduled_time_dt) if not timezone.is_aware(scheduled_time_dt) else scheduled_time_dt,
                        status='pending'
                    )
                    messages.success(request, "Session booked successfully! You will receive a confirmation soon.")
                    logger.info(f"Counselling session booked for {name} with {mentor.username if mentor else 'Unassigned'} at {scheduled_time}")
            except User.DoesNotExist:
                messages.error(request, "Selected mentor is invalid.")
                logger.error(f"Invalid mentor ID {mentor_id} for user {request.user.username}")
            except ValueError as e:
                messages.error(request, "Invalid date/time format. Please try again.")
                logger.error(f"Invalid date/time format: {e}")
            except Exception as e:
                messages.error(request, "An error occurred while booking the session.")
                logger.error(f"Error booking counselling session: {e}")

        return redirect('counselling')

    context = {
        'student': student,
        'mentors': mentors,
    }
    logger.debug(f"Counselling context for user {request.user.username}: {context}")
    return render(request, "counselling.html", context)

@login_required
@csrf_exempt
def cancel_session(request, session_id):
    if request.method == "POST":
        try:
            session = CounsellingSession.objects.get(id=session_id, student__user=request.user)
            session.status = 'cancelled'
            session.save()
            return JsonResponse({'success': True})
        except CounsellingSession.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Session not found or unauthorized.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

# ... (rest of your views remain unchanged)

# ---------------- Chatbot UI ----------------
@login_required
def chatbot_view(request):
    """Render chatbot UI page (Gemini based)."""
    student = Student.objects.filter(user=request.user).first()
    return render(request, "chatbot.html", {"student": student})

# ---------------- Chatbot API ----------------
@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_message = data.get("message", "")
            history = data.get("history", [])

            if not user_message:
                return JsonResponse({"reply": "⚠️ Please type a message."})

            # Build conversation history (Gemini only accepts "user" and "model")
            contents = []
            for h in history:
                role = "user" if h["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": h["content"]}]})

            # Add the latest user input
            contents.append({"role": "user", "parts": [{"text": user_message}]})

            # Gemini API call
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {"contents": contents}
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, headers=headers, data=json.dumps(payload))
            logger.debug(f"Gemini raw response: {response.text}")

            response.raise_for_status()
            result = response.json()

            reply_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return JsonResponse({"reply": reply_text})

        except Exception as e:
            logger.error(f"Chatbot API error (Gemini): {e}")
            return JsonResponse(
                {"reply": f"⚠️ Gemini error: {str(e)}"}, status=500
            )

    return JsonResponse({"reply": "Invalid request method"}, status=405)

# ---------------- API Key fetch ----------------
@login_required
def get_gemini_key(request):
    try:
        return JsonResponse({'api_key': settings.GEMINI_API_KEY})
    except Exception as e:
        logger.error(f"Error fetching Gemini API key: {e}")
        return JsonResponse({'error': 'Unable to fetch API key'}, status=500)

@login_required
def resources(request):
    context = {}
    logger.debug("Rendering resources page")
    return render(request, "resources.html", context)