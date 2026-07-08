"""
ASGI config for QR Attendance System.

Supports both HTTP (Django) and WebSocket (Django Channels) connections.
"""

import os
import logging

logger = logging.getLogger(__name__)

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

from attendance.routing import websocket_urlpatterns  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

logger.info(f"ASGI application loaded with websocket_urlpatterns: {websocket_urlpatterns}")

application = ProtocolTypeRouter(
    {
        # Standard Django HTTP requests
        "http": django_asgi_app,
        # WebSocket connections (with auth middleware)
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)



