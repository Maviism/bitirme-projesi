from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from job_recommender.models import Student, Course, Experience
from utils.llm_utils import get_llm_instance, cache_llm_response
import json
import os
import logging

# Standard logger configuration
logger = logging.getLogger(__name__)

# A placeholder function to simulate getting a student.
# In a real app, you\'d get this from the logged-in user.
def get_current_student(request: HttpRequest):
    # Placeholder: using the first student. Replace with actual user logic.
    # For example, if Student model has a OneToOneField to User:
    # if request.user.is_authenticated:
    #     try:
    #         return Student.objects.get(user=request.user)
    #     except Student.DoesNotExist:
    #         return None
    # return None
    student = Student.objects.first()
    if not student:
        # Create a dummy student if none exist, for development purposes
        # This is NOT for production.
        student = Student.objects.create(
            student_id="00000", fullname="Dummy", last_name="User",
            birth_date="2000-01-01", faculty="Science", program="General Science", gpa="3.0",
            skills=["Sample Skill 1", "Sample Skill 2"]
        )
        # You might want to create dummy related objects too if needed for the template
    return student

# Create your views here.
def generate_resume_view(request: HttpRequest):
    job_id = request.GET.get('job_id')
    job_title = request.GET.get('title')
    job_company = request.GET.get('company')
    job_description = request.GET.get('description')

    student = get_current_student(request)
    if not student:
        # Handle case where student is not found (e.g., redirect to login or show error)
        return HttpResponse("Student profile not found. Please log in.", status=404)

    # Fetch related data for the student
    courses = Course.objects.filter(student=student)
    internships = Experience.objects.filter(student=student, experience_type='internship')
    organizations = Experience.objects.filter(student=student, experience_type='organization')

    # Prepare student data for the form
    # Add fields that might not be directly on the Student model but are useful for a resume
    student_form_data = {
        'id': student.id,
        'fullname': student.fullname,
        'last_name': student.last_name,
        'email': getattr(student, 'email', 'your_email@example.com'), # Assuming an email field
        'phone': getattr(student, 'phone', '555-1234'), # Assuming a phone field
        'linkedin_profile': getattr(student, 'linkedin_profile', ''), # Assuming a linkedin field
        'faculty': student.faculty,
        'program': student.program,
        'gpa': str(student.gpa),
        'skills': ', '.join(student.skills) if isinstance(student.skills, list) else student.skills,
        'summary': getattr(student, 'summary', 'A brief professional summary.'), # Assuming a summary field
        'courses': courses,
        'internships': internships,
        'organizations': organizations
    }

    context = {
        'job_id': job_id,
        'job_title': job_title,
        'job_company': job_company,
        'job_description': job_description,
        'student': student_form_data,
    }
    # Assuming you have a template named 'generate_resume_form.html' 
    # or similar in your resume_generator templates directory.
    return render(request, 'resume_generator/generate_resume_form.html', context)

