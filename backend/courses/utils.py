import logging

logger = logging.getLogger(__name__)

TEACHER_SESSION_OVERLAP_MESSAGE = (
    "Vous avez déjà une séance prévue pendant ce créneau. "
    "Terminez-la ou choisissez un autre horaire."
)


def get_teacher_conflicting_sessions(
    teacher_id,
    date,
    start_time,
    end_time,
    exclude_session_id=None,
):
    """Return not-closed sessions of ``teacher_id`` overlapping the slot.

    Overlap rule (same as room conflicts): an existing session overlaps when
    ``existing.start_time < new.end_time`` AND ``existing.end_time > new.start_time``.
    This detects any partial overlap, not only identical start times.

    Sessions already closed (``is_closed=True``) are ignored: they are finished,
    their attendance has been finalised and their report generated.
    """
    from .models import Session

    if not teacher_id or not date or not start_time or not end_time:
        return Session.objects.none()

    qs = Session.objects.filter(
        teacher_id=teacher_id,
        date=date,
        is_closed=False,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    if exclude_session_id:
        qs = qs.exclude(pk=exclude_session_id)

    return qs.order_by("start_time")


def get_conflicting_sessions(
    date,
    start_time,
    end_time,
    location_type=None,
    room_id=None,
    block_id=None,
    amphitheater_id=None,
    exclude_session_id=None,
):
    """Return queryset of sessions that conflict with the given slot."""
    from .models import Session

    if not date or not start_time or not end_time:
        return Session.objects.none()

    qs = Session.objects.filter(date=date)

    # Time overlap: existing.start < new.end AND existing.end > new.start
    qs = qs.filter(start_time__lt=end_time, end_time__gt=start_time)

    if location_type == "block":
        if room_id:
            qs = qs.filter(room_id=room_id)
        elif block_id:
            qs = qs.filter(block_id=block_id)
        else:
            return Session.objects.none()
    elif location_type == "amphitheater":
        if amphitheater_id:
            qs = qs.filter(amphitheater_id=amphitheater_id)
        else:
            return Session.objects.none()

    if exclude_session_id:
        qs = qs.exclude(id=exclude_session_id)

    return qs


def get_occupied_location_ids(date, start_time, end_time, exclude_session_id=None):
    """Return dict of occupied room_ids, block_ids, amphitheater_ids for a time slot."""
    from .models import Session

    if not date or not start_time or not end_time:
        return {"room_ids": [], "block_ids": [], "amphitheater_ids": []}

    qs = Session.objects.filter(date=date)
    qs = qs.filter(start_time__lt=end_time, end_time__gt=start_time)

    if exclude_session_id:
        qs = qs.exclude(id=exclude_session_id)

    return {
        "room_ids": list(
            qs.filter(room_id__isnull=False)
            .values_list("room_id", flat=True)
            .distinct()
        ),
        "block_ids": list(
            qs.filter(block_id__isnull=False)
            .values_list("block_id", flat=True)
            .distinct()
        ),
        "amphitheater_ids": list(
            qs.filter(amphitheater_id__isnull=False)
            .values_list("amphitheater_id", flat=True)
            .distinct()
        ),
    }
