from django.urls import path
from .views import (
    landing_page,
    career_form,
    submit_application,
    recommendation_results,  # Added new view
    # AI-powered views
    analyze_job_compatibility,
    get_ai_job_recommendations,
    get_career_advice,
    get_skill_gap_analysis,
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('career-form/', career_form, name='job_recommendations'),
    path('api/submit-application/', submit_application, name='submit_application'),
    path('recommendation-results/', recommendation_results, name='recommendation_results'),  # New URL route
    # AI-powered endpoints
    path('api/analyze-compatibility/', analyze_job_compatibility, name='analyze_job_compatibility'),
    path('api/ai-recommendations/', get_ai_job_recommendations, name='ai_job_recommendations'),
    path('api/career-advice/', get_career_advice, name='career_advice'),
    path('api/skill-gap-analysis/', get_skill_gap_analysis, name='skill_gap_analysis'),
]