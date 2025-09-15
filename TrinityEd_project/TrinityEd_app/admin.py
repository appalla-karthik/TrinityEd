from django.contrib import admin
from django.db.models import Count, Q, FloatField, ExpressionWrapper
from .models import Student, Attendance, Performance, Fee, Alert

# ----------------- Student -----------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'attendance_percentage',
        'average_score',
        'is_at_risk',
        'enrollment_date',
    )
    search_fields = ('name', 'user__username')
    list_filter = ('is_at_risk',)

# ----------------- Attendance -----------------
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_week', 'get_percentage', 'date', 'status')
    search_fields = ('student__name',)
    list_filter = ('date', 'status')  # ✅ existing fields

    # Week column
    def get_week(self, obj):
        return obj.week
    get_week.short_description = 'Week'

    # Percentage column (calculated)
    def get_percentage(self, obj):
        qs = Attendance.objects.filter(student=obj.student)
        agg = qs.aggregate(
            percentage=ExpressionWrapper(
                Count('id', filter=Q(status="Present")) * 100.0 / Count('id'),
                output_field=FloatField()
            )
        )
        return round(agg['percentage'], 2) if agg['percentage'] is not None else 0
    get_percentage.short_description = 'Percentage'

# ----------------- Performance -----------------
@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'test_name', 'score', 'test_date')
    search_fields = ('student__name', 'test_name')
    list_filter = ('test_date',)

# ----------------- Fee -----------------
@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_fee', 'paid', 'pending', 'due_date', 'is_overdue')
    search_fields = ('student__name',)
    list_filter = ('is_overdue',)

# ----------------- Alert -----------------
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'timestamp', 'is_read')
    search_fields = ('title', 'description')
    list_filter = ('type', 'is_read')
