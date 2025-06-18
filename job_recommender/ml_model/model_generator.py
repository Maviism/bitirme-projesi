"""
ML Model Generator for Job Recommendation System

This module handles the generation and persistence of ML models used 
for job recommendations in the hybrid recommender system.
"""
import os
import pickle
import logging
import traceback
import sys
from datetime import datetime
from django.db import transaction
from django.conf import settings
from ..models import Student, Course, Experience, Job, JobRecommendation, Alumni, MLModelInfo
from sentence_transformers import SentenceTransformer
# For AutoML
try:
    import flaml
    from .automl_recommender import AlumniAutoMLRecommender
    automl_available = True
    logger = logging.getLogger(__name__)
    logger.info(f"FLAML successfully imported. Version: {flaml.__version__}")
except ImportError as e:
    automl_available = False
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing AutoML libraries: {e}")
    logger.error(traceback.format_exc())
    pass

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
        
        # Initialize AutoML recommender if available
        if not automl_available:
            logger.error("AutoML libraries (FLAML) are not available. Check if FLAML is installed correctly.")
            self.automl_recommender = None
        else:
            try:
                self.automl_recommender = AlumniAutoMLRecommender(time_budget=300)  # Longer training for persistence
                logger.info("AutoML recommender initialized for model generation")
            except Exception as e:
                logger.error(f"Failed to initialize AutoML recommender: {e}")
                logger.error(traceback.format_exc())
                self.automl_recommender = None
    
    def generate_alumni_model(self):
        """
        Generate and save the alumni model data
        
        Creates a data structure used by the AutoML recommender system.
        """
        try:
            # Retrieve alumni data from the database
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
                
            # If AutoML is available, also generate an AutoML model
            if self.automl_recommender is not None:
                self.generate_automl_model()
            
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
    
    def generate_automl_model(self):
        """
        Generate and save the AutoML model for alumni recommendations
        """
        if self.automl_recommender is None:
            logger.error("AutoML recommender not available")
            return None
            
        try:
            # Get alumni data - reuse code from generate_alumni_model 
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
            
            # Train the AutoML model
            logger.info("Training AutoML model for persistence")
            
            # Log the size of the dataset for debugging
            logger.info(f"Training with {len(alumni_data)} alumni records")
            
            if len(alumni_data) < 5:
                logger.warning(f"Very small dataset ({len(alumni_data)} records). "
                              f"Consider adding more alumni data for better recommendations.")
            
            success = self.automl_recommender.train(alumni_data)
            
            if not success:
                logger.error("AutoML model training failed")
                return None
                
            # Save the trained AutoML model
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(MODEL_DIR, f'automl_model_{timestamp}.pkl')
            
            with open(file_path, 'wb') as f:
                pickle.dump(self.automl_recommender, f)
            
            # Create/update a symlink to the latest model
            latest_path = os.path.join(MODEL_DIR, 'automl_model_latest.pkl')
            if os.path.exists(latest_path):
                os.remove(latest_path)
            os.symlink(file_path, latest_path)
            
            # Extract model metadata for the database
            import json
            algorithm = self.automl_recommender.model.best_estimator_name
            hyperparameters = json.dumps(self.automl_recommender.model.best_config)
            
            # Extract metrics if available
            metrics = self.automl_recommender.metric
            train_score = None
            test_score = None
            training_time = None
            
            # Try to extract scores and training time from model history
            if hasattr(self.automl_recommender.model, 'best_loss'):
                test_score = -self.automl_recommender.model.best_loss  # Convert loss to score
            
            if hasattr(self.automl_recommender.model, 'best_config_train_time'):
                training_time = self.automl_recommender.model.best_config_train_time
                
            # For training score, check if available in model history
            try:
                if hasattr(self.automl_recommender.model, 'model'):
                    # Try to access training score from model history
                    train_history = getattr(self.automl_recommender.model, 'training_history', {})
                    if train_history:
                        # Try to get score from the latest history entry if available
                        train_score = train_history.get('train_scores', [0])[-1]
            except Exception as e:
                logger.warning(f"Could not extract training score: {e}")
                
            # Record the model generation in the database
            with transaction.atomic():
                # Set all previous automl models as inactive
                MLModelInfo.objects.filter(model_type='automl').update(is_active=False)
                
                # Create a record for the new model with metadata
                MLModelInfo.objects.create(
                    model_type='automl',
                    file_path=file_path,
                    is_active=True,
                    algorithm=algorithm,
                    hyperparameters=hyperparameters,
                    train_score=train_score,
                    test_score=test_score,
                    metrics=metrics,
                    training_time=training_time
                )
            
            logger.info(f"AutoML model generated and saved: {file_path}")
            logger.info(f"Model metadata: algorithm={algorithm}, metrics={metrics}, test_score={test_score}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error generating AutoML model: {e}")
            return None
    
    def generate_all_models(self):
        """Generate all models at once"""
        alumni_path = self.generate_alumni_model()
        job_path = self.generate_job_model()
        automl_path = self.generate_automl_model()
        
        return {
            'alumni_model_path': alumni_path,
            'job_model_path': job_path,
            'automl_model_path': automl_path,
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
    
    @staticmethod
    def load_automl_model():
        """Load the latest AutoML model"""
        try:
            latest_path = os.path.join(MODEL_DIR, 'automl_model_latest.pkl')
            if not os.path.exists(latest_path):
                logger.warning("No AutoML model found, returning None")
                return None
                
            with open(latest_path, 'rb') as f:
                automl_model = pickle.load(f)
            
            logger.info(f"Loaded AutoML model from {latest_path}")
            return automl_model
        except Exception as e:
            logger.error(f"Error loading AutoML model: {e}")
            return None
