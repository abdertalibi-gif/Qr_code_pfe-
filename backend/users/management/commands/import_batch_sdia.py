"""
Management command - Importe 40 etudiants SDIA (Licence d'Excellence, S5/S6).
Usage:  python manage.py import_batch_sdia [--dry-run]
"""
from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, NIVEAU_SEMESTRE_MAP, Student, StudentModuleEnrollment, User

STUDENT_NAMES = [
    "ABDERRAZZAQ JALIL",
    "AHOUDI MAROUAN",
    "AIT OUISSAADEN ZAID",
    "AOUAD IBTISSAM",
    "BADAOUI MOHAMMED",
    "BARKHIOUI ANAS",
    "BELGUEZZAR ZAYNAB",
    "BENNIS LOUBNA",
    "BENYOUSSEF HAYTHAM",
    "BOURMA REDA",
    "DAOUDI HAFSA",
    "EDRISSI ABDELLAH",
    "EL AOUINA YASSINE",
    "EL GHORMI ANAS",
    "EL GHOU SARA",
    "EL HIOUAT RIDA",
    "EL JAMY ILHAM",
    "EL OUAFFI EL GHALIA",
    "EL OUAZZANI ISMAIL",
    "EL YAHYAOUJ BOUTAINA",
    "ELBOUNSRI NIHAL",
    "EL-MANFALOUTI OUSSAMA",
    "ESSADRAOUI ADIL",
    "HOMMAN ZINEB",
    "KACIMI MOHAMED",
    "LAMRINI ISHAK",
    "MAHJOUBI AYYOUB",
    "OUBZA FADOUA",
    "OUCHENI NOUSSAIBA",
    "OUFNINE FATIMA EZZAHRA",
    "OUHDACH ABDELLATIF",
    "RABHI HAMZA",
    "SAIDI HIBA",
    "SIBOUS HAMZA",
    "SIDID MOAAD",
    "TALIBI ABDERRAHIM",
    "TALIBI MOUAD",
    "TAZI EL HALOUANI AYA",
    "ZAID SALMA",
    "ZEROUAL FATIMA AZAHRA",
]

FILIERE_NAME = "Sciences des Donnees et Intelligence Artificielle"
NIVEAU = "LIC_EXC"
SEMESTRE_NAMES = ["S5", "S6"]
ACADEMIC_YEAR = "2025-2026"


@dataclass
class Report:
    created: list[dict] = field(default_factory=list)
    skipped_duplicates: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().rsplit(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def _slug(name: str) -> str:
    s = name.lower()
    s = s.replace("-", "").replace("'", "").replace(" ", ".")
    return s


def _generate_code(existing: set[str]) -> str:
    while True:
        code = "SDIA" + "".join(secrets.choice(string.digits) for _ in range(8))
        if code not in existing:
            return code


def _generate_email(first_name: str, last_name: str, existing: set[str]) -> str:
    base = f"{_slug(first_name)}.{_slug(last_name)}@umi.ac.ma"
    if base not in existing:
        return base
    for i in range(2, 100):
        candidate = f"{_slug(first_name)}.{_slug(last_name)}{i}@umi.ac.ma"
        if candidate not in existing:
            return candidate
    return base


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(14))


