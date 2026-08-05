from django.urls import path

from .views import (
    AllAttendanceListView,
    AttendanceExportView,
    ExportAttendanceView,
    ExportWizardView,
    MyAttendanceListView,
    MyScheduleListView,
    QrSessionInfoView,
    SessionAttendanceListView,
    SessionStatsView,
    SessionSuspiciousAttemptsView,
    ValidateAppAttendanceView,
    ValidateAttendanceView,
    SessionReportView,
)

urlpatterns = [
    path("validate/", ValidateAttendanceView.as_view(), name="attendance-validate"),
    path(
        "validate/app/",
        ValidateAppAttendanceView.as_view(),
        name="attendance-validate-app",
    ),
    path("qr-info/", QrSessionInfoView.as_view(), name="attendance-qr-info"),
    path("my/", MyAttendanceListView.as_view(), name="attendance-my"),
    path("my-schedule/", MyScheduleListView.as_view(), name="attendance-my-schedule"),
    path("", AllAttendanceListView.as_view(), name="attendance-list"),
    path(
        "session/<int:session_id>/",
        SessionAttendanceListView.as_view(),
        name="session-attendance-list",
    ),
    path(
        "session/<int:session_id>/stats/",
        SessionStatsView.as_view(),
        name="session-attendance-stats",
    ),
    path(
        "session/<int:session_id>/suspicious/",
        SessionSuspiciousAttemptsView.as_view(),
        name="session-suspicious-attempts",
    ),
    path(
        "session/<int:session_id>/export/",
        ExportAttendanceView.as_view(),
        name="attendance-export",
    ),
    path(
        "session/<int:session_id>/report/",
        SessionReportView.as_view(),
        name="session-report",
    ),
    path("export/", AttendanceExportView.as_view(), name="attendance-export-filtered"),
    path("export-wizard/", ExportWizardView.as_view(), name="attendance-export-wizard"),
]
