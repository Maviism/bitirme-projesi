"""
Job Recommendation System

This module implements a hybrid job recommendation system that uses pre-generated 
ML models rather than direct database queries. The system combines:

1. Alumni-based recommendations: Using AutoML (FLAML) to automatically find the best model
   for matching students with jobs based on academic profiles
2. Job-based recommendations: Using experience and skills to match with suitable job postings

Models are loaded from disk or generated on first use, and contain pre-computed data
structures to speed up the recommendation process.
"""

from collections import Counter
from sentence_transformers import SentenceTransformer, util
import torch
import logging
import os

logger = logging.getLogger(__name__)

# Import the ML model generator
try:
    from .ml_model.model_generator import MLModelGenerator
    from .ml_model.automl_recommender import AlumniAutoMLRecommender  # Import AutoML recommender
except ImportError:
    logger.error("Failed to import MLModelGenerator or AlumniAutoMLRecommender. A model needs to be generated before recommendations will work.")

# Function to access alumni model data
def get_alumni_database():
    """
    Load alumni model data from the pre-generated model or generate a new one.
    Returns the data as a list structure or empty list if no model is available.
    """
    try:
        if 'MLModelGenerator' not in globals():
            logger.error("MLModelGenerator not available")
            return []
            
        # First try to load existing model
        logger.info("Loading alumni model data")
        alumni_data = MLModelGenerator.load_alumni_model()
        
        if alumni_data:
            logger.info(f"Alumni model loaded successfully with {len(alumni_data)} records")
            return alumni_data
        
        # If no model found, generate a new one
        logger.info("No alumni model found, generating new model")
        model_generator = MLModelGenerator()
        file_path = model_generator.generate_alumni_model()
        
        if file_path:
            # Load the newly generated model
            alumni_data = MLModelGenerator.load_alumni_model()
            if alumni_data:
                logger.info(f"New alumni model generated and loaded with {len(alumni_data)} records")
                return alumni_data
        
        logger.warning("Could not generate or load alumni model")
        return []
    except Exception as e:
        logger.error(f"Error in alumni model processing: {e}")
        return []

def get_job_postings_database():
    """
    Load job model data from the pre-generated model or generate a new one.
    Returns the data as a list structure or empty list if no model is available.
    """
    try:
        if 'MLModelGenerator' not in globals():
            logger.error("MLModelGenerator not available")
            return []
            
        # First try to load existing model
        logger.info("Loading job model data")
        job_postings = MLModelGenerator.load_job_model()
        
        if job_postings:
            logger.info(f"Job model loaded successfully with {len(job_postings)} records")
            return job_postings
        
        # If no model found, generate a new one
        logger.info("No job model found, generating new model")
        model_generator = MLModelGenerator()
        file_path = model_generator.generate_job_model()
        
        if file_path:
            # Load the newly generated model
            job_postings = MLModelGenerator.load_job_model()
            if job_postings:
                logger.info(f"New job model generated and loaded with {len(job_postings)} records")
                return job_postings
        
        logger.warning("Could not generate or load job model")
        return []
    except Exception as e:
        logger.error(f"Error in job model processing: {e}")
        return []

def get_automl_model():
    """
    Load AutoML recommender model from the pre-generated model or return None if not available.
    """
    try:
        if 'MLModelGenerator' not in globals():
            logger.error("MLModelGenerator not available")
            return None
            
        # Try to load existing model
        logger.info("Loading AutoML model")
        automl_model = MLModelGenerator.load_automl_model()
        
        if automl_model:
            logger.info("AutoML model loaded successfully")
            return automl_model
        
        # If no model found, we return None and let the caller decide what to do
        logger.warning("Could not find AutoML model")
        return None
    except Exception as e:
        logger.error(f"Error loading AutoML model: {e}")
        return None

