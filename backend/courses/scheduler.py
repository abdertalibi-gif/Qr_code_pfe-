import logging
import threading
import time
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

def auto_close_sessions():
    """
    Wakes up periodically, checks for active sessions that have ended
    more than 15 minutes ago, and closes them automatically.
    """
    from courses.models import Session

    try:
        now = timezone.now()
        # Find sessions that are active and not closed
        sessions = Session.objects.filter(is_active=True, is_closed=False)
        
        for session in sessions:
            try:
                # Combine session date and end_time to form a complete datetime
                end_naive = datetime.combine(session.date, session.end_time)
                # Make it timezone-aware (using current Django timezone)
                end_dt = timezone.make_aware(end_naive, timezone.get_current_timezone())
                
                # Check if 15 minutes have passed since the end of the session
                if now >= end_dt + timedelta(minutes=15):
                    logger.info(f"Auto-closing session {session.id} ({session.subject}) which ended at {end_dt}")
                    session.close_session()
            except Exception as e:
                logger.error(f"Error auto-closing session {session.id}: {str(e)}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error in auto_close_sessions job: {str(e)}", exc_info=True)


def start_scheduler():
    """Starts the background scheduler thread."""
    def run_loop():
        # Wait a few seconds for the app to fully initialize
        time.sleep(5)
        while True:
            auto_close_sessions()
            # Wait 5 minutes before checking again
            time.sleep(300)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
