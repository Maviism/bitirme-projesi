import uuid
import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import InterviewSession
from job_recommender.models import Job, Student

# Create your views here.
def index(request):
    # Get all interview sessions for the current user if authenticated
    interview_sessions = None
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            interview_sessions = InterviewSession.objects.filter(student=student).order_by('-created_at')
        except Student.DoesNotExist:
            interview_sessions = []
    
    return render(request, "interview/index.html", {
        "interview_sessions": interview_sessions
    })

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
        return redirect('interview:index')
    
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

@login_required
def interview_transcript(request, interview_id):
    """
    Display the transcript of a completed interview
    """
    # Get the interview session
    interview_session = get_object_or_404(InterviewSession, id=interview_id)
    
    # Check if the user has permission to view this interview
    if request.user.is_staff or (hasattr(request.user, 'student') and 
                               interview_session.student == request.user.student):
        # Process transcript data
        transcript_data = []
        if interview_session.transcript:
            try:
                transcript_data = json.loads(interview_session.transcript)
            except Exception as e:
                print(f"Error parsing transcript data: {e}")
                transcript_data = []
        
        # Process feedback data
        feedback_data = None
        if interview_session.feedback:
            try:
                feedback_data = json.loads(interview_session.feedback)
                # If it's a list, use the most recent feedback
                if isinstance(feedback_data, list) and len(feedback_data) > 0:
                    feedback_data = feedback_data[-1]
            except Exception as e:
                print(f"Error parsing feedback data: {e}")
                feedback_data = None
                
        # Render the template
        return render(request, "interview/transcript.html", {
            "interview_session": interview_session,
            "transcript_data": transcript_data,
            "feedback": feedback_data
        })
    else:
        # User doesn't have permission
        return redirect('interview:index')