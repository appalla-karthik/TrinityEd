import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Import Django models for fetching real data
from TrinityEd_app.models import Student, Attendance, Performance

class MLPredictor:
    """
    Machine Learning Predictor class for student dropout risk prediction.
    Implements multiple ML models and provides prediction capabilities.
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.label_encoders = {}
        self.model_metrics = {}
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize ML models."""
        self.models = {
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
            'XGBoost': RandomForestClassifier(n_estimators=150, random_state=42),  # Placeholder for XGBoost
            'Neural Network': RandomForestClassifier(n_estimators=120, random_state=42)  # Placeholder for NN
        }
        
        for model_name in self.models.keys():
            self.scalers[model_name] = StandardScaler()
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML models."""
        try:
            if data.empty:
                return pd.DataFrame()
            
            # Feature engineering
            features = pd.DataFrame()
            
            # Basic features
            features['attendance_rate'] = data.get('attendance_rate', 0)
            features['current_gpa'] = data.get('current_gpa', 0)
            features['behavioral_incidents'] = data.get('behavioral_incidents', 0)
            features['grade_level'] = data.get('grade_level', 9)
            
            # Derived features
            features['gpa_attendance_ratio'] = features['current_gpa'] / (features['attendance_rate'] + 1)
            risk_score_data = data.get('risk_score', 0)
            risk_score_data = risk_score_data if risk_score_data is not None else 0
            features['risk_score_normalized'] = risk_score_data / 10.0
            features['incidents_per_month'] = features['behavioral_incidents'] / 9  # Assuming 9-month school year
            
            # Grade level encoding
            features['is_freshman'] = (features['grade_level'] == 9).astype(int)
            features['is_sophomore'] = (features['grade_level'] == 10).astype(int)
            features['is_junior'] = (features['grade_level'] == 11).astype(int)
            features['is_senior'] = (features['grade_level'] == 12).astype(int)
            
            # Risk categories
            features['low_attendance'] = (features['attendance_rate'] < 85).astype(int)
            features['low_gpa'] = (features['current_gpa'] < 2.5).astype(int)
            features['high_incidents'] = (features['behavioral_incidents'] > 3).astype(int)
            
            # Interaction features
            features['gpa_grade_interaction'] = features['current_gpa'] * features['grade_level']
            features['attendance_incidents_interaction'] = features['attendance_rate'] * features['behavioral_incidents']
            
            self.feature_columns = list(features.columns)
            return features
            
        except Exception as e:
            print(f"Error preparing features: {e}")
            return pd.DataFrame()
    
    def create_risk_labels(self, data: pd.DataFrame) -> np.ndarray:
        """Create risk labels for training."""
        try:
            if data.empty:
                return np.array([])
            
            # Convert risk levels to numeric labels
            risk_mapping = {
                'Very Low': 0,
                'Low': 1,
                'Medium': 2,
                'High': 3,
                'Very High': 4
            }
            
            risk_level_data = data.get('risk_level', 'Low')
            if risk_level_data is None:
                return np.array([1] * len(data))
            risk_labels = risk_level_data.map(risk_mapping).fillna(1)
            return risk_labels.values
            
        except Exception as e:
            print(f"Error creating risk labels: {e}")
            return np.array([])
    
    def train_model(self, model_name: str, features: pd.DataFrame, labels: np.ndarray) -> bool:
        """Train a specific model."""
        try:
            if features.empty or len(labels) == 0:
                print(f"No data available for training {model_name}")
                return False
            
            # Convert features to numpy array for scaling
            X = features.values
            y = labels
            
            # Determine number of classes and samples
            n_classes = len(np.unique(y))
            n_samples = len(y)
            
            # Adjust test_size dynamically
            min_test_size = max(2, n_classes)  # At least 2 samples or number of classes
            test_size = min(0.2, max(0.1, min_test_size / n_samples))  # Dynamic test_size
            
            if n_samples < min_test_size:
                print(f"Insufficient samples ({n_samples}) for training {model_name} with {n_classes} classes. Using all data.")
                X_train, y_train = X, y
                X_test, y_test = None, None
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42, stratify=y if n_classes > 1 else None
                )
            
            # Scale features
            scaler = self.scalers[model_name]
            X_train_scaled = scaler.fit_transform(X_train)
            
            if X_test is not None:
                X_test_scaled = scaler.transform(X_test)
            else:
                X_test_scaled = None
            
            # Train model
            model = self.models[model_name]
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model if test data exists
            if X_test_scaled is not None and y_test is not None:
                y_pred = model.predict(X_test_scaled)
                self.model_metrics[model_name] = {
                    'accuracy': accuracy_score(y_test, y_pred),
                    'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                    'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
                    'f1_score': f1_score(y_test, y_pred, average='weighted', zero_division=0)
                }
            else:
                self.model_metrics[model_name] = {
                    'accuracy': np.nan,
                    'precision': np.nan,
                    'recall': np.nan,
                    'f1_score': np.nan
                }
                print(f"No test split for {model_name} due to insufficient data. Metrics not calculated.")
            
            return True
            
        except Exception as e:
            print(f"Error training model {model_name}: {e}")
            return False
    
    def predict_dropout_risk(self, model_name: str, prediction_horizon: str) -> pd.DataFrame:
        """Predict dropout risk for students using real Django model data."""
        try:
            students = Student.objects.all()
            students_data = []
            
            for student in students:
                student_id = student.enrollment_no or f"STU{student.id}"
                name_parts = student.name.split() if ' ' in student.name else [student.name, '']
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                grade_level = student.year or 9
                attendance_rate = student.attendance_percentage
                current_gpa = student.average_score or 0
                behavioral_incidents = 0  # Not in model; assume 0
                
                # Calculate risk score
                risk_score = (
                    (100 - attendance_rate) * 0.3 +
                    (4.0 - current_gpa) * 2.0 +
                    behavioral_incidents * 0.5
                )
                
                # Determine risk level
                if risk_score >= 8:
                    predicted_risk = 'Very High'
                elif risk_score >= 6:
                    predicted_risk = 'High'
                elif risk_score >= 4:
                    predicted_risk = 'Medium'
                elif risk_score >= 2:
                    predicted_risk = 'Low'
                else:
                    predicted_risk = 'Very Low'
                
                # Calculate confidence (higher for extreme values)
                confidence = min(0.95, 0.5 + abs(risk_score - 5) * 0.1)
                
                # Identify primary risk factors
                factors = []
                if attendance_rate < 85:
                    factors.append("Low Attendance")
                if current_gpa < 2.5:
                    factors.append("Low GPA")
                if behavioral_incidents > 3:
                    factors.append("Behavioral Issues")
                
                primary_factors = ", ".join(factors) if factors else "No major concerns"
                
                students_data.append({
                    'student_id': student_id,
                    'student_name': f"{first_name} {last_name}",
                    'grade_level': grade_level,
                    'predicted_risk': predicted_risk,
                    'confidence': confidence,
                    'risk_score': min(10, max(0, risk_score)),
                    'primary_factors': primary_factors,
                    'attendance_rate': attendance_rate,
                    'current_gpa': current_gpa,
                    'behavioral_incidents': behavioral_incidents
                })
            
            return pd.DataFrame(students_data)
            
        except Exception as e:
            print(f"Error predicting dropout risk: {e}")
            return pd.DataFrame()

    # The rest of the methods (get_model_metrics, get_feature_importance, etc.) remain unchanged.
    # For methods like get_accuracy_timeline, get_risk_level_trends, etc., they use sample data; 
    # you can modify similarly to fetch real trends if needed (e.g., query over dates).