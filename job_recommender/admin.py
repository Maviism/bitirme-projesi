from django.contrib import admin
from .models import Student, Course, Organization, Internship, Job, JobRecommendation

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'fullname', 'last_name', 'program', 'gpa', 'created_at')
    search_fields = ('student_id', 'fullname', 'last_name', 'program')
    list_filter = ('program', 'faculty')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'student', 'grade')
    list_filter = ('grade',)
    search_fields = ('code', 'name', 'student__fullname')

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'student', 'start_date', 'end_date')
    search_fields = ('name', 'position', 'student__fullname')

@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ('company', 'position', 'student', 'start_date', 'end_date')
    search_fields = ('company', 'position', 'student__fullname')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company')
    search_fields = ('title', 'company', 'description')

@admin.register(JobRecommendation)
class JobRecommendationAdmin(admin.ModelAdmin):
    list_display = ('student', 'job', 'match_score', 'source', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('student__fullname', 'job__title', 'job__company')
