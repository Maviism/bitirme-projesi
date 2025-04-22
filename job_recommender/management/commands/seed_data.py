import csv
import json
import os
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from job_recommender.models import Student, Course, Organization, Internship, Job, JobRecommendation, Alumni

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
        
        # Import Organizations
        self.import_organizations(os.path.join(base_path, 'organizations.csv'))
        
        # Import Internships
        self.import_internships(os.path.join(base_path, 'internships.csv'))
        
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
    
    def import_organizations(self, file_path):
        self.stdout.write('Importing organizations...')
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
                    
                    # Create the organization
                    Organization.objects.create(
                        student=student,
                        name=row['name'],
                        position=row['position'],
                        start_date=start_date,
                        end_date=end_date,
                        description=row['description']
                    )
                    count += 1
                except Student.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Student {row['student_id']} not found, skipping organization {row['name']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error importing organization: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} organizations'))
    
    def import_internships(self, file_path):
        self.stdout.write('Importing internships...')
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
                    
                    # Create the internship
                    Internship.objects.create(
                        student=student,
                        company=row['company'],
                        position=row['position'],
                        start_date=start_date,
                        end_date=end_date,
                        description=row['description']
                    )
                    count += 1
                except Student.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Student {row['student_id']} not found, skipping internship at {row['company']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error importing internship: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} internships'))
    
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
        
        # Get a sample of students to convert to alumni (about 30%)
        students = Student.objects.all()
        alumni_count = max(int(students.count() * 0.3), 1)  # At least 1 alumni
        alumni_candidates = random.sample(list(students), min(alumni_count, students.count()))
        
        # Get all jobs for alumni employment
        jobs = Job.objects.all()
        if not jobs:
            self.stdout.write(self.style.WARNING('No jobs available for alumni. Create jobs first.'))
            return
        
        for student in alumni_candidates:
            # Generate a graduation date within the last 5 years
            days_ago = random.randint(0, 5*365)  # Up to 5 years ago
            graduation_date = datetime.now().date() - timedelta(days=days_ago)
            
            # Assign a random job
            current_job = random.choice(jobs)
            
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
                if match_score > 0 or job.company in [i.company for i in student.internships.all()]:
                    if job.company in [i.company for i in student.internships.all()]:
                        match_score = max(match_score, 90.0)  # Higher score for company match
                    
                    # Check alumni connection
                    alumni_match = False
                    try:
                        # Check if there are alumni with the same program working at this job's company
                        alumni_at_company = Alumni.objects.filter(
                            current_company=job.company,
                            student__program=student.program
                        ).exists()
                        if alumni_at_company:
                            match_score = max(match_score, 95.0)  # Highest score for alumni connection
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