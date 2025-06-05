from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/agent/$', consumers.AgentConsumer.as_asgi()),
    re_path(r'ws/agent/(?P<interview_room>\w+)/$', consumers.AgentConsumer.as_asgi()),
    # Add new patterns for the interview-specific routes
    re_path(r'ws/interview/(?P<interview_room>\w+)/$', consumers.AgentConsumer.as_asgi()),
]