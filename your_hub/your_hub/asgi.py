import os
#important 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_hub.settings')

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from chat import routing as chat_routing
from notifications import routing as notifications_routing 

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat_routing.websocket_urlpatterns + notifications_routing.websocket_urlpatterns
            )
        )
    ),
})