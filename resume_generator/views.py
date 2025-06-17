from django.shortcuts import render, get_object_or_404, redirect
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

# Helper method for calculating duration in months
def _calculate_duration_months(start_date, end_date):
    """Calculate duration between two dates in months"""
    if not start_date:
        return 0
    
    from datetime import date
    end = end_date or date.today()
    
    months = (end.year - start_date.year) * 12 + (end.month - start_date.month)
    return max(months, 1)  # Minimum 1 month

# Function to get the student related to the current user
def get_current_student(request: HttpRequest):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        try:
            # Get the username
            username = request.user.username
            logger.info(f"Finding student for authenticated user: {username}")
            
            # Check if a specific student ID is requested from the session or URL parameter
            requested_student_id = request.session.get('active_student_id') or request.GET.get('student_profile_id')
            if requested_student_id:
                try:
                    # Try to get the specific student
                    student = Student.objects.get(id=requested_student_id, user=request.user)
                    logger.info(f"Using specifically requested student: {student.fullname} {student.last_name}")
                    return student
                except Student.DoesNotExist:
                    logger.warning(f"Requested student ID {requested_student_id} not found or doesn't belong to user")
            
            # First try to find student profiles directly linked to the user
            student_profiles = Student.objects.filter(user=request.user)
            if student_profiles.exists():
                # Get the most recently updated student profile
                student = student_profiles.order_by('-updated_at').first()
                logger.info(f"Found student by user relation: {student.fullname} {student.last_name}")
                return student
            
            # Try to find student by student_id matching username
            try:
                student = Student.objects.get(student_id=username)
                logger.info(f"Found student by matching student_id: {student.fullname} {student.last_name}")
                
                # Link this student to the user if not already linked
                if not student.user:
                    student.user = request.user
                    student.save(update_fields=['user'])
                    logger.info(f"Linked student {student.student_id} to user {username}")
                
                return student
            except Student.DoesNotExist:
                logger.info(f"No student found with student_id={username}")
            
            # Try by email if available
            if hasattr(request.user, 'email') and request.user.email:
                try:
                    # Look for students with email field
                    student = Student.objects.filter(email=request.user.email).first()
                    if student:
                        logger.info(f"Found student by email: {student.fullname} {student.last_name}")
                        
                        # Link this student to the user if not already linked
                        if not student.user:
                            student.user = request.user
                            student.save(update_fields=['user'])
                            logger.info(f"Linked student with email {request.user.email} to user {username}")
                        
                        return student
                except Exception as e:
                    logger.info(f"Could not find student by email: {e}")
            
            # If we reach here, no student was found for this user
            logger.warning(f"No student record found for user: {username}")
            
        except Exception as e:
            logger.error(f"Error fetching student for user: {e}")
    
    # If not authenticated or no match found, log appropriately
    if not request.user.is_authenticated:
        logger.warning("User is not authenticated - using default student")
    else:
        logger.warning(f"No student record found for user '{request.user.username}' - using default student")
    
    # Fall back to default student (for development only)
    student = Student.objects.first()
    if not student:
        # Create a dummy student if none exist, for development purposes only
        from datetime import date
        student = Student.objects.create(
            student_id="00000", fullname="Dummy", last_name="User",
            birth_date=date(2000, 1, 1), faculty="Science", program="General Science", gpa="3.0",
            skills=["Sample Skill 1", "Sample Skill 2"]
        )
        logger.warning(f"Created dummy student: {student.fullname} {student.last_name}")
    else:
        logger.info(f"Using existing student as fallback: {student.fullname} {student.last_name}")
        
    return student

