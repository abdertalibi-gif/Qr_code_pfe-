from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    name = 'attendance'

    def ready(self):
        # Connect signal handlers that push session changes to student
        # WebSocket groups in real time.
        from . import student_signals  # noqa: F401

