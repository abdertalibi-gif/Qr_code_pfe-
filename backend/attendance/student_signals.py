"""Signal handlers that push session changes to student WebSocket groups.

When a ``Session`` is created, updated, or deleted, the relevant student
class group ``schedule_class_{classe_id}`` is notified so connected students
can update their schedule UI in real time.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from courses.models import Session

logger = logging.getLogger(__name__)


def _broadcast_to_class(classe_id, payload):
    """Send *payload* to the student group for the given class."""
    if classe_id is None:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f"schedule_class_{classe_id}",
            payload,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to broadcast session change to class {classe_id}: {e}")


def _serialize_session(instance):
    """Serialize a Session for the student schedule view."""
    from attendance.serializers import StudentScheduleSerializer

    return StudentScheduleSerializer(instance).data


@receiver(post_save, sender=Session)
def session_saved(sender, instance, created, **kwargs):
    """Broadcast session create/update to the class's student group."""
    action = "created" if created else "updated"
    data = _serialize_session(instance)
    _broadcast_to_class(
        instance.classe_id,
        {
            "type": "session_change",
            "action": action,
            "data": data,
        },
    )


@receiver(post_delete, sender=Session)
def session_deleted(sender, instance, **kwargs):
    """Broadcast session deletion to the class's student group."""
    _broadcast_to_class(
        instance.classe_id,
        {
            "type": "session_change",
            "action": "deleted",
            "data": {"id": instance.id, "classe": instance.classe_id},
        },
    )
