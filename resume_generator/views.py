from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from job_recommender.models import Student, Course, Experience
from utils.llm_utils import get_llm_instance, cache_llm_response
from resume_generator.utils import (
    generate_resume_content, improve_resume_section as improve_section_util,
    generate_cover_letter_content, improve_cover_letter,
    # New utility functions
    calculate_duration_months, get_student_data_for_resume, get_template_name,
    get_context_for_resume_template, get_enhanced_user_data_for_llm,
    get_comprehensive_job_data, get_error_response,
    generate_fallback_cover_letter, generate_fallback_resume_content
)

# Import the global student utility function
from utils.user_utils import get_current_student

import json
import os
import logging

# Standard logger configuration
logger = logging.getLogger(__name__)

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
            
            # Redirect to the resume generator job selection page
            return redirect('resume_generator:generate_resume_for_job')
    
    # Get all profiles linked to this user
    student_profiles = Student.objects.filter(user=request.user).order_by('-updated_at')
    
    # Get the currently active profile ID from session
    active_profile_id = request.session.get('active_student_id')
    
    # If there's only one profile, set it as active and redirect
    if student_profiles.count() == 1:
        request.session['active_student_id'] = str(student_profiles.first().id)
        return redirect('resume_generator:generate_resume_for_job')
        
    context = {
        'profiles': student_profiles,
        'active_profile_id': active_profile_id
    }
    
    return render(request, 'resume_generator/select_profile.html', context)



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

        # 3. Construct student_data for the PDF using the utility function
        student_data_for_pdf = get_student_data_for_resume(student_obj, request.POST)

        # Get template based on style
        template_style = request.POST.get('resume_template_style', 'ats')
        template_name = get_template_name(template_style)

        # Get context for template rendering
        context_for_template = get_context_for_resume_template(
            job_title, job_company, job_description, student_data_for_pdf
        )

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
        return get_error_response("We encountered an error while generating your resume PDF. Please try again.")

def preview_resume_view(request: HttpRequest):
    # Check request method
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=400)
    
    try:
        # Wrap everything in a transaction for performance
        from django.db import transaction
        with transaction.atomic():
            
            # Get basic job and student information
            job_title = request.POST.get('job_title')
            job_company = request.POST.get('job_company')
            job_description = request.POST.get('job_description')
            student_id = request.POST.get('student_id')

            if not student_id:
                return HttpResponse("Student ID missing.", status=400)
            
            student_obj = get_object_or_404(Student, pk=student_id)
            logger.info(f"Retrieved student: {student_obj.fullname} {student_obj.last_name}")

            # Get student data using the utility function
            student_data_for_preview = get_student_data_for_resume(student_obj, request.POST)
            
            # Get template and context
            template_style = request.POST.get('resume_template_style', 'ats')
            template_name = get_template_name(template_style)
            
            context_for_template = get_context_for_resume_template(
                job_title, job_company, job_description, student_data_for_preview, is_preview=True
            )

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
        
        # Try to get LLM instance and use fallback content if it fails
        llm = get_llm_instance()
        
        # Check if we need to use fallback content
        if not hasattr(llm, 'provider') or not llm.provider:
            # Return fallback content when LLM is not available
            fallback_content = generate_fallback_resume_content(student_obj)
            return JsonResponse({
                'success': True,
                'content': fallback_content
            })

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
                    'match_score': float(rec.match_score),
                    'is_current_job': job_id and str(rec.job.id) == str(job_id),
                    'required_skills': rec.job.required_skills if isinstance(rec.job.required_skills, list) else [],
                    'description': rec.job.description[:200]  # Truncated description
                })
                
            logger.info(f"Processed {len(job_recommendations)} job recommendations for AI content generation")
        except Exception as e:
            logger.warning(f"Error fetching job recommendations: {e}")
        
        # Prepare enhanced user data using the utility function
        user_data = get_enhanced_user_data_for_llm(student_obj, job_recommendations)
        
        # Get job description if provided
        job_description = request.POST.get('job_description', '')
        
        # Generate content with the LLM instance we already have
        content = generate_resume_content(llm, user_data, job_description)
        
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
        
        try:
            # Get LLM instance and improve section
            llm = get_llm_instance()
            improved_content = improve_section_util(llm, section_content, section_type, job_context)
            
            return JsonResponse({
                'success': True,
                'improved_content': improved_content
            })
            
        except Exception as e:
            logger.error(f"Error improving resume section: {e}")
            # Provide a graceful fallback
            fallback_msg = "Özetiniz temel geliştirmelerle güçlendirildi. Daha gelişmiş güncellemeler için AI hizmeti şu anda kullanılamıyor."
            return JsonResponse({
                'success': True,
                'improved_content': f"{fallback_msg}\n\n{section_content}"
            })
    
    except Exception as e:
        logger.error(f"Failed to improve section: {e}")
        return JsonResponse({"error": "Failed to improve section", "details": str(e)}, status=500)
        
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
        
        # Try to get LLM instance
        llm = get_llm_instance()
        
        # Check if we need to use fallback content
        if not hasattr(llm, 'provider') or not llm.provider:
            # Return fallback content when LLM is not available
            job_title = request.POST.get('job_title', 'pozisyon')
            fallback_letter = generate_fallback_cover_letter(student_obj, job_title)

            return JsonResponse({
                'success': True,
                'cover_letter': fallback_letter
            })
        
        # Get comprehensive user data using the utility function
        user_data = get_enhanced_user_data_for_llm(student_obj)
        
        # Add education-specific fields for cover letter
        user_data['education'] = {
            'degree': f"{student_obj.program} - {student_obj.faculty}",
            'gpa': str(student_obj.gpa),
            'academic_achievements': [
                f"GNO: {student_obj.gpa}",
                f"Toplam {Course.objects.filter(student=student_obj).count()} ders tamamlandı",
                f"{Course.objects.filter(student=student_obj, grade__in=['AA', 'BA']).count()} yüksek not"
            ]
        }
        
        # Add career motivation
        user_data['career_motivation'] = {
            'field_alignment': f"{student_obj.program} alanında kariyer hedefi",
            'growth_mindset': 'Sürekli öğrenme ve gelişim odaklı',
            'value_proposition': 'Akademik bilgi ve pratik deneyimi harmanlayan yaklaşım'
        }
        
        # Get job data from the request
        job_title = request.POST.get('job_title', '')
        job_description = request.POST.get('job_description', '')
        
        # Create job data using utility function
        job_data = get_comprehensive_job_data(job_title, job_description)
        
        # Generate cover letter using the LLM instance we already have
        cover_letter = generate_cover_letter_content(llm, user_data, job_data)
        
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