class Command(BaseCommand):
    help = "Importe 40 etudiants pour la filiere SDIA (Licence d'Excellence, S5/S6)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulation sans ecriture en base de donnees",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        report = Report()

        # -- 1. Verification / creation des semestres --
        self.stdout.write("Verification des semestres S5, S6...")
        sems: dict[str, Semestre] = {}
        for sname in SEMESTRE_NAMES:
            sem, created = Semestre.objects.get_or_create(name=sname)
            sems[sname] = sem
            if created:
                self.stdout.write(f"   [+] Semestre {sname} cree.")
            else:
                self.stdout.write(f"   [OK] Semestre {sname} existe deja.")

        # -- 2. Verification / creation de la filiere pour chaque semestre --
        self.stdout.write(f"\nVerification de la filiere << {FILIERE_NAME} >>...")
        allowed_sems = NIVEAU_SEMESTRE_MAP.get(NIVEAU, frozenset())
        filieres: dict[str, Filiere] = {}
        for sname in SEMESTRE_NAMES:
            if sname not in allowed_sems:
                report.errors.append({
                    "type": "validation",
                    "message": f"Le niveau {NIVEAU} ne permet pas le semestre {sname}.",
                })
                self.stderr.write(f"   [ERR] Semestre {sname} non autorise pour {NIVEAU}.")
                continue
            filiere = Filiere.objects.filter(name=FILIERE_NAME, semestre=sems[sname], niveau=NIVEAU).first()
            if not filiere:
                if dry_run:
                    self.stdout.write(f"   [DRY] Filiere {sname} serait creee.")
                    filieres[sname] = Filiere(name=FILIERE_NAME, semestre=sems[sname], niveau=NIVEAU)
                else:
                    filiere = Filiere.objects.create(name=FILIERE_NAME, semestre=sems[sname], niveau=NIVEAU)
                    self.stdout.write(f"   [+] Filiere {FILIERE_NAME} ({sname}) creee.")
                    filieres[sname] = filiere
            else:
                self.stdout.write(f"   [OK] Filiere {FILIERE_NAME} ({sname}) existe deja (id={filiere.id}).")
                filieres[sname] = filiere

        if not filieres:
            report.errors.append({
                "type": "fatal",
                "message": "Aucune filiere disponible. Arret.",
            })
            self.stderr.write("   [ERR] Aucune filiere trouvee/creee.")
            self._print_report(report)
            return

        # -- 3. Verification / creation des classes --
        self.stdout.write("\nVerification des classes...")
        classes: dict[str, Classe] = {}
        for sname, filiere in filieres.items():
            classe = Classe.objects.filter(
                filiere=filiere, semestre=sems[sname], niveau=NIVEAU,
                academic_year=ACADEMIC_YEAR,
            ).first()
            if not classe:
                if dry_run:
                    self.stdout.write(f"   [DRY] Classe {sname} serait creee.")
                    classe = Classe(
                        filiere=filiere, semestre=sems[sname], niveau=NIVEAU,
                        academic_year=ACADEMIC_YEAR, location_type="BLOC",
                    )
                else:
                    classe = Classe.objects.create(
                        filiere=filiere, semestre=sems[sname], niveau=NIVEAU,
                        academic_year=ACADEMIC_YEAR, location_type="BLOC",
                    )
                    self.stdout.write(f"   [+] Classe {classe.name} creee.")
                classes[sname] = classe
            else:
                self.stdout.write(f"   [OK] Classe {classe.name} existe deja (id={classe.id}).")
                classes[sname] = classe

        # -- 4. Collecter les codes et emails existants --
        existing_codes: set[str] = set(
            Student.objects.values_list("code_massar", flat=True)
        )
        existing_emails: set[str] = set(
            Student.objects.values_list("email", flat=True)
        )
        existing_emails.update(
            User.objects.values_list("email", flat=True)
        )
        existing_emails.discard("")

        # -- 5. Preparer les etudiants --
        self.stdout.write(f"\nPreparation de {len(STUDENT_NAMES)} etudiants...")

        student_data: list[dict] = []
        sem_names = sorted(classes.keys())
        if not sem_names:
            report.errors.append({
                "type": "fatal",
                "message": "Aucune classe disponible. Arret.",
            })
            self._print_report(report)
            return

        for idx, full_name in enumerate(STUDENT_NAMES):
            last_name, first_name = _split_name(full_name)
            if not first_name:
                report.errors.append({
                    "type": "parse",
                    "line": idx + 1,
                    "name": full_name,
                    "message": "Impossible d'extraire le prenom et le nom.",
                })
                continue

            code_massar = _generate_code(existing_codes)
            email = _generate_email(first_name, last_name, existing_emails)
            password = _generate_password()
            classe = classes[sem_names[idx % len(sem_names)]]

            existing_codes.add(code_massar)
            existing_emails.add(email)

            student_data.append({
                "last_name": last_name,
                "first_name": first_name,
                "code_massar": code_massar,
                "email": email,
                "password": password,
                "classe": classe,
                "semestre_name": classe.semestre.name,
            })

        self.stdout.write(f"   [OK] {len(student_data)} etudiants prepares.")

        # -- 6. Verification des doublons (securite) --
        codes_in_batch = [s["code_massar"] for s in student_data]
        emails_in_batch = [s["email"] for s in student_data]

        codes_in_db = set(
            Student.objects.filter(code_massar__in=codes_in_batch)
            .values_list("code_massar", flat=True)
        )
        emails_in_db = set(
            Student.objects.filter(email__in=emails_in_batch)
            .values_list("email", flat=True)
        )
        emails_in_users = set(
            User.objects.filter(email__in=emails_in_batch)
            .values_list("email", flat=True)
        )

        final_data = []
        for s in student_data:
            if s["code_massar"] in codes_in_db:
                report.skipped_duplicates.append({**s, "reason": "code_massar existe deja en BD"})
                continue
            if s["email"] in emails_in_db or s["email"] in emails_in_users:
                report.skipped_duplicates.append({**s, "reason": "email existe deja en BD"})
                continue
            final_data.append(s)

        # -- 7. Insertion atomique --
        if dry_run:
            self.stdout.write("\n[DRY-RUN] Aucune ecriture effectuee.")
            for s in final_data:
                report.created.append({
                    "first_name": s["first_name"],
                    "last_name": s["last_name"],
                    "code_massar": s["code_massar"],
                    "email": s["email"],
                    "password": s["password"],
                    "classe": str(s["classe"]),
                    "semestre": s["semestre_name"],
                })
            self._print_report(report)
            return

        self.stdout.write("\nInsertion atomique...")
        with transaction.atomic():
            for s in final_data:
                try:
                    user = User.objects.create_user(
                        email=s["email"],
                        password=s["password"],
                        first_name=s["first_name"],
                        last_name=s["last_name"],
                        role="student",
                        is_active=True,
                    )
                    student = Student.objects.create(
                        user=user,
                        first_name=s["first_name"],
                        last_name=s["last_name"],
                        code_massar=s["code_massar"],
                        email=s["email"],
                        classe=s["classe"],
                    )
                    report.created.append({
                        "id": student.id,
                        "user_id": user.id,
                        "first_name": s["first_name"],
                        "last_name": s["last_name"],
                        "code_massar": s["code_massar"],
                        "email": s["email"],
                        "password": s["password"],
                        "classe": str(s["classe"]),
                        "semestre": s["semestre_name"],
                    })
                except Exception as exc:
                    report.errors.append({
                        "type": "insert",
                        "name": f"{s['first_name']} {s['last_name']}",
                        "code_massar": s["code_massar"],
                        "message": str(exc),
                    })
                    raise

        self._print_report(report)

    def _print_report(self, report: Report) -> None:
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RAPPORT D'IMPORTATION")
        self.stdout.write("=" * 60)
        self.stdout.write(f"   Creess :              {len(report.created)}")
        self.stdout.write(f"   Doublons ignores :    {len(report.skipped_duplicates)}")
        self.stdout.write(f"   Erreurs :             {len(report.errors)}")
        self.stdout.write("-" * 60)

        if report.created:
            self.stdout.write("\nEtudiants crees :")
            for s in report.created:
                self.stdout.write(
                    f"   * {s['first_name']} {s['last_name']}  |  "
                    f"Code: {s['code_massar']}  |  "
                    f"Email: {s['email']}  |  "
                    f"Pass: {s['password']}  |  "
                    f"Classe: {s['classe']}"
                )

        if report.skipped_duplicates:
            self.stdout.write("\nDoublons ignores :")
            for s in report.skipped_duplicates:
                self.stdout.write(
                    f"   * {s['first_name']} {s['last_name']} "
                    f"({s.get('reason', '')})"
                )

        if report.errors:
            self.stdout.write("\nErreurs :")
            for e in report.errors:
                self.stdout.write(f"   * {e.get('message', '')}")
                if "name" in e:
                    self.stdout.write(f"     -> {e['name']} ({e.get('code_massar', '')})")

        self.stdout.write("=" * 60)
