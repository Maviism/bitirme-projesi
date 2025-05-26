from django.contrib import admin
from .models import InterviewSession, InterviewQuestion, InterviewFeedback, InterviewTemplate

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'job_position', 'difficulty_level', 'status', 'created_at', 'overall_score']
    list_filter = ['status', 'difficulty_level', 'created_at']
    search_fields = ['user__username', 'job_position']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'deepgram_session_id']
    
    def overall_score(self, obj):
        if hasattr(obj, 'feedback') and obj.feedback:
            return f"{obj.feedback.overall_score:.1f}/10"
        return "No feedback yet"
    overall_score.short_description = "Overall Score"

@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['session', 'question_order', 'question_text_short', 'score', 'asked_at']
    list_filter = ['session__status', 'asked_at']
    search_fields = ['question_text', 'session__job_position']
    readonly_fields = ['asked_at']
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = "Question"

@admin.register(InterviewFeedback)
class InterviewFeedbackAdmin(admin.ModelAdmin):
    list_display = ['session', 'overall_score', 'communication_score', 'technical_score', 'confidence_score', 'created_at']
    list_filter = ['created_at']
    search_fields = ['session__user__username', 'session__job_position']
    readonly_fields = ['created_at']

@admin.register(InterviewTemplate)
class InterviewTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'job_position', 'difficulty_level', 'estimated_duration', 'is_active', 'created_at']
    list_filter = ['difficulty_level', 'is_active', 'created_at']
    search_fields = ['title', 'job_position']
    readonly_fields = ['created_at']
