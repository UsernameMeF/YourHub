from django.urls import re_path
from chat import consumers


websocket_urlpatterns = [
    re_path(r'chat/(?P<room_type>\w+)/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]