"""
Tests de la relation enseignant <-> département.

Scénarios couverts :
  - affichage d'un enseignant ayant déjà un département ;
  - affichage d'un enseignant sans département ;
  - affectation d'un département via le formulaire de modification (PATCH) ;
  - import Excel avec un département valide ;
  - import Excel avec un nom de département inconnu.
"""
import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from users.models import Department, User
from users.services.teacher_import import import_teachers


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _xlsx(rows) -> SimpleUploadedFile:
    wb = Workbook()
    ws = wb.active
    ws.append([
        "Prénom", "Nom", "Email", "Téléphone", "CIN",
        "Département", "Grade", "Spécialité",
    ])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return SimpleUploadedFile(
        "teachers.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class TeacherDepartmentTests(TestCase):
    def setUp(self):
        super().setUp()
        self.department = Department.objects.create(name=_unique("Département Test"))
        self.admin = User.objects.create_user(
            email=f"{_unique('admin')}@umi.ac.ma",
            password="testpass123",
            first_name="Admin",
            last_name="Test",
            role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _teacher(self, **kwargs):
        defaults = {
            "email": f"{_unique('teacher')}@umi.ac.ma",
            "password": "testpass123",
            "first_name": "Enseignant",
            "last_name": "Test",
            "role": "teacher",
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)

    def _teacher_row(self, teacher_id):
        response = self.client.get("/api/v1/teachers/")
        self.assertEqual(response.status_code, 200)
        return next(row for row in response.data if row["id"] == teacher_id)

    def test_teacher_with_department_is_displayed(self):
        teacher = self._teacher(department=self.department)

        row = self._teacher_row(teacher.id)

        self.assertEqual(row["department_id"], self.department.id)
        self.assertEqual(row["department_name"], self.department.name)

    def test_teacher_without_department_is_not_invented(self):
        teacher = self._teacher()

        row = self._teacher_row(teacher.id)
        self.assertIsNone(row["department_id"])
        self.assertIsNone(row["department_name"])

        detail = self.client.get(f"/api/v1/users/{teacher.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data["department_id"])
        self.assertIsNone(detail.data["department_name"])

    def test_department_assignment_through_edit_form(self):
        teacher = self._teacher()

        response = self.client.patch(
            f"/api/v1/users/{teacher.id}/",
            {"department_id": self.department.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        teacher.refresh_from_db()
        self.assertEqual(teacher.department_id, self.department.id)
        self.assertEqual(
            self._teacher_row(teacher.id)["department_name"],
            self.department.name,
        )

    def test_create_teacher_persists_department(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "first_name": "Nouveau",
                "last_name": "Enseignant",
                "email": f"{_unique('new')}@umi.ac.ma",
                "role": "teacher",
                "password": "testpass123",
                "department_id": self.department.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["department_id"], self.department.id)

        teacher = User.objects.get(email=response.data["email"])
        self.assertEqual(teacher.department_id, self.department.id)

    def test_import_valid_department(self):
        email = f"{_unique('import')}@umi.ac.ma"
        cin = f"CIN-{uuid.uuid4().hex[:8]}"

        report = import_teachers(_xlsx([[
            "Import", "Valide", email, "0612345678", cin,
            self.department.name, "Professeur", "Informatique",
        ]]))

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["imported"], 1)
        teacher = User.objects.get(email=email)
        self.assertEqual(teacher.department_id, self.department.id)

    def test_import_updates_existing_teacher_department(self):
        teacher = self._teacher(department=None)
        cin = f"CIN-{uuid.uuid4().hex[:8]}"

        report = import_teachers(_xlsx([[
            "Enseignant", "Existant", teacher.email, "0612345678", cin,
            self.department.name, "Professeur", "Informatique",
        ]]))

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["updated"], 1)
        teacher.refresh_from_db()
        self.assertEqual(teacher.department_id, self.department.id)

    def test_import_unknown_department_reports_explicit_error(self):
        email = f"{_unique('import-unknown')}@umi.ac.ma"
        cin = f"CIN-{uuid.uuid4().hex[:8]}"
        unknown = _unique("Département Inexistant")

        report = import_teachers(_xlsx([[
            "Import", "Inconnu", email, "0612345678", cin,
            unknown, "Professeur", "Informatique",
        ]]))

        self.assertEqual(report["imported"], 0)
        self.assertEqual(report["skipped"], 1)
        messages = [msg for error in report["errors"] for msg in error["messages"]]
        self.assertIn(f"Département introuvable : {unknown}", messages)
        self.assertFalse(User.objects.filter(email=email).exists())
