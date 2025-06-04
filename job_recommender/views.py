from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.db import transaction
from django.contrib.auth.decorators import login_required

# Import our recommender system
from .recommender import HybridRecommender
# Import our models
from .models import Student, Course, Experience, Job, JobRecommendation
# Import LLM utils
from utils.llm_utils import get_llm_instance, cache_llm_response
import logging

logger = logging.getLogger(__name__)

# Initialize the recommender system
recommender = HybridRecommender(alumni_weight=0.6, job_weight=0.4)

# Create your views here.
def landing_page(request):
    return render(request, 'common/landing_page.html')

@login_required
def career_form(request):
    return render(request, 'job_recommender/career_form.html')

# View for the recommendation results page
@login_required
def recommendation_results(request):
    return render(request, 'job_recommender/recommendation_results.html')

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
        org_fields = ['name', 'position', 'start_date', 'end_date', 'description']
        i = 0
        while True:
            if f'organizations[{i}][name]' not in request.POST:
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
        intern_fields = ['company', 'position', 'start_date', 'end_date', 'description']
        i = 0
        while True:
            if f'internships[{i}][company]' not in request.POST:
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
            try:
                # Convert birth date string to date object
                birth_date = datetime.strptime(student_data['birth_date'], '%d/%m/%Y').date()
            except ValueError:
                try:
                    birth_date = datetime.strptime(student_data['birth_date'], '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({"error": "Invalid birth date format. Use DD/MM/YYYY"}, status=400)
            
            # Create or update student record
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
                }
            )
            
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
            
            # Save organizations as experiences
            for org_data in organizations:
                start_date = datetime.strptime(org_data['start_date'], '%Y-%m-%d').date()
                end_date = None
                if org_data.get('end_date'):
                    end_date = datetime.strptime(org_data['end_date'], '%Y-%m-%d').date()
                
                Experience.objects.create(
                    student=student,
                    experience_type='organization',
                    institution_name=org_data.get('institution_name', org_data.get('name', '')),
                    position=org_data['position'],
                    start_date=start_date,
                    end_date=end_date,
                    description=org_data.get('description', '')
                )
            
            # Save internships as experiences
            for intern_data in internships:
                start_date = datetime.strptime(intern_data['start_date'], '%Y-%m-%d').date()
                end_date = None
                if intern_data.get('end_date'):
                    end_date = datetime.strptime(intern_data['end_date'], '%Y-%m-%d').date()
                
                Experience.objects.create(
                    student=student,
                    experience_type='internship',
                    institution_name=intern_data.get('institution_name', intern_data.get('company', '')),
                    position=intern_data['position'],
                    start_date=start_date,
                    end_date=end_date,
                    description=intern_data.get('description', '')
                )
            
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


@cache_llm_response("job_compatibility")
@login_required
def analyze_job_compatibility(request):
    """Analyze compatibility between student profile and specific job using AI"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        # Get student ID and job ID from request
        student_id = request.POST.get('student_id')
        job_id = request.POST.get('job_id')
        
        if not student_id or not job_id:
            return JsonResponse({"error": "Student ID and Job ID are required"}, status=400)
        
        # Get student and job objects
        try:
            student = Student.objects.get(pk=student_id)
            job = Job.objects.get(pk=job_id)
        except (Student.DoesNotExist, Job.DoesNotExist):
            return JsonResponse({"error": "Student or Job not found"}, status=404)
        
        # Prepare user profile data
        user_profile = {
            'personal_info': {
                'name': f"{student.fullname} {student.last_name}",
                'faculty': student.faculty,
                'program': student.program,
                'gpa': str(student.gpa)
            },
            'skills': student.skills if isinstance(student.skills, list) else [student.skills] if student.skills else [],
            'courses': [
                {
                    'name': course.course_name,
                    'grade': getattr(course, 'grade', 'N/A')
                } for course in Course.objects.filter(student=student)
            ],
            'experience': [
                {
                    'company': exp.institution_name,
                    'position': getattr(exp, 'position', 'Intern'),
                    'duration': getattr(exp, 'duration', 'N/A')
                } for exp in Experience.objects.filter(student=student, experience_type='internship')
            ],
            'organizations': [
                {
                    'name': exp.institution_name,
                    'role': getattr(exp, 'position', 'Member')
                } for exp in Experience.objects.filter(student=student, experience_type='organization')
            ]
        }
        
        # Prepare job data
        job_data = {
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'required_majors': job.required_majors if hasattr(job, 'required_majors') else [],
            'required_skills': job.required_skills if hasattr(job, 'required_skills') else []
        }
        
        # Get LLM instance and analyze compatibility
        llm = get_llm_instance()
        compatibility_analysis = llm.analyze_job_compatibility(user_profile, job_data)
        
        return JsonResponse({
            'success': True,
            'analysis': compatibility_analysis
        })
        
    except Exception as e:
        logger.error(f"Error analyzing job compatibility: {e}")
        return JsonResponse({
            'error': 'Failed to analyze job compatibility',
            'details': str(e)
        }, status=500)


@login_required
def get_ai_job_recommendations(request):
    """Get AI-powered job recommendations for a student"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        student_id = request.POST.get('student_id')
        if not student_id:
            return JsonResponse({"error": "Student ID is required"}, status=400)
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)
        
        # Prepare user profile
        user_profile = {
            'personal_info': {
                'name': f"{student.fullname} {student.last_name}",
                'faculty': student.faculty,
                'program': student.program,
                'gpa': str(student.gpa)
            },
            'skills': student.skills if isinstance(student.skills, list) else [student.skills] if student.skills else [],
            'experience_level': 'entry' if not Experience.objects.filter(student=student, experience_type='internship').exists() else 'experienced',
            'preferences': {
                'industry': request.POST.get('preferred_industry', ''),
                'location': request.POST.get('preferred_location', ''),
                'salary_range': request.POST.get('preferred_salary', '')
            }
        }
        
        # Get available jobs (limit to active/recent jobs)
        available_jobs = []
        for job in Job.objects.all()[:20]:  # Limit to 20 jobs for performance
            available_jobs.append({
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description[:500],  # Truncate description
                'required_majors': job.required_majors if hasattr(job, 'required_majors') else [],
                'required_skills': job.required_skills if hasattr(job, 'required_skills') else []
            })
        
        # Get LLM instance and generate recommendations
        llm = get_llm_instance()
        ai_recommendations = llm.generate_job_recommendations(user_profile, available_jobs)
        
        return JsonResponse({
            'success': True,
            'recommendations': ai_recommendations
        })
        
    except Exception as e:
        logger.error(f"Error getting AI job recommendations: {e}")
        return JsonResponse({
            'error': 'Failed to get AI recommendations',
            'details': str(e)
        }, status=500)


