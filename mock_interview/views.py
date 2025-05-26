from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
import json
import asyncio
import logging
from .models import InterviewSession, InterviewQuestion, InterviewFeedback, InterviewTemplate
from .deepgram_service import DeepgramInterviewAgent, DeepgramVoiceInterviewAgent
from utils.llm_utils import generate_interview_questions, analyze_interview_response

logger = logging.getLogger(__name__)

@login_required
def interview_dashboard(request):
    """Dashboard showing user's interview history and options"""
    sessions = InterviewSession.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available templates
    templates = InterviewTemplate.objects.filter(is_active=True)
    
    # Calculate average score
    completed_sessions = sessions.filter(status='completed')
    avg_score = None
    if completed_sessions.exists():
        # Get all feedback objects for completed sessions
        total_score = 0
        count = 0
        for session in completed_sessions:
            if hasattr(session, 'feedback') and session.feedback.overall_score:
                total_score += session.feedback.overall_score
                count += 1
        avg_score = total_score / count if count > 0 else 0
    
    context = {
        'sessions': page_obj,
        'templates': templates,
        'total_sessions': sessions.count(),
        'completed_sessions': completed_sessions.count(),
        'avg_score': avg_score,
    }
    
    return render(request, 'mock_interview/dashboard.html', context)

@login_required
def create_interview(request):
    """Create a new mock interview session"""
    if request.method == 'POST':
        job_position = request.POST.get('job_position')
        difficulty_level = request.POST.get('difficulty_level', 'intermediate')
        duration_minutes = int(request.POST.get('duration_minutes', 30))
        template_id = request.POST.get('template_id')
        
        # Create interview session
        session = InterviewSession.objects.create(
            user=request.user,
            job_position=job_position,
            difficulty_level=difficulty_level,
            duration_minutes=duration_minutes,
            status='pending'
        )
        
        # Generate questions based on template or AI
        if template_id:
            template = get_object_or_404(InterviewTemplate, id=template_id, is_active=True)
            questions = template.questions
        else:
            # Generate questions using AI
            try:
                questions = generate_interview_questions(
                    job_position=job_position,
                    difficulty_level=difficulty_level,
                    num_questions=5
                )
            except Exception as e:
                logger.error(f"Error generating questions: {str(e)}")
                messages.error(request, "Error generating interview questions. Please try again.")
                return redirect('mock_interview:dashboard')
        
        # Create question objects
        for i, q in enumerate(questions):
            InterviewQuestion.objects.create(
                session=session,
                question_text=q.get('text', q) if isinstance(q, dict) else str(q),
                question_order=i + 1
            )
        
        messages.success(request, "Interview session created successfully!")
        return redirect('mock_interview:interview_room', session_id=session.id)
    
    # GET request - show form
    templates = InterviewTemplate.objects.filter(is_active=True)
    context = {'templates': templates}
    return render(request, 'mock_interview/create_interview.html', context)

