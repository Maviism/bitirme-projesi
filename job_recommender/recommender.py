from collections import Counter
from .models import Student, Course, Organization, Internship, Job, JobRecommendation, Alumni

# Updated function to retrieve alumni data from the database
def get_alumni_database():
    """
    Retrieve alumni data from the database using the dedicated Alumni model
    """
    try:
        # Find alumni using the Alumni model
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
                    'gpa': float(student.gpa)
                },
                'course_grades': course_grades,
                'graduation_date': alumni_record.graduation_date,
                'current_job': {
                    'id': alumni_record.current_job.id,
                    'title': alumni_record.current_job.title,
                    'company': alumni_record.current_job.company,
                    'description': alumni_record.current_job.description,
                    'required_majors': alumni_record.current_job.required_majors
                }
            }
            alumni_data.append(alumni_record_data)
            
        return alumni_data
    except Exception as e:
        return []

def get_job_postings_database():
    """
    Retrieve job postings from the database
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
                'required_majors': job.required_majors
            })
            
        return job_postings
    except Exception as e:
        return []

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
        # No need to load data at initialization as we'll fetch from DB when needed
    
    def _extract_keywords(self, text):
        """
        Extract keywords from text string.
        """
        if not text or not isinstance(text, str):
            return []
        # Simple implementation - split by spaces and clean up
        keywords = [word.lower().strip() for word in text.split() if word.strip()]
        return keywords
    
    def get_alumni_recommendations(self, student_data, courses):
        """
        Generate job recommendations based on alumni with similar academic profiles.
        
        Parameters:
        -----------
        student_data : dict
            Student information including GPA, program, etc.
        courses : list
            List of courses taken by the student with grades
            
        Returns:
        --------
        list
            Recommended jobs based on alumni with similar profiles
        """
        # Get alumni data from database
        alumni_data = get_alumni_database()
        if not alumni_data:
            return []
            
        # Extract student features: GPA, program, and course performance
        try:
            student_gpa = float(student_data.get('gpa', 0))
        except (ValueError, TypeError):
            student_gpa = 0.0
            
        student_program = student_data.get('program', '')
        
        # Create a simple course grade mapping (could be more sophisticated)
        grade_mapping = {
            'AA': 4.0, 'BA': 3.5, 'BB': 3.0, 'CB': 2.5, 'CC': 2.0, 'DC': 1.5, 'DD': 1.0, 'FF': 0.0
        }
        
        # Create course vector for student
        student_courses = {}
        for course in courses:
            if isinstance(course, dict) and 'code' in course and 'grade' in course:
                student_courses[course['code']] = grade_mapping.get(course['grade'], 0)
        
        # Calculate similarity with each alumni
        similarities = []
        
        for alumni in alumni_data:
            try:
                # Get alumni's courses
                alumni_course_grades = alumni.get('course_grades', {})
                
                # Skip alumni without job information
                if 'current_job' not in alumni or not isinstance(alumni['current_job'], dict):
                    continue
                
                # Program match bonus
                program_bonus = 1.5 if alumni.get('student', {}).get('program') == student_program else 1.0
                
                # GPA similarity (inverse of difference)
                try:
                    alumni_gpa = float(alumni.get('student', {}).get('gpa', 0))
                    gpa_similarity = max(0, 1 - abs(student_gpa - alumni_gpa) / 4.0)
                except (ValueError, TypeError):
                    gpa_similarity = 0.5  # Default if GPA can't be compared
                
                # Course similarity
                common_courses = 0
                grade_diff_sum = 0
                for code, grade in student_courses.items():
                    if code in alumni_course_grades:
                        common_courses += 1
                        grade_diff_sum += abs(grade - alumni_course_grades[code])
                
                course_similarity = 1.0
                if common_courses > 0:
                    avg_grade_diff = grade_diff_sum / common_courses
                    course_similarity = max(0, 1 - avg_grade_diff / 4.0)
                
                # Calculate overall similarity
                similarity = (0.3 * gpa_similarity + 0.7 * course_similarity) * program_bonus
                
                # Get recommended job for this alumni
                job = alumni['current_job']
                similarities.append((similarity, job))
                    
            except Exception as e:
                continue
        
        # Sort by similarity (highest first)
        similarities.sort(reverse=True)
        
        # Extract top recommendations (up to 10 to ensure we have enough even with low scores)
        recommendations = [item[1] for item in similarities[:10]]
        return recommendations
    
    def get_job_recommendations(self, student_data, orgs, internships):
        """
        Generate job recommendations based on the student's organization and internship experiences.
        
        Parameters:
        -----------
        student_data : dict
            Student information including program, etc.
        orgs : list
            List of organization experiences
        internships : list
            List of internship experiences
            
        Returns:
        --------
        list
            Recommended jobs based on experiences
        """
        # Get job postings data from database
        job_postings = get_job_postings_database()
        if not job_postings:
            return []
            
        # Make sure orgs and internships are lists
        if not isinstance(orgs, list):
            orgs = []
        if not isinstance(internships, list):
            internships = []
            
        # Extract keywords from organizations and internships
        experience_keywords = []
        
        # Extract from organization descriptions
        for org in orgs:
            if isinstance(org, dict):
                if 'description' in org and org['description']:
                    experience_keywords.extend(self._extract_keywords(org['description']))
                if 'position' in org and org['position']:
                    experience_keywords.extend(self._extract_keywords(org['position']))
        
        # Extract from internship descriptions
        for internship in internships:
            if isinstance(internship, dict):
                if 'description' in internship and internship['description']:
                    experience_keywords.extend(self._extract_keywords(internship['description']))
                if 'position' in internship and internship['position']:
                    experience_keywords.extend(self._extract_keywords(internship['position']))
                if 'company' in internship and internship['company']:
                    experience_keywords.extend(self._extract_keywords(internship['company']))
        
        
        # Count keyword frequencies
        keyword_counts = Counter(experience_keywords)
        
        # Match with job postings
        matches = []
        
        for job in job_postings:
            try:
                # Extract keywords from job description
                job_keywords = self._extract_keywords(job['description'])
                job_keywords.extend(self._extract_keywords(job['title']))
                
                # Program match bonus (safely get program from student_data)
                program = student_data.get('program', '')
                required_majors = job.get('required_majors', '')
                program_match = 1.5 if program in required_majors else 1.0
                
                # Calculate keyword match score
                match_score = sum(keyword_counts.get(kw, 0) for kw in job_keywords) * program_match
                matches.append((match_score, job))
            except Exception as e:
                continue
        
        try:
            # Sort using the first element of each tuple (the match score)
            matches.sort(key=lambda x: x[0], reverse=True)
        except Exception as e:
            pass
        
        # Extract top recommendations (up to 10 to ensure we have enough even with low scores)
        recommendations = [item[1] for item in matches[:10]]
        return recommendations
    
    def get_hybrid_recommendations(self, student_data, courses, orgs, internships):
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
            
        # Get recommendations from both sources
        try:
            alumni_recs = self.get_alumni_recommendations(student_data, courses)
            
            # Even with empty orgs and internships, try to get recommendations
            job_recs = self.get_job_recommendations(student_data, orgs, internships)
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
                        'sources': ['alumni']
                    }
                else:
                    combined_scores[job_id]['score'] += score * self.alumni_weight
                    if 'alumni' not in combined_scores[job_id]['sources']:
                        combined_scores[job_id]['sources'].append('alumni')
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