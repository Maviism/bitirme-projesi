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
    
    # Resume content generation moved to resume_generator/utils.py
    
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
    
    # Cover letter generation moved to resume_generator/utils.py
    
    # Cover letter improvement moved to resume_generator/utils.py
    

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
            # Fallback implementation for text generation
            def generate_text(self, prompt, **kwargs):
                return "The AI service is currently unavailable. Please try again later."
                
            # Fallback implementation for JSON generation
            def generate_json(self, prompt, schema=None, **kwargs):
                if schema:
                    return {key: "Not available" for key in schema.keys()}
                return {"error": "LLM service unavailable"}
                
            # Fallback implementations moved to specific app utilities
                
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
