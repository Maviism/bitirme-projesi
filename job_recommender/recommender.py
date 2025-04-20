from collections import Counter

class HybridRecommender:
    """
    A hybrid recommender system that combines alumni-based and job-posting-based recommendations.
    """
    
    def __init__(self, alumni_weight=0.6, job_weight=0.4):
        """
        Initialize the recommender with weights for each component.
        
        Parameters:
        -----------
        alumni_weight : float
            Weight for alumni-based recommendations (between 0 and 1)
        job_weight : float
            Weight for job-posting-based recommendations (between 0 and 1)
        """
        self.alumni_weight = alumni_weight
        self.job_weight = job_weight
        
        # Sample database - in a real application, these would come from a database
        self.alumni_db = []
        self.job_postings_db = []
    
    def set_databases(self, alumni_db, job_postings_db):
        """Set the alumni and job postings databases."""
        self.alumni_db = alumni_db
        self.job_postings_db = job_postings_db
    
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
        if not self.alumni_db:
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
        for alumni in self.alumni_db:
            try:
                # Program match bonus
                program_bonus = 1.5 if alumni['student']['program'] == student_program else 1.0
                
                # GPA similarity (inverse of difference)
                try:
                    alumni_gpa = float(alumni['student']['gpa'])
                except (ValueError, TypeError):
                    alumni_gpa = 0.0
                    
                gpa_similarity = max(0, 1 - abs(student_gpa - alumni_gpa) / 4.0)
                
                # Course similarity
                common_courses = 0
                grade_diff_sum = 0
                for code, grade in student_courses.items():
                    if code in alumni['course_grades']:
                        common_courses += 1
                        grade_diff_sum += abs(grade - alumni['course_grades'][code])
                
                course_similarity = 1.0
                if common_courses > 0:
                    avg_grade_diff = grade_diff_sum / common_courses
                    course_similarity = max(0, 1 - avg_grade_diff / 4.0)
                
                # Calculate overall similarity
                similarity = (0.3 * gpa_similarity + 0.7 * course_similarity) * program_bonus
                similarities.append((similarity, alumni['current_job']))
            except Exception:
                continue
        
        # Sort by similarity (highest first)
        similarities.sort(reverse=True)
        
        # Extract top recommendations
        recommendations = [item[1] for item in similarities[:5]]
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
        if not self.job_postings_db:
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
        for job in self.job_postings_db:
            try:
                # Extract keywords from job description
                job_keywords = self._extract_keywords(job['description'])
                job_keywords.extend(self._extract_keywords(job['title']))
                
                # Program match bonus (safely get program from student_data)
                program = student_data.get('program', '')
                required_majors = job.get('required_majors', [])
                program_match = 1.5 if program in required_majors else 1.0
                
                # Calculate keyword match score
                match_score = sum(keyword_counts.get(kw, 0) for kw in job_keywords) * program_match
                matches.append((match_score, job))
            except Exception:
                continue
        
        try:
            # Sort using the first element of each tuple (the match score)
            matches.sort(key=lambda x: x[0], reverse=True)
        except Exception:
            pass
        
        # Extract top recommendations
        recommendations = [item[1] for item in matches[:5]]
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
            job_recs = self.get_job_recommendations(student_data, orgs, internships)
        except Exception:
            return []
        
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
            except Exception:
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
            except Exception:
                continue
        
        try:
            # Convert dictionary values to list and sort by score
            ranked_jobs = list(combined_scores.values())
            
            # Defensive sorting - make sure we have scores to sort by
            ranked_jobs = [job for job in ranked_jobs if 'score' in job and job['score'] is not None]
            
            # Sort using key function
            ranked_jobs.sort(key=lambda x: float(x['score']) if isinstance(x['score'], (int, float, str)) else 0, reverse=True)
            
            return ranked_jobs
        except Exception:
            return []
    
    def _extract_keywords(self, text):
        """
        Extract relevant keywords from text.
        
        Parameters:
        -----------
        text : str
            Text to extract keywords from
            
        Returns:
        --------
        list
            List of keywords
        """
        if not text or not isinstance(text, str):
            return []
            
        # In a real implementation, this would use NLP techniques
        # For simplicity, we'll just split on spaces and filter common words
        text = text.lower()
        words = text.split()
        
        # Filter out common words (this would be more sophisticated in a real system)
        stopwords = {'and', 'the', 'is', 'at', 'of', 'to', 'for', 'in', 'on', 'with'}
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        return keywords