# Create your views here.
def select_profile_view(request: HttpRequest):
    """View for selecting among multiple student profiles"""
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        if profile_id:
            # Store the selected profile ID in session
            request.session['active_student_id'] = profile_id
            
            # Redirect to the resume generator
            return redirect('resume_generator:generate_resume')
    
    # Get all profiles linked to this user
    student_profiles = Student.objects.filter(user=request.user).order_by('-updated_at')
    
    # Get the currently active profile ID from session
    active_profile_id = request.session.get('active_student_id')
    
    # If there's only one profile, set it as active and redirect
    if student_profiles.count() == 1:
        request.session['active_student_id'] = str(student_profiles.first().id)
        return redirect('resume_generator:generate_resume')
        
    context = {
        'profiles': student_profiles,
        'active_profile_id': active_profile_id
    }
    
    return render(request, 'resume_generator/select_profile.html', context)

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
    
    # Get job recommendations for this student if available
    job_recommendations = None
    if job_id:
        try:
            from job_recommender.models import JobRecommendation, Job
            
            # Debug information
            logger.info(f"Fetching recommendations for student ID: {student.id}, job ID: {job_id}")
            
            # Get all recommendations for this student
            recommendations = JobRecommendation.objects.filter(
                student=student
            ).select_related('job').order_by('-match_score')[:5]  # Get top 5
            
            logger.info(f"Found {recommendations.count()} recommendations for student")
            
            # Find the current job in recommendations if it exists
            current_job_rec = None
            for rec in recommendations:
                logger.info(f"Checking recommendation job ID: {rec.job.id} ({type(rec.job.id)}) vs requested job ID: {job_id} ({type(job_id)})")
                if str(rec.job.id) == str(job_id):
                    current_job_rec = rec
                    logger.info(f"Match found! Job: {rec.job.title} with score: {rec.match_score}")
                    break
            
            # If we didn't find the current job in recommendations, try to fetch it directly
            if not current_job_rec:
                logger.info(f"Current job not found in recommendations, trying direct fetch")
                try:
                    # Try to find a recommendation for this specific job
                    direct_rec = JobRecommendation.objects.filter(
                        student=student,
                        job__id=job_id
                    ).first()
                    
                    if direct_rec:
                        logger.info(f"Direct job recommendation found with score: {direct_rec.match_score}")
                        current_job_rec = direct_rec
                    else:
                        # If there's no recommendation, create the job object for reference
                        job_obj = Job.objects.get(id=job_id)
                        logger.info(f"Found job: {job_obj.title} at {job_obj.company}")
                except Exception as job_error:
                    logger.error(f"Error looking up job directly: {job_error}")
            
            job_recommendations = {
                'recommendations': recommendations,
                'current_job_rec': current_job_rec
            }
        except Exception as e:
            logger.error(f"Error fetching job recommendations: {e}")
            # Don't let this block the resume generation

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
        'summary': getattr(student, 'summary', ''), # Empty to trigger auto-generation
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
        'job_recommendations': job_recommendations,  # Add recommendations to context
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

        # Get job recommendations to enhance resume content
        job_recommendations = []
        try:
            from job_recommender.models import JobRecommendation, Job
            
            # Get job ID if it was passed to the form
            job_id = request.POST.get('job_id')
            if job_id:
                logger.info(f"Job ID from form: {job_id}")
                
                # First try to get recommendation specifically for this job
                job_rec = JobRecommendation.objects.filter(
                    student=student_obj,
                    job__id=job_id
                ).select_related('job').first()
                
                if job_rec:
                    logger.info(f"Found specific job recommendation for job ID {job_id}")
                    # Add this first as it's the most relevant
                    job_recommendations.append({
                        'title': job_rec.job.title,
                        'company': job_rec.job.company,
                        'match_score': float(job_rec.match_score),
                        'is_current_job': True,
                        'required_skills': job_rec.job.required_skills if isinstance(job_rec.job.required_skills, list) else [],
                        'description': job_rec.job.description[:200]
                    })
            
            # Get general recommendations
            recommendations = JobRecommendation.objects.filter(
                student=student_obj
            ).select_related('job').order_by('-match_score')[:3]  # Top 3 recommendations
            
            for rec in recommendations:
                # Skip if this is the current job we already added
                if job_id and str(rec.job.id) == str(job_id) and len(job_recommendations) > 0:
                    continue
                    
                job_recommendations.append({
                    'title': rec.job.title,
                    'company': rec.job.company,
                    'match_score': float(rec.match_score),
                    'is_current_job': job_id and str(rec.job.id) == str(job_id),
                    'required_skills': rec.job.required_skills if isinstance(rec.job.required_skills, list) else [],
                    'description': rec.job.description[:200]  # Truncated description
                })
                
            logger.info(f"Processed {len(job_recommendations)} job recommendations for AI content generation")
        except Exception as e:
            logger.warning(f"Error fetching job recommendations: {e}")
        
        # Prepare enhanced user data for LLM with comprehensive information
        user_data = {
            'personal_info': {
                'name': f"{student_obj.fullname} {student_obj.last_name}",
                'email': getattr(student_obj, 'email', ''),
                'phone': getattr(student_obj, 'phone', ''),
                'linkedin': getattr(student_obj, 'linkedin_profile', ''),
                'student_id': student_obj.student_id,
                'birth_date': student_obj.birth_date.strftime('%Y-%m-%d') if student_obj.birth_date else '',
                'is_alumni': student_obj.is_alumni,
                'faculty': student_obj.faculty,
                'program': student_obj.program,
                'gpa': str(student_obj.gpa)
            },
            'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else [],
            'courses': [
                {
                    'code': course.code,
                    'name': course.name,
                    'grade': getattr(course, 'grade', 'N/A'),
                    'success_level': 'yüksek' if course.grade in ['AA', 'BA'] else 'orta' if course.grade in ['BB', 'CB'] else 'düşük' if course.grade not in ['--', 'N/A'] else 'belirsiz'
                } for course in Course.objects.filter(student=student_obj).order_by('-grade')
            ],
            'experience': {
                'internships': [
                    {
                        'company': internship.institution_name,
                        'position': getattr(internship, 'position', 'Stajyer'),
                        'start_date': internship.start_date.strftime('%Y-%m-%d') if internship.start_date else '',
                        'end_date': internship.end_date.strftime('%Y-%m-%d') if internship.end_date else 'Devam ediyor',
                        'duration': f"{internship.start_date} - {internship.end_date or 'Devam ediyor'}",
                        'description': getattr(internship, 'description', ''),
                        'is_current': not internship.end_date
                    } for internship in Experience.objects.filter(student=student_obj, experience_type='internship').order_by('-start_date')
                ],
                'organizations': [
                    {
                        'name': org.institution_name,
                        'role': getattr(org, 'position', 'Üye'),
                        'start_date': org.start_date.strftime('%Y-%m-%d') if org.start_date else '',
                        'end_date': org.end_date.strftime('%Y-%m-%d') if org.end_date else 'Devam ediyor',
                        'duration': f"{org.start_date} - {org.end_date or 'Devam ediyor'}",
                        'description': getattr(org, 'description', ''),
                        'is_current': not org.end_date
                    } for org in Experience.objects.filter(student=student_obj, experience_type='organization').order_by('-start_date')
                ]
            },
            'academic_performance': {
                'total_courses': Course.objects.filter(student=student_obj).count(),
                'high_grades_count': Course.objects.filter(student=student_obj, grade__in=['AA', 'BA']).count(),
                'gpa_level': 'yüksek' if float(student_obj.gpa) >= 3.0 else 'orta' if float(student_obj.gpa) >= 2.5 else 'düşük',
                'graduation_status': 'mezun' if student_obj.is_alumni else 'öğrenci'
            },
            'career_context': {
                'has_internship_experience': Experience.objects.filter(student=student_obj, experience_type='internship').exists(),
                'has_organization_experience': Experience.objects.filter(student=student_obj, experience_type='organization').exists(),
                'total_experiences': Experience.objects.filter(student=student_obj).count(),
                'has_leadership_experience': any(['başkan' in exp.position.lower() or 'lider' in exp.position.lower() 
                                                 for exp in Experience.objects.filter(student=student_obj) 
                                                 if hasattr(exp, 'position') and exp.position])
            },
            'job_recommendations': job_recommendations  # Add job recommendations
        }
        
        # Get job description if provided
        job_description = request.POST.get('job_description', '')
        
        # Get LLM instance and generate content
        llm = get_llm_instance()
        content = llm.generate_resume_content(user_data, job_description)
        
        return JsonResponse({
            'success': True,
            'content': content
        })
        
    except Exception as e:
        logger.error(f"Error generating resume content: {e}")
        return JsonResponse({
            'error': str(e)
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
                job_title = request.POST.get('job_title', 'pozisyon')
                job_company = request.POST.get('job_company', 'şirketiniz')
                
                # Create skills list in Turkish
                skills_list = student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else ['problem çözme', 'iletişim', 'ekip çalışması']
                skills_text = ', '.join(skills_list[:3]) if len(skills_list) >= 3 else ', '.join(skills_list + ['analitik düşünce', 'hızlı öğrenme'][:3-len(skills_list)])
                
                fallback_letter = f"""Sayın İnsan Kaynakları Müdürü,

{job_company} bünyesindeki {job_title} pozisyonuna olan ilgimi ve başvurumu bildirmek isterim. {student_obj.faculty} {student_obj.program} bölümünden {student_obj.gpa} GNO ile {"mezun" if student_obj.is_alumni else "son sınıf öğrencisi"} olarak, edindiğim bilgi ve becerileri takımınıza katkı sağlamak için sabırsızlanıyorum.

Akademik geçmişim ve sahip olduğum {skills_text} gibi yetenekler sayesinde bu pozisyonda başarılı olabileceğime inanıyorum. {"Mezuniyet" if student_obj.is_alumni else "Öğrencilik"} sürecimde edindiğim teorik bilgileri pratik deneyimlerle harmanlayarak, hem bireysel hem de ekip halinde çalışabilen bir profil geliştirdim.

{job_company}'nin sektördeki saygın konumu ve inovatif yaklaşımı beni çok etkiledi. Niteliklerimin şirketinizin ihtiyaçlarıyla ne kadar uyumlu olduğunu görüşme sürecinde detaylı olarak paylaşma fırsatı bulabilirsem çok memnun olurum.

Zamanınız ve ilginiz için teşekkür ederim.

Saygılarımla,
{student_obj.fullname} {student_obj.last_name}"""

                return JsonResponse({
                    'success': True,
                    'cover_letter': fallback_letter
                })
        except Exception as e:
            logger.warning(f"Error checking LLM API keys: {e}")
        
        # Prepare comprehensive user data for cover letter generation
        user_data = {
            'personal_info': {
                'name': f"{student_obj.fullname} {student_obj.last_name}",
                'email': getattr(student_obj, 'email', ''),
                'phone': getattr(student_obj, 'phone', ''),
                'linkedin': getattr(student_obj, 'linkedin_profile', ''),
                'faculty': student_obj.faculty,
                'program': student_obj.program,
                'gpa': str(student_obj.gpa),
                'graduation_status': 'mezun' if student_obj.is_alumni else 'öğrenci'
            },
            'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else [],
            'education': {
                'degree': f"{student_obj.program} - {student_obj.faculty}",
                'gpa': str(student_obj.gpa),
                'academic_achievements': [
                    f"GNO: {student_obj.gpa}",
                    f"Toplam {Course.objects.filter(student=student_obj).count()} ders tamamlandı",
                    f"{Course.objects.filter(student=student_obj, grade__in=['AA', 'BA']).count()} yüksek not"
                ]
            },
            'experience': {
                'internships': [
                    {
                        'company': exp.institution_name,
                        'position': getattr(exp, 'position', 'Stajyer'),
                        'duration': f"{exp.start_date.strftime('%m/%Y') if exp.start_date else ''} - {exp.end_date.strftime('%m/%Y') if exp.end_date else 'Devam ediyor'}",
                        'description': getattr(exp, 'description', ''),
                        'key_achievements': [
                            'Pratik deneyim kazandım',
                            'Ekip çalışması becerilerimi geliştirdim',
                            'Sektörel bilgi edindim'
                        ]
                    } for exp in Experience.objects.filter(student=student_obj, experience_type='internship').order_by('-start_date')
                ],
                'organizations': [
                    {
                        'name': org.institution_name,
                        'role': getattr(org, 'position', 'Üye'),
                        'duration': f"{org.start_date.strftime('%m/%Y') if org.start_date else ''} - {org.end_date.strftime('%m/%Y') if org.end_date else 'Devam ediyor'}",
                        'description': getattr(org, 'description', ''),
                        'leadership_skills': 'başkan' in getattr(org, 'position', '').lower() or 'lider' in getattr(org, 'position', '').lower()
                    } for org in Experience.objects.filter(student=student_obj, experience_type='organization').order_by('-start_date')
                ]
            },
            'strengths': {
                'academic_performance': 'yüksek' if float(student_obj.gpa) >= 3.0 else 'orta',
                'practical_experience': Experience.objects.filter(student=student_obj, experience_type='internship').exists(),
                'leadership_experience': any(['başkan' in exp.position.lower() or 'lider' in exp.position.lower() 
                                             for exp in Experience.objects.filter(student=student_obj) 
                                             if hasattr(exp, 'position') and exp.position]),
                'diverse_background': Experience.objects.filter(student=student_obj).count() > 2,
                'technical_skills': len(student_obj.skills) if isinstance(student_obj.skills, list) else 1 if student_obj.skills else 0
            },
            'career_motivation': {
                'field_alignment': f"{student_obj.program} alanında kariyer hedefi",
                'growth_mindset': 'Sürekli öğrenme ve gelişim odaklı',
                'value_proposition': 'Akademik bilgi ve pratik deneyimi harmanlayan yaklaşım'
            }
        }
        
        # Get comprehensive job data
        job_data = {
            'position': {
                'title': request.POST.get('job_title', ''),
                'company': request.POST.get('job_company', ''),
                'description': request.POST.get('job_description', '')
            },
            'company_context': {
                'name': request.POST.get('job_company', ''),
                'sector': 'teknoloji',  # Could be enhanced with company data
                'size': 'orta ölçekli',  # Could be enhanced with company data
                'values': ['inovasyon', 'ekip çalışması', 'sürekli gelişim']  # Could be enhanced
            },
            'application_context': {
                'application_date': '2025-06-17',
                'source': 'kariyer portalı',
                'motivation': 'kariyer gelişimi ve deneyim kazanımı'
            }
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

def start_interview_from_resume(request: HttpRequest):
    """
    Handle the flow from resume generation to interview preparation
    This function prepares the resume data and redirects to the interview system
    """
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=400)
    
    try:
        # Get job and student data from POST
        job_title = request.POST.get('job_title')
        job_company = request.POST.get('job_company')
        job_description = request.POST.get('job_description')
        job_id = request.POST.get('job_id')
        student_id = request.POST.get('student_id')

        if not student_id:
            return HttpResponse("Student ID missing.", status=400)
        
        # Get the student object
        student_obj = get_object_or_404(Student, pk=student_id)
        
        # Format the resume content as text for the interview system
        skills_str = request.POST.get('student_skills', '')
        
        # Create a simple text format for the resume that the interview system can use
        resume_content = f"""
RESUME: {student_obj.fullname} {student_obj.last_name}

CONTACT INFORMATION:
Email: {request.POST.get('student_email', '')}
Phone: {request.POST.get('student_phone', '')}
LinkedIn: {request.POST.get('student_linkedin', '')}

EDUCATION:
{student_obj.faculty} - {student_obj.program}
GPA: {student_obj.gpa}

SKILLS:
{skills_str}

PROFESSIONAL SUMMARY:
{request.POST.get('student_summary', '')}
        """
        
        # Get the cover letter content if it was generated
        cover_letter = request.POST.get('cover_letter_content', '')
        
        # Check if there's cover letter content in the DOM (from generated content)
        if not cover_letter and request.POST.get('has_generated_cover_letter') == 'true':
            # Extract from the hidden field that might have been populated by JS
            cover_letter_elem = request.POST.get('hidden_cover_letter', '')
            if cover_letter_elem:
                cover_letter = cover_letter_elem
                
        # Prepare data for the interview system
        interview_data = {
            'student_id': student_id,
            'job_id': job_id,
            'job_title': job_title,
            'job_company': job_company,
            'resume_content': resume_content,
            'cover_letter': cover_letter
        }
        
        # If we have job recommendation data, include match information
        if job_id:
            try:
                from job_recommender.models import JobRecommendation
                job_rec = JobRecommendation.objects.filter(
                    student=student_obj,
                    job__id=job_id
                ).first()
                
                if job_rec:
                    interview_data['match_score'] = str(job_rec.match_score)
                    interview_data['match_source'] = job_rec.source
            except Exception as e:
                logger.warning(f"Could not retrieve job recommendation data: {e}")
        
        # Redirect to the interview preparation page
        from django.urls import reverse
        return redirect(reverse('interview:prepare_interview') + '?' + '&'.join([f"{k}={v}" for k, v in interview_data.items() if v]))
        
    except Exception as e:
        logger.error(f"Error starting interview from resume: {e}")
        error_message = f"""
        <html>
        <head>
            <title>Error Starting Interview</title>
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
                <h2 class="error-title">Error Starting Interview</h2>
                <p>We encountered an error while preparing your interview. Please try again.</p>
                <div class="error-details">
                    <p>{str(e)}</p>
                </div>
                <a href="javascript:history.back()" class="back-button">Go Back</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(error_message, status=500)
