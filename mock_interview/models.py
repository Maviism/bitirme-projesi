from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class InterviewSession(models.Model):
    """Model to store mock interview sessions"""
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_position = models.CharField(max_length=200)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='intermediate')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=30)
    deepgram_session_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Store interview configuration as JSON
    interview_config = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.job_position} ({self.status})"

class InterviewQuestion(models.Model):
    """Model to store interview questions and responses"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_order = models.IntegerField()
    asked_at = models.DateTimeField(default=timezone.now)
    
    # Audio files
    question_audio_url = models.URLField(null=True, blank=True)
    response_audio_url = models.URLField(null=True, blank=True)
    
    # Transcriptions
    response_transcript = models.TextField(null=True, blank=True)
    
    # AI Analysis
    response_analysis = models.JSONField(default=dict, blank=True)
    score = models.FloatField(null=True, blank=True)  # 0-10 scale
    
    class Meta:
        ordering = ['question_order']
    
    def __str__(self):
        return f"Q{self.question_order}: {self.question_text[:50]}..."

class InterviewFeedback(models.Model):
    """Model to store overall interview feedback"""
    session = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='feedback')
    overall_score = models.FloatField()  # 0-10 scale
    strengths = models.JSONField(default=list)  # List of strengths
    areas_for_improvement = models.JSONField(default=list)  # List of improvement areas
    detailed_feedback = models.TextField()
    recommendations = models.TextField(null=True, blank=True)
    
    # Performance metrics
    communication_score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Feedback for {self.session.user.username} - Score: {self.overall_score}"

class InterviewTemplate(models.Model):
    """Predefined question templates for different job positions"""
    title = models.CharField(max_length=200)
    job_position = models.CharField(max_length=200)
    difficulty_level = models.CharField(max_length=20, choices=InterviewSession.DIFFICULTY_CHOICES)
    questions = models.JSONField()  # List of question objects
    estimated_duration = models.IntegerField(default=30)  # in minutes
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['job_position', 'difficulty_level']
    
    def __str__(self):
        return f"{self.title} - {self.job_position} ({self.difficulty_level})"
