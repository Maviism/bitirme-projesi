import csv
import json
import os
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from job_recommender.models import Student, Course, Experience, Job, JobRecommendation, Alumni

class Command(BaseCommand):
    help = 'Seeds the database with initial data from CSV files'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting to seed data...'))
        
        # Define the base path for CSV files
        base_path = os.path.join(settings.BASE_DIR, 'data', 'csv')
        
        # Import Students
        self.import_students(os.path.join(base_path, 'students.csv'))
        
        # Import Courses
        self.import_courses(os.path.join(base_path, 'courses.csv'))
        
        # Import Organizations and Internships (as experiences)
        self.import_experiences(os.path.join(base_path, 'experiences.csv'))
        
        # Import Jobs
        self.import_jobs(os.path.join(base_path, 'jobs.csv'))
        
        # Generate Alumni records
        self.generate_alumni()
        
        # Generate Job Recommendations (simple matching based on program)
        self.generate_recommendations()
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
    
    def import_students(self, file_path):
        self.stdout.write('Importing students...')
        count = 0
        
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Parse birth_date
                birth_date = datetime.strptime(row['birth_date'], '%Y-%m-%d').date()
                
                # Create or update the student
                Student.objects.update_or_create(
                    student_id=row['student_id'],
                    defaults={
                        'id_number': row['id_number'],
                        'fullname': row['fullname'],
                        'last_name': row['last_name'],
                        'birth_date': birth_date,
                        'faculty': row['faculty'],
                        'program': row['program'],
                        'gpa': float(row['gpa'])
                    }
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} students'))
    
    def import_courses(self, file_path):
        self.stdout.write('Importing courses...')
        count = 0
        
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Get the student
                try:
                    student = Student.objects.get(student_id=row['student_id'])
                    
                    # Create or update the course
                    Course.objects.update_or_create(
                        student=student,
                        code=row['code'],
                        defaults={
                            'name': row['name'],
                            'grade': row['grade']
                        }
                    )
                    count += 1
                except Student.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Student {row['student_id']} not found, skipping course {row['code']}"))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} courses'))
    
    def import_experiences(self, file_path):
        self.stdout.write('Importing experiences...')
        count = 0
        
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Get the student
                try:
                    student = Student.objects.get(student_id=row['student_id'])
                    
                    # Parse dates
                    start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                    end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date() if row['end_date'] else None
                    
                    # Create the experience
                    Experience.objects.create(
                        student=student,
                        experience_type=row['experience_type'],
                        institution_name=row['institution_name'],
                        position=row['position'],
                        start_date=start_date,
                        end_date=end_date,
                        description=row['description']
                    )
                    count += 1
                except Student.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Student {row['student_id']} not found, skipping experience at {row['institution_name']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error importing experience: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} experiences'))
    
    def import_jobs(self, file_path):
        self.stdout.write('Importing jobs...')
        count = 0

        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                majors = [major.strip() for major in row['required_majors'].split(';') if major.strip()]
                self.stdout.write(f"Parsed required_majors for job '{row['title']}': {majors}")

                Job.objects.update_or_create(
                    title=row['title'],
                    company=row['company'],
                    defaults={
                        'description': row['description'],
                        'required_majors': majors
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} jobs'))
    
    def generate_alumni(self):
        self.stdout.write('Generating alumni records...')
        count = 0
        
        # Convert ALL students to alumni (100% instead of just 30%)
        students = Student.objects.all()
        alumni_candidates = list(students)
        
        # Get all jobs for alumni employment
        jobs = Job.objects.all()
        if not jobs:
            self.stdout.write(self.style.WARNING('No jobs available for alumni. Create jobs first.'))
            return
        
        for student in alumni_candidates:
            # Skip if student already has an alumni record
            if hasattr(student, 'alumni_profile'):
                self.stdout.write(self.style.WARNING(f"Student {student.student_id} already has an alumni profile, skipping"))
                continue
                
            # Generate a graduation date within the last 5 years
            days_ago = random.randint(0, 5*365)  # Up to 5 years ago
            graduation_date = datetime.now().date() - timedelta(days=days_ago)
            
            # Try to find a job that matches the student's program
            matching_jobs = [job for job in jobs if student.program in job.required_majors]
            
            # If no matching jobs, fall back to any job
            if matching_jobs:
                # Apply the same 1-4 index limit to matching jobs
                limited_matching_jobs = matching_jobs[1:5]
                if limited_matching_jobs:
                    current_job = random.choice(limited_matching_jobs)
                else:
                    current_job = random.choice(matching_jobs) # Fallback to any matching if limited pool is empty
                self.stdout.write(self.style.SUCCESS(f"Found matching job for {student.program}"))
            else:
                # Fallback to a random job from a limited index range (1 to 4)
                fallback_jobs = jobs[1:5]
                if fallback_jobs:
                    current_job = random.choice(fallback_jobs)
                else:
                    current_job = random.choice(jobs) # Fallback to any if limited pool is empty
                self.stdout.write(self.style.WARNING(f"No matching job for {student.program}, using random job"))
            
            # Create the alumni record
            alumni = Alumni.objects.create(
                student=student,
                graduation_date=graduation_date,
                current_job=current_job,
                current_company=current_job.company,
                current_position=current_job.title,
                linkedin_profile=f"https://linkedin.com/in/{student.fullname.lower()}-{student.last_name.lower()}"
            )
            
            # Set is_alumni flag on the student
            student.is_alumni = True
            student.save()
            
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} alumni records'))
    
    def generate_recommendations(self):
        self.stdout.write('Generating job recommendations...')
        count = 0
        
        # Get all students and jobs
        students = Student.objects.all()
        jobs = Job.objects.all()
        
        # Get all alumni records to improve recommendation quality
        alumni_records = Alumni.objects.select_related('student', 'current_job').all()
        alumni_job_mapping = {}
        
        # Build a map of program -> jobs based on alumni data
        for alumni in alumni_records:
            program = alumni.student.program
            if program not in alumni_job_mapping:
                alumni_job_mapping[program] = []
            
            if alumni.current_job:
                alumni_job_mapping[program].append(alumni.current_job.id)
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(alumni_records)} alumni records for job mapping'))
        
        for student in students:
            # Find jobs that match the student's program
            for job in jobs:
                match_score = 0
                
                # Check if student's program is in required_majors
                if student.program in job.required_majors:
                    match_score = 85.0  # Base score for program match
                    
                    # Add bonus for GPA
                    if student.gpa >= 3.7:
                        match_score += 10.0
                    elif student.gpa >= 3.3:
                        match_score += 5.0
                
                # Check internship experience for company match
                if match_score > 0 or job.company in [i.institution_name for i in student.internships.all()]:
                    if job.company in [i.institution_name for i in student.internships.all()]:
                        match_score = max(match_score, 90.0)  # Higher score for company match
                    
                # Check alumni connection - this is now the primary recommendation source
                alumni_match = False
                
                # Check if this job is commonly held by alumni with the same program
                if student.program in alumni_job_mapping and job.id in alumni_job_mapping[student.program]:
                    match_score = max(match_score, 95.0)  # Highest score for alumni connection
                    alumni_match = True
                    
                # Also check if there are alumni with the same program working at this job's company
                try:
                    alumni_at_company = Alumni.objects.filter(
                        current_company=job.company,
                        student__program=student.program
                    ).exists()
                    if alumni_at_company:
                        match_score = max(match_score, 92.0)  # High score for alumni at same company
                        alumni_match = True
                except:
                    pass
                    
                # Create a recommendation if there's a match
                if match_score > 0:
                    source = 'alumni' if alumni_match else ('hybrid' if match_score > 85.0 else 'job_posting')
                    JobRecommendation.objects.update_or_create(
                        student=student,
                        job=job,
                        defaults={
                            'match_score': match_score,
                            'source': source
                        }
                    )
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} job recommendations'))