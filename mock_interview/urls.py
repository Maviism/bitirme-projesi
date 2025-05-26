from django.urls import path
from . import views

app_name = 'mock_interview'

urlpatterns = [
    # Main pages
    path('', views.interview_dashboard, name='dashboard'),
    path('create/', views.create_interview, name='create_interview'),
    path('room/<int:session_id>/', views.interview_room, name='interview_room'),
    path('results/<int:session_id>/', views.interview_results, name='interview_results'),
    path('history/', views.interview_history, name='interview_history'),
    
    # Original API endpoints
    path('api/start/<int:session_id>/', views.start_interview_session, name='start_session'),
    path('api/submit/<int:session_id>/', views.submit_response, name='submit_response'),
    path('api/cancel/<int:session_id>/', views.cancel_interview, name='cancel_interview'),
    path('api/question-audio/<int:question_id>/', views.get_question_audio, name='question_audio'),
    
    # Voice Interview API endpoints
    path('api/voice/start/<int:session_id>/', views.start_voice_interview, name='start_voice_interview'),
    path('api/voice/stream/<int:session_id>/', views.voice_stream_audio, name='voice_stream_audio'),
    path('api/voice/submit/<int:session_id>/', views.submit_voice_response, name='submit_voice_response'),
    path('api/voice/question-audio/<int:question_id>/', views.get_voice_question_audio, name='voice_question_audio'),
    path('api/voice/transcript/<int:session_id>/', views.get_voice_transcript, name='voice_transcript'),
]