@login_required
def get_career_advice(request):
    """Get personalized career advice using AI"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        student_id = request.POST.get('student_id')
        career_goal = request.POST.get('career_goal', '')
        
        if not student_id:
            return JsonResponse({"error": "Student ID is required"}, status=400)
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)
        
        # Prepare user data for career advice
        user_data = {
            'name': f"{student.fullname} {student.last_name}",
            'faculty': student.faculty,
            'program': student.program,
            'gpa': str(student.gpa),
            'skills': student.skills if isinstance(student.skills, list) else [student.skills] if student.skills else [],
            'courses': [course.course_name for course in Course.objects.filter(student=student)],
            'experience': [
                {
                    'company': exp.institution_name,
                    'position': getattr(exp, 'position', 'Intern')
                } for exp in Experience.objects.filter(student=student, experience_type='internship')
            ],
            'career_goal': career_goal
        }
        
        # Generate career advice prompt
        prompt = f"""
        Provide personalized career advice for this student:
        
        Student Profile:
        {json.dumps(user_data, indent=2)}
        
        Please provide advice on:
        1. Skills to develop
        2. Career paths to consider
        3. Next steps to take
        4. Industry insights
        5. Professional development recommendations
        
        Make the advice specific, actionable, and encouraging.
        """
        
        llm = get_llm_instance()
        career_advice = llm.provider.generate_text(prompt)
        
        return JsonResponse({
            'success': True,
            'advice': career_advice
        })
        
    except Exception as e:
        logger.error(f"Error generating career advice: {e}")
        return JsonResponse({
            'error': 'Failed to generate career advice',
            'details': str(e)
        }, status=500)


@login_required
def get_skill_gap_analysis(request):
    """Analyze skill gaps for specific job or career path"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        student_id = request.POST.get('student_id')
        target_job_id = request.POST.get('job_id')
        target_role = request.POST.get('target_role', '')
        
        if not student_id:
            return JsonResponse({"error": "Student ID is required"}, status=400)
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)
        
        # Prepare current skills
        current_skills = student.skills if isinstance(student.skills, list) else [student.skills] if student.skills else []
        current_experience = [
            exp.institution_name for exp in Experience.objects.filter(student=student, experience_type='internship')
        ]
        
        # Get target job requirements
        target_requirements = {}
        if target_job_id:
            try:
                job = Job.objects.get(pk=target_job_id)
                target_requirements = {
                    'title': job.title,
                    'company': job.company,
                    'required_skills': job.required_skills if hasattr(job, 'required_skills') else [],
                    'description': job.description
                }
            except Job.DoesNotExist:
                pass
        
        # Generate skill gap analysis
        prompt = f"""
        Analyze the skill gap for this student:
        
        Current Profile:
        - Name: {student.fullname} {student.last_name}
        - Program: {student.program}
        - Current Skills: {current_skills}
        - Experience: {current_experience}
        
        Target Position:
        {json.dumps(target_requirements, indent=2) if target_requirements else f"Role: {target_role}"}
        
        Provide a detailed skill gap analysis including:
        1. Skills the student already has that match
        2. Missing skills that need to be developed
        3. Recommended learning resources or courses
        4. Timeline for skill development
        5. Alternative skills that could compensate
        
        Format the response as a structured analysis.
        """
        
        llm = get_llm_instance()
        gap_analysis = llm.provider.generate_text(prompt)
        
        return JsonResponse({
            'success': True,
            'analysis': gap_analysis
        })
        
    except Exception as e:
        logger.error(f"Error analyzing skill gap: {e}")
        return JsonResponse({
            'error': 'Failed to analyze skill gap',
            'details': str(e)
        }, status=500)


