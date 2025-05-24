from django.urls import path
from . import views

app_name = 'resume_generator'

urlpatterns = [
    path('generate/', views.generate_resume_view, name='generate_resume'),
    path('download/', views.download_resume_view, name='download_resume'),
    path('preview/', views.preview_resume_view, name='preview_resume'),
    # Add other URL patterns for the resume_generator app here
]
