import logging
from collections import defaultdict
from io import BytesIO

import openpyxl
from django.db.models import Q
from django.utils import timezone
from openpyxl.styles import Alignment, Font, PatternFill

from courses.models import Session
from users.models import Classe, Student
from users.permissions import apply_role_filtering

from .models import Attendance

logger = logging.getLogger(__name__)

STYLE_HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
STYLE_HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
STYLE_PRESENT_FILL = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
STYLE_ABSENT_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
STYLE_TITLE_FONT = Font(bold=True, size=12, color="1F4E79")
STYLE_BOLD = Font(bold=True)

DETAIL_HEADERS = [
    "Code Apogée",
    "Code Massar / CNE",
    "Nom",
    "Prénom",
    "Email",
    "Filière",
    "Classe",
    "Semestre",
    "Module",
    "Enseignant",
    "Date de la séance",
    "Heure de début",
    "Heure de fin",
    "Heure du scan",
    "Statut",
]

SUMMARY_HEADERS = [
    "Code Apogée",
    "Code Massar / CNE",
    "Nom",
    "Prénom",
    "Email",
    "Filière",
    "Classe",
    "Semestre",
    "Nombre total de séances",
    "Nombre de présences",
    "Nombre d'absences",
    "Taux de présence (%)",
]


class ExportWizardService:
    EXPORT_TYPE_ALL = "all"
    EXPORT_TYPE_PRESENT = "present"
    EXPORT_TYPE_ABSENT = "absent"

    EXPORT_MODE_BY_STUDENT = "by_student"
    EXPORT_MODE_BY_MODULE = "by_module"
    EXPORT_MODE_BY_SESSION = "by_session"
    EXPORT_MODE_RESUME_ABSENCES = "resume_absences"
    EXPORT_MODE_RESUME_PRESENCES = "resume_presences"

    @staticmethod
    def build_filtered_queryset(request, filters):
        qs = Attendance.objects.select_related(
            "student__classe__filiere",
            "student__classe__semestre",
            "session__teacher",
            "session__classe",
            "session__classe__filiere",
            "session__classe__semestre",
        )

        if request.user.role == "teacher":
            qs = qs.filter(session__teacher=request.user)
        elif request.user.role == "department_head":
            qs = apply_role_filtering(qs, "attendance", request)
        elif request.user.role == "program_manager":
            qs = apply_role_filtering(qs, "attendance", request)

        start_date = filters.get("start_date")
        if start_date:
            qs = qs.filter(session__date__gte=start_date)

        end_date = filters.get("end_date")
        if end_date:
            qs = qs.filter(session__date__lte=end_date)

        semestre = filters.get("semestre")
        if semestre:
            qs = qs.filter(student__classe__semestre__name__icontains=semestre)

        filiere = filters.get("filiere")
        if filiere:
            qs = qs.filter(student__classe__filiere__name__icontains=filiere)

        module = filters.get("module")
        if module:
            qs = qs.filter(session__subject__icontains=module)

        classe_id = filters.get("classe_id")
        if classe_id:
            qs = qs.filter(session__classe_id=classe_id)

        export_type = filters.get("export_type", ExportWizardService.EXPORT_TYPE_ALL)
        if export_type == ExportWizardService.EXPORT_TYPE_PRESENT:
            qs = qs.filter(attendance_status=Attendance.STATUS_CONFIRMED)
        elif export_type == ExportWizardService.EXPORT_TYPE_ABSENT:
            qs = qs.filter(attendance_status=Attendance.STATUS_ABSENT)

        enseignant_id = filters.get("enseignant_id")
        if enseignant_id and request.user.role == "admin":
            qs = qs.filter(session__teacher_id=enseignant_id)

        etudiant_id = filters.get("etudiant_id")
        if etudiant_id:
            qs = qs.filter(student_id=etudiant_id)

        return qs

    @staticmethod
    def _build_detail_rows(qs):
        rows = []
        for att in qs.iterator(chunk_size=500):
            student = att.student
            session = att.session
            classe = student.classe

            local_time = timezone.localtime(att.validation_time) if att.validation_time else None
            statut = "Présent" if att.attendance_status == Attendance.STATUS_CONFIRMED else "Absent"

            rows.append({
                "code_apogee": student.code_apogee or "",
                "code_massar": student.code_massar or "",
                "nom": student.last_name,
                "prenom": student.first_name,
                "email": student.email or "",
                "filiere": classe.filiere.name if classe and classe.filiere else "",
                "classe": str(classe) if classe else "",
                "semestre": classe.semestre.name if classe and classe.semestre else "",
                "module": session.subject,
                "enseignant": session.teacher.full_name if session.teacher else "",
                "date_seance": str(session.date),
                "heure_debut": str(session.start_time) if session.start_time else "",
                "heure_fin": str(session.end_time) if session.end_time else "",
                "heure_scan": local_time.strftime("%H:%M:%S") if local_time else "",
                "statut": statut,
                "_student_id": student.id,
                "_session_id": session.id,
                "_module_name": session.subject,
            })
        return rows

    @staticmethod
    def _build_summary_rows(qs, export_type):
        students_data = defaultdict(lambda: {
            "total": 0, "presents": 0, "absents": 0,
        })

        for att in qs.iterator(chunk_size=500):
            student = att.student
            sid = student.id
            students_data[sid]["student"] = student
            students_data[sid]["total"] += 1

            if att.attendance_status == Attendance.STATUS_CONFIRMED:
                students_data[sid]["presents"] += 1
            elif att.attendance_status == Attendance.STATUS_ABSENT:
                students_data[sid]["absents"] += 1

        rows = []
        for sid, data in students_data.items():
            student = data["student"]
            classe = student.classe
            total = data["total"]
            presents = data["presents"]
            absents = data["absents"]
            taux = round((presents / total * 100), 1) if total else 0

            rows.append({
                "code_apogee": student.code_apogee or "",
                "code_massar": student.code_massar or "",
                "nom": student.last_name,
                "prenom": student.first_name,
                "email": student.email or "",
                "filiere": classe.filiere.name if classe and classe.filiere else "",
                "classe": str(classe) if classe else "",
                "semestre": classe.semestre.name if classe and classe.semestre else "",
                "total_seances": total,
                "presents": presents,
                "absents": absents,
                "taux_presence": f"{taux}%",
            })

        if export_type == ExportWizardService.EXPORT_MODE_RESUME_ABSENCES:
            rows.sort(key=lambda r: r["absents"], reverse=True)
        else:
            rows.sort(key=lambda r: r["taux_presence"], reverse=True)

        return rows

    @staticmethod
    def _style_header_row(ws, num_cols):
        for cell in ws[1]:
            cell.font = STYLE_HEADER_FONT
            cell.fill = STYLE_HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

    @staticmethod
    def _auto_width(ws):
        for column in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in column), default=0)
            ws.column_dimensions[column[0].column_letter].width = min(max_len + 4, 40)

    @staticmethod
    def _compute_student_summary(detail_rows):
        total = len(detail_rows)
        presents = sum(1 for r in detail_rows if r["statut"] == "Présent")
        absents = total - presents
        taux = round((presents / total * 100), 1) if total else 0
        return {
            "total_seances": total,
            "presents": presents,
            "absents": absents,
            "taux_presence": f"{taux}%",
        }

    @staticmethod
    def _append_summary_to_sheet(ws, summary):
        ws.append([])
        ws.append(["RÉSUMÉ"])
        ws.cell(row=ws.max_row, column=1).font = STYLE_TITLE_FONT

        summary_headers = [
            "Nombre total de séances",
            "Nombre de présences",
            "Nombre d'absences",
            "Taux de présence (%)",
        ]
        summary_values = [
            summary["total_seances"],
            summary["presents"],
            summary["absents"],
            summary["taux_presence"],
        ]

        ws.append(summary_headers)
        for cell in ws[ws.max_row]:
            cell.font = STYLE_BOLD
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.append(summary_values)
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if summary["total_seances"] > 0:
                is_present = summary["presents"] >= summary["absents"]
                cell.fill = STYLE_PRESENT_FILL if is_present else STYLE_ABSENT_FILL

    @staticmethod
    def _generate_detail_xlsx(rows, export_mode, student_summary=None):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Présences"

        ws.append(DETAIL_HEADERS)
        ExportWizardService._style_header_row(ws, len(DETAIL_HEADERS))

        if export_mode == ExportWizardService.EXPORT_MODE_BY_STUDENT:
            rows.sort(key=lambda r: (r["nom"], r["prenom"], r["date_seance"]))
        elif export_mode == ExportWizardService.EXPORT_MODE_BY_MODULE:
            rows.sort(key=lambda r: (r["module"], r["date_seance"], r["nom"]))
        elif export_mode == ExportWizardService.EXPORT_MODE_BY_SESSION:
            rows.sort(key=lambda r: (r["date_seance"], r["module"], r["nom"]))

        for row in rows:
            ws.append([
                row["code_apogee"],
                row["code_massar"],
                row["nom"],
                row["prenom"],
                row["email"],
                row["filiere"],
                row["classe"],
                row["semestre"],
                row["module"],
                row["enseignant"],
                row["date_seance"],
                row["heure_debut"],
                row["heure_fin"],
                row["heure_scan"],
                row["statut"],
            ])
            last_row = ws.max_row
            is_present = row["statut"] == "Présent"
            for cell in ws[last_row]:
                cell.fill = STYLE_PRESENT_FILL if is_present else STYLE_ABSENT_FILL

        if student_summary:
            ExportWizardService._append_summary_to_sheet(ws, student_summary)

        ExportWizardService._auto_width(ws)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _generate_summary_xlsx(rows, export_mode):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Résumé des présences"

        ws.append(SUMMARY_HEADERS)
        ExportWizardService._style_header_row(ws, len(SUMMARY_HEADERS))

        for row in rows:
            ws.append([
                row["code_apogee"],
                row["code_massar"],
                row["nom"],
                row["prenom"],
                row["email"],
                row["filiere"],
                row["classe"],
                row["semestre"],
                row["total_seances"],
                row["presents"],
                row["absents"],
                row["taux_presence"],
            ])

        ExportWizardService._auto_width(ws)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def generate_xlsx(request, filters):
        export_mode = filters.get("export_mode", ExportWizardService.EXPORT_MODE_BY_STUDENT)
        etudiant_id = filters.get("etudiant_id")

        qs = ExportWizardService.build_filtered_queryset(request, filters)

        if export_mode in (
            ExportWizardService.EXPORT_MODE_RESUME_ABSENCES,
            ExportWizardService.EXPORT_MODE_RESUME_PRESENCES,
        ):
            rows = ExportWizardService._build_summary_rows(qs, export_mode)
            content = ExportWizardService._generate_summary_xlsx(rows, export_mode)
            filename = "resume_presences.xlsx"
        else:
            rows = ExportWizardService._build_detail_rows(qs)
            student_summary = None
            if etudiant_id:
                student_summary = ExportWizardService._compute_student_summary(rows)
            content = ExportWizardService._generate_detail_xlsx(rows, export_mode, student_summary)
            filename = "presences.xlsx"

        return content, filename
