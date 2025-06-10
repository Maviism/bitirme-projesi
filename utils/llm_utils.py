"""
LLM Utils for Resume Generator and Job Recommender
Supports multiple LLM providers: OpenAI, Google Gemini, and others
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the LLM"""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON response using the LLM"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("OpenAI library not installed. Install with: pip install openai")
                raise
        else:
            logger.warning("OpenAI API key not provided")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI GPT"""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check API key.")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get('max_tokens', 1500),
                temperature=kwargs.get('temperature', 0.7)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON response using OpenAI"""
        json_prompt = f"{prompt}\n\nPlease respond with a valid JSON object only."
        if schema:
            json_prompt += f"\nExpected schema: {json.dumps(schema, indent=2)}"
        
        response_text = self.generate_text(json_prompt, **kwargs)
        
        try:
            # Extract JSON from response (handle cases where model adds extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise


class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
            except ImportError:
                logger.error("Google Generative AI library not installed. Install with: pip install google-generativeai")
                raise
        else:
            logger.warning("Gemini API key not provided")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Google Gemini"""
        if not self.client:
            raise ValueError("Gemini client not initialized. Check API key.")
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': kwargs.get('max_tokens', 1500),
                    'temperature': kwargs.get('temperature', 0.7)
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON response using Gemini"""
        json_prompt = f"{prompt}\n\nPlease respond with a valid JSON object only."
        if schema:
            json_prompt += f"\nExpected schema: {json.dumps(schema, indent=2)}"
        
        response_text = self.generate_text(json_prompt, **kwargs)
        
        try:
            # Extract JSON from response (handle cases where model adds extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise


