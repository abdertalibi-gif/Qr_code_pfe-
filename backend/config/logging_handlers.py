"""
Custom logging handlers compatible with Windows + Daphne + autoreload.

Windows cannot rename a file held open by another process.
Daphne's autoreloader spawns two processes (watcher + worker) that both
inherit the same RotatingFileHandler — rotation always fails with
PermissionError.

This handler catches the error and silently skips rotation.
"""
import logging
import os
import sys


class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that won't crash on Windows when another
    process holds the log file open.

    If os.rename() fails with PermissionError (or any OSError), the
    handler simply continues writing to the current file — rotation is
    skipped.
    """

    def doRollover(self):
        """Override: catch PermissionError during rollover on Windows."""
        if self.stream:
            self.stream.close()
            self.stream = None

        try:
            self._do_rollover()
        except OSError:
            # Windows: another process (autoreload watcher, etc.) holds
            # the file — skip rotation, keep writing to current file.
            self._report_rollover_failure()
        finally:
            if not self.stream:
                self.stream = self._open()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_rollover(self):
        """Standard RotatingFileHandler rotation logic, extracted so it
        can be wrapped in a try/except."""
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                dfn = self.rotation_filename(
                    "%s.%d" % (self.baseFilename, i + 1)
                )
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename(self.baseFilename + ".1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        else:
            sfn = self.rotation_filename(self.baseFilename)
            if os.path.exists(sfn):
                os.remove(sfn)
            self.rotate(self.baseFilename, sfn)

    def _report_rollover_failure(self):
        """Print a one-line warning to stderr (cannot use logging because
        we *are* the logger)."""
        msg = (
            f"[logging] SafeRotatingFileHandler: rotation skipped for "
            f"{self.baseFilename} (file locked by another process)\n"
        )
        sys.stderr.write(msg)
        sys.stderr.flush()
