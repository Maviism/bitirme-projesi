from django.db import models
from job_recommender.models import Student, Job

# Create your models here.
class InterviewSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='interview_sessions')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='interview_sessions')
    room_name = models.CharField(max_length=100, unique=True)
    resume_content = models.TextField(blank=True, null=True)
    cover_letter = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    transcript = models.JSONField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    interview_duration = models.IntegerField(blank=True, null=True, help_text="Interview duration in seconds")

    def __str__(self):
        return f"Interview for {self.student.fullname} - {self.job.title if self.job else 'General'}"
