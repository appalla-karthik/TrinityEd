import os
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env
api_key = os.getenv("OPENAI_API_KEY")
import json
from typing import Dict, List, Any
import numpy as np
from datetime import datetime, timedelta
from openai import OpenAI

# Import Django models for fetching real data
from TrinityEd_app.models import Student, Attendance, Performance, Alert

class AIInsightsGenerator:
    """
    AI Insights Generator class for generating AI-powered insights and recommendations
    using OpenAI's language models for student dropout prediction and intervention planning.
    """
    
    def __init__(self):
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "default_key"))
        self.model_name = "gpt-5"
    
    def generate_insights(self) -> Dict[str, Any]:
        """Generate comprehensive AI insights for the student monitoring system."""
        try:
            # Prepare context data for AI analysis
            context_data = self._prepare_context_data()
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(context_data)
            
            # Generate key findings
            key_findings = self._generate_key_findings(context_data)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(context_data)
            
            # Generate student-specific insights
            student_insights = self._generate_student_insights(context_data)
            
            # Generate pattern analysis
            pattern_analysis = self._generate_pattern_analysis(context_data)
            
            return {
                'executive_summary': executive_summary,
                'key_findings': key_findings,
                'immediate_actions': recommendations['immediate'],
                'long_term_strategies': recommendations['long_term'],
                'student_insights': student_insights,
                'risk_patterns': pattern_analysis['risk_patterns'],
                'emerging_trends': pattern_analysis['emerging_trends'],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            return self._get_fallback_insights()
    
    def _prepare_context_data(self) -> Dict[str, Any]:
        """Prepare context data for AI analysis by fetching from Django models."""
        total_students = Student.objects.count()
        high_risk_students = Student.objects.filter(is_at_risk=True).count()
        
        # Calculate risk distribution based on is_at_risk and average_score
        risk_distribution = {
            'Very High': Student.objects.filter(is_at_risk=True, average_score__lt=50).count(),
            'High': Student.objects.filter(is_at_risk=True, average_score__gte=50, average_score__lt=70).count(),
            'Medium': Student.objects.filter(is_at_risk=False, average_score__lt=80).count(),
            'Low': Student.objects.filter(is_at_risk=False, average_score__gte=80, average_score__lt=90).count(),
            'Very Low': Student.objects.filter(is_at_risk=False, average_score__gte=90).count()
        }
        
        # Calculate recent trends (example logic; adjust as needed)
        avg_attendance = Attendance.objects.aggregate(avg=Avg('percentage'))['avg'] or 0
        avg_gpa = Student.objects.aggregate(avg=Avg('average_score'))['avg'] or 0
        recent_trends = {
            'attendance_trend': 'declining' if avg_attendance < 80 else 'stable',
            'gpa_trend': 'stable' if avg_gpa > 70 else 'declining',
            'behavioral_incidents': 'increasing'  # Assume; no field, so static
        }
        
        intervention_success_rate = 79.5  # Static; calculate if data available
        
        # Grade level risks (percentage at risk per year/grade)
        grade_level_risks = {}
        for grade in [1, 2, 3, 4]:  # Assuming year=1 to 4; adjust to 9-12 if needed
            total_in_grade = Student.objects.filter(year=grade).count()
            at_risk_in_grade = Student.objects.filter(year=grade, is_at_risk=True).count()
            grade_level_risks[str(grade + 8)] = (at_risk_in_grade / total_in_grade * 100) if total_in_grade else 0.0
        
        top_risk_factors = []
        if avg_attendance < 85:
            top_risk_factors.append('chronic_absenteeism')
        if avg_gpa < 2.5:
            top_risk_factors.append('low_gpa')
        top_risk_factors.extend(['behavioral_issues', 'family_instability'])  # Static assumptions
        
        return {
            'total_students': total_students,
            'high_risk_students': high_risk_students,
            'risk_distribution': risk_distribution,
            'recent_trends': recent_trends,
            'intervention_success_rate': intervention_success_rate,
            'grade_level_risks': grade_level_risks,
            'top_risk_factors': top_risk_factors
        }
    
    # The rest of the methods (_generate_executive_summary, etc.) remain unchanged,
    # as they use the context_data which now fetches from models.
    # Fallback methods remain as is.

    def _generate_student_insights(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights for specific high-risk students."""
        try:
            # Fetch real high-risk students (top 3 for example)
            high_risk_students = Student.objects.filter(is_at_risk=True)[:3]
            high_risk_data = [
                {
                    'name': student.name,
                    'grade': student.year or 9,
                    'risk_score': 8.5 if student.average_score < 70 else 7.2,  # Example based on score
                    'attendance': student.attendance_percentage,
                    'gpa': student.average_score,
                    'incidents': 0  # Assume
                } for student in high_risk_students
            ]
            
            insights = []
            
            for student in high_risk_data:
                prompt = f"""
                Analyze this high-risk student and provide insights:
                
                Student: {student['name']}, Grade {student['grade']}
                Risk Score: {student['risk_score']}/10
                Attendance: {student['attendance']}%
                GPA: {student['gpa']}
                Behavioral Incidents: {student['incidents']}
                
                Provide:
                1. Analysis of risk factors
                2. Recommended interventions (3-4 specific actions)
                3. Success probability estimate (percentage)
                
                Format as JSON with 'analysis', 'interventions' array, and 'success_probability' number.
                """
                
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a school counselor analyzing student risk factors."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if not content:
                    insights.append({
                        'student_name': student['name'],
                        'risk_level': 'High',
                        'analysis': 'Student requires immediate attention',
                        'interventions': ['Academic support', 'Attendance monitoring'],
                        'success_probability': 75
                    })
                    continue
                result = json.loads(content)
                
                insights.append({
                    'student_name': student['name'],
                    'risk_level': 'High',
                    'analysis': result.get('analysis', 'Student requires immediate attention'),
                    'interventions': result.get('interventions', ['Academic support', 'Attendance monitoring']),
                    'success_probability': result.get('success_probability', 75)
                })
            
            return insights
            
        except Exception as e:
            print(f"Error generating student insights: {e}")
            return self._get_fallback_student_insights()

    # The other methods (generate_intervention_recommendation, analyze_intervention_effectiveness, generate_risk_explanation) remain unchanged,
    # but you can modify student_data input to come from real Student objects when calling them.
    # Fallback methods remain as is.