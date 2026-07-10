"""
Root URL configuration for QR Attendance System.
"""

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import include, path, re_path
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.generic import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from users.views import (
    UserViewSet,
    StudentViewSet,
    ClasseViewSet,
    absence_statistics,
    admin_statistics,
    amphitheater_detail,
    amphitheater_list,
    app_settings,
    block_detail,
    block_list,
    department_list,
    department_detail,
    room_detail,
    room_list,
    teacher_list,
    teacher_import_excel,
    teacher_import_template,
    dashboard_counts,
    system_info,
)
from courses.views import SessionViewSet

# ---------------------------------------------------------------------------
# Swagger / ReDoc schema view
# ---------------------------------------------------------------------------
schema_view = get_schema_view(
    openapi.Info(
        title="QR Attendance API",
        default_version="v1",
        description=(
            "Production-ready REST API for a QR Code-based student attendance system.\n\n"
            "## Roles\n"
            "- **Admin** — full access (users, classes, sessions)\n"
            "- **Teacher** — manage sessions for assigned classes, generate QR codes\n"
            "- **Student** — validate attendance via scanned QR token\n\n"
            "## Authentication\n"
            "All protected endpoints require `Authorization: Bearer <access_token>`."
        ),
        terms_of_service="https://example.com/terms/",
        contact=openapi.Contact(email="admin@qrattendance.local"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


# ---------------------------------------------------------------------------
# Frontend page views — serve raw HTML files from templates/
# ---------------------------------------------------------------------------
def serve_template(filename):
    """Return a simple view that streams an HTML file from the templates/ folder."""

    def view(request):
        path_ = os.path.join(settings.BASE_DIR, "templates", filename)
        if not os.path.exists(path_):
            raise Http404(f"{filename} not found")
        f = open(path_, "rb")
        try:
            return FileResponse(f, content_type="text/html")
        except Exception:
            f.close()
            raise

    return view


def password_reset_page(request, uidb64, token):
    """Render the password reset confirmation page with token validation."""
    valid = False
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        from users.models import User
        user = User.objects.get(pk=uid)
        token_generator = PasswordResetTokenGenerator()
        valid = token_generator.check_token(user, token)
    except Exception:
        valid = False
    return render(request, "password_reset.html", {
        "uidb64": uidb64,
        "token": token,
        "valid": valid,
    })


def serve_admin_page(template_name):
    """Return a view that renders an admin Django template."""

    def view(request):
        return render(request, template_name)

    return view


def serve_js(filename):
    """Serve a JS file from the templates/ folder."""

    def view(request):
        path_ = os.path.join(settings.BASE_DIR, "templates", filename)
        if not os.path.exists(path_):
            raise Http404(f"{filename} not found")
        f = open(path_, "rb")
        try:
            return FileResponse(f, content_type="application/javascript")
        except Exception:
            f.close()
            raise

    return view


def serve_css(filename):
    """Serve a CSS file from the templates/ folder."""

    def view(request):
        path_ = os.path.join(settings.BASE_DIR, "templates", filename)
        if not os.path.exists(path_):
            raise Http404(f"{filename} not found")
        f = open(path_, "rb")
        try:
            return FileResponse(f, content_type="text/css")
        except Exception:
            f.close()
            raise

    return view


def redirect_attend_token(request, token):
    """Support /attend/TOKEN/ for basic phone QR scanners."""
    return HttpResponseRedirect(f"/attend/?token={token}")


# ---------------------------------------------------------------------------
# API v1 router
# ---------------------------------------------------------------------------
api_router = DefaultRouter()
api_router.register("users", UserViewSet, basename="user")
api_router.register("classes", ClasseViewSet, basename="classe")
api_router.register("students", StudentViewSet, basename="student")
api_router.register("sessions", SessionViewSet, basename="session")

api_v1_urlpatterns = [
    path("", include(api_router.urls)),
    path("auth/", include("users.urls")),
    path("attendance/", include("attendance.urls")),
    path("dashboard/counts/", dashboard_counts, name="dashboard-counts"),
    path("statistics/", admin_statistics, name="admin-statistics"),
    path("absence-stats/", absence_statistics, name="absence-stats"),
    path("settings/", app_settings, name="app-settings"),
    path("system-info/", system_info, name="system-info"),
    path("blocks/", block_list, name="block-list"),
    path("blocks/<int:pk>/", block_detail, name="block-detail"),
    path("rooms/", room_list, name="room-list"),
    path("rooms/<int:pk>/", room_detail, name="room-detail"),
    path("amphitheaters/", amphitheater_list, name="amphitheater-list"),
    path("amphitheaters/<int:pk>/", amphitheater_detail, name="amphitheater-detail"),
    path("teachers/", teacher_list, name="teacher-list"),
    path("teachers/import-excel/", teacher_import_excel, name="teacher-import-excel"),
    path("teachers/import-excel/template/", teacher_import_template, name="teacher-import-template"),
    path("departments/", department_list, name="department-list"),
    path("departments/<int:pk>/", department_detail, name="department-detail"),
    path("", include("curriculum.urls")),
]

# ---------------------------------------------------------------------------
# Root URL patterns
# ---------------------------------------------------------------------------
urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),
    path("login/", serve_template("login.html"), name="login-page"),
    path("password-reset/<str:uidb64>/<str:token>/", password_reset_page, name="password-reset-page"),
    path("admin-ui/", serve_template("admin.html"), name="admin-page"),

    # Admin sub-pages (independent routes)
    path("admin/attendance-live/", serve_admin_page("admin_attendance_live.html"), name="admin-attendance-live"),
    path("admin/users/", serve_admin_page("admin_users.html"), name="admin-users"),
    path("admin/teachers/", serve_admin_page("admin_teachers.html"), name="admin-teachers"),
    path("admin/students/", serve_admin_page("admin_students.html"), name="admin-students"),
    path("admin/classes/", serve_admin_page("admin_classes.html"), name="admin-classes"),
    path("admin/curriculum/", serve_admin_page("admin_curriculum.html"), name="admin-curriculum"),
    path("admin/sessions/", serve_admin_page("admin_sessions.html"), name="admin-sessions"),
    path("admin/departments/", serve_admin_page("admin_departments.html"), name="admin-departments"),
    path("admin/filieres/", serve_admin_page("admin_filieres.html"), name="admin-filieres"),
    path("admin/rooms/", serve_admin_page("admin_rooms.html"), name="admin-rooms"),
    path("admin/reports/", serve_admin_page("admin_reports.html"), name="admin-reports"),
    path("admin/statistics/", serve_admin_page("admin_statistics.html"), name="admin-statistics"),
    path("admin/settings/", serve_admin_page("admin_settings.html"), name="admin-settings"),
    path("admin/attendances/", serve_admin_page("admin_attendances.html"), name="admin-attendances"),
    path("admin/absences/", serve_admin_page("admin_absences.html"), name="admin-absences"),
    path("admin/assistants/", serve_admin_page("admin_assistants.html"), name="admin-assistants"),

    path("teacher/", serve_template("teacher.html"), name="teacher-page"),
    path("student/", serve_template("student.html"), name="student-page"),
    path("attend/", serve_template("attend.html"), name="attend-page"),
    re_path(
        r"^attend/(?P<token>[A-Za-z0-9_\-]+)/?$",
        redirect_attend_token,
        name="attend-token-redirect",
    ),
    path("api.js", serve_js("api.js"), name="api-js"),
    path("i18n-fr.js", serve_js("i18n-fr.js"), name="i18n-fr"),
    path("session-form.js", serve_js("session_form.js"), name="session-form-js"),
    path("admin-common.js", serve_js("admin-common.js"), name="admin-common-js"),
    path("admin-attendance-live.js", serve_js("admin-attendance-live.js"), name="admin-attendance-live-js"),
    path("admin-users.js", serve_js("admin-users.js"), name="admin-users-js"),
    path("admin-teachers.js", serve_js("admin-teachers.js"), name="admin-teachers-js"),
    path("admin-students.js", serve_js("admin-students.js"), name="admin-students-js"),
    path("admin-classes.js", serve_js("admin-classes.js"), name="admin-classes-js"),
    path("admin-curriculum.js", serve_js("admin-curriculum.js"), name="admin-curriculum-js"),
    path("admin-sessions.js", serve_js("admin-sessions.js"), name="admin-sessions-js"),
    path("admin-departments.js", serve_js("admin-departments.js"), name="admin-departments-js"),
    path("admin-filieres.js", serve_js("admin-filieres.js"), name="admin-filieres-js"),
    path("admin-rooms.js", serve_js("admin-rooms.js"), name="admin-rooms-js"),
    path("admin-reports.js", serve_js("admin-reports.js"), name="admin-reports-js"),
    path("admin-statistics.js", serve_js("admin-statistics.js"), name="admin-statistics-js"),
    path("admin-settings.js", serve_js("admin-settings.js"), name="admin-settings-js"),
    path("admin-attendances.js", serve_js("admin-attendances.js"), name="admin-attendances-js"),
    path("admin-absences.js", serve_js("admin-absences.js"), name="admin-absences-js"),
    path("admin-assistants.js", serve_js("admin-assistants.js"), name="admin-assistants-js"),
    path("dashboard.css", serve_css("dashboard.css"), name="dashboard-css"),
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_urlpatterns)),
    re_path(
        r"^api/docs/swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "api/docs/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/docs/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
