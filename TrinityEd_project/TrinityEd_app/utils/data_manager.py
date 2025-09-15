# TrinityEd_app/utils/data_manager.py
import pandas as pd
from TrinityEd_app.models import Student, Attendance, Performance


class DataManager:
    """
    Data Manager for handling all student data operations.
    Now uses Django ORM instead of direct SQLite access.
    """

    def __init__(self):
        # No external db_path or connection needed
        pass

    def get_students_overview(self):
        """
        Return DataFrame with student ID, attendance %, average score, risk flag.
        """
        students = Student.objects.all().values(
            "id", "attendance_percentage", "average_score", "is_at_risk"
        )
        return pd.DataFrame(list(students))

    def get_all_students(self):
        """
        Return DataFrame of all students with linked user info.
        """
        students = Student.objects.select_related("user").all().values(
            "id", "user__username", "attendance_percentage", "average_score", "is_at_risk"
        )
        return pd.DataFrame(list(students))

    def get_attendance(self):
        """
        Return DataFrame of all attendance records.
        """
        qs = Attendance.objects.all().values("student_id", "percentage", "week", "recorded_date")
        return pd.DataFrame(list(qs))

    def get_performance(self):
        """
        Return DataFrame of all performance records.
        """
        qs = Performance.objects.all().values("student_id", "score", "test_name", "test_date")
        return pd.DataFrame(list(qs))

    # If you had more helper methods in the old DataManager (like filtering,
    # aggregating, etc.), they can now wrap Django ORM queries instead of SQL.

