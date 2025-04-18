from django.urls import path
from .views import (
    landing_page,
    career_form,
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('career-form/', career_form, name='job_recommendations')
]