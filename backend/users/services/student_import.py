"""
Bulk student import per curriculum module.

Expected columns (French or English headers):
- Student Code (CNE / Apogée / code_massar)
- Last Name / Nom
- First Name / Prénom
- Email / E-mail
- Phone / Téléphone (optional)
"""

from __future__ import annotations

import csv
import io
import logging
import re
import secrets
import string
from dataclasses import dataclass, field
from typing import Any

from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from curriculum.models import Module
from users.constants import SINGLE_FILIERE_MESSAGE, same_filiere
from users.models import Classe, Student, StudentModuleEnrollment, User

logger = logging.getLogger(__name__)

STUDENT_EMAIL_RE = re.compile(r"^[^@\s]+@edu\.umi\.ac\.ma$")

HEADER_ALIASES = {
    "code": {
        "student code",
        "code",
        "cne",
        "apogee",
        "apogée",
        "code_massar",
        "code massar",
        "code etudiant",
        "code étudiant",
    },
    "last_name": {"last name", "nom", "lastname", "family name"},
    "first_name": {"first name", "prenom", "prénom", "firstname", "given name"},
    "email": {"email", "e-mail", "mail", "courriel"},
    "phone": {"phone", "telephone", "téléphone", "tel", "mobile", "gsm"},
}


@dataclass
class ImportRow:
    line_number: int
    code: str
    last_name: str
    first_name: str
    email: str
    phone: str = ""
    password: str = ""


@dataclass
class ImportReport:
    created: list[dict[str, Any]] = field(default_factory=list)
    updated: list[dict[str, Any]] = field(default_factory=list)
    linked: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": len(self.created),
            "updated": len(self.updated),
            "linked": len(self.linked),
            "skipped": len(self.skipped),
            "errors": self.errors,
            "summary": {
                "imported_students": len(self.created),
                "existing_students": len(self.updated) + len(self.skipped),
                "newly_enrolled": len(self.linked),
                "duplicate_enrollments_skipped": len(self.skipped),
                "errors": len(self.errors),
            },
            "created_students": self.created,
            "updated_students": self.updated,
            "linked_students": self.linked,
            "skipped_students": self.skipped,
            "imported_students": self.created,
            "existing_students": self.updated,
            "newly_enrolled": self.linked,
            "duplicate_enrollments_skipped": self.skipped,
        }