@login_required
def interview_room(request, session_id):
    """The main interview room where the interview takes place"""
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    if session.status == 'completed':
        return redirect('mock_interview:interview_results', session_id=session.id)
    
    questions = session.questions.all().order_by('question_order')
    
    # Serialize questions for JavaScript
    questions_data = []
    for question in questions:
        questions_data.append({
            'id': question.id,
            'question_id': question.id,  # For backward compatibility
            'text': question.question_text,
            'question_text': question.question_text,  # For backward compatibility
            'order': question.question_order
        })
    
    context = {
        'session': session,
        'questions': json.dumps(questions_data),  # Serialize for JavaScript
        'questions_list': questions,  # Keep original for Django template loops
        'total_questions': questions.count(),
    }
    
    return render(request, 'mock_interview/interview_room.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def start_interview_session(request, session_id):
    """API endpoint to start an interview session with Deepgram"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        if session.status != 'pending':
            return JsonResponse({'error': 'Interview session already started or completed'}, status=400)
        
        # Update session status
        session.status = 'in_progress'
        session.started_at = timezone.now()
        session.save()
        
        # Prepare questions for Deepgram agent
        questions = []
        for q in session.questions.all().order_by('question_order'):
            questions.append({
                'id': q.id,
                'text': q.question_text,
                'order': q.question_order
            })
        
        # Initialize Deepgram agent
        agent = DeepgramInterviewAgent()
        
        session_config = {
            'user_id': request.user.id,
            'session_id': session.id,
            'questions': questions,
            'timestamp': int(timezone.now().timestamp())
        }
        
        # Initialize the session
        deepgram_session_id = agent.initialize_session(session_config)
        session.deepgram_session_id = deepgram_session_id
        session.save()
        
        return JsonResponse({
            'status': 'success',
            'session_id': session.id,
            'deepgram_session_id': deepgram_session_id,
            'questions': questions
        })
        
    except Exception as e:
        logger.error(f"Error starting interview session: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def submit_response(request, session_id):
    """API endpoint to submit an interview response"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        data = json.loads(request.body)
        
        question_id = data.get('question_id')
        transcript = data.get('transcript', '')
        audio_data = data.get('audio_data')  # Base64 encoded audio
        
        question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
        
        # Update question with response
        question.response_transcript = transcript
        
        # Analyze response using AI
        try:
            analysis = analyze_interview_response(
                question=question.question_text,
                response=transcript,
                job_position=session.job_position
            )
            question.response_analysis = analysis
            question.score = analysis.get('overall_score', 0)
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            question.response_analysis = {'error': str(e)}
            question.score = 0
        
        question.save()
        
        # Check if this was the last question
        total_questions = session.questions.count()
        answered_questions = session.questions.filter(response_transcript__isnull=False).count()
        
        if answered_questions >= total_questions:
            # Complete the interview
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            # Generate overall feedback
            generate_interview_feedback(session)
            
            return JsonResponse({
                'status': 'interview_completed',
                'redirect_url': f'/mock-interview/results/{session.id}/'
            })
        
        return JsonResponse({
            'status': 'response_submitted',
            'next_question': answered_questions + 1 if answered_questions < total_questions else None
        })
        
    except Exception as e:
        logger.error(f"Error submitting response: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def interview_results(request, session_id):
    """Display interview results and feedback"""
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    if session.status != 'completed':
        return redirect('mock_interview:interview_room', session_id=session.id)
    
    questions = session.questions.all().order_by('question_order')
    feedback = getattr(session, 'feedback', None)
    
    context = {
        'session': session,
        'questions': questions,
        'feedback': feedback,
    }
    
    return render(request, 'mock_interview/results.html', context)

@login_required
def interview_history(request):
    """View all past interviews"""
    sessions = InterviewSession.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter and status_filter in ['pending', 'in_progress', 'completed', 'cancelled']:
        sessions = sessions.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(sessions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sessions': page_obj,
        'status_filter': status_filter,
    }
    
    return render(request, 'mock_interview/history.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def cancel_interview(request, session_id):
    """Cancel an ongoing interview"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        if session.status in ['completed', 'cancelled']:
            return JsonResponse({'error': 'Interview already completed or cancelled'}, status=400)
        
        session.status = 'cancelled'
        session.save()
        
        return JsonResponse({'status': 'cancelled'})
        
    except Exception as e:
        logger.error(f"Error cancelling interview: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def generate_interview_feedback(session):
    """Generate comprehensive feedback for completed interview"""
    try:
        questions = session.questions.all()
        
        if not questions.exists():
            return
        
        # Calculate scores
        scores = [q.score for q in questions if q.score is not None]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Analyze all responses together
        all_responses = [q.response_transcript for q in questions if q.response_transcript]
        combined_text = " ".join(all_responses)
        
        # Extract insights from individual analyses
        strengths = []
        improvements = []
        
        for question in questions:
            analysis = question.response_analysis
            if isinstance(analysis, dict):
                strengths.extend(analysis.get('strengths', []))
                improvements.extend(analysis.get('areas_for_improvement', []))
        
        # Remove duplicates and limit
        strengths = list(set(strengths))[:5]
        improvements = list(set(improvements))[:5]
        
        # Calculate component scores
        communication_scores = []
        technical_scores = []
        confidence_scores = []
        
        for question in questions:
            analysis = question.response_analysis
            if isinstance(analysis, dict):
                communication_scores.append(analysis.get('communication_clarity', 0))
                technical_scores.append(analysis.get('technical_accuracy', 0))
                confidence_scores.append(analysis.get('confidence_level', 0))
        
        communication_score = sum(communication_scores) / len(communication_scores) if communication_scores else 0
        technical_score = sum(technical_scores) / len(technical_scores) if technical_scores else 0
        confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Generate detailed feedback
        detailed_feedback = f"""
        Based on your interview performance for the {session.job_position} position, here's your comprehensive feedback:
        
        Overall Performance: {overall_score:.1f}/10
        
        Communication Skills: {communication_score:.1f}/10
        Technical Knowledge: {technical_score:.1f}/10
        Confidence Level: {confidence_score:.1f}/10
        
        You demonstrated strong performance in several areas and have opportunities for improvement in others.
        """
        
        # Create or update feedback
        feedback, created = InterviewFeedback.objects.get_or_create(
            session=session,
            defaults={
                'overall_score': overall_score,
                'strengths': strengths,
                'areas_for_improvement': improvements,
                'detailed_feedback': detailed_feedback,
                'communication_score': communication_score,
                'technical_score': technical_score,
                'confidence_score': confidence_score,
            }
        )
        
        if not created:
            # Update existing feedback
            feedback.overall_score = overall_score
            feedback.strengths = strengths
            feedback.areas_for_improvement = improvements
            feedback.detailed_feedback = detailed_feedback
            feedback.communication_score = communication_score
            feedback.technical_score = technical_score
            feedback.confidence_score = confidence_score
            feedback.save()
        
        logger.info(f"Generated feedback for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error generating feedback for session {session.id}: {str(e)}")

@login_required 
def get_question_audio(request, question_id):
    """Generate and serve audio for a question using Deepgram TTS"""
    try:
        question = get_object_or_404(InterviewQuestion, id=question_id)
        
        # Check if user has access to this question
        if question.session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Initialize Deepgram agent
        agent = DeepgramInterviewAgent()
        
        # Generate audio asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_url = loop.run_until_complete(agent.text_to_speech(question.question_text))
        loop.close()
        
        return JsonResponse({
            'audio_url': audio_url,
            'question_text': question.question_text
        })
        
    except Exception as e:
        logger.error(f"Error generating question audio: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

# Voice Interview Views

@csrf_exempt
@require_http_methods(["POST"])
def start_voice_interview(request, session_id):
    """API endpoint to start a voice-enabled interview session"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        if session.status != 'pending':
            return JsonResponse({'error': 'Interview session already started or completed'}, status=400)
        
        # Update session status
        session.status = 'in_progress'
        session.started_at = timezone.now()
        session.save()
        
        # Prepare questions for voice agent
        questions = []
        for q in session.questions.all().order_by('question_order'):
            questions.append({
                'id': q.id,
                'text': q.question_text,
                'order': q.question_order
            })
        
        # Initialize voice agent
        voice_agent = DeepgramVoiceInterviewAgent()
        
        session_config = {
            'user_id': request.user.id,
            'session_id': session.id,
            'questions': questions,
            'timestamp': int(timezone.now().timestamp())
        }
        
        # Initialize voice session
        voice_session_id = voice_agent.initialize_voice_session(session_config)
        session.deepgram_session_id = voice_session_id
        session.save()
        
        # Store voice agent in session (in production, use Redis or similar)
        request.session[f'voice_agent_{session.id}'] = voice_session_id
        
        return JsonResponse({
            'status': 'success',
            'session_id': session.id,
            'voice_session_id': voice_session_id,
            'questions': questions,
            'first_question': questions[0] if questions else None
        })
        
    except Exception as e:
        logger.error(f"Error starting voice interview: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def voice_stream_audio(request, session_id):
    """Handle streaming audio data for real-time transcription"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        if session.status != 'in_progress':
            return JsonResponse({'error': 'Interview session not active'}, status=400)
        
        # Get audio data from request
        audio_data = request.body
        
        if not audio_data:
            return JsonResponse({'error': 'No audio data received'}, status=400)
        
        # Process audio through voice agent (in production, use WebSocket)
        # For now, return success
        return JsonResponse({
            'status': 'audio_received',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing voice stream: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def submit_voice_response(request, session_id):
    """Submit a voice response with enhanced analysis"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        data = json.loads(request.body)
        
        question_id = data.get('question_id')
        transcript = data.get('transcript', '')
        voice_confidence = data.get('voice_confidence', 0)
        confidence_scores = data.get('confidence_scores', [])
        speaking_duration = data.get('speaking_duration', 0)
        
        question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
        
        # Update question with voice response
        question.response_transcript = transcript
        
        # Enhanced analysis for voice responses
        try:
            # Basic analysis
            base_analysis = analyze_interview_response(
                question=question.question_text,
                response=transcript,
                job_position=session.job_position
            )
            
            # Add voice-specific metrics
            voice_analysis = {
                **base_analysis,
                'voice_confidence': voice_confidence,
                'confidence_scores': confidence_scores,
                'speaking_duration': speaking_duration,
                'voice_clarity_score': calculate_voice_clarity_score(voice_confidence, confidence_scores),
                'speech_fluency_score': calculate_speech_fluency_score(transcript, speaking_duration),
                'filler_word_analysis': analyze_filler_words_detailed(transcript)
            }
            
            question.response_analysis = voice_analysis
            question.score = calculate_voice_response_score(voice_analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing voice response: {str(e)}")
            question.response_analysis = {'error': str(e)}
            question.score = 0
        
        question.save()
        
        # Check if this was the last question
        total_questions = session.questions.count()
        answered_questions = session.questions.filter(response_transcript__isnull=False).count()
        
        if answered_questions >= total_questions:
            # Complete the interview
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            # Generate voice-enhanced feedback
            generate_voice_interview_feedback(session)
            
            return JsonResponse({
                'status': 'interview_completed',
                'redirect_url': f'/mock-interview/results/{session.id}/'
            })
        
        return JsonResponse({
            'status': 'response_submitted',
            'next_question': answered_questions + 1 if answered_questions < total_questions else None
        })
        
    except Exception as e:
        logger.error(f"Error submitting voice response: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_voice_question_audio(request, question_id):
    """Generate and serve audio for a question using enhanced voice synthesis"""
    try:
        question = get_object_or_404(InterviewQuestion, id=question_id)
        
        # Check access
        if question.session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Initialize voice agent
        voice_agent = DeepgramVoiceInterviewAgent()
        
        # Generate audio asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(voice_agent.text_to_speech_voice(question.question_text))
        loop.close()
        
        # Return audio data as base64 for direct playback
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return JsonResponse({
            'audio_data': audio_base64,
            'question_text': question.question_text,
            'content_type': 'audio/wav'
        })
        
    except Exception as e:
        logger.error(f"Error generating voice question audio: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_voice_transcript(request, session_id):
    """Get real-time transcript updates for voice interview"""
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        if session.status != 'in_progress':
            return JsonResponse({'error': 'Interview session not active'}, status=400)
        
        # In production, this would connect to the voice agent's real-time transcript
        # For now, return a placeholder response
        return JsonResponse({
            'transcript': '',
            'confidence': 0,
            'is_listening': True,
            'current_question': session.questions.filter(response_transcript__isnull=True).first().question_order if session.questions.filter(response_transcript__isnull=True).exists() else None
        })
        
    except Exception as e:
        logger.error(f"Error getting voice transcript: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

# Helper functions for voice analysis

def calculate_voice_clarity_score(voice_confidence: float, confidence_scores: list) -> float:
    """Calculate voice clarity score based on confidence metrics"""
    if not confidence_scores:
        return voice_confidence * 10
    
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    consistency = 1 - (max(confidence_scores) - min(confidence_scores)) if len(confidence_scores) > 1 else 1
    
    clarity_score = (avg_confidence * 0.7 + consistency * 0.3) * 10
    return min(10, max(0, clarity_score))

def calculate_speech_fluency_score(transcript: str, speaking_duration: float) -> float:
    """Calculate speech fluency score"""
    words = transcript.split()
    word_count = len(words)
    
    if speaking_duration <= 0 or word_count == 0:
        return 0
    
    # Calculate words per minute
    wpm = (word_count / speaking_duration) * 60
    
    # Optimal range is 120-180 WPM
    if 120 <= wpm <= 180:
        fluency_base = 8.0
    elif 100 <= wpm < 120 or 180 < wpm <= 200:
        fluency_base = 6.0
    elif 80 <= wpm < 100 or 200 < wpm <= 220:
        fluency_base = 4.0
    else:
        fluency_base = 2.0
    
    # Adjust for filler words
    filler_count = count_filler_words(transcript)
    filler_penalty = min(2.0, filler_count * 0.2)
    
    fluency_score = max(0, fluency_base - filler_penalty)
    return min(10, fluency_score)

def analyze_filler_words_detailed(transcript: str) -> dict:
    """Detailed analysis of filler words"""
    filler_categories = {
        'hesitation': ['um', 'uh', 'er'],
        'thinking': ['like', 'you know', 'i mean'],
        'emphasis': ['actually', 'basically', 'literally', 'really'],
        'transition': ['so', 'well', 'okay', 'right']
    }
    
    transcript_lower = transcript.lower()
    analysis = {'total': 0, 'categories': {}}
    
    for category, fillers in filler_categories.items():
        count = sum(transcript_lower.count(filler) for filler in fillers)
        analysis['categories'][category] = count
        analysis['total'] += count
    
    word_count = len(transcript.split())
    analysis['density'] = analysis['total'] / word_count if word_count > 0 else 0
    
    return analysis

def count_filler_words(transcript: str) -> int:
    """Count total filler words"""
    filler_words = ['um', 'uh', 'like', 'you know', 'so', 'actually', 'basically', 'literally', 'er', 'well', 'okay', 'right', 'i mean', 'really']
    transcript_lower = transcript.lower()
    
    count = 0
    for filler in filler_words:
        count += transcript_lower.count(filler)
    
    return count

def calculate_voice_response_score(analysis: dict) -> float:
    """Calculate overall score for voice response"""
    # Base content score
    content_score = analysis.get('overall_score', 0)
    
    # Voice-specific adjustments
    voice_confidence = analysis.get('voice_confidence', 0)
    fluency_score = analysis.get('speech_fluency_score', 0)
    clarity_score = analysis.get('voice_clarity_score', 0)
    
    # Weighted combination
    overall_score = (
        content_score * 0.4 +
        voice_confidence * 0.2 +
        fluency_score * 0.2 +
        clarity_score * 0.2
    )
    
    return min(10, max(0, overall_score))

def generate_voice_interview_feedback(session):
    """Generate comprehensive feedback for voice-enabled interview"""
    try:
        questions = session.questions.all()
        
        if not questions.exists():
            return
        
        # Calculate voice-specific scores
        voice_scores = []
        fluency_scores = []
        clarity_scores = []
        confidence_scores = []
        
        for question in questions:
            analysis = question.response_analysis
            if isinstance(analysis, dict):
                voice_scores.append(analysis.get('voice_confidence', 0))
                fluency_scores.append(analysis.get('speech_fluency_score', 0))
                clarity_scores.append(analysis.get('voice_clarity_score', 0))
                confidence_scores.append(analysis.get('confidence_level', 0))
        
        # Calculate averages
        avg_voice_score = sum(voice_scores) / len(voice_scores) if voice_scores else 0
        avg_fluency_score = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 0
        avg_clarity_score = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0
        avg_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Overall score calculation
        overall_score = (avg_voice_score + avg_fluency_score + avg_clarity_score + avg_confidence_score) / 4
        
        # Generate voice-specific insights
        voice_strengths = []
        voice_improvements = []
        
        if avg_voice_score > 7:
            voice_strengths.append("Clear voice and excellent pronunciation")
        if avg_fluency_score > 7:
            voice_strengths.append("Natural and fluent speech pattern")
        if avg_clarity_score > 7:
            voice_strengths.append("Consistent voice confidence throughout")
        
        if avg_voice_score < 5:
            voice_improvements.append("Work on speaking more clearly and with better pronunciation")
        if avg_fluency_score < 5:
            voice_improvements.append("Practice speaking at a more natural pace")
        if avg_clarity_score < 5:
            voice_improvements.append("Maintain consistent confidence in your voice")
        
        # Analyze filler word usage across all responses
        total_filler_words = 0
        total_words = 0
        
        for question in questions:
            if question.response_transcript:
                total_words += len(question.response_transcript.split())
                analysis = question.response_analysis
                if isinstance(analysis, dict) and 'filler_word_analysis' in analysis:
                    total_filler_words += analysis['filler_word_analysis'].get('total', 0)
        
        filler_density = total_filler_words / total_words if total_words > 0 else 0
        
        if filler_density > 0.1:
            voice_improvements.append("Reduce excessive use of filler words (um, uh, like)")
        elif filler_density < 0.03:
            voice_strengths.append("Minimal use of filler words, speaks confidently")
        
        # Create enhanced feedback
        detailed_feedback = f"""
        Voice Interview Feedback for {session.job_position} Position:
        
        Overall Performance: {overall_score:.1f}/10
        
        Voice & Communication Metrics:
        • Voice Clarity: {avg_voice_score:.1f}/10
        • Speech Fluency: {avg_fluency_score:.1f}/10
        • Communication Confidence: {avg_confidence_score:.1f}/10
        • Filler Word Density: {filler_density:.1%}
        
        Your voice interview demonstrated {'strong' if overall_score > 7 else 'good' if overall_score > 5 else 'developing'} communication skills with opportunities for targeted improvement.
        """
        
        # Create or update feedback with voice metrics
        feedback, created = InterviewFeedback.objects.get_or_create(
            session=session,
            defaults={
                'overall_score': overall_score,
                'strengths': voice_strengths,
                'areas_for_improvement': voice_improvements,
                'detailed_feedback': detailed_feedback,
                'communication_score': avg_clarity_score,
                'technical_score': avg_confidence_score,
                'confidence_score': avg_voice_score,
            }
        )
        
        if not created:
            # Update with voice metrics
            feedback.overall_score = overall_score
            feedback.strengths = voice_strengths
            feedback.areas_for_improvement = voice_improvements
            feedback.detailed_feedback = detailed_feedback
            feedback.communication_score = avg_clarity_score
            feedback.technical_score = avg_confidence_score
            feedback.confidence_score = avg_voice_score
            feedback.save()
        
        logger.info(f"Generated voice interview feedback for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error generating voice feedback for session {session.id}: {str(e)}")
