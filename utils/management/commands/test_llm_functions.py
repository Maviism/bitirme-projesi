"""
Test LLM functions dengan Django management command
Usage: python manage.py test_llm_functions
"""

from django.core.management.base import BaseCommand
from utils.llm_utils import get_llm_instance
import json


class Command(BaseCommand):
    help = 'Test all LLM functions'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Testing LLM Functions...')
        
        # Test 1: Simple text generation
        self.stdout.write('\n1️⃣ Testing simple text generation...')
        try:
            llm = get_llm_instance('gemini')
            result = llm.provider.generate_text('Write one sentence about AI.', max_tokens=50)
            self.stdout.write(self.style.SUCCESS(f'✅ Success: {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {e}'))
        
        # Test 2: Resume generation
        self.stdout.write('\n2️⃣ Testing resume generation...')
        try:
            user_data = {
                'personal_info': {'name': 'Test User', 'program': 'Computer Science'},
                'skills': ['Python', 'Django']
            }
            
            llm = get_llm_instance('gemini')
            result = llm.generate_resume_content(user_data)
            self.stdout.write(self.style.SUCCESS(f'✅ Success! Generated resume sections: {list(result.keys())}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {e}'))
        
        # Test 3: Job compatibility
        self.stdout.write('\n3️⃣ Testing job compatibility...')
        try:
            user_profile = {'skills': ['Python'], 'experience_level': 'Junior'}
            job_data = {'title': 'Python Developer', 'required_skills': ['Python', 'Django']}
            
            llm = get_llm_instance('gemini')
            result = llm.analyze_job_compatibility(user_profile, job_data)
            score = result.get('compatibility_score', 'N/A')
            self.stdout.write(self.style.SUCCESS(f'✅ Success! Compatibility score: {score}%'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {e}'))
        
        self.stdout.write('\n🎉 LLM testing completed!')
