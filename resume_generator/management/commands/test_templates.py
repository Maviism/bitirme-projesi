from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test template rendering for resume templates'

    def handle(self, *args, **options):
        self.stdout.write("Testing resume templates...")
        
        templates_to_test = [
            'resume_generator/resume_template_ats.html',
            'resume_generator/resume_template_modern.html',
        ]
        
        # Simple test data
        context = {
            'student': {
                'fullname': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone': '123-456-7890',
                'linkedin_profile': 'https://linkedin.com/in/testuser',
                'faculty': 'Test Faculty',
                'program': 'Computer Science',
                'gpa': '3.5',
                'skills': ['Python', 'Django', 'React'],
                'summary': 'Test summary',
                'courses': [],
                'internships': [],
                'organizations': [],
            },
            'job_title': 'Software Engineer',
            'job_company': 'Tech Company',
            'job_description': 'Test job description',
            'is_preview': True
        }
        
        success_count = 0
        for template_name in templates_to_test:
            try:
                self.stdout.write(f"Testing template: {template_name}")
                html = render_to_string(template_name, context)
                if html:
                    self.stdout.write(self.style.SUCCESS(f"✓ Successfully rendered {template_name}"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"✗ Template {template_name} rendered empty content"))
            except TemplateDoesNotExist:
                self.stdout.write(self.style.ERROR(f"✗ Template {template_name} does not exist"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error rendering {template_name}: {e}"))
        
        if success_count == len(templates_to_test):
            self.stdout.write(self.style.SUCCESS("All templates tested successfully!"))
        else:
            self.stdout.write(self.style.ERROR(f"Only {success_count}/{len(templates_to_test)} templates rendered successfully."))
