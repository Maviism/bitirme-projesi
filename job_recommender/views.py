from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.db import transaction
from django.contrib.auth.decorators import login_required
import logging
from utils.user_utils import get_current_student


# Import our recommender system
from .recommender import HybridRecommender
# Import our models
from .models import Student, Course, Experience, Job, JobRecommendation
# Import LLM utils
from utils.llm_utils import get_llm_instance

logger = logging.getLogger(__name__)

# Initialize the recommender system
recommender = HybridRecommender(alumni_weight=0.6, job_weight=0.4)

# Create your views here.
def landing_page(request):
    return render(request, 'common/landing_page.html')

@login_required
def career_form(request):    
    # Get current student profile if exists
    student = get_current_student(request)
    context = {}
    
    if student:
        # Convert birth date to string format DD/MM/YYYY
        birth_date_str = student.birth_date.strftime('%d/%m/%Y') if student.birth_date else ""
        
        # Get student courses
        courses = student.courses.all()
        formatted_courses = []
        for course in courses:
            formatted_courses.append({
                'code': course.code,
                'name': course.name,
                'grade': course.grade
            })
        
        # Get student experiences
        organizations = student.experiences.filter(experience_type='organization')
        formatted_organizations = []
        for org in organizations:
            formatted_organizations.append({
                'institution_name': org.institution_name,
                'position': org.position,
                'start_date': org.start_date.strftime('%Y-%m-%d') if org.start_date else '',
                'end_date': org.end_date.strftime('%Y-%m-%d') if org.end_date else '',
                'description': org.description
            })
        
        internships = student.experiences.filter(experience_type='internship')
        formatted_internships = []
        for internship in internships:
            formatted_internships.append({
                'institution_name': internship.institution_name,
                'position': internship.position,
                'start_date': internship.start_date.strftime('%Y-%m-%d') if internship.start_date else '',
                'end_date': internship.end_date.strftime('%Y-%m-%d') if internship.end_date else '',
                'description': internship.description
            })
        # Pass student data to template
        context = {
            'student': {
                'id': student.id,
                'student_id': student.student_id,
                'id_number': student.id_number,
                'fullname': student.fullname,
                'last_name': student.last_name,
                'birth_date': birth_date_str,
                'faculty': student.faculty,
                'program': student.program, 
                'gpa': float(student.gpa),
                'skills': student.skills
            },
            'courses': formatted_courses,
            'organizations': formatted_organizations,
            'internships': formatted_internships,
            'has_existing_profile': True
        }
        logger.info(f"Found existing student profile for user: {request.user.username}")
    else:
        context['has_existing_profile'] = False
        logger.info(f"No existing student profile found for user: {request.user.username}")
    
    return render(request, 'job_recommender/career_form.html', context)

# View for the recommendation results page
@login_required
def recommendation_results(request):
    # Get the current user's student profile
    student = get_current_student(request)
    
    if student:
        # Get the student's job recommendations
        recommendations = JobRecommendation.objects.filter(
            student=student
        ).select_related('job').order_by('-match_score')[:10]
        
        # Format the recommendations for the template
        formatted_recommendations = []
        for rec in recommendations:
            # Define the recommendation sources based on the source field
            sources = []
            if rec.source == 'alumni':
                sources = ['alumni']
            elif rec.source == 'job_posting':
                sources = ['job_posting']
            elif rec.source == 'hybrid':
                sources = ['alumni', 'job_posting']  # Hybrid means both sources contributed
            
            formatted_recommendations.append({
                'id': rec.job.id,
                'title': rec.job.title,
                'company': rec.job.company,
                'description': rec.job.description,
                'match_score': float(rec.match_score),
                'recommendation_sources': sources
            })
        
        context = {
            'has_recommendations': len(formatted_recommendations) > 0,
            'job_recommendations': formatted_recommendations,
            'student': student
        }
        logger.info(f"Found {len(formatted_recommendations)} recommendations for user {request.user.username}")
        
    else:
        context = {
            'has_recommendations': False,
            'error_message': 'No student profile found. Please complete your profile first.'
        }
        logger.warning(f"No student profile found for user {request.user.username}")
    
    return render(request, 'job_recommender/recommendation_results.html', context)

