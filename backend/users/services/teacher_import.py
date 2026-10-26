"""
Bulk teacher import from Excel (.xlsx).

Expected columns:
  first_name, last_name, email, phone, cin, department, grade, speciality
Optional:
  password
"""
from __future__ import annotations

import io
import logging
import re
import secrets
import string
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from users.models import Department, User

logger = logging.getLogger(__name__)

EMAIL_UMI_RE = re.compile(r"^[^@\s]+@umi\.ac\.ma$")
EMAIL_GENERIC_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

HEADER_ALIASES = {
    "first_name": {"first name", "first_name", "prenom", "prénom", "given name", "firstname"},
    "last_name": {"last name", "last_name", "nom", "family name", "lastname"},
    "email": {"email", "e-mail", "mail", "courriel"},
    "phone": {"phone", "telephone", "téléphone", "tel", "mobile", "gsm"},
    "cin": {"cin", "c.i.n", "carte nationale", "identity"},
    "department": {"department", "departement", "département", "dept"},
    "grade": {"grade", "rank"},
    "speciality": {"speciality", "specialty", "specialite", "spécialité", "field of study"},
    "password": {"password", "mot de passe", "pass"},
}


@dataclass
class TeacherImportRow:
    line_number: int
    first_name: str
    last_name: str
    email: str
    phone: str
    cin: str
    department: str
    grade: str
    speciality: str
    password: str


@dataclass
class ImportReport:
    created: list[dict[str, Any]] = field(default_factory=list)
    updated: list[dict[str, Any]] = field(default_factory=list)
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "imported": len(self.created),
            "updated": len(self.updated),
            "skipped": self.skipped,
            "errors": self.errors,
            "created_teachers": self.created,
            "updated_teachers": self.updated,
            "summary": {
                "created": len(self.created),
                "updated": len(self.updated),
                "skipped": self.skipped,
                "errors": len(self.errors),
            },
        }


def _normalize_header(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
    )


