import os
import re
import secrets
from datetime import datetime, time
from io import BytesIO

from django.db import models
from django.utils import timezone


class Session(models.Model):
    """Séance de cours : matière, enseignant, classe, date."""

    LOCATION_TYPE_CHOICES = [
        ("block", "Bloc"),
        ("amphitheater", "Amphithéâtre"),
    ]

    SESSION_TYPE_CHOICES = [
        ("Cours", "Cours"),
        ("TD", "TD"),
        ("TP", "TP"),
        ("Exam", "Examen"),
        ("Other", "Autre"),
    ]

    subject = models.CharField(max_length=200, verbose_name="Matière", blank=True, default="")
    module = models.ForeignKey(
        "curriculum.Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="Module",
    )
    teacher = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="sessions",
        limit_choices_to={"role": "teacher"},
    )
    classe = models.ForeignKey(
        "users.Classe",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        default="block",
        verbose_name="Type de lieu",
    )
    block = models.ForeignKey(
        "users.Block",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="Bloc",
    )
    room = models.ForeignKey(
        "users.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="Salle",
    )
    amphitheater = models.ForeignKey(
        "users.Amphitheater",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="Amphithéâtre",
    )
    date = models.DateField()
    start_time = models.TimeField(default=time(8, 0), verbose_name="Heure de début")
    end_time = models.TimeField(default=time(18, 0), verbose_name="Heure de fin")
    qr_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    qr_session_id = models.CharField(max_length=64, blank=True, default="")
    qr_expires_at = models.DateTimeField(null=True, blank=True)
    attendance_radius_meters = models.PositiveIntegerField(default=50)
    location_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    location_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False, verbose_name="Clôturée")
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        default="cours",
        verbose_name="Type de séance",
    )
    report_file = models.FileField(
        upload_to="reports/",
        null=True,
        blank=True,
        verbose_name="Rapport Excel",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sessions"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.subject} — {self.classe} ({self.date})"

    def _session_window_bounds(self):
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(self.date, self.start_time), tz)
        end = timezone.make_aware(datetime.combine(self.date, self.end_time), tz)
        return start, end

    @property
    def is_within_session_window(self):
        now = timezone.now()
        start, end = self._session_window_bounds()
        return start <= now <= end

    @property
    def can_generate_qr(self):
        return self.is_active and self.is_within_session_window

    def generate_qr_token(
        self,
        expiry_minutes=20,
        attendance_radius_meters=50,
        latitude=None,
        longitude=None,
    ):
        from django.conf import settings

        self.qr_token = secrets.token_urlsafe(32)
        self.qr_session_id = secrets.token_urlsafe(16)
        minutes = expiry_minutes or getattr(
            settings, "QR_TOKEN_DEFAULT_EXPIRY_MINUTES", 20
        )
        self.qr_expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        self.attendance_radius_meters = attendance_radius_meters
        if latitude is not None:
            self.location_latitude = latitude
        if longitude is not None:
            self.location_longitude = longitude
        self.save(
            update_fields=[
                "qr_token",
                "qr_session_id",
                "qr_expires_at",
                "attendance_radius_meters",
                "location_latitude",
                "location_longitude",
            ]
        )

    @property
    def is_qr_valid(self):
        if not self.qr_token or not self.qr_expires_at:
            return False
        now = timezone.now()
        _, window_end = self._session_window_bounds()
        if now > window_end:
            return False
        return now < self.qr_expires_at

    def teacher_can_manage(self, user) -> bool:
        if user.role == "admin":
            return True
        if user.role != "teacher":
            return False
        if self.teacher_id == user.id:
            return True
        return self.classe_id in user.assigned_classes.values_list("pk", flat=True)

    def close_session(self):
        """
        Clôture la séance :
        1. Marque les absents (étudiants sans enregistrement de présence confirmée).
        2. Génère le fichier Excel récapitulatif.
        3. Sauvegarde le fichier et marque is_closed=True, is_active=False.
        """
        from attendance.models import Attendance
        from django.conf import settings

        # Récupérer tous les étudiants de la classe
        all_students = list(self.classe.students.all())

        # Récupérer les IDs des étudiants déjà présents (confirmed)
        present_ids = set(
            Attendance.objects.filter(
                session=self,
                attendance_status=Attendance.STATUS_CONFIRMED,
            ).values_list("student_id", flat=True)
        )

        # Créer des enregistrements "absent" pour ceux qui n'ont pas scanné
        absent_records = []
        for student in all_students:
            if student.id not in present_ids:
                # Éviter les doublons si une entrée existe déjà
                if not Attendance.objects.filter(student=student, session=self).exists():
                    absent_records.append(
                        Attendance(
                            student=student,
                            session=self,
                            attendance_status=Attendance.STATUS_ABSENT,
                        )
                    )
        if absent_records:
            Attendance.objects.bulk_create(absent_records, ignore_conflicts=True)

        # Générer le rapport Excel
        wb = self._build_report_workbook()
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Nom du fichier : Presence_<Classe>_<Module>_<Date>.xlsx
        safe = lambda s: re.sub(r'[^\w]', '_', str(s or ''))[:30]
        filename = f"Presence_{safe(self.classe)}_{safe(self.subject)}_{self.date}.xlsx"

        # Sauvegarder dans media/reports/
        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, "wb") as f:
            f.write(buffer.getvalue())

        # Mise à jour du modèle
        self.report_file = f"reports/{filename}"
        self.is_closed = True
        self.is_active = False
        self.save(update_fields=["report_file", "is_closed", "is_active"])

        return filename

    def _build_report_workbook(self):
        """Construit le classeur Excel avec présents ET absents."""
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from attendance.models import Attendance
        from django.utils import timezone

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Présence"

        # En-têtes
        headers = [
            "Code Massar", "Nom", "Prénom", "Classe",
            "Module", "Enseignant", "Date Séance", "Heure Scan", "Statut",
        ]
        ws.append(headers)

        # Style en-têtes
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        # Récupérer la map student_id -> attendance
        att_map = {
            a.student_id: a
            for a in Attendance.objects.filter(session=self).select_related("student")
        }

        teacher_name = self.teacher.full_name if self.teacher else ""
        present_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
        absent_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        for student in self.classe.students.order_by("last_name", "first_name"):
            att = att_map.get(student.id)
            if att and att.attendance_status == Attendance.STATUS_CONFIRMED:
                scan_time = timezone.localtime(att.validation_time).strftime("%H:%M:%S") if att.validation_time else ""
                statut = "Présent"
                row_fill = present_fill
            else:
                scan_time = ""
                statut = "Absent"
                row_fill = absent_fill

            row = [
                student.code_massar,
                student.last_name,
                student.first_name,
                str(self.classe),
                self.subject or "",
                teacher_name,
                str(self.date),
                scan_time,
                statut,
            ]
            ws.append(row)
            for cell in ws[ws.max_row]:
                cell.fill = row_fill

        # Ajuster largeur colonnes
        for column in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in column), default=0)
            ws.column_dimensions[column[0].column_letter].width = max_len + 4

        return wb


class SessionReport(models.Model):
    """Fichier de présence Excel stocké en base de données (si nécessaire)."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    filename = models.CharField(max_length=255)
    file_data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_reports"

    def __str__(self):
        return f"Report {self.filename} for {self.session}"

