from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
import logging
from .models import Student, Course, Experience, Job, JobRecommendation, Alumni, MLModelInfo

logger = logging.getLogger(__name__)

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

# Create a proper model admin interface for ML Model Info
# Note: We're explicitly removing the old registration if it exists
try:
    admin.site.unregister(MLModelInfo)
except admin.sites.NotRegistered:
    pass

@admin.register(MLModelInfo)
class MLModelInfoAdmin(admin.ModelAdmin):
    """Admin interface for ML model information"""
    list_display = ('model_type', 'created_at', 'is_active', 'file_path')
    list_filter = ('model_type', 'is_active', 'created_at')
    readonly_fields = ('model_type', 'file_path', 'created_at')
    
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return True  # Allow deleting outdated models
        
    # Add action to generate models
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate-models/', self.admin_site.admin_view(self.generate_models_view),
                 name='job_recommender_mlmodelinfo_generate_models'),
        ]
        return custom_urls + urls
        
    def generate_models_view(self, request):
        """
        Instead of instantiating ModelGenerationAdmin directly,
        we'll implement a simplified version of its functionality here.
        """
        from django.core.management import call_command
        
        context = {
            'title': 'Generate ML Models',
            **self.admin_site.each_context(request),
        }
        
        if request.method == 'POST':
            model_type = request.POST.get('model_type', 'all')
            
            try:
                # Call the Django management command to generate models
                call_command('generate_ml_models', model=model_type)
                
                messages.success(
                    request, 
                    f"Successfully generated {model_type} ML model(s). The recommender will now use the updated model."
                )
                logger.info(f"Admin user {request.user.username} generated {model_type} ML model(s)")
                
            except Exception as e:
                messages.error(request, f"Error generating ML models: {str(e)}")
                logger.error(f"Error generating ML models: {e}")
            
            # Redirect to MLModelInfo list after generating model
            return HttpResponseRedirect(reverse('admin:job_recommender_mlmodelinfo_changelist'))
        
        return render(request, 'admin/job_recommender/generate_ml_models.html', context)
        
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_generate_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
        
    # Add an action to generate a new model
    actions = ['generate_new_model']
    
    def generate_new_model(self, request, queryset):
        """Admin action to generate new models"""
        return HttpResponseRedirect(reverse('admin:job_recommender_mlmodelinfo_generate_models'))
    
    generate_new_model.short_description = "Generate new ML models"
