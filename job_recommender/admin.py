from django.contrib import admin
from .models import Student, Course, Experience, Job, JobRecommendation, Alumni

class CourseInline(admin.TabularInline):
    model = Course
    extra = 1

class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 1
    fields = ('experience_type', 'institution_name', 'position', 'start_date', 'end_date', 'description')

class JobRecommendationInline(admin.TabularInline):
    model = JobRecommendation
    extra = 0
    readonly_fields = ('job', 'match_score', 'source', 'created_at')
    can_delete = False

class AlumniInline(admin.StackedInline):
    model = Alumni
    can_delete = False
    verbose_name_plural = 'Alumni Info'
    fk_name = 'student'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'fullname', 'last_name', 'program', 'gpa', 'is_alumni')
    search_fields = ('student_id', 'fullname', 'last_name', 'program')
    list_filter = ('program', 'faculty', 'is_alumni')
    inlines = [AlumniInline, CourseInline, ExperienceInline, JobRecommendationInline]

@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ('get_student_id', 'get_student_name', 'graduation_date', 'current_company', 'current_position')
    search_fields = ('student__student_id', 'student__fullname', 'student__last_name', 'current_company')
    list_filter = ('graduation_date',)
    
    def get_student_id(self, obj):
        return obj.student.student_id
    get_student_id.short_description = 'Student ID'
    get_student_id.admin_order_field = 'student__student_id'
    
    def get_student_name(self, obj):
        return f"{obj.student.fullname} {obj.student.last_name}"
    get_student_name.short_description = 'Name'
    get_student_name.admin_order_field = 'student__fullname'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'student', 'grade')
    search_fields = ('code', 'name', 'student__fullname')
    list_filter = ('grade',)

@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'position', 'experience_type', 'student', 'start_date', 'end_date')
    search_fields = ('institution_name', 'position', 'student__fullname', 'description')
    list_filter = ('experience_type', 'start_date')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company')
    search_fields = ('title', 'company', 'description')

@admin.register(JobRecommendation)
class JobRecommendationAdmin(admin.ModelAdmin):
    list_display = ('job', 'student', 'match_score', 'source', 'created_at')
    search_fields = ('job__title', 'student__fullname')
    list_filter = ('source', 'created_at')
    readonly_fields = ('created_at',)