# View to handle form submission
@csrf_exempt
@login_required
def submit_application(request):
    """
    View to receive POST data from career form and return JSON response with job recommendations
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        # Try to find an existing student profile for the logged-in user
        existing_student = None
        if request.user.is_authenticated:
            existing_student = Student.objects.filter(user=request.user).first()
        
        # Extract basic student information
        student_data = {
            'student_id': request.POST.get('student_id'),
            'id_number': request.POST.get('id_number'),
            'fullname': request.POST.get('fullname'),
            'last_name': request.POST.get('last_name'),
            'birth_date': request.POST.get('birth_date'),
            'faculty': request.POST.get('faculty'),
            'program': request.POST.get('program'),
            'gpa': request.POST.get('gpa')
        }
        
        print(f"[DEBUG] Extracted student_data: {student_data}")
        print(f"[DEBUG] Birth date value: '{student_data['birth_date']}' (type: {type(student_data['birth_date'])})")
        
        # Parse courses data from JSON string
        courses_data = []
        if 'courses_data' in request.POST:
            try:
                courses_data = json.loads(request.POST.get('courses_data'))
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid courses data format"}, status=400)
        else:
            print("[DEBUG] No courses data provided")
        
        # Parse skills data from JSON string
        skills_data = []
        if 'skills_data' in request.POST:
            try:
                skills_data = json.loads(request.POST.get('skills_data'))
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid skills data format"}, status=400)
        else:
            print("[DEBUG] No skills data provided")
        
        # Process organization experiences
        organizations = []
        org_fields = ['institution_name', 'position', 'start_date', 'end_date', 'description']
        i = 0
        while True:
            if f'organizations[{i}][institution_name]' not in request.POST:
                break
            
            org = {}
            for field in org_fields:
                key = f'organizations[{i}][{field}]'
                if key in request.POST:
                    org[field] = request.POST.get(key)
            
            if org:  # Only add if we have data
                organizations.append(org)
            i += 1
        
        # Process internship experiences
        internships = []
        intern_fields = ['institution_name', 'position', 'start_date', 'end_date', 'description']
        i = 0
        while True:
            if f'internships[{i}][institution_name]' not in request.POST:
                break
            
            intern = {}
            for field in intern_fields:
                key = f'internships[{i}][{field}]'
                if key in request.POST:
                    intern[field] = request.POST.get(key)
            
            if intern:  # Only add if we have data
                internships.append(intern)
            i += 1
        
        # Generate job recommendations using the hybrid recommender
        job_recommendations = recommender.get_hybrid_recommendations(
            student_data,
            courses_data,
            organizations,
            internships,
            skills_data  # Add skills data to the recommender
        )
        
        # Format job recommendations for response
        formatted_recommendations = []
        for rec in job_recommendations:
            job = rec.get('job', {})
            formatted_recommendations.append({
                'id': job.get('id', ''),
                'title': job.get('title', ''),
                'company': job.get('company', ''),
                'description': job.get('description', ''),
                'match_score': round(rec.get('score', 0) * 100),  # Convert to percentage
                'recommendation_sources': rec.get('sources', [])
            })
        
        # Save all data to the database
        with transaction.atomic():
            # Save student data
            birth_date = None
            if student_data['birth_date']:
                try:
                    # Convert birth date string to date object
                    birth_date = datetime.strptime(student_data['birth_date'], '%d/%m/%Y').date()
                except ValueError:
                    try:
                        birth_date = datetime.strptime(student_data['birth_date'], '%Y-%m-%d').date()
                    except ValueError:
                        return JsonResponse({"error": "Invalid birth date format. Use DD/MM/YYYY"}, status=400)
            
            # Create or update student record
            if existing_student:
                # Update existing student record
                existing_student.id_number = student_data['id_number']
                existing_student.fullname = student_data['fullname']  
                existing_student.last_name = student_data['last_name']
                existing_student.birth_date = birth_date
                existing_student.faculty = student_data['faculty']
                existing_student.program = student_data['program']
                existing_student.gpa = float(student_data['gpa']) if student_data['gpa'] else 0.0
                existing_student.skills = skills_data  # Save the skills data
                existing_student.save()
                student = existing_student
                created = False
                logger.info(f"Updated existing student record for user {request.user.username}")
            else:
                # Create new student record
                student, created = Student.objects.update_or_create(
                    student_id=student_data['student_id'],
                    defaults={
                        'id_number': student_data['id_number'],
                        'fullname': student_data['fullname'],
                        'last_name': student_data['last_name'],
                        'birth_date': birth_date,
                        'faculty': student_data['faculty'],
                        'program': student_data['program'],
                        'gpa': float(student_data['gpa']) if student_data['gpa'] else 0.0,
                        'skills': skills_data,  # Save the skills data
                        'user': request.user,  # Link the student to the current logged-in user
                    }
                )
                logger.info(f"Created new student record for user {request.user.username}")
            
            # Save courses
            for course_data in courses_data:
                Course.objects.update_or_create(
                    student=student,
                    code=course_data['code'],
                    defaults={
                        'name': course_data['name'],
                        'grade': course_data['grade']
                    }
                )
            
            # Clear existing experiences before saving new ones if updating profile
            if not created:
                Experience.objects.filter(student=student).delete()
            
            # Save organizations as experiences
            for org_data in organizations:
                try:
                    start_date = None
                    if org_data.get('start_date'):
                        start_date = datetime.strptime(org_data['start_date'], '%Y-%m-%d').date()
                    
                    end_date = None
                    if org_data.get('end_date'):
                        end_date = datetime.strptime(org_data['end_date'], '%Y-%m-%d').date()
                    
                    # Only create experience if we have required fields
                    if start_date and org_data.get('institution_name') and org_data.get('position'):
                        Experience.objects.create(
                            student=student,
                            experience_type='organization',
                            institution_name=org_data['institution_name'],
                            position=org_data['position'],
                            start_date=start_date,
                            end_date=end_date,
                            description=org_data.get('description', '')
                        )
                except ValueError as e:
                    logger.warning(f"Invalid date format in organization data: {e}")
                    continue
                except KeyError as e:
                    logger.warning(f"Missing required field in organization data: {e}")
                    continue
            
            # Save internships as experiences
            for intern_data in internships:
                try:
                    start_date = None
                    if intern_data.get('start_date'):
                        start_date = datetime.strptime(intern_data['start_date'], '%Y-%m-%d').date()
                    
                    end_date = None
                    if intern_data.get('end_date'):
                        end_date = datetime.strptime(intern_data['end_date'], '%Y-%m-%d').date()
                    
                    # Only create experience if we have required fields
                    if start_date and intern_data.get('institution_name') and intern_data.get('position'):
                        Experience.objects.create(
                            student=student,
                            experience_type='internship',
                            institution_name=intern_data['institution_name'],
                            position=intern_data['position'],
                            start_date=start_date,
                            end_date=end_date,
                            description=intern_data.get('description', '')
                        )
                except ValueError as e:
                    logger.warning(f"Invalid date format in internship data: {e}")
                    continue
                except KeyError as e:
                    logger.warning(f"Missing required field in internship data: {e}")
                    continue
            
            # Save job recommendations
            for rec in job_recommendations:
                job_data = rec.get('job', {})
                # Create or get the job
                job, _ = Job.objects.get_or_create(
                    title=job_data.get('title', ''),
                    company=job_data.get('company', ''),
                    defaults={
                        'description': job_data.get('description', ''),
                        'required_majors': job_data.get('required_majors', []),
                        'required_skills': job_data.get('required_skills', []),  # Add required skills
                    }
                )
                
                # Determine the source
                sources = rec.get('sources', [])
                if len(sources) > 1:
                    source = 'hybrid'
                elif sources and sources[0] in ('alumni', 'job_posting'):
                    source = sources[0]
                else:
                    source = 'hybrid'
                
                # Create recommendation
                JobRecommendation.objects.update_or_create(
                    student=student,
                    job=job,
                    defaults={
                        'match_score': rec.get('score', 0) * 100,  # Convert to percentage
                        'source': source
                    }
                )
        
        # Construct the complete response
        response_data = {
            "status": "success",
            "message": "Application received and saved successfully",
            "data": {
                "student": student_data,
                "courses": courses_data,
                "skills": skills_data,  # Include skills in the response
                "organizations": organizations,
                "internships": internships,
                "job_recommendations": formatted_recommendations
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"[DEBUG] Error in submit_application: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)








