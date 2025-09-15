import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import sqlite3
from TrinityEd_app.models import Student, Attendance, Performance

class RiskCalculator:
    """
    Risk Calculator class for computing student dropout risk scores based on
    multiple factors including attendance, academic performance, and behavioral indicators.
    """
    
    def __init__(self):
        self.thresholds = self._get_default_thresholds()
        self.weights = self._get_default_weights()
        self.risk_factors = [
            'attendance_rate',
            'current_gpa', 
            'behavioral_incidents',
            'grade_level',
            'credits_on_track',
            'family_stability',
            'socioeconomic_status'
        ]
    
    def _get_default_thresholds(self) -> Dict[str, float]:
        """Return default thresholds for categorizing risk levels."""
        return {
            'very_high': 0.8,
            'high': 0.6,
            'medium': 0.4,
            'low': 0.2,
            'very_low': 0.0
        }
    
    def _get_default_weights(self) -> Dict[str, float]:
        """Return default weights for risk factors."""
        return {
            'attendance_rate': 0.3,
            'current_gpa': 0.3,
            'behavioral_incidents': 0.2,
            'grade_level': 0.05,
            'credits_on_track': 0.1,
            'family_stability': 0.025,
            'socioeconomic_status': 0.025
        }
    
    def calculate_composite_risk_score(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate composite risk score from all factors."""
        try:
            attendance_score = 1 - (student_data['attendance_rate'] / 100)
            gpa_score = 1 - (student_data['current_gpa'] / 4.0)
            behavioral_score = min(student_data['behavioral_incidents'] / 5, 1.0)
            credits_on_track = 1 - (student_data['credits_earned'] / student_data['credits_required'])
            grade_level_score = (student_data['grade_level'] - 9) / 3
            family_stability_score = 0.5 if student_data['recent_family_changes'] else 0.0
            ses_score = {'low': 0.5, 'medium': 0.25, 'high': 0.0}.get(student_data['family_income_level'], 0.25)

            composite_score = (
                self.weights['attendance_rate'] * attendance_score +
                self.weights['current_gpa'] * gpa_score +
                self.weights['behavioral_incidents'] * behavioral_score +
                self.weights['grade_level'] * grade_level_score +
                self.weights['credits_on_track'] * credits_on_track +
                self.weights['family_stability'] * family_stability_score +
                self.weights['socioeconomic_status'] * ses_score
            )

            risk_level = 'Very Low'
            for level, threshold in self.thresholds.items():
                if composite_score >= threshold:
                    risk_level = level.replace('_', ' ').title()
                    break

            individual_levels = {
                'attendance': 'High' if attendance_score >= 0.6 else 'Medium' if attendance_score >= 0.4 else 'Low',
                'academic': 'High' if gpa_score >= 0.6 else 'Medium' if gpa_score >= 0.4 else 'Low',
                'behavioral': 'High' if behavioral_score >= 0.6 else 'Medium' if behavioral_score >= 0.4 else 'Low'
            }

            primary_risk_factors = [
                factor for factor, level in individual_levels.items() if level in ['High', 'Very High']
            ]

            return {
                'composite_score': round(composite_score, 2),
                'overall_risk_level': risk_level,
                'individual_levels': individual_levels,
                'primary_risk_factors': primary_risk_factors
            }
        except Exception as e:
            print(f"Error calculating composite risk score: {e}")
            return {
                'composite_score': 0.0,
                'overall_risk_level': 'Unknown',
                'individual_levels': {},
                'primary_risk_factors': []
            }
    
    def calculate_all_risks(self) -> pd.DataFrame:
        """Calculate risk assessments for all students using real Django model data."""
        try:
            students = Student.objects.all()
            students_data = []
            
            for student in students:
                student_id = student.enrollment_no or f"STU{student.id}"
                student_name = student.name
                grade_level = student.year or 9
                attendance_rate = student.attendance_percentage
                current_gpa = student.average_score
                behavioral_incidents = student.incidents.count() if hasattr(student, 'incidents') else 0
                credits_earned = student.credits_earned if hasattr(student, 'credits_earned') else 0
                credits_required = 24
                free_lunch_eligible = student.free_lunch_eligible if hasattr(student, 'free_lunch_eligible') else False
                family_income_level = student.family_income_level or 'medium'
                family_structure = student.family_structure or 'two_parent'
                recent_family_changes = student.recent_family_changes or False
                
                student_data = {
                    'attendance_rate': attendance_rate,
                    'current_gpa': current_gpa,
                    'behavioral_incidents': behavioral_incidents,
                    'grade_level': grade_level,
                    'credits_earned': credits_earned,
                    'credits_required': credits_required,
                    'free_lunch_eligible': free_lunch_eligible,
                    'family_income_level': family_income_level,
                    'family_structure': family_structure,
                    'recent_family_changes': recent_family_changes
                }
                
                risk_assessment = self.calculate_composite_risk_score(student_data)
                
                result = {
                    'student_id': student_id,
                    'student_name': student_name,
                    'grade_level': grade_level,
                    'attendance_rate': round(attendance_rate, 1),
                    'current_gpa': round(current_gpa, 2),
                    'behavioral_incidents': behavioral_incidents,
                    'risk_score': risk_assessment['composite_score'],
                    'risk_level': risk_assessment['overall_risk_level'],
                    'attendance_risk': risk_assessment['individual_levels'].get('attendance', 'Medium'),
                    'academic_risk': risk_assessment['individual_levels'].get('academic', 'Medium'),
                    'behavioral_risk': risk_assessment['individual_levels'].get('behavioral', 'Medium'),
                    'primary_risk_factors': ', '.join(risk_assessment['primary_risk_factors'])
                }
                
                students_data.append(result)
            
            return pd.DataFrame(students_data)
            
        except Exception as e:
            print(f"Error calculating all risks: {e}")
            return pd.DataFrame({
                'student_id': [], 'student_name': [], 'grade_level': [], 'attendance_rate': [],
                'current_gpa': [], 'behavioral_incidents': [], 'risk_score': [], 'risk_level': [],
                'attendance_risk': [], 'academic_risk': [], 'behavioral_risk': [], 'primary_risk_factors': []
            })