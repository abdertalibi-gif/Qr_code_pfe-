import os
from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "courses"

    def ready(self):
        import sys
        # Only start scheduler if we are running runserver
        if "runserver" in sys.argv:
            # Django auto-reloader spawns a child process. Only start in the child (RUN_MAIN=true) or if noreload is set.
            if os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv:
                from .scheduler import start_scheduler
                start_scheduler()

