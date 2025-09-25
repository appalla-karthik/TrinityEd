from django.contrib import admin
from django.db.models import Count, Q, FloatField, ExpressionWrapper, Avg
from .models import CounsellingSession, Progress, Student, Attendance, Performance, Fee, Alert

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
    list_filter = ('date', 'status')

    # Week column (calculated dynamically from date)
    def get_week(self, obj):
        return obj.date.isocalendar()[1] if obj.date else '-'
    get_week.short_description = 'Week'

    # Percentage column (calculated)
    def get_percentage(self, obj):
        qs = Attendance.objects.filter(student=obj.student)
        total = qs.count()
        if total == 0:
            return 0
        present_count = qs.filter(status="Present").count()
        return round(present_count * 100.0 / total, 2)
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

# ----------------- Progress -----------------
@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'last_updated', 'incidents_count')
    search_fields = ('student__name', 'student__user__username')
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)  # Make last_updated read-only

    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'last_updated')
        }),
        ('GPA / Score Trend', {
            'fields': ('gpa_labels', 'gpa_data')
        }),
        ('Attendance Trend', {
            'fields': ('attendance_labels', 'attendance_data')
        }),
        ('Subject Performance', {
            'fields': ('subject_labels', 'subject_data')
        }),
        ('Grade Summary', {
            'fields': ('grade_summary',)
        }),
        ('Behavioral Incidents', {
            'fields': ('incidents_count', 'incident_list')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # Make all fields read-only except incidents_count and incident_list for manual updates
        if obj:  # Editing an existing object
            return self.readonly_fields + ('student', 'gpa_labels', 'gpa_data', 'attendance_labels', 
                                        'attendance_data', 'subject_labels', 'subject_data', 'grade_summary')
        return self.readonly_fields

# ... (other admin registrations remain unchanged)

@admin.register(CounsellingSession)
class CounsellingSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'name', 'mentor', 'scheduled_time', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'mentor__username')
    date_hierarchy = 'scheduled_time'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'mentor')