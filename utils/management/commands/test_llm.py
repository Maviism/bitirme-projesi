"""
Simple LLM testing command
Usage: python manage.py test_llm [--provider openai|gemini]
"""

from django.core.management.base import BaseCommand
from utils.llm_utils import get_llm_instance


class Command(BaseCommand):
    help = 'Test LLM connection and basic functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            default=None,  # Will use Django settings default
            help='LLM provider to test (openai or gemini). If not specified, uses DEFAULT_LLM_PROVIDER from settings.'
        )

    def handle(self, *args, **options):
        provider = options['provider']
        
        # If no provider specified, get from Django settings
        if provider is None:
            try:
                from django.conf import settings
                provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'openai')
            except:
                provider = 'openai'
        
        self.stdout.write(f'Testing {provider.upper()} LLM connection...')
        
        try:
            # Test basic connection
            llm = get_llm_instance(provider)
            
            # Simple test prompt
            test_prompt = "Write a one-sentence professional summary for a computer science student."
            
            self.stdout.write('Sending test prompt...')
            response = llm.provider.generate_text(test_prompt, max_tokens=100)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {provider.upper()} LLM working!')
            )
            self.stdout.write(f'Test response: {response[:100]}...')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ {provider.upper()} LLM failed: {str(e)}')
            )
            self.stdout.write('Check your API key in .env file')
