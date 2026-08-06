"""WebSocket consumer for real-time student schedule updates.

When a teacher creates, modifies, or deletes a session, the signal handler
in ``student_signals`` broadcasts the change to the group
``schedule_class_{classe_id}``.  Students listening on that channel receive
the event immediately and can update their UI without polling.

Security: a student may only subscribe to the channel of *its own* class.
The connection must carry a valid JWT (``?token=...``) and the authenticated
user must be a student whose ``Classe`` matches the URL ``classe_id``.
"""

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from users.models import Student

logger = logging.getLogger(__name__)


@database_sync_to_async
def _user_from_query_string(query_string):
    """Resolve the authenticated User from a JWT in the query string."""
    params = parse_qs(query_string.decode("utf-8"))
    token = (params.get("token") or [None])[0]
    if not token:
        return None
    try:
        access_token = AccessToken(token)
        user_id = access_token["user_id"]
    except (InvalidToken, TokenError, KeyError, IndexError):
        return None
    user_model = get_user_model()
    try:
        return user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return None


@database_sync_to_async
def _student_belongs_to_class(user, classe_id):
    """True only if *user* is a student attached to the given class."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) != "student":
        return False
    try:
        student = user.student_profile
    except Student.DoesNotExist:
        return False
    if student is None or student.classe_id is None:
        return False
    return str(student.classe_id) == str(classe_id)


class StudentScheduleConsumer(AsyncWebsocketConsumer):
    """Pushes session changes to every student in a given class."""

    async def connect(self):
        self.classe_id = self.scope["url_route"]["kwargs"]["classe_id"]
        self.group_name = f"schedule_class_{self.classe_id}"

        # Authorize: JWT + student of THIS class only. Never broadcast the
        # schedule of another class to a non-member.
        query_string = self.scope.get("query_string", b"")
        user = await _user_from_query_string(query_string)
        if not await _student_belongs_to_class(user, self.classe_id):
            logger.warning(
                f"WebSocket rejected: schedule subscribe for classe {self.classe_id} "
                f"by non-member (user={getattr(user, 'id', None)})"
            )
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(
            f"Student schedule WS connected: classe_id={self.classe_id} "
            f"group={self.group_name}"
        )
        await self.send(
            text_data=json.dumps(
                {
                    "type": "schedule_ready",
                    "classe_id": self.classe_id,
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(
            f"Student schedule WS disconnected: classe_id={self.classe_id} "
            f"code={close_code}"
        )

    async def session_change(self, event):
        """Called when a Session is created, updated, or deleted."""
        await self.send(text_data=json.dumps(event))