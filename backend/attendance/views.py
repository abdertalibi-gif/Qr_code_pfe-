import csv
import logging
from io import BytesIO

import openpyxl
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A3
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from courses.models import Session
from users.models import Classe, Student
from users.permissions import IsAdminOrTeacher, IsStudent, apply_role_filtering

from .models import Attendance, SuspiciousAttempt
from .serializers import (
    AttendanceSerializer,
    StudentScheduleSerializer,
    SuspiciousAttemptSerializer,
    ValidateAppAttendanceSerializer,
    ValidateAttendanceSerializer,
)
from .services import AttendanceService
from .export_service import ExportWizardService

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


def broadcast_attendance(attendance, session):
    try:
        channel_layer = get_channel_layer()
        payload = {
            "type": "attendance_update",
            "data": AttendanceSerializer(attendance).data,
        }
        async_to_sync(channel_layer.group_send)(f"attendance_{session.id}", payload)
        async_to_sync(channel_layer.group_send)("attendance_admin", payload)
        teacher_id = session.teacher_id
        if teacher_id:
            async_to_sync(channel_layer.group_send)(
                f"attendance_teacher_{teacher_id}", payload
            )
    except Exception as e:
        logger.warning(f"WebSocket broadcast failed: {e}")


class ValidateAttendanceThrottle(ScopedRateThrottle):
    scope = "validate_attendance"