class LLMUtils:
    """Main utility class for LLM operations"""
    
    def __init__(self, provider: str = "openai", **kwargs):
        """
        Initialize LLM Utils with specified provider
        
        Args:
            provider: 'openai' or 'gemini'
            **kwargs: Additional arguments passed to provider
        """
        self.provider_name = provider.lower()
        
        if self.provider_name == "openai":
            self.provider = OpenAIProvider(**kwargs)
        elif self.provider_name == "gemini":
            self.provider = GeminiProvider(**kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate_resume_content(self, user_data: Dict, job_description: str = "") -> Dict:
        """
        Generate resume content based on user data and optional job description
        
        Args:
            user_data: Dictionary containing user information
            job_description: Optional job description for tailoring
            
        Returns:
            Dictionary with generated resume sections
        """
        prompt = f"""
        Generate professional resume content based on the following user data:
        
        User Information:
        {json.dumps(user_data, indent=2)}
        
        {f"Job Description to tailor for: {job_description}" if job_description else ""}
        
        Generate a comprehensive resume with the following sections:
        - Professional Summary (2-3 sentences)
        - Skills (list of relevant skills)
        - Experience (if any work experience provided)
        - Education
        - Projects (if any projects provided)
        
        Make the content professional, concise, and ATS-friendly.
        """
        
        schema = {
            "professional_summary": "string",
            "skills": ["string"],
            "experience": [
                {
                    "company": "string",
                    "position": "string",
                    "duration": "string",
                    "description": "string"
                }
            ],
            "education": [
                {
                    "institution": "string",
                    "degree": "string",
                    "graduation_year": "string"
                }
            ],
            "projects": [
                {
                    "name": "string",
                    "description": "string",
                    "technologies": ["string"]
                }
            ]
        }
        
        return self.provider.generate_json(prompt, schema)
    
    def analyze_job_compatibility(self, user_profile: Dict, job_data: Dict) -> Dict:
        """
        Analyze compatibility between user profile and job requirements
        
        Args:
            user_profile: User's skills, experience, education
            job_data: Job requirements and description
            
        Returns:
            Dictionary with compatibility analysis
        """
        prompt = f"""
        Analyze the compatibility between this user profile and job requirements:
        
        User Profile:
        {json.dumps(user_profile, indent=2)}
        
        Job Requirements:
        {json.dumps(job_data, indent=2)}
        
        Provide a detailed compatibility analysis including:
        - Overall compatibility score (0-100)
        - Matching skills
        - Missing skills
        - Recommendations for improvement
        - Likelihood of getting the job
        """
        
        schema = {
            "compatibility_score": "number",
            "matching_skills": ["string"],
            "missing_skills": ["string"],
            "recommendations": ["string"],
            "likelihood": "string",
            "analysis_summary": "string"
        }
        
        return self.provider.generate_json(prompt, schema)
    
    def generate_job_recommendations(self, user_profile: Dict, available_jobs: List[Dict]) -> List[Dict]:
        """
        Generate personalized job recommendations
        
        Args:
            user_profile: User's skills, experience, preferences
            available_jobs: List of available job positions
            
        Returns:
            List of recommended jobs with reasoning
        """
        prompt = f"""
        Based on this user profile, recommend the most suitable jobs from the available positions:
        
        User Profile:
        {json.dumps(user_profile, indent=2)}
        
        Available Jobs:
        {json.dumps(available_jobs, indent=2)}
        
        Rank and recommend jobs based on:
        - Skill match
        - Experience level
        - Career growth potential
        - User preferences (if provided)
        
        Provide top recommendations with explanations.
        """
        
        response = self.provider.generate_text(prompt)
        
        # Parse the response to extract job recommendations
        # This is a simplified implementation - you might want to use structured JSON here too
        return {"recommendations": response}
    
    def improve_resume_section(self, section_content: str, section_type: str, job_context: str = "") -> str:
        """
        Improve a specific resume section
        
        Args:
            section_content: Current content of the section
            section_type: Type of section (summary, experience, skills, etc.)
            job_context: Optional job context for tailoring
            
        Returns:
            Improved section content
        """
        prompt = f"""
        Improve this {section_type} section of a resume:
        
        Current content:
        {section_content}
        
        {f"Job context: {job_context}" if job_context else ""}
        
        Make it more:
        - Professional and compelling
        - ATS-friendly
        - Quantified (where possible)
        - Action-oriented
        
        Return only the improved content.
        """
        
        return self.provider.generate_text(prompt)
    
    def generate_cover_letter(self, user_data: Dict, job_data: Dict) -> str:
        """
        Generate a personalized cover letter
        
        Args:
            user_data: User's background and experience
            job_data: Job description and company information
            
        Returns:
            Generated cover letter text
        """
        prompt = f"""
        Write a professional cover letter based on:
        
        User Background:
        {json.dumps(user_data, indent=2)}
        
        Job Information:
        {json.dumps(job_data, indent=2)}
        
        The cover letter should be:
        - Professional and engaging
        - Tailored to the specific job
        - Highlight relevant experience and skills
        - Show enthusiasm for the role
        - Be approximately 3-4 paragraphs
        """
        
        return self.provider.generate_text(prompt)


# Decorator for caching LLM responses (optional)
def cache_llm_response(cache_key_prefix: str = "llm"):
    """
    Decorator to cache LLM responses (requires Django cache framework)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                from django.core.cache import cache
                import hashlib
                
                # Create cache key from function arguments
                key_data = f"{func.__name__}_{str(args)}_{str(kwargs)}"
                cache_key = f"{cache_key_prefix}_{hashlib.md5(key_data.encode()).hexdigest()}"
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Cache hit for {func.__name__}")
                    return cached_result
                
                # Generate new response
                result = func(*args, **kwargs)
                
                # Cache for 1 hour
                cache.set(cache_key, result, 3600)
                logger.info(f"Cached response for {func.__name__}")
                
                return result
            except ImportError:
                # If Django cache is not available, just run the function
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Mock Interview specific functions

@cache_llm_response()
def generate_interview_questions(job_position: str, difficulty_level: str = "intermediate", num_questions: int = 5) -> List[Dict]:
    """
    Generate interview questions for a specific job position and difficulty level
    """
    try:
        provider = get_llm_provider()
        
        prompt = f"""
        Generate {num_questions} interview questions for a {job_position} position at {difficulty_level} level.
        
        Requirements:
        - Questions should be relevant to the job position
        - Appropriate for {difficulty_level} level candidates
        - Mix of behavioral, technical, and situational questions
        - Each question should be clear and well-structured
        
        Return a JSON array where each question has:
        - "text": The question text
        - "type": "behavioral", "technical", or "situational"
        - "expected_duration": Expected response time in seconds
        - "key_points": Array of key points to look for in answers
        
        Job Position: {job_position}
        Difficulty: {difficulty_level}
        Number of Questions: {num_questions}
        """
        
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "type": {"type": "string", "enum": ["behavioral", "technical", "situational"]},
                    "expected_duration": {"type": "integer"},
                    "key_points": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["text", "type", "expected_duration", "key_points"]
            }
        }
        
        response = provider.generate_json(prompt, schema)
        
        if isinstance(response, list):
            return response
        elif isinstance(response, dict) and 'questions' in response:
            return response['questions']
        else:
            logger.error(f"Unexpected response format: {response}")
            return _get_fallback_questions(job_position, difficulty_level, num_questions)
            
    except Exception as e:
        logger.error(f"Error generating interview questions: {str(e)}")
        return _get_fallback_questions(job_position, difficulty_level, num_questions)

def _get_fallback_questions(job_position: str, difficulty_level: str, num_questions: int) -> List[Dict]:
    """Fallback questions when LLM fails"""
    fallback_questions = [
        {
            "text": f"Tell me about yourself and why you're interested in this {job_position} role.",
            "type": "behavioral",
            "expected_duration": 120,
            "key_points": ["relevant experience", "passion for role", "clear communication"]
        },
        {
            "text": f"What relevant experience do you have for this {job_position} position?",
            "type": "technical",
            "expected_duration": 180,
            "key_points": ["specific examples", "technical skills", "achievements"]
        },
        {
            "text": "Describe a challenging situation you faced at work and how you handled it.",
            "type": "behavioral",
            "expected_duration": 150,
            "key_points": ["problem-solving", "resilience", "learning from challenges"]
        },
        {
            "text": "Where do you see yourself in 5 years?",
            "type": "behavioral",
            "expected_duration": 90,
            "key_points": ["career goals", "growth mindset", "alignment with role"]
        },
        {
            "text": f"What do you think are the most important skills for a {job_position}?",
            "type": "technical",
            "expected_duration": 120,
            "key_points": ["industry knowledge", "relevant skills", "understanding of role"]
        }
    ]
    
    return fallback_questions[:num_questions]

@cache_llm_response()
def analyze_interview_response(question: str, response: str, job_position: str) -> Dict:
    """
    Analyze an interview response and provide detailed feedback
    """
    try:
        provider = get_llm_provider()
        
        prompt = f"""
        Analyze this interview response and provide detailed feedback.
        
        Job Position: {job_position}
        Question: {question}
        Candidate Response: {response}
        
        Analyze the response for:
        1. Content Quality (0-10): Relevance, depth, and accuracy of the response
        2. Communication Clarity (0-10): How clear and well-structured the response is
        3. Technical Accuracy (0-10): Technical correctness (if applicable)
        4. Confidence Level (0-10): How confident the candidate sounds
        5. Overall Score (0-10): Overall quality of the response
        
        Also provide:
        - Strengths: What the candidate did well
        - Areas for Improvement: Specific areas to work on
        - Suggestions: Actionable advice for improvement
        - Key Missing Elements: Important points not addressed
        
        Return a JSON object with the analysis.
        """
        
        schema = {
            "type": "object",
            "properties": {
                "content_quality": {"type": "number", "minimum": 0, "maximum": 10},
                "communication_clarity": {"type": "number", "minimum": 0, "maximum": 10},
                "technical_accuracy": {"type": "number", "minimum": 0, "maximum": 10},
                "confidence_level": {"type": "number", "minimum": 0, "maximum": 10},
                "overall_score": {"type": "number", "minimum": 0, "maximum": 10},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "areas_for_improvement": {"type": "array", "items": {"type": "string"}},
                "suggestions": {"type": "array", "items": {"type": "string"}},
                "key_missing_elements": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["content_quality", "communication_clarity", "technical_accuracy", 
                        "confidence_level", "overall_score", "strengths", "areas_for_improvement", 
                        "suggestions", "key_missing_elements"]
        }
        
        analysis = provider.generate_json(prompt, schema)
        
        # Validate scores are in range
        for score_key in ["content_quality", "communication_clarity", "technical_accuracy", 
                         "confidence_level", "overall_score"]:
            if score_key in analysis:
                analysis[score_key] = max(0, min(10, analysis[score_key]))
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing interview response: {str(e)}")
        return _get_fallback_analysis(response)

def _get_fallback_analysis(response: str) -> Dict:
    """Fallback analysis when LLM fails"""
    word_count = len(response.split())
    
    # Basic scoring based on response length and structure
    content_score = min(10, max(2, word_count / 10))
    clarity_score = 7.0 if word_count > 20 else 4.0
    technical_score = 6.0  # Neutral score
    confidence_score = 8.0 if "I" in response and len(response) > 50 else 5.0
    overall_score = (content_score + clarity_score + technical_score + confidence_score) / 4
    
    return {
        "content_quality": content_score,
        "communication_clarity": clarity_score,
        "technical_accuracy": technical_score,
        "confidence_level": confidence_score,
        "overall_score": overall_score,
        "strengths": ["Provided a response", "Engaged with the question"],
        "areas_for_improvement": ["Provide more detailed examples", "Structure responses more clearly"],
        "suggestions": ["Practice answering with specific examples", "Work on organizing thoughts before speaking"],
        "key_missing_elements": ["Specific examples", "Quantifiable achievements"]
    }

@cache_llm_response()
def generate_interview_feedback(session_data: Dict) -> Dict:
    """
    Generate comprehensive feedback for an entire interview session
    """
    try:
        provider = get_llm_provider()
        
        job_position = session_data.get('job_position', '')
        difficulty_level = session_data.get('difficulty_level', 'intermediate')
        questions = session_data.get('questions', [])
        responses = session_data.get('responses', [])
        
        # Prepare question-response pairs
        qa_pairs = []
        for i, (question, response) in enumerate(zip(questions, responses)):
            qa_pairs.append(f"Q{i+1}: {question}\nA{i+1}: {response}\n")
        
        qa_text = "\n".join(qa_pairs)
        
        prompt = f"""
        Provide comprehensive feedback for this complete interview session.
        
        Job Position: {job_position}
        Difficulty Level: {difficulty_level}
        
        Questions and Responses:
        {qa_text}
        
        Analyze the overall performance and provide:
        1. Overall Assessment: General performance summary
        2. Top Strengths: What the candidate excelled at
        3. Key Areas for Improvement: Main areas needing work
        4. Communication Skills: How well they communicated
        5. Technical Competency: Technical knowledge demonstrated
        6. Interview Readiness: How ready they are for real interviews
        7. Next Steps: Specific recommendations for improvement
        8. Overall Score: 0-10 rating
        
        Provide actionable, constructive feedback that helps the candidate improve.
        """
        
        schema = {
            "type": "object",
            "properties": {
                "overall_assessment": {"type": "string"},
                "top_strengths": {"type": "array", "items": {"type": "string"}},
                "key_areas_for_improvement": {"type": "array", "items": {"type": "string"}},
                "communication_skills": {"type": "string"},
                "technical_competency": {"type": "string"},
                "interview_readiness": {"type": "string"},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "overall_score": {"type": "number", "minimum": 0, "maximum": 10}
            }
        }
        
        feedback = provider.generate_json(prompt, schema)
        return feedback
        
    except Exception as e:
        logger.error(f"Error generating interview feedback: {str(e)}")
        return {
            "overall_assessment": "Unable to generate detailed feedback at this time.",
            "top_strengths": ["Completed the interview session"],
            "key_areas_for_improvement": ["Continue practicing interview skills"],
            "communication_skills": "Keep working on clear communication.",
            "technical_competency": "Continue building technical knowledge.",
            "interview_readiness": "More practice recommended.",
            "next_steps": ["Take more mock interviews", "Practice common interview questions"],
            "overall_score": 6.0
        }

def create_interview_template(title: str, job_position: str, difficulty_level: str, 
                            estimated_duration: int = 30) -> Dict:
    """
    Create a new interview template with pre-generated questions
    """
    try:
        questions = generate_interview_questions(
            job_position=job_position,
            difficulty_level=difficulty_level,
            num_questions=max(1, estimated_duration // 6)  # ~6 minutes per question
        )
        
        template_data = {
            "title": title,
            "job_position": job_position,
            "difficulty_level": difficulty_level,
            "estimated_duration": estimated_duration,
            "questions": questions,
            "is_active": True
        }
        
        return template_data
        
    except Exception as e:
        logger.error(f"Error creating interview template: {str(e)}")
        return {
            "title": title,
            "job_position": job_position,
            "difficulty_level": difficulty_level,
            "estimated_duration": estimated_duration,
            "questions": _get_fallback_questions(job_position, difficulty_level, 3),
            "is_active": True
        }


# Convenience function to get LLM instance
def get_llm_instance(provider: str = None) -> LLMUtils:
    """
    Get LLM instance with the specified provider
    
    Args:
        provider: Provider name ('openai' or 'gemini')
                 If None, will use settings from Django configuration
    """
    try:
        if provider is None:
            # Try to get from Django settings
            try:
                from django.conf import settings
                provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'openai')
            except:
                provider = 'openai'  # Default fallback
        
        # Check if API keys are available
        import os
        if provider == 'openai' and not os.environ.get('OPENAI_API_KEY'):
            logger.warning("OpenAI API key not available. Using a fallback LLM provider.")
        elif provider == 'gemini' and not os.environ.get('GEMINI_API_KEY'):
            logger.warning("Gemini API key not available. Using a fallback LLM provider.")
        
        return LLMUtils(provider=provider)
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider: {e}")
        
        # Create a simple fallback provider that doesn't make API calls
        class FallbackProvider:
            def generate_resume_content(self, user_data, job_description=""):
                return {
                    "summary": f"Recent graduate from {user_data.get('personal_info', {}).get('program', 'University')} with skills in problem-solving and communication.",
                    "skills": ["Communication", "Problem Solving", "Adaptability"] + user_data.get('skills', [])[:3],
                }
                
            def improve_resume_section(self, section_content, section_type, job_context=""):
                return section_content
                
            def generate_cover_letter(self, user_data, job_data):
                name = user_data.get('name', 'Candidate')
                program = user_data.get('program', 'University program')
                job_title = job_data.get('title', 'the position')
                company = job_data.get('company', 'your company')
                
                return f"""Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company}. As a graduate of {program}, I believe my skills and experiences make me a strong candidate for this role.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Sincerely,
{name}"""
                
        return FallbackProvider()
