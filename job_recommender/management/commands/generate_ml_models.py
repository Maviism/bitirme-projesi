"""
Django management command to generate ML models
"""
from django.core.management.base import BaseCommand
from job_recommender.ml_model.model_generator import MLModelGenerator
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate ML models for job recommendation system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='all',
            help='Specify which model to generate: "alumni", "job", or "all"'
        )

    def handle(self, *args, **options):
        model_type = options['model'].lower()
        generator = MLModelGenerator()
        
        if model_type == 'alumni':
            self.stdout.write('Generating alumni model...')
            path = generator.generate_alumni_model()
            if path:
                self.stdout.write(self.style.SUCCESS(f'Successfully generated alumni model at {path}'))
            else:
                self.stdout.write(self.style.ERROR('Failed to generate alumni model'))
                
        elif model_type == 'job':
            self.stdout.write('Generating job model...')
            path = generator.generate_job_model()
            if path:
                self.stdout.write(self.style.SUCCESS(f'Successfully generated job model at {path}'))
            else:
                self.stdout.write(self.style.ERROR('Failed to generate job model'))
                
        elif model_type == 'all':
            self.stdout.write('Generating all models...')
            result = generator.generate_all_models()
            if result.get('alumni_model_path') and result.get('job_model_path'):
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully generated all models:\n'
                    f'Alumni model: {result["alumni_model_path"]}\n'
                    f'Job model: {result["job_model_path"]}'
                ))
            else:
                self.stdout.write(self.style.ERROR('Failed to generate some or all models'))
                
        else:
            self.stdout.write(self.style.ERROR(f'Invalid model type: {model_type}. Use "alumni", "job", or "all".'))
