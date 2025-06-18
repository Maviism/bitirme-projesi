"""
AutoML Recommender for Job Recommendations

This module implements an AutoML-based recommendation system using FLAML.
It focuses on providing a simplified alumni-based recommendation algorithm
without complex bonus calculations.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from flaml import AutoML
import math

logger = logging.getLogger(__name__)

class AlumniAutoMLRecommender:
    """
    Alumni recommendation system using FLAML AutoML
    """
    
    def __init__(self, time_budget=60, metric="r2", estimator_list=None, ensemble=True):
        """
        Initialize the AutoML recommender with configuration parameters.
        
        Parameters:
        -----------
        time_budget : int
            Time budget in seconds for the AutoML training
        metric : str
            Evaluation metric for model selection
        estimator_list : list
            List of estimators to try. If None, will use FLAML default estimators
        ensemble : bool
            Whether to use ensemble models
        """
        self.time_budget = time_budget
        self.metric = metric
        self.estimator_list = estimator_list
        self.ensemble = ensemble
        self.model = AutoML()
        self.is_trained = False
        self.grade_mapping = {
            'AA': 4.0, 'BA': 3.5, 'BB': 3.0, 'CB': 2.5, 
            'CC': 2.0, 'DC': 1.5, 'DD': 1.0, 'FF': 0.0
        }
        
        # Record config for logging/debugging
        self.config = {
            "time_budget": time_budget,
            "metric": metric,
            "estimator_list": estimator_list,
            "ensemble": ensemble
        }
    
    def _preprocess_alumni_data(self, alumni_data):
        """
        Preprocess alumni data for training the AutoML model.
        
        Parameters:
        -----------
        alumni_data : list
            List of alumni records from the database
            
        Returns:
        --------
        tuple
            X, y for model training
        """
        # Create lists to hold features and target
        records = []
        job_targets = []
        
        for alumni in alumni_data:
            # Skip alumni without job information
            if 'current_job' not in alumni or not isinstance(alumni['current_job'], dict):
                continue
                
            student = alumni.get('student', {})
            job = alumni.get('current_job', {})
            course_grades = alumni.get('course_grades', {})
            
            # Basic features
            record = {
                'gpa': float(student.get('gpa', 0)),
                'program': student.get('program', ''),
            }
            
            # Add course grades
            for course_code, grade in course_grades.items():
                record[f'course_{course_code}'] = float(grade)
            
            records.append(record)
            job_targets.append(job.get('id', -1))
        
        if not records:
            return None, None
        
        # Convert to pandas DataFrames
        X_df = pd.DataFrame(records)
        y = np.array(job_targets)
        
        return X_df, y
    
    def train(self, alumni_data):
        """
        Train the AutoML model on alumni data.
        
        Parameters:
        -----------
        alumni_data : list
            List of alumni records from the database
            
        Returns:
        --------
        bool
            True if training was successful, False otherwise
        """
        try:
            X_df, y = self._preprocess_alumni_data(alumni_data)
            
            if X_df is None or y is None:
                logger.warning("No valid alumni data for training")
                return False
            
            # Log dataset size for debugging
            n_samples = len(X_df)
            logger.info(f"Training AutoML model with {n_samples} alumni records")
            
            if n_samples < 5:
                logger.warning(f"Very small dataset detected ({n_samples} samples). " 
                               f"AutoML may not perform optimally.")
            
            # Determine best estimators based on dataset characteristics
            if self.estimator_list is None:
                self.estimator_list = self._determine_best_estimators(X_df)
            
            # Create column transformer for preprocessing
            numeric_features = [col for col in X_df.columns if col != 'program']
            categorical_features = ['program'] if 'program' in X_df.columns else []
            
            preprocessor = ColumnTransformer(
                transformers=[
                    ('num', StandardScaler(), numeric_features),
                    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
                ]
            )
            
            # Use the previously determined estimator list
            auto_estimator_list = self.estimator_list
            
            # Set up automl with preprocessing pipeline
            settings = {
                "time_budget": self.time_budget,
                "metric": self.metric,
                "task": "classification",  # Predicting job ID as a classification task
                "verbose": 1,
                "ensemble": self.ensemble,
            }
            
            # Add estimator_list if determined
            if auto_estimator_list is not None:
                settings["estimator_list"] = auto_estimator_list
                logger.info(f"Using optimized estimator list: {auto_estimator_list}")
            
            # Adjust CV folds based on dataset size to avoid the error:
            # "Cannot have number of splits n_splits=5 greater than the number of samples"
            if n_samples < 10:
                # For very small datasets, use leave-one-out CV or a small number of folds
                n_folds = max(2, math.floor(n_samples / 2))
                logger.info(f"Small dataset detected. Adjusting CV folds from default 5 to {n_folds}")
                settings["n_splits"] = n_folds
            
            # Log configuration
            logger.info(f"Training AutoML with settings: {settings}")
            
            # Fit the model
            self.model.fit(
                X_train=X_df, 
                y_train=y, 
                **settings
            )
            
            logger.info(f"AutoML training completed. Best model: {self.model.best_estimator_name}")
            self.is_trained = True
            
            # Log best config for future reference
            logger.info(f"Best config: {self.model.best_config}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training AutoML model: {e}")
            return False
    
    def recommend(self, student_data, courses, top_n=10):
        """
        Generate job recommendations using the trained AutoML model.
        
        Parameters:
        -----------
        student_data : dict
            Student information including GPA, program, etc.
        courses : list
            List of courses taken by the student with grades
        top_n : int
            Number of recommendations to return
            
        Returns:
        --------
        list
            Recommended jobs sorted by probability
        """
        if not self.is_trained:
            logger.warning("AutoML model not trained yet")
            return []
        
        try:
            # Validate inputs
            if not isinstance(student_data, dict):
                logger.warning("Invalid student_data format")
                student_data = {}
                
            if not isinstance(courses, list):
                logger.warning("Invalid courses format")
                courses = []
                
            # Convert student data to model format
            try:
                gpa = float(student_data.get('gpa', 0))
            except (ValueError, TypeError):
                gpa = 0.0
                
            student_record = {
                'gpa': gpa,
                'program': str(student_data.get('program', '')),
            }
            
            # Add course grades
            for course in courses:
                if isinstance(course, dict) and 'code' in course and 'grade' in course:
                    course_code = course['code']
                    grade = self.grade_mapping.get(course['grade'], 0)
                    student_record[f'course_{course_code}'] = grade
            
            # Convert to DataFrame
            X_student = pd.DataFrame([student_record])
            
            # Handle missing features that were in training but not in test data
            # Get model features from best config if available
            logger.debug(f"Student data fields: {list(student_record.keys())}")
            
            # Get predictions with probabilities
            try:
                job_probs = self.model.predict_proba(X_student)
                job_ids = self.model.classes_
                
                # Create recommendations list
                recommendations = []
                for i, job_id in enumerate(job_ids):
                    if i < len(job_probs[0]):
                        prob = job_probs[0][i]
                        recommendations.append({
                            'job_id': int(job_id),
                            'probability': float(prob)
                        })
                
                # Sort by probability (highest first)
                recommendations.sort(key=lambda x: x['probability'], reverse=True)
                
                # Return top N recommendations
                return recommendations[:top_n]
            except Exception as e:
                logger.error(f"Error in prediction with model: {e}")
                # If prediction fails, try a simple fallback using just the course codes
                return self._simple_recommendation_fallback(student_data, courses, top_n)
                
        except Exception as e:
            logger.error(f"Error generating AutoML recommendations: {e}")
            return []
            
    def _simple_recommendation_fallback(self, student_data, courses, top_n=10):
        """
        Fallback method when the main AutoML model fails to make predictions.
        
        Returns:
        --------
        list
            Empty list of recommendations
        """
        logger.warning("AutoML prediction failed, no recommendations available")
        return []
    
    def get_job_details(self, recommendations, job_db):
        """
        Enrich recommendations with job details from the database
        
        Parameters:
        -----------
        recommendations : list
            List of job recommendations with job IDs and probabilities
        job_db : list
            List of job details from the database
            
        Returns:
        --------
        list
            Enriched job recommendations
        """
        job_map = {job['id']: job for job in job_db}
        
        enriched_recommendations = []
        for rec in recommendations:
            job_id = rec['job_id']
            if job_id in job_map:
                # Check if we have skill match score to adjust the final score
                probability = rec['probability']
                skill_match_score = rec.get('skill_match_score', 0)
                
                # Blend probability with skill match if available (70% model, 30% skills)
                if skill_match_score > 0:
                    final_score = 0.7 * probability + 0.3 * skill_match_score
                else:
                    final_score = probability
                    
                enriched_recommendations.append({
                    'job': job_map[job_id],
                    'score': final_score,
                    'model_score': probability,
                    'skill_score': skill_match_score,
                    'sources': ['alumni_automl']
                })
        
        # Sort by final score
        enriched_recommendations.sort(key=lambda x: x['score'], reverse=True)
        return enriched_recommendations
    
    def post_filter_by_skills(self, recommendations, skills, job_db):
        """
        Apply post-filtering to recommendations based on skills matching.
        Does not change the order but adds a skill_match_score for hybrid recommender to use.
        
        Parameters:
        -----------
        recommendations : list
            List of job recommendations with job IDs and probabilities
        skills : list 
            List of student skills
        job_db : list
            List of job details from the database
            
        Returns:
        --------
        list
            Recommendations with additional skill_match_score
        """
        if not skills or not isinstance(skills, list) or len(skills) == 0:
            return recommendations
            
        job_map = {job['id']: job for job in job_db}
        
        for rec in recommendations:
            job_id = rec['job_id']
            skill_match_score = 0.0
            
            if job_id in job_map:
                job = job_map[job_id]
                job_skills = job.get('required_skills', [])
                
                if job_skills and isinstance(job_skills, list):
                    # Calculate number of matching skills
                    matching_skills = len(set(skills) & set(job_skills))
                    if matching_skills > 0:
                        # More matching skills = higher score
                        skill_match_score = matching_skills / max(len(skills), 1) 
            
            rec['skill_match_score'] = skill_match_score
            
        return recommendations
    
    def _determine_best_estimators(self, X_df):
        """
        Determine the best estimators to use based on dataset characteristics.
        
        Parameters:
        -----------
        X_df : DataFrame
            The feature DataFrame
            
        Returns:
        --------
        list
            List of estimator names to try
        """
        n_samples, n_features = X_df.shape
        
        # Logic to select estimators based on dataset size
        if n_samples < 100:
            # For very small datasets, simple models work best
            return ['lgbm', 'rf', 'xgboost','kneighbor']
        elif n_samples < 1000:
            # Medium datasets - add more options
            return ['lgbm', 'rf', 'xgboost', 'catboost', 'extra_tree', 'kneighbor']
        else:
            # Large datasets - use all available estimators
            return None  # None means use all default estimators
    
    def _adjust_cv_folds(self, n_samples):
        """
        Adjust the number of cross-validation folds based on dataset size.
        
        Parameters:
        -----------
        n_samples : int
            Number of samples in the dataset
            
        Returns:
        --------
        int
            Recommended number of cross-validation folds
        """
        if n_samples < 100:
            return 2  # Minimum folds for very small datasets
        elif n_samples < 1000:
            return 3  # Recommended folds for small to medium datasets
        else:
            return 5  # Default to 5 folds for larger datasets