def improve_cover_letter_view(request: HttpRequest):
    """Improve an existing cover letter using AI"""
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=405)
    
    try:
        # Get student data and current cover letter
        student_id = request.POST.get('student_id')
        current_cover_letter = request.POST.get('current_cover_letter')
        
        if not student_id:
            return JsonResponse({'error': 'Student ID missing'}, status=400)
            
        if not current_cover_letter:
            return JsonResponse({'error': 'No cover letter to improve'}, status=400)
        
        student_obj = get_object_or_404(Student, pk=student_id)
        
        # Try to get LLM instance
        llm = get_llm_instance()
        
        # Check if we need to use fallback content
        if not hasattr(llm, 'provider') or not llm.provider:
            logger.warning("No LLM API keys available - returning original cover letter")
            # Return the original letter with minimal changes
            return JsonResponse({
                'success': True,
                'improved_cover_letter': current_cover_letter.replace("Saygılarımla", "En içten saygılarımla")
            })
        
        # Get job information
        job_title = request.POST.get('job_title', '')
        job_company = request.POST.get('job_company', '')
        job_description = request.POST.get('job_description', '')
        
        # Generate improvement context
        improvement_context = {
            'current_letter': current_cover_letter,
            'job_info': {
                'title': job_title,
                'description': job_description
            },
            'candidate_info': {
                'name': f"{student_obj.fullname} {student_obj.last_name}",
                'faculty': student_obj.faculty, 
                'program': student_obj.program,
                'gpa': str(student_obj.gpa),
                'graduation_status': 'mezun' if student_obj.is_alumni else 'öğrenci',
                'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else []
            },
            'improvement_goals': [
                'İş tanımındaki anahtar noktaları daha iyi vurgulama',
                'Kişiselleştirme ve özgünlüğü artırma',
                'Daha ikna edici ve etkileyici bir dil kullanma',
                'İş özelindeki deneyimleri öne çıkarma',
                'Profesyonel ve akıcı ifadeler'
            ]
        }
        
        # Improve cover letter using the LLM instance we already have
        improved_cover_letter = improve_cover_letter(llm, improvement_context)
        
        return JsonResponse({
            'success': True,
            'improved_cover_letter': improved_cover_letter
        })
        
    except Exception as e:
        logger.error(f"Error improving cover letter: {e}")
        return JsonResponse({
            'error': 'Failed to improve cover letter',
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
        return get_error_response("We encountered an error while preparing your interview. Please try again.")

def generate_resume_for_job_view(request: HttpRequest):
    """
    Generate a resume tailored for a specific job.
    Handles three scenarios:
    1. GET request without parameters - show job selection UI
    2. POST request with job_id - generate resume for specific job
    3. POST request with job details - generate resume for custom job
    
    Args:
        request: The HTTP request object
    """
    # Handle GET requests - redirect to recommendation results
    if request.method == 'GET':
        # This is a direct access without a specific job
        # Redirect to recommendation results page where the user can select a job
        return redirect('recommendation_results')
    
    # For POST requests, check if it's a custom job or job_id
    has_custom_job = 'job_title' in request.POST and 'company' in request.POST
        
    # If not custom and no job_id provided, return error
    if not has_custom_job and 'job_id' not in request.POST:
        return HttpResponse("Invalid request. Either job ID or job details must be provided.", status=400)
    
    # Get job ID from POST data or process custom job
    job_id = None
    job_title = None
    job_company = None
    job_description = None
    
    if has_custom_job:
        # This is a custom job submission
        job_title = request.POST.get('job_title')
        job_company = request.POST.get('company')
        job_description = request.POST.get('job_description', '')
        logger.info(f"Custom job submission: {job_title} at {job_company}")
    else:
        # This is a job_id based submission
        try:
            job_id = int(request.POST.get('job_id'))
        except (TypeError, ValueError):
            return HttpResponse("Invalid job ID format.", status=400)
    # Get current student
    student = get_current_student(request)
    if not student:
        # Handle case where student is not found
        return HttpResponse("Student profile not found. Please log in.", status=404)

    # Fetch job details from the database
    try:
        from job_recommender.models import Job, JobRecommendation

        # Get the job object
        job = get_object_or_404(Job, id=job_id)
        
            # Get job details
        job_title = job.title
        job_company = job.company
        job_description = job.description
        
        # Verify that this job is either public or recommended to the student
        # to prevent access to unauthorized jobs
        has_access = False
        try:
            # Check if this job has been recommended to the student
            recommendation = JobRecommendation.objects.filter(
                student=student,
                job=job
            ).exists()
            
            if recommendation:
                has_access = True
            else:
                # Check if this is a public job (you might need to add a 'is_public' field to your Job model)
                # For now, assume all jobs are accessible
                has_access = True
                
            if not has_access:
                logger.warning(f"User {request.user.username} attempted to access unauthorized job {job_id}")
                return HttpResponse("You don't have access to this job.", status=403)
                
        except Exception as e:
            logger.error(f"Error checking job access: {e}")
            # Continue for now, but with a warning

        # Fetch related data for the student
        courses = Course.objects.filter(student=student)
        internships = Experience.objects.filter(student=student, experience_type='internship')
        organizations = Experience.objects.filter(student=student, experience_type='organization')
        
        # Get job recommendations for this student
        job_recommendations = None
        try:
            # Get all recommendations for this student
            recommendations = JobRecommendation.objects.filter(
                student=student
            ).select_related('job').order_by('-match_score')[:5]  # Get top 5
            
            # Find the current job in recommendations if it exists
            current_job_rec = None
            for rec in recommendations:
                if rec.job.id == job_id:
                    current_job_rec = rec
                    break
            
            # If we didn't find the current job in recommendations, try to fetch it directly
            if not current_job_rec:
                # Try to find a recommendation for this specific job
                direct_rec = JobRecommendation.objects.filter(
                    student=student,
                    job__id=job_id
                ).first()
                
                if direct_rec:
                    current_job_rec = direct_rec
            
            job_recommendations = {
                'recommendations': recommendations,
                'current_job_rec': current_job_rec
            }
        except Exception as e:
            logger.error(f"Error fetching job recommendations: {e}")
            # Don't let this block the resume generation

        # Prepare student data for the form
        student_form_data = {
            'id': student.id,
            'fullname': student.fullname,
            'last_name': student.last_name,
            'email': getattr(student, 'email', 'your_email@example.com'),
            'phone': getattr(student, 'phone', '555-1234'),
            'linkedin_profile': getattr(student, 'linkedin_profile', ''),
            'faculty': student.faculty,
            'program': student.program,
            'gpa': str(student.gpa),
            'skills': ', '.join(student.skills) if isinstance(student.skills, list) else student.skills,
            'summary': getattr(student, 'summary', ''),
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
            'job_recommendations': job_recommendations,
        }
        
        return render(request, 'resume_generator/generate_resume_form.html', context)
        
    except Exception as e:
        logger.error(f"Error retrieving job details: {e}")
        return HttpResponse(f"Error loading job data: {e}", status=500)
