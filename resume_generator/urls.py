from django.urls import path
from . import views

app_name = 'resume_generator'

urlpatterns = [
    path('profiles/', views.select_profile_view, name='select_profile'),
    path('generate/', views.generate_resume_view, name='generate_resume'),
    path('download/', views.download_resume_view, name='download_resume'),
    path('preview/', views.preview_resume_view, name='preview_resume'),
    # AI-powered endpoints
    path('ai/generate/', views.generate_ai_resume_content, name='ai_generate_content'),
    path('ai/improve/', views.improve_resume_section, name='ai_improve_section'),
    path('ai/cover-letter/', views.generate_cover_letter, name='ai_cover_letter'),
    # Interview flow
    path('start-interview/', views.start_interview_from_resume, name='start_interview'),
]
