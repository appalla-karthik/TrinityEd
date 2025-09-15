import os
import django
import pandas as pd
import numpy as np
import logging
from django.db.models import Avg

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TrinityEd_project.settings")
django.setup()

from trinity_app.models import Student, Attendance, Performance
from trinity_app.utils.ml_models import MLPredictor

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_student_data():
    """Fetch and preprocess student data from Django models."""
    students = Student.objects.select_related('user').all()
    students_data = []

    for student in students:
        # Latest attendance
        latest_attendance = (
            Attendance.objects.filter(student=student)
            .order_by('-recorded_date')
            .first()
        )

        # Average performance score
        avg_score = (
            Performance.objects.filter(student=student)
            .aggregate(avg=Avg('score'))['avg'] or 0
        )

        students_data.append({
            'student_id': student.enrollment_no,
            'attendance_rate': latest_attendance.percentage if latest_attendance else student.attendance_percentage,
            'current_gpa': student.average_score / 25,  # normalize to GPA scale
            'behavioral_incidents': 0,  # placeholder
            'risk_level': 'High' if student.is_at_risk else 'Low'
        })

    return pd.DataFrame(students_data)


def train_and_save_models():
    """Train ML models using student data and save them."""
    try:
        students_data = fetch_student_data()

        if students_data.empty:
            raise ValueError("No student data available for training.")
        logger.info("Student data loaded successfully.")

        ml_predictor = MLPredictor()
        logger.info("MLPredictor initialized.")

        features = ml_predictor.prepare_features(students_data)
        labels = ml_predictor.create_risk_labels(students_data)

        if features.size == 0 or labels.size == 0:
            raise ValueError("Feature or label preparation failed.")
        logger.info("Features and labels prepared successfully.")
        logger.info(f"Labels distribution: {np.unique(labels, return_counts=True)}")

        models = ['Random Forest', 'Logistic Regression']
        save_path = os.path.join(
            os.path.dirname(__file__), 'ml_models', 'at_risk_model.pkl'
        )

        for model_name in models:
            logger.info(f"Training {model_name}...")
            success = ml_predictor.train_model(model_name, features, labels)
            if success:
                logger.info(f"{model_name} trained successfully.")
                ml_predictor.save_model(model_name, save_path)
                logger.info(f"{model_name} saved to {save_path}.")
            else:
                logger.warning(f"{model_name} training failed.")

    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        raise

    logger.info("Training process completed.")


if __name__ == "__main__":
    train_and_save_models()
