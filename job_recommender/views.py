from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.
def landing_page(request):
    return render(request, 'landing_page.html')

def career_form(request):
    return render(request, 'career_form.html')

# New view to handle form submission
@csrf_exempt
def submit_application(request):
    """
    View to receive POST data from career form and return JSON response
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
        
        # Construct the complete response
        response_data = {
            "status": "success",
            "message": "Application received successfully",
            "data": {
                "student": student_data,
                "courses": courses_data,
                "organizations": organizations,
                "internships": internships
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