# Sample alumni database initialization function
def initialize_alumni_database():
    """
    Initialize a sample alumni database.
    In a real application, this would come from a database.
    """
    return [
        {
            'id': 1,
            'student': {
                'program': 'Computer Engineering Pr.',
                'gpa': '3.5'
            },
            'course_grades': {
                'BLM1101': 4.0,  # Physics
                'BLM1102': 3.5,  # Mathematics
                'BLM1121': 3.0,  # Linear Algebra
                'BLM1123': 4.0,  # Introduction to Programming
            },
            'current_job': {
                'id': 101,
                'title': 'Software Engineer',
                'company': 'Tech Solutions Inc.',
                'description': 'Developing backend systems using Java and Spring Boot',
                'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Software Engineering']
            }
        },
        {
            'id': 2,
            'student': {
                'program': 'Computer Engineering Pr.',
                'gpa': '2.8'
            },
            'course_grades': {
                'BLM1101': 3.0,  # Physics
                'BLM1102': 2.5,  # Mathematics
                'BLM1121': 3.0,  # Linear Algebra
                'BLM1123': 3.5,  # Introduction to Programming
            },
            'current_job': {
                'id': 102,
                'title': 'QA Engineer',
                'company': 'Quality Solutions',
                'description': 'Testing software applications and writing automated tests',
                'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Information Technology']
            }
        },
        {
            'id': 3,
            'student': {
                'program': 'Computer Engineering Pr.',
                'gpa': '3.2'
            },
            'course_grades': {
                'BLM1101': 3.0,  # Physics
                'BLM1102': 3.0,  # Mathematics
                'BLM1121': 3.5,  # Linear Algebra
                'BLM1123': 4.0,  # Introduction to Programming
            },
            'current_job': {
                'id': 103,
                'title': 'Data Analyst',
                'company': 'Data Insights Co.',
                'description': 'Analyzing data and creating visualization dashboards',
                'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Statistics', 'Mathematics']
            }
        }
    ]

# Sample job postings database initialization function
def initialize_job_postings_database():
    """
    Initialize a sample job postings database.
    In a real application, this would come from a database.
    """
    return [
        {
            'id': 101,
            'title': 'Software Engineer',
            'company': 'Tech Solutions Inc.',
            'description': 'Developing backend systems using Java and Spring Boot',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Software Engineering']
        },
        {
            'id': 102,
            'title': 'QA Engineer',
            'company': 'Quality Solutions',
            'description': 'Testing software applications and writing automated tests',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Information Technology']
        },
        {
            'id': 103,
            'title': 'Data Analyst',
            'company': 'Data Insights Co.',
            'description': 'Analyzing data and creating visualization dashboards',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Statistics', 'Mathematics']
        },
        {
            'id': 104,
            'title': 'Web Developer',
            'company': 'Web Solutions',
            'description': 'Building responsive web applications using React and Node.js',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Web Development']
        },
        {
            'id': 105,
            'title': 'Machine Learning Engineer',
            'company': 'AI Innovations',
            'description': 'Developing and implementing machine learning algorithms',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Data Science']
        },
        {
            'id': 106,
            'title': 'DevOps Engineer',
            'company': 'Cloud Services Inc.',
            'description': 'Managing cloud infrastructure and CI/CD pipelines',
            'required_majors': ['Computer Engineering', 'Computer Engineering Pr.', 'Cloud Computing']
        }
    ]