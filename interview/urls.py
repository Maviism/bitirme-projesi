from django.urls import path

from . import views

app_name = 'interview'

urlpatterns = [
    path("", views.index, name="index"),
    path("prepare/", views.prepare_interview, name="prepare_interview"),
    path("feedback/<int:interview_id>/", views.save_feedback, name="save_feedback"),
    path("transcript/<int:interview_id>/", views.interview_transcript, name="transcript"),
    path("<str:room_name>/", views.room, name="room"),
]