def _normalize_header(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
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
    missing = [
        key for key in ("code", "last_name", "first_name", "email") if key not in mapping
    ]
    if missing:
        labels = {
            "code": "Student Code",
            "last_name": "Last Name",
            "first_name": "First Name",
            "email": "Email",
        }
        return [f"Missing required column: {labels[key]}" for key in missing]
    return []


def _cell(row: list[Any], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    value = row[index]
    if value is None:
        return ""
    return str(value).strip()


def _is_empty_row(row: list[Any]) -> bool:
    return not any(str(cell or "").strip() for cell in row)


def _decode_csv_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _parse_rows_from_csv(content: bytes) -> tuple[list[str], list[list[str]]]:
    text = _decode_csv_text(content)
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


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


def parse_import_file(uploaded_file) -> tuple[list[str], list[list[Any]]]:
    name = (uploaded_file.name or "").lower()
    content = uploaded_file.read()
    if not content:
        raise ValueError("The uploaded file is empty.")
    if name.endswith(".csv"):
        return _parse_rows_from_csv(content)
    if name.endswith(".xlsx"):
        return _parse_rows_from_xlsx(content)
    raise ValueError("Unsupported file type. Upload a .xlsx or .csv file.")


def _validate_email_value(email: str) -> bool:
    if not email:
        return False
    if not STUDENT_EMAIL_RE.match(email):
        return False
    try:
        validate_email(email)
        return True
    except Exception:
        return False


def _build_import_rows(
    headers: list[str], data_rows: list[list[Any]]
) -> tuple[list[ImportRow], list[dict[str, Any]], list[str]]:
    mapping = _map_headers(headers)
    header_errors = _validate_headers(mapping)
    if header_errors:
        return [], [], header_errors

    parsed: list[ImportRow] = []
    errors: list[dict[str, Any]] = []
    seen_codes: dict[str, int] = {}
    seen_emails: dict[str, int] = {}

    for offset, row in enumerate(data_rows, start=2):
        if _is_empty_row(row):
            continue

        code = _cell(row, mapping["code"]).strip()
        last_name = _cell(row, mapping["last_name"]).strip()
        first_name = _cell(row, mapping["first_name"]).strip()
        email = _cell(row, mapping["email"]).strip().lower()
        phone = _cell(row, mapping.get("phone")).strip()

        row_errors: list[str] = []
        if not code:
            row_errors.append("Student Code is required.")
        if not last_name:
            row_errors.append("Last Name is required.")
        if not first_name:
            row_errors.append("First Name is required.")
        if not email:
            row_errors.append("Email is required.")
        elif not _validate_email_value(email):
            row_errors.append("Invalid email format.")

        if code:
            code_key = code.casefold()
            if code_key in seen_codes:
                row_errors.append(
                    f"Duplicate Student Code in file (first seen on line {seen_codes[code_key]})."
                )
            else:
                seen_codes[code_key] = offset

        if email and email in seen_emails:
            row_errors.append(
                f"Duplicate email in file (first seen on line {seen_emails[email]})."
            )
        elif email:
            seen_emails[email] = offset

        if row_errors:
            errors.append({"line": offset, "code": code, "messages": row_errors})
            continue

        parsed.append(
            ImportRow(
                line_number=offset,
                code=code,
                last_name=last_name,
                first_name=first_name,
                email=email,
                phone=phone,
            )
        )

    return parsed, errors, []


def _generate_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _integrity_message(exc: IntegrityError) -> str:
    """Message lisible pour une violation d'unicité d'identifiant étudiant."""
    message = str(exc).lower()
    if "uniq_student_cin" in message or "students.cin" in message:
        return "Ce CIN est déjà utilisé par un autre étudiant."
    if (
        "uniq_student_profile_email_ci" in message
        or "uniq_student_user_email_ci" in message
        or "students.email" in message
        or "users.email" in message
    ):
        return "Cette adresse email est déjà utilisée par un autre étudiant."
    if "code_massar" in message:
        return "Ce CNE (code Massar) est déjà utilisé par un autre étudiant."
    return f"Database constraint violation: {exc}"


def _student_payload(student: Student) -> dict[str, Any]:
    return {
        "id": student.id,
        "code_massar": student.code_massar,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "phone": student.phone,
        "user_id": student.user_id,
    }


def _resolve_classe_for_module(module: Module) -> Classe:
    filiere = module.filiere
    semestre = filiere.semestre
    niveau = filiere.niveau or "LIC"

    classe = (
        Classe.objects.filter(module=module).first()
        or Classe.objects.filter(
            filiere=filiere,
            semestre=semestre,
            niveau=niveau,
        )
        .order_by("academic_year", "id")
        .first()
    )
    if classe:
        return classe

    now = timezone.now()
    academic_year = f"{now.year}-{now.year + 1}"
    return Classe.objects.create(
        filiere=filiere,
        semestre=semestre,
        module=module,
        niveau=niveau,
        academic_year=academic_year,
        location_type="BLOC",
    )


def _resolve_user_for_row(
    row: ImportRow, student: Student | None
) -> tuple[User | None, list[str]]:
    """Trouve ou crée au plus un compte pour l'étudiant.

    Un étudiant déjà lié à un compte n'en reçoit jamais un second : si l'email
    du fichier diffère de celui du compte, l'import est bloqué au lieu de
    modifier l'identifiant existant.
    """
    if not row.email:
        return (student.user if student and student.user_id else None), []

    user = User.objects.filter(email__iexact=row.email).first()

    # Étudiant déjà lié à un compte : le compte est la référence.
    if student is not None and student.user_id:
        linked = student.user
        if user is not None and user.pk != linked.pk:
            return None, [
                "Cette adresse email est déjà liée à un autre compte étudiant."
            ]
        if linked.email and linked.email.strip().lower() != row.email:
            return None, [
                "L'email saisi ne correspond pas au compte de cet étudiant "
                f"(email du compte : {linked.email})."
            ]
        if not linked.email:
            linked.email = row.email
            try:
                linked.save(update_fields=["email"])
            except IntegrityError:
                return None, [
                    "Impossible d'ajouter cet email : il est déjà utilisé par un autre compte."
                ]
        return linked, []

    if user is not None:
        if user.role != "student":
            return None, [f"Email already used by a {user.role} account."]
        try:
            profile = user.student_profile
        except Student.DoesNotExist:
            profile = None
        if profile is not None and (student is None or profile.pk != student.pk):
            return None, [
                f"Email already linked to student {profile.code_massar}."
            ]
        return user, []

    # Aucun compte pour cet email : en créer un seul, rattaché à l'étudiant.
    try:
        user = User.objects.create_user(
            email=row.email,
            password=row.password or _generate_password(),
            first_name=row.first_name,
            last_name=row.last_name,
            role="student",
        )
    except IntegrityError:
        user = User.objects.filter(email__iexact=row.email).first()
        if user is None:
            return None, [
                "Impossible de créer le compte étudiant : cette adresse email est déjà utilisée."
            ]
    return user, []


def _apply_student_updates(student: Student, row: ImportRow, user: User | None) -> bool:
    changed = False
    update_fields: list[str] = []

    if row.first_name and student.first_name != row.first_name:
        student.first_name = row.first_name
        update_fields.append("first_name")
        changed = True
    if row.last_name and student.last_name != row.last_name:
        student.last_name = row.last_name
        update_fields.append("last_name")
        changed = True
    # Un email déjà renseigné est un identifiant : il n'est jamais remplacé
    # automatiquement. Seul un email manquant peut être complété.
    if row.email and not student.email:
        student.email = row.email
        update_fields.append("email")
        changed = True
    if row.phone and student.phone != row.phone:
        student.phone = row.phone
        update_fields.append("phone")
        changed = True
    if user and student.user_id != user.id:
        student.user = user
        update_fields.append("user")
        changed = True

    if changed:
        student.save(update_fields=update_fields)
    return changed


def _process_import_row(
    row: ImportRow,
    module: Module,
    classe: Classe,
    report: ImportReport,
) -> None:
    sid = transaction.savepoint()
    try:
        # Identifier l'étudiant par CNE (code Massar) ou email, sans jamais
        # fusionner deux identifiants appartenant à des étudiants différents.
        by_code = (
            Student.objects.select_related("user")
            .filter(code_massar__iexact=row.code)
            .first()
            if row.code
            else None
        )
        by_email = (
            Student.objects.select_related("user")
            .filter(email__iexact=row.email)
            .first()
            if row.email
            else None
        )

        if by_code and by_email and by_code.pk != by_email.pk:
            report.errors.append({
                "line": row.line_number,
                "code": row.code,
                "messages": [
                    "Le CNE et l'email saisis appartiennent à deux étudiants différents."
                ],
            })
            transaction.savepoint_rollback(sid)
            return

        student = by_code or by_email

        if student is not None:
            if (
                row.code
                and student.code_massar
                and student.code_massar.strip().casefold() != row.code.casefold()
            ):
                report.errors.append({
                    "line": row.line_number,
                    "code": row.code,
                    "messages": [
                        "Le CNE saisi ne correspond pas à l'étudiant existant "
                        f"(CNE actuel : {student.code_massar})."
                    ],
                })
                transaction.savepoint_rollback(sid)
                return
            if (
                row.email
                and student.email
                and student.email.strip().lower() != row.email
            ):
                report.errors.append({
                    "line": row.line_number,
                    "code": row.code,
                    "messages": [
                        "L'email saisi ne correspond pas à l'étudiant existant "
                        f"(email actuel : {student.email})."
                    ],
                })
                transaction.savepoint_rollback(sid)
                return

        user, user_errors = _resolve_user_for_row(row, student)
        if user_errors:
            report.errors.append(
                {"line": row.line_number, "code": row.code, "messages": user_errors}
            )
            transaction.savepoint_rollback(sid)
            return

        if student is None and user:
            try:
                student = user.student_profile
            except Student.DoesNotExist:
                student = None

        # Le compte a pu révéler un profil dont le CNE diffère de la ligne.
        if (
            student is not None
            and by_code is None
            and row.code
            and student.code_massar
            and student.code_massar.strip().casefold() != row.code.casefold()
        ):
            report.errors.append({
                "line": row.line_number,
                "code": row.code,
                "messages": [
                    "Le CNE saisi ne correspond pas à l'étudiant lié à ce compte "
                    f"(CNE actuel : {student.code_massar})."
                ],
            })
            transaction.savepoint_rollback(sid)
            return

        if student is None:
            student = Student.objects.create(
                code_massar=row.code,
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                phone=row.phone,
                classe=classe,
                user=user,
            )
            report.created.append(_student_payload(student))
        else:
            # Une seule filière par étudiant : les modules d'autres semestres
            # (S1 à S6) sont autorisés dans la même filière, jamais dans une
            # autre. Un refus ne modifie ni le compte ni les inscriptions.
            if (
                student.classe_id
                and student.classe.filiere_id
                and module.filiere
                and not same_filiere(student.classe.filiere, module.filiere)
            ):
                report.errors.append({
                    "line": row.line_number,
                    "code": row.code,
                    "messages": [SINGLE_FILIERE_MESSAGE],
                })
                transaction.savepoint_rollback(sid)
                return
            if student.classe_id != classe.id:
                student.classe = classe
                student.save(update_fields=["classe"])
            if _apply_student_updates(student, row, user):
                report.updated.append(_student_payload(student))

        if StudentModuleEnrollment.objects.filter(
            student=student, module=module
        ).exists():
            report.skipped.append(_student_payload(student))
        else:
            StudentModuleEnrollment.objects.create(
                student=student, module=module
            )
            report.linked.append(_student_payload(student))

        transaction.savepoint_commit(sid)
    except IntegrityError as exc:
        transaction.savepoint_rollback(sid)
        logger.warning("Import row integrity error line %s: %s", row.line_number, exc)
        report.errors.append(
            {
                "line": row.line_number,
                "code": row.code,
                "messages": [_integrity_message(exc)],
            }
        )
    except Exception as exc:
        transaction.savepoint_rollback(sid)
        logger.exception("Import row failed line %s", row.line_number)
        report.errors.append(
            {
                "line": row.line_number,
                "code": row.code,
                "messages": [str(exc)],
            }
        )


def import_students_for_module(module_id: int, uploaded_file) -> dict[str, Any]:
    try:
        module = Module.objects.select_related(
            "filiere__semestre"
        ).get(pk=module_id)
    except Module.DoesNotExist as exc:
        raise ValueError("Selected module does not exist.") from exc

    headers, data_rows = parse_import_file(uploaded_file)
    rows, row_errors, header_errors = _build_import_rows(headers, data_rows)

    report = ImportReport(errors=list(row_errors))
    if header_errors:
        for message in header_errors:
            report.errors.append({"line": 1, "code": "", "messages": [message]})
        return report.as_dict()

    if not rows:
        report.errors.append(
            {
                "line": 0,
                "code": "",
                "messages": ["No valid data rows found in the file."],
            }
        )
        return report.as_dict()

    classe = _resolve_classe_for_module(module)

    with transaction.atomic():
        for row in rows:
            _process_import_row(row, module, classe, report)

    return report.as_dict()


def build_import_template_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"

    headers = ["Student Code", "Last Name", "First Name", "Email", "Phone"]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sample_data = [
        ["M123456789", "Benali",   "Ayman",   "ayman.benali@edu.umi.ac.ma",   "0612345678"],
        ["M987654321", "Alaoui",   "Fatima",  "fatima.alaoui@edu.umi.ac.ma",  "0612345679"],
        ["M456789123", "Idrissi",  "Karim",   "karim.idrissi@edu.umi.ac.ma",  "0612345680"],
        ["M321654987", "Zahraoui", "Nadia",   "nadia.zahraoui@edu.umi.ac.ma", "0612345681"],
        ["M741852963", "El Amrani","Youssef", "youssef.elamrani@edu.umi.ac.ma","0612345682"],
        ["M852963741", "Bennani",  "Sara",    "sara.bennani@edu.umi.ac.ma",   "0612345683"],
        ["M159753456", "Tazi",     "Omar",    "omar.tazi@edu.umi.ac.ma",      "0612345684"],
        ["M357951852", "Fassi",    "Imane",   "imane.fassi@edu.umi.ac.ma",    "0612345685"],
    ]
    for row in sample_data:
        sheet.append(row)

    for column, width in zip("ABCDE", [22, 22, 22, 35, 18]):
        sheet.column_dimensions[column].width = width

    # Instructions sheet
    ws2 = workbook.create_sheet("Instructions")
    instructions = [
        "INSTRUCTIONS POUR L'IMPORT D'ÉTUDIANTS (format simple)",
        "",
        "Colonnes obligatoires :",
        "  - Student Code   (Code Massar ou CNE)",
        "  - Last Name      (Nom de famille)",
        "  - First Name     (Prénom)",
        "  - Email          (adresse email)",
        "",
        "Colonne optionnelle :",
        "  - Phone          (numéro de téléphone)",
        "",
        "Formats acceptés : .xlsx et .csv",
        "",
        "Chaque ligne sera importée dans le module sélectionné.",
        "Si un étudiant existe déjà avec le même email ou le même Code Massar,",
        "ses informations seront mises à jour sans créer de doublon.",
    ]
    for i, line in enumerate(instructions, 1):
        cell = ws2.cell(row=i, column=1, value=line)
        if i == 1:
            cell.font = Font(bold=True, size=14)

    ws2.column_dimensions["A"].width = 80

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ──────────────────────────────────────────────
#  Complete-format import (Excel only)
# ──────────────────────────────────────────────

NEW_HEADER_ALIASES: dict[str, set[str]] = {
    "nom": {"nom", "last name", "family name"},
    "prenom": {"prenom", "prénom", "first name", "given name"},
    "code_massar": {
        "code massar",
        "code_massar",
        "cne",
        "apogée",
        "apogee",
        "student code",
        "code",
    },
    "email": {"email", "e-mail", "mail", "courriel"},
    "mot_de_passe": {"mot de passe", "password", "pass"},
    "niveau": {"niveau", "level"},
    "filiere": {"filiere", "filière", "field", "filiere name"},
    "semestre": {"semestre", "semester"},
    "module": {"module", "subject", "matiere", "matière"},
}


@dataclass
class CompleteImportRow:
    line_number: int
    nom: str
    prenom: str
    code_massar: str
    email: str
    password: str
    niveau: str
    filiere: str
    semestre: str
    module: str


def _normalize_new_header(value: str) -> str:
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


def _map_new_headers(raw_headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, header in enumerate(raw_headers):
        normalized = _normalize_new_header(header)
        if not normalized:
            continue
        for field_name, aliases in NEW_HEADER_ALIASES.items():
            if normalized in aliases and field_name not in mapping:
                mapping[field_name] = index
                break
    return mapping


def _validate_new_headers(mapping: dict[str, int]) -> list[str]:
    required = ("nom", "prenom", "code_massar", "niveau", "filiere", "semestre", "module")
    missing = [key for key in required if key not in mapping]
    labels = {
        "nom": "Nom",
        "prenom": "Prénom",
        "code_massar": "Code Massar",
        "niveau": "Niveau",
        "filiere": "Filière",
        "semestre": "Semestre",
        "module": "Module",
    }
    return [f"Colonne obligatoire manquante : {labels[key]}" for key in missing]


def import_students_complete(uploaded_file) -> dict[str, Any]:
    from curriculum.models import Filiere as FiliereModel, Module as ModuleModel

    headers, data_rows = _parse_rows_from_xlsx(uploaded_file.read())
    if not headers:
        raise ValueError("Le fichier est vide ou illisible.")

    mapping = _map_new_headers(headers)
    header_errors = _validate_new_headers(mapping)
    report = ImportReport()
    if header_errors:
        report.errors.append({"line": 1, "code": "", "messages": header_errors})
        return report.as_dict()

    rows_to_process: list[CompleteImportRow] = []
    seen_codes: dict[str, str] = {}
    seen_emails: dict[str, str] = {}

    for offset, row in enumerate(data_rows, start=2):
        if _is_empty_row(row):
            continue

        nom = _cell(row, mapping.get("nom"))
        prenom = _cell(row, mapping.get("prenom"))
        code = _cell(row, mapping.get("code_massar"))
        email = _cell(row, mapping.get("email")).lower()
        password = _cell(row, mapping.get("mot_de_passe"))
        niveau = _cell(row, mapping.get("niveau")).upper()
        filiere = _cell(row, mapping.get("filiere"))
        semestre = _cell(row, mapping.get("semestre")).upper()
        module_name = _cell(row, mapping.get("module"))

        row_errors: list[str] = []
        if not nom:
            row_errors.append("Nom obligatoire.")
        if not prenom:
            row_errors.append("Prénom obligatoire.")
        if not code:
            row_errors.append("Code Massar obligatoire.")
        elif (
            code in seen_codes
            and seen_codes[code]
            and email
            and seen_codes[code] != email
        ):
            row_errors.append(
                "Code Massar déjà associé à un autre email dans ce fichier."
            )
        else:
            seen_codes.setdefault(code, email)
        if not niveau:
            row_errors.append("Niveau obligatoire.")
        if not filiere:
            row_errors.append("Filière obligatoire.")
        if not semestre:
            row_errors.append("Semestre obligatoire.")
        if not module_name:
            row_errors.append("Module obligatoire.")
        if email:
            if not _validate_email_value(email):
                row_errors.append("Email invalide. Seuls les emails @edu.umi.ac.ma sont acceptés.")
            elif (
                email in seen_emails
                and seen_emails[email]
                and code
                and seen_emails[email] != code
            ):
                row_errors.append(
                    "Email déjà associé à un autre Code Massar dans ce fichier."
                )
            else:
                seen_emails.setdefault(email, code)

        if row_errors:
            report.errors.append({"line": offset, "code": code, "messages": row_errors})
            continue

        if not password:
            password = _generate_password()

        rows_to_process.append(
            CompleteImportRow(
                line_number=offset,
                nom=nom,
                prenom=prenom,
                code_massar=code,
                email=email,
                password=password,
                niveau=niveau,
                filiere=filiere,
                semestre=semestre,
                module=module_name,
            )
        )

    if not rows_to_process:
        report.errors.append(
            {"line": 0, "code": "", "messages": ["Aucune ligne valide à importer."]}
        )
        return report.as_dict()

    module_cache: dict[tuple[str, str, str, str], ModuleModel] = {}
    for r in rows_to_process:
        key = (r.niveau, r.filiere, r.semestre, r.module)
        if key in module_cache:
            continue
        f_obj = FiliereModel.objects.filter(
            niveau=r.niveau,
            name__iexact=r.filiere,
            semestre__name__iexact=r.semestre,
        ).first()
        if f_obj is None and r.niveau:
            f_obj = FiliereModel.objects.filter(
                name__iexact=r.filiere,
                semestre__name__iexact=r.semestre,
            ).first()
        if f_obj is None:
            report.errors.append(
                {
                    "line": r.line_number,
                    "code": r.code_massar,
                    "messages": [
                        f"Filière introuvable : Niveau={r.niveau}, Filière={r.filiere}, Semestre={r.semestre}"
                    ],
                }
            )
            continue
        m_obj = ModuleModel.objects.filter(
            filiere=f_obj, name__iexact=r.module
        ).first()
        if m_obj is None:
            report.errors.append(
                {
                    "line": r.line_number,
                    "code": r.code_massar,
                    "messages": [f"Module introuvable : {r.module}"],
                }
            )
            continue
        module_cache[key] = m_obj

    with transaction.atomic():
        for r in rows_to_process:
            key = (r.niveau, r.filiere, r.semestre, r.module)
            mod = module_cache.get(key)
            if not mod:
                continue
            import_row = ImportRow(
                line_number=r.line_number,
                code=r.code_massar,
                last_name=r.nom,
                first_name=r.prenom,
                email=(r.email or "").strip().lower(),
                phone="",
                password=r.password,
            )
            classe = _resolve_classe_for_module(mod)
            _process_import_row(import_row, mod, classe, report)

    result = report.as_dict()
    result["skipped_existing"] = len(report.skipped)
    result["errors_count"] = len(report.errors)
    result["imported_students"] = report.created
    result["skipped_students"] = report.skipped
    return result


def build_complete_import_template_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Import Étudiants"

    headers = [
        "Nom", "Prénom", "Code Massar", "Email", "Mot de passe",
        "Niveau", "Filière", "Semestre", "Module",
    ]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sample_data = [
        ["Benali",   "Ayman",   "M123456789", "ayman.benali@edu.umi.ac.ma",   "Pass1234", "LIC", "Informatique",            "S3", "Java"],
        ["Alaoui",   "Fatima",  "M987654321", "fatima.alaoui@edu.umi.ac.ma",  "Pass1234", "LIC", "Informatique",            "S3", "Java"],
        ["Idrissi",  "Karim",   "M456789123", "karim.idrissi@edu.umi.ac.ma",  "Pass1234", "LIC", "Informatique",            "S3", "Python"],
        ["Zahraoui", "Nadia",   "M321654987", "nadia.zahraoui@edu.umi.ac.ma", "Pass1234", "LIC", "Mathématiques",           "S3", "Algèbre"],
        ["El Amrani","Youssef", "M741852963", "youssef.elamrani@edu.umi.ac.ma","Pass1234","LIC", "Mathématiques",           "S3", "Analyse"],
        ["Bennani",  "Sara",    "M852963741", "sara.bennani@edu.umi.ac.ma",   "Pass1234", "MAS", "Génie Logiciel",          "S1", "Architecture"],
        ["Tazi",     "Omar",    "M159753456", "omar.tazi@edu.umi.ac.ma",      "Pass1234", "MAS", "Génie Logiciel",          "S1", "UML"],
        ["Fassi",    "Imane",   "M357951852", "imane.fassi@edu.umi.ac.ma",    "Pass1234", "MAS", "Sécurité Informatique",   "S2", "Cryptographie"],
        ["Chraibi",  "Amine",   "M753159456", "amine.chraibi@edu.umi.ac.ma",  "Pass1234", "MAS", "Réseaux",                "S2", "Routage"],
    ]
    for row in sample_data:
        sheet.append(row)

    widths = [18, 18, 20, 35, 16, 10, 26, 10, 26]
    for col_letter, width in zip("ABCDEFGHI", widths):
        sheet.column_dimensions[col_letter].width = width

    # Instructions sheet
    ws2 = workbook.create_sheet("Instructions")
    instructions = [
        "INSTRUCTIONS POUR L'IMPORT COMPLET D'ÉTUDIANTS",
        "",
        "Colonnes obligatoires :",
        "  - Nom, Prénom, Code Massar, Niveau, Filière, Semestre, Module",
        "",
        "Colonnes optionnelles :",
        "  - Email (si vide, l'étudiant n'aura pas de compte email)",
        "  - Mot de passe (si vide, un mot de passe sera généré automatiquement)",
        "",
        "Format accepté : .xlsx uniquement",
        "",
        "Le système va :",
        "  1. Chercher ou créer la filière correspondante",
        "  2. Chercher ou créer le module correspondant",
        "  3. Créer ou mettre à jour l'étudiant",
        "  4. L'inscrire au module",
        "",
        "Si un étudiant existe déjà avec le même email ou Code Massar,",
        "ses informations seront mises à jour.",
    ]
    for i, line in enumerate(instructions, 1):
        cell = ws2.cell(row=i, column=1, value=line)
        if i == 1:
            cell.font = Font(bold=True, size=14)

    ws2.column_dimensions["A"].width = 80

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