class HybridRecommender:
    """
    A hybrid recommender system that combines alumni-based and job-posting-based recommendations.
    """
    
    def __init__(self, alumni_weight=0.6, job_weight=0.4, min_recommendations=5):
        """
        Initialize the recommender with weights for each component.
        
        Parameters:
        -----------
        alumni_weight : float
            Weight for alumni-based recommendations (between 0 and 1)
        job_weight : float
            Weight for job-posting-based recommendations (between 0 and 1)
        min_recommendations : int
            Minimum number of recommendations to return, even with low scores
        """
        self.alumni_weight = alumni_weight
        self.job_weight = job_weight
        self.min_recommendations = min_recommendations
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.automl_recommender = None
        
        # Try to load pre-trained AutoML model
        try:
            self.automl_recommender = get_automl_model()
            
            if self.automl_recommender is not None:
                logger.info("Using pre-trained AutoML model")
            else:
                logger.info("No pre-trained AutoML model found - will train on first use")
        except Exception as e:
            logger.error(f"Error loading AutoML model: {e}")
    
    def _extract_keywords(self, text):
        """
        Extract keywords from text string.
        """
        if not text or not isinstance(text, str):
            return []
        # Simple implementation - split by spaces and clean up
        keywords = [word.lower().strip() for word in text.split() if word.strip()]
        return keywords
    
    def get_alumni_recommendations(self, student_data, courses, skills=None):
        """
        Generate job recommendations based on alumni with similar academic profiles using AutoML.
        
        Parameters:
        -----------
        student_data : dict
            Student information including GPA, program, etc.
        courses : list
            List of courses taken by the student with grades
        skills : list
            List of student skills used for post-filtering recommendations
            
        Returns:
        --------
        list
            Recommended jobs based on AutoML prediction
        """
        # Get alumni data from database
        alumni_data = get_alumni_database()
        if not alumni_data:
            logger.warning("No alumni data available for AutoML recommendations")
            return []
            
        try:
            # If no AutoML recommender available, initialize it
            if self.automl_recommender is None:
                try:
                    from .ml_model.automl_recommender import AlumniAutoMLRecommender
                    logger.info("Initializing new AutoML recommender")
                    self.automl_recommender = AlumniAutoMLRecommender(time_budget=60)
                except Exception as e:
                    logger.error(f"Failed to initialize AutoML recommender: {e}")
                    return []
                
            # Train the model if not already trained
            if not self.automl_recommender.is_trained:
                # Log dataset size for debugging
                logger.info(f"Training AutoML model on {len(alumni_data)} alumni records")
                
                # Check if we have enough data to train properly
                if len(alumni_data) < 5:
                    logger.warning(f"Very small dataset ({len(alumni_data)} records). "
                                  f"AutoML may not perform optimally.")
                
                logger.info("Training AutoML model on alumni data")
                success = self.automl_recommender.train(alumni_data)
                if not success:
                    logger.error("AutoML training failed, attempting with longer time budget")
                    # Try again with a longer time budget as fallback
                    self.automl_recommender.time_budget = 120
                    success = self.automl_recommender.train(alumni_data)
                    if not success:
                        logger.error("AutoML training failed even with extended time budget")
                        return []
                logger.info("AutoML model trained successfully")
            else:
                logger.info("Using pre-trained AutoML model for recommendations")
            
            # Get job postings database
            job_postings = get_job_postings_database()
            
            # Get recommendations using the trained model
            recommendations = self.automl_recommender.recommend(student_data, courses)
            
            # Apply skill post-filtering if skills provided
            if skills and isinstance(skills, list) and len(skills) > 0:
                recommendations = self.automl_recommender.post_filter_by_skills(
                    recommendations, skills, job_postings)
                logger.info(f"Applied skill filtering with {len(skills)} skills")
            
            # Get job details for the recommendations
            enriched_recommendations = self.automl_recommender.get_job_details(recommendations, job_postings)
            
            if enriched_recommendations:
                logger.info(f"Generated {len(enriched_recommendations)} AutoML recommendations")
            else:
                logger.warning("No AutoML recommendations were generated")
                
            return [rec['job'] for rec in enriched_recommendations]
            
        except Exception as e:
            logger.error(f"Error in AutoML alumni recommendations: {e}")
            return []
    

    
    def get_job_recommendations(self, student_data, orgs, internships, skills=None):
        """
        Generate job recommendations based on experience similarity and skills matching.
        Uses pre-computed embeddings when available.
        """
        # Get job data from model
        job_postings = get_job_postings_database()
        if not job_postings:
            return []

        # Validate inputs
        if not isinstance(orgs, list): orgs = []
        if not isinstance(internships, list): internships = []
        if not isinstance(skills, list): skills = []

        # Combine all experience text
        experience_texts = []
        for org in orgs:
            if isinstance(org, dict):
                experience_texts.append(org.get('description', ''))
                experience_texts.append(org.get('position', ''))
        
        for internship in internships:
            if isinstance(internship, dict):
                experience_texts.append(internship.get('description', ''))
                experience_texts.append(internship.get('position', ''))
                experience_texts.append(internship.get('company', ''))

        combined_experience = ' '.join(filter(None, experience_texts)).strip()
        if not combined_experience:
            return []

        # Generate embedding for student experience
        try:
            experience_embedding = self.model.encode(combined_experience, convert_to_tensor=True)
        except Exception as e:
            logger.error(f"Error encoding experience: {e}")
            return []

        matches = []
        program = student_data.get('program', '')

        for job in job_postings:
            try:
                # Use pre-computed embedding if available
                if 'embedding' in job and job['embedding']:
                    # Convert the stored embedding back to tensor for comparison
                    import torch
                    job_embedding = torch.tensor(job['embedding'])
                else:
                    # Generate embedding on the fly if not pre-computed
                    job_text = f"{job.get('title', '')}. {job.get('description', '')}"
                    job_embedding = self.model.encode(job_text, convert_to_tensor=True)
                
                # Calculate similarity score
                similarity_score = float(util.pytorch_cos_sim(experience_embedding, job_embedding)[0][0])

                # Program match bonus
                required_majors = job.get('required_majors', '')
                program_match = 1.5 if program and program in required_majors else 1.0
                
                # Skills matching bonus
                skill_bonus = 1.0
                if skills and len(skills) > 0:
                    job_skills = job.get('required_skills', [])
                    if job_skills and isinstance(job_skills, list):
                        matching_skills = len(set(skills) & set(job_skills))
                        if matching_skills > 0:
                            skill_bonus = 1.0 + (matching_skills / max(len(skills), 1)) * 0.5
                
                # Calculate total score with all bonuses
                total_score = similarity_score * program_match * skill_bonus

                matches.append((total_score, job))
            except Exception as e:
                logger.debug(f"Skipping job {job.get('id')}: {e}")
                continue

        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Return top recommendations
        recommendations = [item[1] for item in matches[:10]]
        return recommendations

    def get_hybrid_recommendations(self, student_data, courses, orgs, internships, skills=None):
        """
        Generate hybrid job recommendations combining both approaches.
        
        Parameters:
        -----------
        student_data : dict
            Student information including GPA, program, etc.
        courses : list
            List of courses taken by the student with grades
        orgs : list
            List of organization experiences
        internships : list
            List of internship experiences
        skills : list
            List of student skill preferences
            
        Returns:
        --------
        list
            List of recommendation objects with job info and scores
        """
        # Handle empty inputs gracefully
        if not isinstance(student_data, dict):
            student_data = {}
        if not isinstance(courses, list):
            courses = []
        if not isinstance(orgs, list):
            orgs = []
        if not isinstance(internships, list):
            internships = []
        if not isinstance(skills, list):
            skills = []
            
        # Get recommendations from both sources
        try:
            alumni_recs = self.get_alumni_recommendations(student_data, courses, skills)
            
            # Even with empty orgs and internships, try to get recommendations
            job_recs = self.get_job_recommendations(student_data, orgs, internships, skills)
        except Exception as e:
            # If there's an error but we don't want to fail completely,
            # return a "no recommendations" message
            return [{
                'job': {
                    'id': 'no-recommendations',
                    'title': 'No Recommendations Available',
                    'company': 'N/A',
                    'description': 'We could not retrieve job recommendations at this time. Please try again later.'
                },
                'score': 0,
                'sources': ['system']
            }]
        
        # If both recommendation sources are empty, return a "no recommendations" message
        if not alumni_recs and not job_recs:
            return [{
                'job': {
                    'id': 'no-recommendations',
                    'title': 'No Recommendations Available',
                    'company': 'N/A',
                    'description': 'We could not find any job recommendations based on your profile. Please check back later as our database grows.'
                },
                'score': 0,
                'sources': ['system']
            }]
        
        # Combine recommendations with weights
        combined_scores = {}
        
        # Process alumni recommendations
        for i, job in enumerate(alumni_recs):
            try:
                if not isinstance(job, dict) or 'id' not in job:
                    continue  # Skip invalid jobs
                    
                score = (len(alumni_recs) - i) / max(1, len(alumni_recs))  # Avoid division by zero
                job_id = str(job['id'])  # Convert to string to ensure consistent key types
                if job_id not in combined_scores:
                    combined_scores[job_id] = {
                        'job': job,
                        'score': score * self.alumni_weight,
                        'sources': ['alumni_automl']
                    }
                else:
                    combined_scores[job_id]['score'] += score * self.alumni_weight
                    if 'alumni_automl' not in combined_scores[job_id]['sources']:
                        combined_scores[job_id]['sources'].append('alumni_automl')
            except Exception as e:
                continue
                
        # Process job posting recommendations
        for i, job in enumerate(job_recs):
            try:
                if not isinstance(job, dict) or 'id' not in job:
                    continue  # Skip invalid jobs
                    
                score = (len(job_recs) - i) / max(1, len(job_recs))  # Avoid division by zero
                job_id = str(job['id'])  # Convert to string to ensure consistent key types
                if job_id not in combined_scores:
                    combined_scores[job_id] = {
                        'job': job,
                        'score': score * self.job_weight,
                        'sources': ['job_posting']
                    }
                else:
                    combined_scores[job_id]['score'] += score * self.job_weight
                    if 'job_posting' not in combined_scores[job_id]['sources']:
                        combined_scores[job_id]['sources'].append('job_posting')
            except Exception as e:
                continue
                        
        # Convert to list and sort by score
        recommendations = list(combined_scores.values())
        recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        if len(recommendations) > 0:
            pass
        else:
            # If we've processed everything but still have no recommendations, return a message
            return [{
                'job': {
                    'id': 'no-recommendations',
                    'title': 'No Recommendations Available',
                    'company': 'N/A',
                    'description': 'We could not find any job recommendations matching your profile. Please try again with more information about your courses and experiences.'
                },
                'score': 0,
                'sources': ['system']
            }]
            
        return recommendations