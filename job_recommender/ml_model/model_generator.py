"""
ML Model Generator for Job Recommendation System

This module handles the generation and persistence of ML models used 
for job recommendations in the hybrid recommender system.
"""
import os
import pickle
import logging
from datetime import datetime
from django.db import transaction
from django.conf import settings
from ..models import Student, Course, Experience, Job, JobRecommendation, Alumni, MLModelInfo
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Path to stored models
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stored_models')

class MLModelGenerator:
    """
    Class for generating and managing ML models for job recommendations
    """
    
    def __init__(self):
        """Initialize the model generator"""
        # Make sure the model directory exists
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def generate_alumni_model(self):
        """
        Generate and save the alumni model data
        """
        try:
            # Retrieve alumni data from the database using the same logic as in recommender.py
            alumni_records = Alumni.objects.select_related('student', 'current_job').all()
            
            # Structure alumni data as needed for recommendations
            alumni_data = []
            grade_mapping = {
                'AA': 4.0, 'BA': 3.5, 'BB': 3.0, 'CB': 2.5, 
                'CC': 2.0, 'DC': 1.5, 'DD': 1.0, 'FF': 0.0
            }
            
            for alumni_record in alumni_records:
                student = alumni_record.student
                
                # Skip alumni without a current job
                if not alumni_record.current_job:
                    continue
                    
                # Build course grades dictionary
                courses = student.courses.all()
                course_grades = {}
                for course in courses:
                    course_grades[course.code] = grade_mapping.get(course.grade, 0)
                
                # Structure the alumni data
                alumni_record_data = {
                    'student': {
                        'id': student.student_id,
                        'program': student.program,
                        'gpa': float(student.gpa),
                        'skills': student.skills if hasattr(student, 'skills') else []
                    },
                    'course_grades': course_grades,
                    'graduation_date': alumni_record.graduation_date,
                    'current_job': {
                        'id': alumni_record.current_job.id,
                        'title': alumni_record.current_job.title,
                        'company': alumni_record.current_job.company,
                        'description': alumni_record.current_job.description,
                        'required_majors': alumni_record.current_job.required_majors,
                        'required_skills': alumni_record.current_job.required_skills if hasattr(alumni_record.current_job, 'required_skills') else []
                    }
                }
                alumni_data.append(alumni_record_data)
            
            # Save the alumni data model
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(MODEL_DIR, f'alumni_model_{timestamp}.pkl')
            
            with open(file_path, 'wb') as f:
                pickle.dump(alumni_data, f)
            
            # Create/update a symlink to the latest model
            latest_path = os.path.join(MODEL_DIR, 'alumni_model_latest.pkl')
            if os.path.exists(latest_path):
                os.remove(latest_path)
            os.symlink(file_path, latest_path)
            
            # Record the model generation in the database
            with transaction.atomic():
                # Set all previous alumni models as inactive
                MLModelInfo.objects.filter(model_type='alumni').update(is_active=False)
                
                # Create a record for the new model
                MLModelInfo.objects.create(
                    model_type='alumni',
                    file_path=file_path,
                    is_active=True
                )
            
            logger.info(f"Alumni model generated and saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error generating alumni model: {e}")
            return None
    
    def generate_job_model(self):
        """
        Generate and save job posting model data
        """
        try:
            # Get job postings from the database
            jobs = Job.objects.all()
            
            # Convert to the format expected by the recommender
            job_postings = []
            for job in jobs:
                job_postings.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'description': job.description,
                    'required_majors': job.required_majors,
                    'required_skills': job.required_skills if hasattr(job, 'required_skills') else [],
                    # Generate and store text embeddings for each job
                    'embedding': self.generate_job_embedding(job)
                })
            
            # Save the job model
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(MODEL_DIR, f'job_model_{timestamp}.pkl')
            
            with open(file_path, 'wb') as f:
                pickle.dump(job_postings, f)
            
            # Create/update a symlink to the latest model
            latest_path = os.path.join(MODEL_DIR, 'job_model_latest.pkl')
            if os.path.exists(latest_path):
                os.remove(latest_path)
            os.symlink(file_path, latest_path)
            
            # Record the model generation in the database
            with transaction.atomic():
                # Set all previous job models as inactive
                MLModelInfo.objects.filter(model_type='job').update(is_active=False)
                
                # Create a record for the new model
                MLModelInfo.objects.create(
                    model_type='job',
                    file_path=file_path,
                    is_active=True
                )
            
            logger.info(f"Job model generated and saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error generating job model: {e}")
            return None
    
    def generate_job_embedding(self, job):
        """Generate text embedding for a job"""
        try:
            job_text = f"{job.title}. {job.company}. {job.description}"
            return self.embedding_model.encode(job_text).tolist()
        except Exception as e:
            logger.error(f"Error generating job embedding: {e}")
            return []
    
    def generate_all_models(self):
        """Generate all models at once"""
        alumni_path = self.generate_alumni_model()
        job_path = self.generate_job_model()
        
        return {
            'alumni_model_path': alumni_path,
            'job_model_path': job_path,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def load_alumni_model():
        """Load the latest alumni model"""
        try:
            latest_path = os.path.join(MODEL_DIR, 'alumni_model_latest.pkl')
            if not os.path.exists(latest_path):
                logger.warning("No alumni model found, returning empty list")
                return []
                
            with open(latest_path, 'rb') as f:
                alumni_data = pickle.load(f)
            
            logger.info(f"Loaded alumni model from {latest_path}")
            return alumni_data
        except Exception as e:
            logger.error(f"Error loading alumni model: {e}")
            return []
    
    @staticmethod
    def load_job_model():
        """Load the latest job model"""
        try:
            latest_path = os.path.join(MODEL_DIR, 'job_model_latest.pkl')
            if not os.path.exists(latest_path):
                logger.warning("No job model found, returning empty list")
                return []
                
            with open(latest_path, 'rb') as f:
                job_data = pickle.load(f)
            
            logger.info(f"Loaded job model from {latest_path}")
            return job_data
        except Exception as e:
            logger.error(f"Error loading job model: {e}")
            return []
