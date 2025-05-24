from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from job_recommender.models import Student, Course, Internship, Organization # Assuming models are in job_recommender
from django.shortcuts import get_object_or_404 # For fetching student

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
    internships = Internship.objects.filter(student=student)
    organizations = Organization.objects.filter(student=student)

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
        'internships': Internship.objects.filter(student=student_obj),
        'organizations': Organization.objects.filter(student=student_obj),
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
    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resume_{student_data_for_pdf["last_name"]}_{job_title}.pdf"'
    
    return response

def preview_resume_view(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponse("Invalid request method.", status=400)

    # Essentially the same data gathering logic as download_resume_view
    job_title = request.POST.get('job_title')
    job_company = request.POST.get('job_company')
    job_description = request.POST.get('job_description')
    student_id = request.POST.get('student_id')

    if not student_id:
        return HttpResponse("Student ID missing.", status=400)
    
    student_obj = get_object_or_404(Student, pk=student_id)

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
        'courses': Course.objects.filter(student=student_obj),
        'internships': Internship.objects.filter(student=student_obj),
        'organizations': Organization.objects.filter(student=student_obj),
    }

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
    html_string = render_to_string(template_name, context_for_template)
    
    # Return as HTML response for preview
    return HttpResponse(html_string)
