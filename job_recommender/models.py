from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Student(models.Model):
    """Model representing student information"""
    student_id = models.CharField(max_length=20, unique=True)
    id_number = models.CharField(max_length=20, blank=True, null=True)
    fullname = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    faculty = models.CharField(max_length=100)
    program = models.CharField(max_length=100)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(4.0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add a flag to differentiate regular students from alumni
    is_alumni = models.BooleanField(default=False)
    
    # Student's skill preferences
    skills = models.JSONField(default=list, blank=True)  # Store selected skills as JSON array

    def __str__(self):
        return f"{self.fullname} {self.last_name} ({self.student_id})"

class Alumni(models.Model):
    """Model representing alumni information, extending the Student model"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='alumni_profile')
    graduation_date = models.DateField()
    current_job = models.ForeignKey('Job', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_employees')
    current_company = models.CharField(max_length=100, blank=True, null=True)
    current_position = models.CharField(max_length=100, blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"Alumni: {self.student.fullname} {self.student.last_name}"

    def save(self, *args, **kwargs):
        # Ensure the linked student is marked as alumni
        if not self.student.is_alumni:
            self.student.is_alumni = True
            self.student.save()
        super().save(*args, **kwargs)

class Course(models.Model):
    """Model representing a course taken by a student"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='courses')
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    
    GRADE_CHOICES = [
        ('AA', 'AA'),
        ('BA', 'BA'),
        ('BB', 'BB'),
        ('CB', 'CB'),
        ('CC', 'CC'),
        ('DC', 'DC'),
        ('DD', 'DD'),
        ('FF', 'FF'),
        ('--', 'Not Graded'),
    ]
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, default='--')
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.grade})"
    
    class Meta:
        unique_together = ('student', 'code')

class Organization(models.Model):
    """Model representing student's organizational experience"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='organizations')
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.position}"

class Internship(models.Model):
    """Model representing student's internship experience"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='internships')
    company = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.company} - {self.position}"

class Job(models.Model):
    """Model representing a job posting"""
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    description = models.TextField()
    required_majors = models.JSONField(default=list)  # Stored as a JSON array
    required_skills = models.JSONField(default=list, blank=True)  # Required skills for the job
    
    def __str__(self):
        return f"{self.title} at {self.company}"

class JobRecommendation(models.Model):
    """Model representing a job recommendation for a student"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='recommendations')
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    match_score = models.DecimalField(max_digits=5, decimal_places=2)  # Score as a percentage
    
    SOURCE_CHOICES = [
        ('alumni', 'Alumni Match'),
        ('job_posting', 'Experience Match'),
        ('hybrid', 'Hybrid Match'),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='hybrid')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.job} for {self.student.fullname} ({self.match_score}%)"
    
    class Meta:
        unique_together = ('student', 'job')
