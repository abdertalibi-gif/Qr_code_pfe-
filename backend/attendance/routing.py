from django.urls import re_path

from .consumers import AdminLiveConsumer, AttendanceConsumer, TeacherLiveConsumer

# IMPORTANT:
# scope['path'] reçu par Channels correspond au chemin de l’URL *sans* le host
# et le plus souvent sans le leading slash.
# On supporte donc les deux pour éviter un 404 de routing.
websocket_urlpatterns = [
    re_path(
        r"^/ws/attendance/live/teacher/(?P<teacher_id>\d+)/$",
        TeacherLiveConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/attendance/live/teacher/(?P<teacher_id>\d+)/$",
        TeacherLiveConsumer.as_asgi(),
    ),
    re_path(r"^/ws/attendance/live/admin/$", AdminLiveConsumer.as_asgi()),
    re_path(r"^ws/attendance/live/admin/$", AdminLiveConsumer.as_asgi()),
    re_path(
        r"^/ws/attendance/(?P<session_id>\d+)/$",
        AttendanceConsumer.as_asgi(),
    ),
    re_path(r"^ws/attendance/(?P<session_id>\d+)/$", AttendanceConsumer.as_asgi()),
]







