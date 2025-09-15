import os
import pandas as pd
import numpy as np
from trinity_app.models import Student, Attendance, Performance
from trinity_app.utils.ml_models import MLPredictor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
logger.info(f"Changed working directory to: {project_root}")

try:
    # Fetch student data from Django models
    students = Student.objects.select_related('user').all()
    students_data = []
    for student in students:
        latest_attendance = Attendance.objects.filter(student=student).order_by('-recorded_date').first()
        avg_score = Performance.objects.filter(student=student).aggregate(Avg('score'))['score__avg'] or 0
        students_data.append({
            'student_id': student.enrollment_no,
            'attendance_rate': latest_attendance.percentage if latest_attendance else student.attendance_percentage,
            'current_gpa': student.average_score / 25,  # Convert to GPA scale
            'behavioral_incidents': 0,  # Add logic if incidents are tracked
            'risk_level': 'High' if student.is_at_risk else 'Low'
        })
    students_data = pd.DataFrame(students_data)
    
    if students_data.empty:
        raise ValueError("No student data available for training.")
    logger.info("Student data loaded successfully.")

    # Initialize MLPredictor
    ml_predictor = MLPredictor()
    logger.info("MLPredictor initialized.")

    # Prepare features and labels
    features = ml_predictor.prepare_features(students_data)
    labels = ml_predictor.create_risk_labels(students_data)
    if features.size == 0 or labels.size == 0:
        raise ValueError("Feature or label preparation failed.")
    logger.info("Features and labels prepared successfully.")
    logger.info(f"Labels unique counts: {np.unique(labels, return_counts=True)}")

    # Train and save models
    models = ['Random Forest', 'Logistic Regression']
    save_path = os.path.join(project_root, 'ml_models/at_risk_model.pkl')
    for model_name in models:
        logger.info(f"Training {model_name} model...")
        success = ml_predictor.train_model(model_name, features, labels)
        if success:
            logger.info(f"{model_name} model trained successfully.")
        else:
            logger.warning(f"{model_name} model training failed.")
        ml_predictor.save_model(model_name, save_path)
        logger.info(f"{model_name} model saved to {save_path}.")

except Exception as e:
    logger.error(f"Error during training: {str(e)}")
    raise

logger.info("Training process completed.")