from django.urls import path
from .views import (
    landing_page,
    career_form,
    submit_application,
    recommendation_results,  # Added new view
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('career-form/', career_form, name='job_recommendations'),
    path('api/submit-application/', submit_application, name='submit_application'),
    path('recommendation-results/', recommendation_results, name='recommendation_results'),  # New URL route
]