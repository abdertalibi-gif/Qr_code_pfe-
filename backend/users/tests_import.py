import io

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, Student, StudentModuleEnrollment
from users.services.student_import import import_students_for_module

User = get_user_model()


class StudentImportServiceTests(TestCase):
    def setUp(self):
        self.semestre = Semestre.objects.create(name="S1")
        self.filiere = Filiere.objects.create(
            name="L1 Info", semestre=self.semestre, niveau="LIC"
        )
        self.module = Module.objects.create(name="Algorithmique", filiere=self.filiere)
        self.classe = Classe.objects.create(
            name="Groupe A",
            niveau="LIC",
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            academic_year="2025-2026",
        )

    def _csv_file(self, content: str, name="students.csv"):
        buffer = io.BytesIO(content.encode("utf-8"))
        buffer.name = name
        return buffer

    def test_import_creates_students_users_and_enrollments(self):
        csv_content = (
            "Student Code,Last Name,First Name,Email,Phone\n"
            "CNE001,Benali,Ayman,ayman@test.ma,0611111111\n"
            "CNE002,Alami,Sara,sara@test.ma,\n"
        )
        report = import_students_for_module(self.module.id, self._csv_file(csv_content))

        self.assertEqual(report["created"], 2)
        self.assertEqual(report["linked"], 2)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(User.objects.filter(role="student").count(), 2)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(module=self.module).count(), 2
        )

    def test_import_is_idempotent(self):
        csv_content = (
            "Student Code,Last Name,First Name,Email\n"
            "CNE001,Benali,Ayman,ayman@test.ma\n"
        )
        first = import_students_for_module(self.module.id, self._csv_file(csv_content))
        second = import_students_for_module(self.module.id, self._csv_file(csv_content))

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(module=self.module).count(), 1
        )

    def test_import_reuses_existing_student_without_duplicate_enrollment(self):
        user = User.objects.create_user(
            email="ayman@test.ma",
            password="Pass12345!",
            first_name="Ayman",
            last_name="Benali",
            role="student",
        )
        student = Student.objects.create(
            user=user,
            code_massar="CNE001",
            first_name="Ayman",
            last_name="Benali",
            email="ayman@test.ma",
            classe=self.classe,
        )
        StudentModuleEnrollment.objects.create(student=student, module=self.module)

        csv_content = (
            "Student Code,Last Name,First Name,Email\n"
            "CNE001,Benali,Ayman,ayman@test.ma\n"
            "CNE003,Idrissi,Hamza,hamza@test.ma\n"
        )
        report = import_students_for_module(self.module.id, self._csv_file(csv_content))

        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["created"], 1)
        self.assertEqual(report["linked"], 1)
        self.assertEqual(Student.objects.count(), 2)

    def test_import_reports_invalid_email_and_duplicate_codes(self):
        csv_content = (
            "Student Code,Last Name,First Name,Email\n"
            "CNE001,Benali,Ayman,not-an-email\n"
            "CNE001,Other,User,valid@test.ma\n"
        )
        report = import_students_for_module(self.module.id, self._csv_file(csv_content))

        self.assertGreaterEqual(len(report["errors"]), 2)
        self.assertEqual(Student.objects.count(), 0)

    def test_import_rejects_email_linked_to_other_student(self):
        user = User.objects.create_user(
            email="shared@test.ma",
            password="Pass12345!",
            first_name="Other",
            last_name="Student",
            role="student",
        )
        Student.objects.create(
            user=user,
            code_massar="CNE999",
            first_name="Other",
            last_name="Student",
            email="shared@test.ma",
            classe=self.classe,
        )

        csv_content = (
            "Student Code,Last Name,First Name,Email\n"
            "CNE001,Benali,Ayman,shared@test.ma\n"
        )
        report = import_students_for_module(self.module.id, self._csv_file(csv_content))

        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(Student.objects.filter(code_massar="CNE001").count(), 0)


class StudentImportAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.ma",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
            role="admin",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.semestre = Semestre.objects.create(name="S1")
        self.filiere = Filiere.objects.create(
            name="L1 Info", semestre=self.semestre, niveau="LIC"
        )
        self.module = Module.objects.create(name="Algorithmique", filiere=self.filiere)
        self.classe = Classe.objects.create(
            name="Groupe A",
            niveau="LIC",
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            academic_year="2025-2026",
        )

    def test_by_module_listing_and_template_download(self):
        student = Student.objects.create(
            code_massar="CNE010",
            first_name="Test",
            last_name="Student",
            email="test@umi.ac.ma",
            classe=self.classe,
        )
        StudentModuleEnrollment.objects.create(student=student, module=self.module)

        response = self.client.get(
            "/api/v1/students/by-module/",
            {"module": self.module.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        template_response = self.client.get("/api/v1/students/import/template/")
        self.assertEqual(template_response.status_code, 200)

    def test_import_endpoint(self):
        csv_content = (
            "Student Code,Last Name,First Name,Email\n"
            "CNE020,Benali,Ayman,ayman@test.ma\n"
        )
        upload = io.BytesIO(csv_content.encode("utf-8"))
        upload.name = "students.csv"

        response = self.client.post(
            "/api/v1/students/import/",
            {"module_id": self.module.id, "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["created"], 1)
