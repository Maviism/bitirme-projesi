from django.urls import path

from . import views

app_name = 'interview'

urlpatterns = [
    path("interview/direct/", views.direct_interview, name="direct_interview"),
    path("interview/prepare/", views.prepare_interview, name="prepare_interview"),
    path("interview/<str:room_name>/", views.room, name="room"),
]