def _map_headers(raw_headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, header in enumerate(raw_headers):
        normalized = _normalize_header(header)
        if not normalized:
            continue
        for field_name, aliases in HEADER_ALIASES.items():
            if normalized in aliases and field_name not in mapping:
                mapping[field_name] = index
                break
    return mapping


def _validate_headers(mapping: dict[str, int]) -> list[str]:
    required = ("first_name", "last_name", "email", "phone", "cin", "department", "grade", "speciality")
    labels = {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "phone": "phone",
        "cin": "cin",
        "department": "department",
        "grade": "grade",
        "speciality": "speciality",
    }
    missing = [f"Colonne obligatoire manquante : {labels[key]}" for key in required if key not in mapping]
    return missing


def _cell(row: list[Any], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    value = row[index]
    if value is None:
        return ""
    return str(value).strip()


def _is_empty_row(row: list[Any]) -> bool:
    return not any(str(cell or "").strip() for cell in row)


def _parse_rows_from_xlsx(content: bytes) -> tuple[list[str], list[list[Any]]]:
    from openpyxl import load_workbook

    workbook = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        return [], []
    headers = [str(cell or "").strip() for cell in rows[0]]
    return headers, [list(row) for row in rows[1:]]


def _validate_email_umi(email: str) -> bool:
    if not email:
        return False
    if not EMAIL_UMI_RE.match(email):
        return False
    try:
        validate_email(email)
        return True
    except Exception:
        return False


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def import_teachers(uploaded_file) -> dict[str, Any]:
    content = uploaded_file.read()
    if not content:
        raise ValueError("Le fichier est vide.")

    if not uploaded_file.name.lower().endswith(".xlsx"):
        raise ValueError("Seul le format .xlsx est accepté.")

    headers, data_rows = _parse_rows_from_xlsx(content)
    if not headers:
        raise ValueError("Le fichier est vide ou illisible.")

    mapping = _map_headers(headers)
    header_errors = _validate_headers(mapping)
    report = ImportReport()
    if header_errors:
        report.errors.append({"line": 1, "code": "", "messages": header_errors})
        return report.as_dict()

    rows_to_process: list[TeacherImportRow] = []
    seen_emails: dict[str, int] = {}
    seen_cins: dict[str, int] = {}

    for offset, row in enumerate(data_rows, start=2):
        if _is_empty_row(row):
            continue

        first_name = _cell(row, mapping.get("first_name"))
        last_name = _cell(row, mapping.get("last_name"))
        email = _cell(row, mapping.get("email")).lower()
        phone = _cell(row, mapping.get("phone"))
        cin = _cell(row, mapping.get("cin"))
        department_name = _cell(row, mapping.get("department"))
        grade = _cell(row, mapping.get("grade"))
        speciality = _cell(row, mapping.get("speciality"))
        password = _cell(row, mapping.get("password"))

        row_errors: list[str] = []

        # Required fields
        if not first_name:
            row_errors.append("Prénom obligatoire.")
        if not last_name:
            row_errors.append("Nom obligatoire.")
        if not email:
            row_errors.append("Email obligatoire.")
        elif not _validate_email_umi(email):
            row_errors.append("Email invalide. Seuls les emails @umi.ac.ma sont acceptés.")
        elif email in seen_emails:
            row_errors.append(f"Email en double dans le fichier (ligne {seen_emails[email]}).")
        else:
            seen_emails[email] = offset
        if not phone:
            row_errors.append("Téléphone obligatoire.")
        if not cin:
            row_errors.append("CIN obligatoire.")
        elif cin in seen_cins:
            row_errors.append(f"CIN en double dans le fichier (ligne {seen_cins[cin]}).")
        else:
            seen_cins[cin] = offset
        if not department_name:
            row_errors.append("Département obligatoire.")
        if not grade:
            row_errors.append("Grade obligatoire.")
        if not speciality:
            row_errors.append("Spécialité obligatoire.")

        if row_errors:
            report.errors.append({"line": offset, "email": email, "messages": row_errors})
            continue

        rows_to_process.append(TeacherImportRow(
            line_number=offset,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            cin=cin,
            department=department_name,
            grade=grade,
            speciality=speciality,
            password=password or _generate_password(),
        ))

    if not rows_to_process:
        report.errors.append({"line": 0, "email": "", "messages": ["Aucune ligne valide à importer."]})
        return report.as_dict()

    # Normalize a string for case-insensitive, accent-insensitive matching
    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()

    # Preload departments in memory (avoids per-row DB queries)
    dept_map: dict[str, Department] = {}
    for dept in Department.objects.all():
        dept_map[_norm(dept.name)] = dept

    # Preload existing users by email
    emails_to_check = [r.email for r in rows_to_process]
    existing_users_map: dict[str, User] = {}
    for u in User.objects.filter(email__in=emails_to_check).only(
        "id", "email", "first_name", "last_name", "phone", "cin",
        "grade", "speciality", "role", "department"
    ):
        existing_users_map[u.email.lower()] = u

    # Batch processing: collect creates and updates
    new_users: list[User] = []
    updated_users: list[tuple[User, list[str]]] = []

    for r in rows_to_process:
        dept = dept_map.get(_norm(r.department))
        if dept is None:
            report.errors.append({
                "line": r.line_number,
                "email": r.email,
                "messages": [f"Département introuvable : {r.department}"],
            })
            report.skipped += 1
            continue

        existing_user = existing_users_map.get(r.email.lower())
        if existing_user:
            changed = False
            update_fields = []
            for attr, val in [
                ("first_name", r.first_name),
                ("last_name", r.last_name),
                ("phone", r.phone),
                ("grade", r.grade),
                ("speciality", r.speciality),
            ]:
                if val and getattr(existing_user, attr, None) != val:
                    setattr(existing_user, attr, val)
                    update_fields.append(attr)
                    changed = True

            if r.cin and not existing_user.cin:
                existing_user.cin = r.cin
                update_fields.append("cin")
                changed = True
            elif r.cin and existing_user.cin and existing_user.cin != r.cin:
                existing_user.cin = r.cin
                update_fields.append("cin")
                changed = True

            if existing_user.role != "teacher":
                existing_user.role = "teacher"
                update_fields.append("role")
                changed = True

            if existing_user.department_id != dept.id:
                existing_user.department = dept
                update_fields.append("department")
                changed = True

            if changed:
                updated_users.append((existing_user, update_fields))

            report.updated.append({
                "id": existing_user.id,
                "email": existing_user.email,
                "first_name": existing_user.first_name,
                "last_name": existing_user.last_name,
                "cin": existing_user.cin,
                "updated_fields": update_fields if changed else [],
            })
        else:
            new_user = User(
                email=r.email,
                first_name=r.first_name,
                last_name=r.last_name,
                role="teacher",
                phone=r.phone,
                cin=r.cin,
                department=dept,
                grade=r.grade,
                speciality=r.speciality,
                is_active=True,
            )
            from django.contrib.auth.hashers import make_password
            new_user.password = make_password(r.password, hasher="md5")
            new_users.append(new_user)

    # Perform all DB writes in a single transaction with minimal queries
    with transaction.atomic():
        try:
            if new_users:
                User.objects.bulk_create(new_users, ignore_conflicts=True)
                # Re-fetch created users to get their IDs
                created_emails = [u.email for u in new_users]
                created_in_db = User.objects.filter(email__in=created_emails).values(
                    "id", "email", "first_name", "last_name", "cin"
                )
                for u in created_in_db:
                    report.created.append({
                        "id": u["id"],
                        "email": u["email"],
                        "first_name": u["first_name"],
                        "last_name": u["last_name"],
                        "cin": u["cin"] or "",
                    })

            # Bulk update existing users
            for user, fields in updated_users:
                user.save(update_fields=fields)

        except IntegrityError as exc:
            logger.warning("Teacher import integrity error: %s", exc)
            report.errors.append({
                "line": 0,
                "email": "",
                "messages": [f"Erreur base de données : {exc}"],
            })
        except Exception as exc:
            logger.exception("Teacher import failed during batch write")
            report.errors.append({
                "line": 0,
                "email": "",
                "messages": [str(exc)],
            })

    # NB: les classes ne sont PAS auto-assignées lors de l'import.
    # L'affectation est exclusivement gérée par l'administrateur via
    # assigned_class_ids (user_detail / admin UI), afin qu'un enseignant
    # ne voie jamais des classes qui ne lui ont pas été explicitement confiées.

    return report.as_dict()


def build_teacher_import_template_xlsx() -> bytes:
    """Generate an Excel template for teacher import."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "Modèle Import Enseignants"

    headers = [
        "Prénom", "Nom", "Email", "Téléphone", "CIN",
        "Département", "Grade", "Spécialité",
        "Mot de passe (optionnel)"
    ]

    # Header row
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Example row
    example = [
        "Jean", "Dupont", "jean.dupont@umi.ac.ma", "0612345678", "EE123456",
        "Informatique", "Professeur", "Intelligence Artificielle",
        "Pass@12345"
    ]
    for col, val in enumerate(example, 1):
        ws.cell(row=2, column=col, value=val)

    # Set column widths
    widths = [15, 15, 30, 15, 15, 20, 15, 25, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    # Instructions sheet
    ws2 = wb.create_sheet("Instructions")
    instructions = [
        "INSTRUCTIONS POUR L'IMPORT D'ENSEIGNANTS",
        "",
        "Colonnes obligatoires :",
        "  - Prénom",
        "  - Nom",
        "  - Email (format @umi.ac.ma)",
        "  - Téléphone",
        "  - CIN",
        "  - Département (nom exact)",
        "  - Grade",
        "  - Spécialité",
        "",
        "Colonnes optionnelles :",
        "  - Mot de passe (généré automatiquement si vide)",
        "",
        "Règles :",
        "  - Le département et la filière doivent exister dans la base",
        "  - L'email doit être unique et au format @umi.ac.ma",
        "  - Le CIN doit être unique",
        "  - Un enseignant existant (même email) sera mis à jour",
        "",
        "Format : Excel .xlsx uniquement"
    ]
    for row, line in enumerate(instructions, 1):
        ws2.cell(row=row, column=1, value=line)

    import io
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
