import uuid
import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import InterviewSession
from job_recommender.models import Job, Student, JobRecommendation

# Create your views here.

def room(request, room_name):
    # Try to get the interview session for this room
    interview_session = None
    try:
        interview_session = InterviewSession.objects.get(room_name=room_name)
    except InterviewSession.DoesNotExist:
        pass
    
    return render(request, "interview/room.html", {
        "room_name": room_name,
        "interview_session": interview_session
    })

def prepare_interview(request):
    """
    Create an interview session from a resume
    """
    if request.method != 'POST' and request.method != 'GET':
        return redirect('recommendation_results')
    
    # Get data from the form or query parameters
    if request.method == 'POST':
        resume_content = request.POST.get('resume_content', '')
        cover_letter = request.POST.get('cover_letter', '')
        job_id = request.POST.get('job_id')
        student_id = request.POST.get('student_id')
    else:  # GET
        resume_content = request.GET.get('resume_content', '')
        cover_letter = request.GET.get('cover_letter', '')
        job_id = request.GET.get('job_id')
        student_id = request.GET.get('student_id')
    
    # Get the student and job
    student = get_object_or_404(Student, pk=student_id)
    job = None
    if job_id:
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            pass
    
    # Create a unique room name
    room_name = f"interview_{uuid.uuid4().hex[:8]}"
    
    # Create the interview session
    interview_session = InterviewSession.objects.create(
        student=student,
        job=job,
        room_name=room_name,
        resume_content=resume_content,
        cover_letter=cover_letter
    )
    
    # Redirect to the room
    return redirect('interview:room', room_name=room_name)

@login_required
@require_POST
def direct_interview(request):
    """
    Create an interview session directly from job ID and send user to interview room
    """
    # Get job_id from the form submission
    job_id = request.POST.get('job_id')
    if not job_id:
        return redirect('recommendation_results')
        
    # Get the job and student
    job = get_object_or_404(Job, pk=job_id)
    student = get_object_or_404(Student, user=request.user)
    
    # Security check: Verify that this job is in the student's recommendations
    job_rec = JobRecommendation.objects.filter(student=student, job=job).first()
    
    if not job_rec:
        # This job wasn't recommended to this student
        return redirect('recommendation_results')
    
    # Create a unique room name
    room_name = f"interview_{uuid.uuid4().hex[:8]}"
    
    # Create the interview session with minimal info
    interview_session = InterviewSession.objects.create(
        student=student,
        job=job,
        room_name=room_name,
        resume_content="",
        cover_letter=""
    )
    
    # Redirect to the room
    return redirect('interview:room', room_name=room_name)

@require_POST
@login_required
def save_feedback(request, interview_id):
    """
    Save feedback for an interview session
    """
    try:
        interview_session = get_object_or_404(InterviewSession, id=interview_id, student__user=request.user)
        
        # Get feedback data
        feedback_text = request.POST.get('feedback', '')
        rating = request.POST.get('rating')
        
        # Store feedback as JSON
        feedback_data = {
            'text': feedback_text,
            'rating': rating,
            'submitted_at': datetime.now().isoformat()
        }
        
        # If there's existing feedback, append to it
        if interview_session.feedback:
            try:
                existing_feedback = json.loads(interview_session.feedback)
                if isinstance(existing_feedback, list):
                    existing_feedback.append(feedback_data)
                    interview_session.feedback = json.dumps(existing_feedback)
                else:
                    interview_session.feedback = json.dumps([existing_feedback, feedback_data])
            except:
                interview_session.feedback = json.dumps([feedback_data])
        else:
            interview_session.feedback = json.dumps([feedback_data])
        
        interview_session.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Feedback saved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

# interview_transcript function removed as it's no longer needed