def download_resume_view(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=400)

    try:
        # 1. Get Job Data from POST
        job_title = request.POST.get('job_title')
        job_company = request.POST.get('job_company')
        job_description = request.POST.get('job_description')

        # 2. Get Student ID from POST and fetch the original student object
        student_id = request.POST.get('student_id')
        if not student_id:
            return HttpResponse("Student ID missing.", status=400)
        
        student_obj = get_object_or_404(Student, pk=student_id)

        # 3. Construct student_data for the PDF using POST data for editable fields
        #    and DB data for non-editable structured data (courses, etc.)
        skills_str = request.POST.get('student_skills', '')
        
        student_data_for_pdf = {
            'fullname': request.POST.get('student_fullname', student_obj.fullname),
            'last_name': request.POST.get('student_last_name', student_obj.last_name),
            'email': request.POST.get('student_email', getattr(student_obj, 'email', '')),
            'phone': request.POST.get('student_phone', getattr(student_obj, 'phone', '')),
            'linkedin_profile': request.POST.get('student_linkedin', getattr(student_obj, 'linkedin_profile', '')),
            'faculty': student_obj.faculty, # Assuming faculty is not editable in this form
            'program': student_obj.program, # Assuming program is not editable
            'gpa': str(student_obj.gpa), # Assuming GPA is not editable
            'skills': [s.strip() for s in skills_str.split(',') if s.strip()],
            'summary': request.POST.get('student_summary', getattr(student_obj, 'summary', '')),
            'courses': Course.objects.filter(student=student_obj),
            'internships': Experience.objects.filter(student=student_obj, experience_type='internship'),
            'organizations': Experience.objects.filter(student=student_obj, experience_type='organization'),
        }

        # Get selected template style
        template_style = request.POST.get('resume_template_style', 'ats') # Default to 'ats'
        if template_style == 'modern':
            template_name = 'resume_generator/resume_template_modern.html'
        else: # Default to ATS
            template_name = 'resume_generator/resume_template_ats.html'

        context_for_template = {
            'job_title': job_title,
            'job_company': job_company,
            'job_description': job_description,
            'student': student_data_for_pdf,
        }

        html_string = render_to_string(template_name, context_for_template)
        
        try:
            pdf_file = HTML(string=html_string).write_pdf()
        except Exception as pdf_error:
            logger.error(f"PDF generation failed: {pdf_error}")
            raise

        # Create response with proper headers
        filename = f"resume_{student_data_for_pdf['last_name']}_{job_title}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating resume PDF: {e}")
        error_html = f"""
        <html>
        <head>
            <title>Error Generating PDF</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                .error-container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #f44336; border-radius: 5px; }}
                .error-title {{ color: #f44336; }}
                .error-details {{ background-color: #f9f9f9; padding: 10px; border-left: 3px solid #f44336; }}
                .back-button {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #4CAF50; color: white; 
                               text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h2 class="error-title">Error Generating Resume PDF</h2>
                <p>We encountered an error while generating your resume PDF. Please try again.</p>
                <a href="javascript:history.back()" class="back-button">Go Back</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(error_html)

def preview_resume_view(request: HttpRequest):
    # Check request method
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=400)
    
    try:
        # Wrap everything in a transaction for performance
        from django.db import transaction
        with transaction.atomic():
            
            # Essentially the same data gathering logic as download_resume_view
            job_title = request.POST.get('job_title')
            job_company = request.POST.get('job_company')
            job_description = request.POST.get('job_description')
            student_id = request.POST.get('student_id')

            if not student_id:
                return HttpResponse("Student ID missing.", status=400)
            
            student_obj = get_object_or_404(Student, pk=student_id)
            logger.info(f"Retrieved student: {student_obj.fullname} {student_obj.last_name}")

            skills_str = request.POST.get('student_skills', '')
            student_data_for_preview = {
                'fullname': request.POST.get('student_fullname', student_obj.fullname),
                'last_name': request.POST.get('student_last_name', student_obj.last_name),
                'email': request.POST.get('student_email', getattr(student_obj, 'email', '')),
                'phone': request.POST.get('student_phone', getattr(student_obj, 'phone', '')),
                'linkedin_profile': request.POST.get('student_linkedin', getattr(student_obj, 'linkedin_profile', '')),
                'faculty': student_obj.faculty,
                'program': student_obj.program,
                'gpa': str(student_obj.gpa),
                'skills': [s.strip() for s in skills_str.split(',') if s.strip()],
                'summary': request.POST.get('student_summary', getattr(student_obj, 'summary', '')),
            }
            
            # Use select_related to optimize queries
            courses = Course.objects.filter(student=student_obj).select_related()
            internships = Experience.objects.filter(student=student_obj, experience_type='internship').select_related()
            organizations = Experience.objects.filter(student=student_obj, experience_type='organization').select_related()
            
            # Add to student data after query optimization
            student_data_for_preview['courses'] = courses
            student_data_for_preview['internships'] = internships
            student_data_for_preview['organizations'] = organizations

            template_style = request.POST.get('resume_template_style', 'ats')
            if template_style == 'modern':
                template_name = 'resume_generator/resume_template_modern.html'
            else:
                template_name = 'resume_generator/resume_template_ats.html'

            context_for_template = {
                'job_title': job_title,
                'job_company': job_company,
                'job_description': job_description,
                'student': student_data_for_preview,
                'is_preview': True # Flag to indicate this is a preview
            }

            # Render the HTML template to a string
            try:
                html_string = render_to_string(template_name, context_for_template)
            except Exception as template_error:
                logger.error(f"Template rendering failed: {template_error}")
                # Re-raise to be caught by the outer exception handler
                raise
            
            # Add base HTML structure to make preview standalone
            complete_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Resume Preview - {student_data_for_preview['fullname']} {student_data_for_preview['last_name']}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                    .preview-controls {{ position: fixed; bottom: 20px; right: 20px; background: #fff; padding: 10px; 
                                        border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); z-index: 1000; }}
                </style>
            </head>
            <body>
                <div class="preview-controls">
                    <button onclick="window.print()" class="btn btn-sm btn-primary">Print</button>
                    <button onclick="window.close()" class="btn btn-sm btn-secondary">Close</button>
                </div>
                {html_string}
                <script>
                    // Send message to parent window that preview is loaded
                    window.onload = function() {{
                        if (window.opener) {{
                            window.opener.postMessage('previewLoaded', '*');
                        }}
                    }};
                </script>
            </body>
            </html>
            """
            
            logger.info(f"Resume preview generation complete")
            # Return as HTML response for preview
            return HttpResponse(complete_html)
    
    except Exception as e:
        logger.error(f"Error generating resume preview: {e}")
        
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Resume Preview Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="alert alert-danger">
                            <h4 class="alert-heading">Error Generating Resume Preview</h4>
                            <p>We encountered an error while generating your resume preview:</p>
                            <pre class="bg-light p-3">{e}</pre>
                            <hr>
                            <p>Please try again or contact support if the issue persists.</p>
                            <button class="btn btn-primary" onclick="window.close()">Close Preview</button>
                            <button class="btn btn-secondary" onclick="window.location.reload()">Try Again</button>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                // Send message to parent window that preview failed
                window.onload = function() {{{{
                    if (window.opener) {{{{
                        window.opener.postMessage('previewFailed', '*');
                    }}}}
                }}}};
            </script>
        </body>
        </html>
        """
        return HttpResponse(error_html)


@cache_llm_response("resume_content")
def generate_ai_resume_content(request: HttpRequest):
    """Generate AI-enhanced resume content"""
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=405)
    
    try:
        # Get student data
        student_id = request.POST.get('student_id')
        if not student_id:
            return JsonResponse({'error': 'Student ID missing'}, status=400)
        
        student_obj = get_object_or_404(Student, pk=student_id)
        
        # Check for API keys
        try:
            import os
            openai_key = os.environ.get('OPENAI_API_KEY')
            gemini_key = os.environ.get('GEMINI_API_KEY')
            if not openai_key and not gemini_key:
                logger.warning("No LLM API keys available - using fallback content")
                # Return fallback content when no API keys are available
                return JsonResponse({
                    'success': True,
                    'content': {
                        'summary': f"Recent graduate from {student_obj.program} at {student_obj.faculty} with a GPA of {student_obj.gpa}. Seeking opportunities to apply academic knowledge in a professional setting.",
                        'skills': ["Communication", "Time Management", "Problem Solving", "Critical Thinking"] + (student_obj.skills if isinstance(student_obj.skills, list) else [])
                    }
                })
        except Exception as e:
            logger.warning(f"Error checking LLM API keys: {e}")
        
        # Prepare user data for LLM
        user_data = {
            'personal_info': {
                'name': f"{student_obj.fullname} {student_obj.last_name}",
                'faculty': student_obj.faculty,
                'program': student_obj.program,
                'gpa': str(student_obj.gpa)
            },
            'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills],
            'courses': [
                {
                    'name': course.name,
                    'grade': getattr(course, 'grade', 'N/A')
                } for course in Course.objects.filter(student=student_obj)
            ],
            'internships': [
                {
                    'company': internship.institution_name,
                    'position': getattr(internship, 'position', 'Intern'),
                    'duration': f"{internship.start_date} to {internship.end_date or 'Present'}",
                    'description': getattr(internship, 'description', '')
                } for internship in Experience.objects.filter(student=student_obj, experience_type='internship')
            ],
            'organizations': [
                {
                    'name': org.institution_name,
                    'role': getattr(org, 'position', 'Member')
                } for org in Experience.objects.filter(student=student_obj, experience_type='organization')
            ]
        }
        
        # Get job description if provided
        job_description = request.POST.get('job_description', '')
        
        # Get LLM instance and generate content
        llm = get_llm_instance()
        ai_content = llm.generate_resume_content(user_data, job_description)
        
        return JsonResponse({
            'success': True,
            'content': ai_content
        })
        
    except Exception as e:
        logger.error(f"Error generating AI resume content: {e}")
        return JsonResponse({
            'error': 'Failed to generate AI content',
            'details': str(e)
        }, status=500)


def improve_resume_section(request: HttpRequest):
    """Improve a specific resume section using AI"""
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=405)
    
    try:
        section_content = request.POST.get('section_content', '')
        section_type = request.POST.get('section_type', '')
        job_context = request.POST.get('job_context', '')
        
        if not section_content or not section_type:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get LLM instance and improve section
        llm = get_llm_instance()
        improved_content = llm.improve_resume_section(section_content, section_type, job_context)
        
        return JsonResponse({
            'success': True,
            'improved_content': improved_content
        })
        
    except Exception as e:
        logger.error(f"Error improving resume section: {e}")
        return JsonResponse({
            'error': 'Failed to improve section',
            'details': str(e)
        }, status=500)


def generate_cover_letter(request: HttpRequest):
    """Generate a cover letter using AI"""
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=405)
    
    try:
        # Get student data
        student_id = request.POST.get('student_id')
        if not student_id:
            return JsonResponse({'error': 'Student ID missing'}, status=400)
        
        student_obj = get_object_or_404(Student, pk=student_id)
        
        # Check for API keys
        try:
            import os
            openai_key = os.environ.get('OPENAI_API_KEY')
            gemini_key = os.environ.get('GEMINI_API_KEY')
            if not openai_key and not gemini_key:
                logger.warning("No LLM API keys available - using fallback cover letter")
                # Return fallback content when no API keys are available
                job_title = request.POST.get('job_title', 'the position')
                job_company = request.POST.get('job_company', 'your company')
                
                fallback_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {job_company}. As a recent graduate from {student_obj.program} at {student_obj.faculty} with a GPA of {student_obj.gpa}, I am eager to contribute my skills and knowledge to your team.

My academic background has equipped me with the necessary skills for this role, including {', '.join(student_obj.skills[:3] if isinstance(student_obj.skills, list) else ['problem-solving', 'communication', 'teamwork'])}.

I am particularly impressed by {job_company}'s reputation in the industry and would welcome the opportunity to discuss how my qualifications align with your needs. Thank you for considering my application.

Sincerely,
{student_obj.fullname} {student_obj.last_name}"""

                return JsonResponse({
                    'success': True,
                    'cover_letter': fallback_letter
                })
        except Exception as e:
            logger.warning(f"Error checking LLM API keys: {e}")
        
        # Prepare user data
        user_data = {
            'name': f"{student_obj.fullname} {student_obj.last_name}",
            'faculty': student_obj.faculty,
            'program': student_obj.program,
            'gpa': str(student_obj.gpa),
            'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills],
            'experience': [
                {
                    'company': exp.institution_name,
                    'position': getattr(exp, 'position', 'Intern')
                } for exp in Experience.objects.filter(student=student_obj, experience_type='internship')
            ]
        }
        
        # Get job data
        job_data = {
            'title': request.POST.get('job_title', ''),
            'company': request.POST.get('job_company', ''),
            'description': request.POST.get('job_description', '')
        }
        
        # Generate cover letter
        llm = get_llm_instance()
        cover_letter = llm.generate_cover_letter(user_data, job_data)
        
        return JsonResponse({
            'success': True,
            'cover_letter': cover_letter
        })
        
    except Exception as e:
        logger.error(f"Error generating cover letter: {e}")
        return JsonResponse({
            'error': 'Failed to generate cover letter',
            'details': str(e)
        }, status=500)

# Diagnostic views and health check removed as they are no longer needed
