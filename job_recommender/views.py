from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.db import transaction

# Import our recommender system
from .recommender import HybridRecommender
# Import our models
from .models import Student, Course, Organization, Internship, Job, JobRecommendation

# Initialize the recommender system
recommender = HybridRecommender(alumni_weight=0.6, job_weight=0.4)

# Create your views here.
def landing_page(request):
    return render(request, 'landing_page.html')

def career_form(request):
    return render(request, 'career_form.html')

# View for the recommendation results page
def recommendation_results(request):
    return render(request, 'recommendation_results.html')

# View to handle form submission
@csrf_exempt
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
            
            # Save organizations
            for org_data in organizations:
                start_date = datetime.strptime(org_data['start_date'], '%Y-%m-%d').date()
                end_date = None
                if org_data.get('end_date'):
                    end_date = datetime.strptime(org_data['end_date'], '%Y-%m-%d').date()
                
                Organization.objects.create(
                    student=student,
                    name=org_data['name'],
                    position=org_data['position'],
                    start_date=start_date,
                    end_date=end_date,
                    description=org_data.get('description', '')
                )
            
            # Save internships
            for intern_data in internships:
                start_date = datetime.strptime(intern_data['start_date'], '%Y-%m-%d').date()
                end_date = None
                if intern_data.get('end_date'):
                    end_date = datetime.strptime(intern_data['end_date'], '%Y-%m-%d').date()
                
                Internship.objects.create(
                    student=student,
                    company=intern_data['company'],
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