class ValidateAttendanceView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ValidateAttendanceThrottle]

    def post(self, request):
        serializer = ValidateAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        try:
            attendance, session = AttendanceService.validate_attendance(
                qr_token=data["qr_token"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                code_massar=data["code_massar"],
                ip_address=ip_address,
                device_id=data.get("device_id", ""),
                device_fingerprint=data.get("device_fingerprint", ""),
                device_info=data.get("device_info", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                user_agent=user_agent,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        broadcast_attendance(attendance, session)

        return Response(
            AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED
        )


class ValidateAppAttendanceView(APIView):
    """Authenticated mobile app validation — uses linked student profile."""

    permission_classes = [IsAuthenticated, IsStudent]
    throttle_classes = [ValidateAttendanceThrottle]

    def post(self, request):
        serializer = ValidateAppAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        try:
            attendance, session = AttendanceService.validate_attendance_for_user(
                qr_token=data["qr_token"],
                user=request.user,
                ip_address=ip_address,
                device_id=data.get("device_id", ""),
                device_fingerprint=data.get("device_fingerprint", ""),
                device_info=data.get("device_info", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                user_agent=user_agent,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        broadcast_attendance(attendance, session)

        return Response(
            AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED
        )


class QrSessionInfoView(APIView):
    """Public endpoint to verify QR token validity before showing the web form."""

    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"error": "Token requis."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = Session.objects.select_related("teacher", "classe").get(
                qr_token=token
            )
        except Session.DoesNotExist:
            return Response(
                {"valid": False, "error": "Code QR invalide."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "valid": session.is_qr_valid and session.is_active,
                "expired": not session.is_qr_valid,
                "session_id": session.id,
                "subject": session.subject,
                "classe": str(session.classe),
                "teacher": session.teacher.full_name,
                "date": session.date,
                "qr_expires_at": session.qr_expires_at,
                "qr_session_id": session.qr_session_id,
                "attendance_radius_meters": session.attendance_radius_meters,
                "requires_location": session.location_latitude is not None,
            }
        )


class MyAttendanceListView(ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        user = self.request.user
        return Attendance.objects.select_related(
            "student__classe",
            "session__teacher",
            "session__classe",
        ).filter(student__user=user).order_by("-validation_time")


class MyScheduleListView(ListAPIView):
    """Emploi du temps de l'étudiant (lecture seule).

    Renvoie les séances de la classe de l'étudiant (filière / semestre /
    groupe implicites via sa classe), triées par date puis heure de début,
    avec un statut calculé (a_venir / en_cours / terminee / annulee) et
    l'indicateur qr_open (QR de présence ouvert par l'enseignant).

    Le token QR de validation n'est jamais exposé ici.
    """

    serializer_class = StudentScheduleSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        user = self.request.user
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return Session.objects.none()
        if student is None or student.classe_id is None:
            return Session.objects.none()

        qs = Session.objects.select_related(
            "module",
            "teacher",
            "classe",
            "block",
            "room",
            "amphitheater",
        ).filter(classe_id=student.classe_id)

        # Filtres optionnels (date, module) pour le confort de l'étudiant.
        date_filter = self.request.query_params.get("date")
        if date_filter:
            qs = qs.filter(date=date_filter)

        return qs.order_by("date", "start_time")


class AllAttendanceListView(ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        qs = Attendance.objects.select_related(
            "student__classe",
            "session__teacher",
            "session__classe",
        ).order_by("-validation_time")

        user = self.request.user
        if user.role == "teacher":
            qs = qs.filter(session__teacher=user)
        elif user.role == "department_head":
            qs = apply_role_filtering(qs, "attendance", self.request)
        elif user.role == "program_manager":
            qs = apply_role_filtering(qs, "attendance", self.request)

        session_id = self.request.query_params.get("session")
        classe_id = self.request.query_params.get("classe")
        if session_id:
            qs = qs.filter(session_id=session_id)
        if classe_id:
            qs = qs.filter(session__classe_id=classe_id)

        return qs

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class SessionAttendanceListView(ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        user = self.request.user

        if user.role == "teacher":
            try:
                session = Session.objects.select_related("teacher", "classe").get(
                    pk=session_id
                )
            except Session.DoesNotExist:
                return Attendance.objects.none()
            if not session.teacher_can_manage(user):
                return Attendance.objects.none()

        return Attendance.objects.select_related(
            "student__classe", "session__teacher", "session__classe"
        ).filter(session_id=session_id).order_by("-validation_time")

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class SessionSuspiciousAttemptsView(ListAPIView):
    serializer_class = SuspiciousAttemptSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        user = self.request.user

        try:
            session = Session.objects.get(pk=session_id)
        except Session.DoesNotExist:
            return SuspiciousAttempt.objects.none()

        if user.role == "teacher" and not session.teacher_can_manage(user):
            return SuspiciousAttempt.objects.none()

        return SuspiciousAttempt.objects.filter(session_id=session_id).order_by(
            "-created_at"
        )

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class SessionStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request, session_id):
        try:
            session = Session.objects.select_related("classe").get(pk=session_id)
        except Session.DoesNotExist:
            return Response(
                {"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if not session.teacher_can_manage(request.user):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        attendances = Attendance.objects.filter(session=session)
        suspicious = SuspiciousAttempt.objects.filter(session=session)
        total_students = session.classe.students.count()

        duplicate_attempts = suspicious.filter(
            attempt_type__in=[
                SuspiciousAttempt.ATTEMPT_DUPLICATE_STUDENT,
                SuspiciousAttempt.ATTEMPT_DUPLICATE_DEVICE,
            ]
        ).count()

        geofence_violations = suspicious.filter(
            attempt_type=SuspiciousAttempt.ATTEMPT_GEOFENCE
        ).count()

        devices_used = (
            attendances.exclude(device_fingerprint="")
            .values("device_fingerprint")
            .distinct()
            .count()
        )

        return Response(
            {
                "session_id": session.id,
                "subject": session.subject,
                "total_students_in_class": total_students,
                "attendance_count": attendances.count(),
                "attendance_rate": round(
                    (attendances.count() / total_students * 100)
                    if total_students
                    else 0,
                    1,
                ),
                "duplicate_attempts": duplicate_attempts,
                "geofence_violations": geofence_violations,
                "suspicious_attempts_total": suspicious.count(),
                "unique_devices": devices_used,
                "locations": [
                    {
                        "student_name": f"{a.student.first_name} {a.student.last_name}",
                        "code_massar": a.student.code_massar,
                        "latitude": a.latitude,
                        "longitude": a.longitude,
                        "validation_time": a.validation_time,
                    }
                    for a in attendances.filter(
                        latitude__isnull=False, longitude__isnull=False
                    )
                ],
            }
        )

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class ExportAttendanceView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request, session_id):
        try:
            session = Session.objects.select_related("teacher", "classe").get(
                pk=session_id
            )
        except Session.DoesNotExist:
            return Response(
                {"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if not session.teacher_can_manage(request.user):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        attendances = Attendance.objects.select_related(
            "student__classe", "session"
        ).filter(session=session)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Présence - {session.subject[:20]}"

        headers = [
            "#",
            "Prénom",
            "Nom",
            "Code Massar",
            "Classe",
            "Matière",
            "Date séance",
            "Heure validation",
            "Adresse IP",
            "Empreinte appareil",
            "Latitude",
            "Longitude",
            "Statut",
            "QR Session ID",
        ]
        ws.append(headers)

        from openpyxl.styles import Alignment, Font, PatternFill

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="1F4E79", end_color="1F4E79", fill_type="solid"
        )
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for idx, att in enumerate(attendances, start=1):
            local_time = timezone.localtime(att.validation_time)
            ws.append(
                [
                    idx,
                    att.student.first_name,
                    att.student.last_name,
                    att.student.code_massar,
                    str(att.student.classe),
                    session.subject,
                    str(session.date),
                    local_time.strftime("%Y-%m-%d %H:%M:%S"),
                    att.ip_address or "",
                    att.device_fingerprint or att.device_id or "",
                    str(att.latitude) if att.latitude is not None else "",
                    str(att.longitude) if att.longitude is not None else "",
                    att.attendance_status,
                    att.qr_session_id,
                ]
            )

        for column in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in column), default=0)
            ws.column_dimensions[column[0].column_letter].width = max_len + 4

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        safe_subject = "".join(c if c.isalnum() else "_" for c in session.subject)[:30]
        filename = f"presence_{safe_subject}_{session.date}.xlsx"
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        logger.info(
            f"Exported attendance for session {session_id} by {request.user.email}"
        )
        return response

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class SessionReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request, session_id):
        try:
            session = Session.objects.select_related("teacher", "classe").get(
                pk=session_id
            )
        except Session.DoesNotExist:
            return Response(
                {"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if not session.teacher_can_manage(request.user):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if not session.report_file:
            try:
                session.close_session()
            except Exception as e:
                return Response(
                    {"error": f"Erreur lors de la génération du rapport: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        try:
            response = HttpResponse(
                session.report_file.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            import os
            filename = os.path.basename(session.report_file.name)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {"error": f"Erreur lors du téléchargement du rapport: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


def _get_export_queryset(request):
    """Build filtered attendance queryset respecting role permissions."""
    qs = Attendance.objects.select_related(
        "student__classe__filiere",
        "student__classe__semestre",
        "session__teacher",
        "session__classe",
    )

    if request.user.role == "teacher":
        qs = qs.filter(session__teacher=request.user)
    elif request.user.role == "department_head":
        qs = apply_role_filtering(qs, "attendance", request)
    elif request.user.role == "program_manager":
        qs = apply_role_filtering(qs, "attendance", request)

    niveau = request.query_params.get("niveau")
    if niveau:
        qs = qs.filter(student__classe__niveau=niveau)

    filiere = request.query_params.get("filiere")
    if filiere:
        qs = qs.filter(student__classe__filiere__name__icontains=filiere)

    semestre = request.query_params.get("semestre")
    if semestre:
        qs = qs.filter(student__classe__semestre__name__icontains=semestre)

    module = request.query_params.get("module")
    if module:
        qs = qs.filter(session__subject__icontains=module)

    start_date = request.query_params.get("start_date")
    if start_date:
        qs = qs.filter(session__date__gte=start_date)

    end_date = request.query_params.get("end_date")
    if end_date:
        qs = qs.filter(session__date__lte=end_date)

    etudiant = request.query_params.get("etudiant")
    if etudiant:
        qs = qs.filter(
            Q(student__first_name__icontains=etudiant)
            | Q(student__last_name__icontains=etudiant)
            | Q(student__code_massar__icontains=etudiant)
            | Q(student__email__icontains=etudiant)
        )

    statut = request.query_params.get("statut")
    if statut:
        if statut == "present":
            qs = qs.filter(attendance_status=Attendance.STATUS_CONFIRMED)
        elif statut == "absent":
            qs = qs.filter(attendance_status=Attendance.STATUS_ABSENT)

    classe_id = request.query_params.get("classe_id") or request.query_params.get("classe")
    if classe_id:
        qs = qs.filter(session__classe_id=classe_id)

    enseignant_id = request.query_params.get("enseignant_id")
    if enseignant_id and request.user.role == "admin":
        qs = qs.filter(session__teacher_id=enseignant_id)

    # ID-based hierarchical filters
    filiere_id = request.query_params.get("filiere_id")
    if filiere_id:
        qs = qs.filter(student__classe__filiere_id=filiere_id)

    semestre_id = request.query_params.get("semestre_id")
    if semestre_id:
        qs = qs.filter(student__classe__semestre_id=semestre_id)

    module_id = request.query_params.get("module_id")
    if module_id:
        qs = qs.filter(session__module_id=module_id)

    department_id = request.query_params.get("department_id")
    if department_id:
        qs = qs.filter(student__classe__department_id=department_id)

    return qs


def _build_export_rows(qs):
    """Build list of dict rows from attendance queryset."""
    rows = []
    for att in qs.iterator(chunk_size=500):
        student = att.student
        session = att.session
        classe = student.classe
        location = ""
        if classe:
            if classe.location_type == "BLOC" and classe.block and classe.room:
                location = f"{classe.block.name} - {classe.room.name}"
            elif classe.location_type == "AMPHI" and classe.amphitheater:
                location = classe.amphitheater.name

        local_time = timezone.localtime(att.validation_time) if att.validation_time else None

        rows.append({
        "code_etudiant": student.code_massar,
        "nom": student.last_name,
        "prenom": student.first_name,
        "filiere": classe.filiere.name if classe and classe.filiere else "",
        "classe": str(classe) if classe else "",
        "semestre": classe.semestre.name if classe and classe.semestre else "",
        "module": session.subject,
        "enseignant": session.teacher.full_name if session.teacher else "",
        "date_seance": session.date,
        "heure_scan": local_time.strftime("%H:%M:%S") if local_time else "",
        "statut": att.attendance_status,
    })
    return rows


def _compute_stats(rows, export_request):
    """Compute statistics from exported rows."""
    total = len(rows)
    presents = sum(1 for r in rows if r["statut"] == Attendance.STATUS_CONFIRMED)
    absents = sum(1 for r in rows if r["statut"] == Attendance.STATUS_REJECTED)
    retards = 0
    excuses = 0
    taux_presence = round((presents / total * 100), 1) if total else 0
    taux_absence = round((absents / total * 100), 1) if total else 0

    params = export_request.query_params
    return {
        "total_etudiants": total,
        "presents": presents,
        "absents": absents,
        "retards": retards,
        "excuses": excuses,
        "taux_presence": taux_presence,
        "taux_absence": taux_absence,
        "periode": f"{params.get('start_date', 'Début')} → {params.get('end_date', 'Fin')}",
        "module": params.get("module", "Tous"),
        "filiere": params.get("filiere", "Toutes"),
        "semestre": params.get("semestre", "Tous"),
    }


EXPORT_HEADERS = [
    "Code Massar",
    "Nom",
    "Prénom",
    "Filière",
    "Classe",
    "Semestre",
    "Module",
    "Enseignant",
    "Date de la séance",
    "Heure du scan",
    "Statut",
]


def _export_xlsx(rows, stats):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Présences"

    from openpyxl.styles import Alignment, Font, PatternFill

    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    ws.append(EXPORT_HEADERS)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in rows:
        statut_label = "Présent" if row.get("statut") == Attendance.STATUS_CONFIRMED else "Absent"
        ws.append(
            [
                row.get("code_etudiant") or "",
                row.get("nom") or "",
                row.get("prenom") or "",
                row.get("filiere") or "",
                row.get("classe") or "",
                row.get("semestre") or "",
                row.get("module") or "",
                row.get("enseignant") or "",
                str(row.get("date_seance") or ""),
                row.get("heure_scan") or "",
                statut_label,
            ]
        )

    # Statistics section
    ws.append([])
    ws.append(["STATISTIQUES"])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=4)
    stat_header_cell = ws.cell(row=ws.max_row, column=1)
    stat_header_cell.font = Font(bold=True, size=12, color="1F4E79")

    stat_labels = [
        ("Total étudiants", stats["total_etudiants"]),
        ("Présents", stats["presents"]),
        ("Absents", stats["absents"]),
        ("Retards", stats["retards"]),
        ("Absences excusées", stats["excuses"]),
        ("Taux de présence", f"{stats['taux_presence']}%"),
        ("Taux d'absence", f"{stats['taux_absence']}%"),
        ("Période", stats["periode"]),
        ("Module", stats["module"]),
        ("Filière", stats["filiere"]),
        ("Semestre", stats["semestre"]),
    ]
    for label, value in stat_labels:
        ws.append([label, value])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

    for column in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in column), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_len + 4, 35)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _export_csv(rows, stats):
    buffer = BytesIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_HEADERS)
    for row in rows:
        writer.writerow([str(row.get(h) or "") for h in [
            "code_etudiant", "nom", "prenom",
            "filiere", "classe", "semestre", "module",
            "enseignant", "date_seance", "heure_scan",
            "statut",
        ]])
    writer.writerow([])
    writer.writerow(["STATISTIQUES"])
    stat_labels = [
        ("Total étudiants", stats["total_etudiants"]),
        ("Présents", stats["presents"]),
        ("Absents", stats["absents"]),
        ("Retards", stats["retards"]),
        ("Absences excusées", stats["excuses"]),
        ("Taux de présence", f"{stats['taux_presence']}%"),
        ("Taux d'absence", f"{stats['taux_absence']}%"),
        ("Période", stats["periode"]),
        ("Module", stats["module"]),
        ("Filière", stats["filiere"]),
        ("Semestre", stats["semestre"]),
    ]
    for label, value in stat_labels:
        writer.writerow([label, value])
    buffer.seek(0)
    return b"\xef\xbb\xbf" + buffer.read()


def _export_pdf(rows, stats):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"], fontSize=14, spaceAfter=10
    )
    normal = styles["Normal"]

    elements = []
    elements.append(Paragraph("Rapport de Présences", title_style))
    elements.append(Spacer(1, 6 * mm))

    # Data table
    table_data = [EXPORT_HEADERS]
    for row in rows:
        table_data.append([
            str(row.get(h) or "") for h in [
                "code_etudiant", "nom", "prenom",
                "filiere", "classe", "semestre", "module",
                "enseignant", "date_seance", "heure_scan",
                "statut",
            ]
        ])

    col_widths = [28 * mm, 28 * mm, 28 * mm, 30 * mm, 28 * mm, 22 * mm, 30 * mm, 30 * mm, 24 * mm, 18 * mm, 28 * mm]

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10 * mm))

    # Statistics
    elements.append(Paragraph("STATISTIQUES", ParagraphStyle(
        "StatTitle", parent=styles["Title"], fontSize=12, spaceAfter=6
    )))
    stat_data = [
        ["Total étudiants", str(stats["total_etudiants"])],
        ["Présents", str(stats["presents"])],
        ["Absents", str(stats["absents"])],
        ["Retards", str(stats["retards"])],
        ["Absences excusées", str(stats["excuses"])],
        ["Taux de présence", f"{stats['taux_presence']}%"],
        ["Taux d'absence", f"{stats['taux_absence']}%"],
        ["Période", stats["periode"]],
        ["Module", stats["module"]],
        ["Filière", stats["filiere"]],
        ["Semestre", stats["semestre"]],
    ]
    st = Table(stat_data, colWidths=[60 * mm, 80 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(st)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


class AttendanceExportView(APIView):
    """Export filtered attendance data in Excel, PDF, or CSV format."""
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request):
        export_format = request.query_params.get("format", "xlsx").lower()

        qs = _get_export_queryset(request)
        rows = _build_export_rows(qs)
        stats = _compute_stats(rows, request)

        if export_format == "csv":
            content = _export_csv(rows, stats)
            content_type = "text/csv; charset=utf-8"
            ext = "csv"
        elif export_format == "pdf":
            content = _export_pdf(rows, stats)
            content_type = "application/pdf"
            ext = "pdf"
        else:
            content = _export_xlsx(rows, stats)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"

        filename = f"rapport_presences.{ext}"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        logger.info(f"Exported attendance report ({ext}) by {request.user.email}")
        return response

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()


class ExportWizardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request):
        filters = {
            "start_date": request.query_params.get("start_date", "").strip(),
            "end_date": request.query_params.get("end_date", "").strip(),
            "semestre": request.query_params.get("semestre", "").strip(),
            "filiere": request.query_params.get("filiere", "").strip(),
            "module": request.query_params.get("module", "").strip(),
            "classe_id": request.query_params.get("classe_id", "").strip(),
            "export_type": request.query_params.get("export_type", "all").strip().lower(),
            "export_mode": request.query_params.get("export_mode", "by_student").strip().lower(),
            "enseignant_id": request.query_params.get("enseignant_id", "").strip(),
            "etudiant_id": request.query_params.get("etudiant_id", "").strip(),
            "department_id": request.query_params.get("department_id", "").strip(),
            "filiere_id": request.query_params.get("filiere_id", "").strip(),
            "semestre_id": request.query_params.get("semestre_id", "").strip(),
            "module_id": request.query_params.get("module_id", "").strip(),
            "filiere_name": request.query_params.get("filiere_name", "").strip(),
            "semestre_name": request.query_params.get("semestre_name", "").strip(),
            "module_name": request.query_params.get("module_name", "").strip(),
            "classe_name": request.query_params.get("classe_name", "").strip(),
            "enseignant_name": request.query_params.get("enseignant_name", "").strip(),
            "department_name": request.query_params.get("department_name", "").strip(),
        }

        etudiant_id = filters.get("etudiant_id")
        has_dates = bool(filters["start_date"] and filters["end_date"])
        is_professional = filters["export_mode"] == "professional"

        if etudiant_id:
            try:
                int(etudiant_id)
            except ValueError:
                return Response(
                    {"error": "L'identifiant étudiant est invalide."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not has_dates and not is_professional:
            return Response(
                {"error": "Les dates de début et de fin sont obligatoires sauf si un étudiant spécifique est sélectionné."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if filters["export_mode"] not in (
            "by_student", "by_module", "by_session",
            "resume_absences", "resume_presences",
            "professional",
        ):
            return Response(
                {"error": "Mode d'export invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if filters["export_type"] not in ("all", "present", "absent"):
            return Response(
                {"error": "Type d'export invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not filters["etudiant_id"]:
            filters.pop("etudiant_id", None)
        if not filters["start_date"]:
            filters.pop("start_date", None)
        if not filters["end_date"]:
            filters.pop("end_date", None)
        if not filters["classe_id"]:
            filters.pop("classe_id", None)
        if not filters["enseignant_id"]:
            filters.pop("enseignant_id", None)
        if not filters["department_id"]:
            filters.pop("department_id", None)
        if not filters["filiere_id"]:
            filters.pop("filiere_id", None)
        if not filters["semestre_id"]:
            filters.pop("semestre_id", None)
        if not filters["module_id"]:
            filters.pop("module_id", None)

        if request.user.role == "teacher":
            filters.pop("enseignant_id", None)

        # For department_head/program_manager, ensure enseignant_id is not used to bypass role filtering
        if request.user.role in ("department_head", "program_manager"):
            filters.pop("enseignant_id", None)

        try:
            content, filename = ExportWizardService.generate_xlsx(request, filters)
        except Exception as e:
            logger.exception(f"Export wizard failed for {request.user.email}")
            return Response(
                {"error": f"Erreur lors de la génération du fichier: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        safe_filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        logger.info(f"Export wizard successful for {request.user.email} (mode={filters['export_mode']})")
        return response

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()
