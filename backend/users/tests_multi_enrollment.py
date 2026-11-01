"""Inscriptions multiples d'un même étudiant dans une seule filière.

Un étudiant conserve un compte et des identifiants uniques (CIN, CNE, email)
de S1 à S6. Il peut être inscrit à plusieurs modules et semestres de sa
filière ; chaque nouvelle inscription réutilise le même étudiant et crée
uniquement une ligne dans la table de liaison. Une inscription dans une autre
filière est refusée avec un message explicite.
"""
import io
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Session
from curriculum.models import Filiere, Module, Semestre
from users.constants import SINGLE_FILIERE_MESSAGE, same_filiere
from users.models import Classe, Student, StudentModuleEnrollment, User
from users.services.student_import import import_students_for_module


class MultiEnrollmentTestMixin:
    def setUp(self):
        self.semestre1 = Semestre.objects.create(name="S1")
        self.semestre4 = Semestre.objects.create(name="S4")

        # Filière unique de l'étudiant : plusieurs modules et semestres.
        # Chaque semestre est une ligne de filière distincte portant le même
        # nom : « Génie Informatique » S1, S4, ... comptent pour la même filière.
        self.filiere1 = Filiere.objects.create(
            name="Génie Informatique", semestre=self.semestre1, niveau="LIC"
        )
        self.module1 = Module.objects.create(
            name="Algorithmique", code="ALGO1", filiere=self.filiere1
        )
        self.classe1 = Classe.objects.create(
            name="Groupe A - S1",
            niveau="LIC",
            filiere=self.filiere1,
            semestre=self.semestre1,
            module=self.module1,
            academic_year="2025-2026",
        )
        self.filiere4 = Filiere.objects.create(
            name="Génie Informatique", semestre=self.semestre4, niveau="LIC"
        )
        self.module2 = Module.objects.create(
            name="Bases de données", code="BDD4", filiere=self.filiere4
        )
        self.classe2 = Classe.objects.create(
            name="Groupe A - S4",
            niveau="LIC",
            filiere=self.filiere4,
            semestre=self.semestre4,
            module=self.module2,
            academic_year="2025-2026",
        )

        # Autre filière : toute inscription doit être refusée.
        self.filiere2 = Filiere.objects.create(
            name="Génie Civil", semestre=self.semestre4, niveau="LIC"
        )
        self.module_other = Module.objects.create(
            name="Résistance des matériaux", code="RDM4", filiere=self.filiere2
        )
        self.classe_other = Classe.objects.create(
            name="Groupe B",
            niveau="LIC",
            filiere=self.filiere2,
            semestre=self.semestre4,
            module=self.module_other,
            academic_year="2025-2026",
        )

        self.admin = User.objects.create_user(
            email="admin@umi.ac.ma",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
            role="admin",
            is_staff=True,
        )

        self.account = User.objects.create_user(
            email="ayman@edu.umi.ac.ma",
            password="Pass12345!",
            first_name="Ayman",
            last_name="Benali",
            role="student",
            cin="AB111",
        )
        self.student = Student.objects.create(
            user=self.account,
            code_massar="CNE001",
            cin="AB111",
            first_name="Ayman",
            last_name="Benali",
            email="ayman@edu.umi.ac.ma",
            phone="0611111111",
            classe=self.classe1,
        )
        StudentModuleEnrollment.objects.create(
            student=self.student, module=self.module1
        )

    def _admin_client(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        return client

    def _student_client(self):
        client = APIClient()
        client.force_authenticate(user=self.account)
        return client

    def _enroll_payload(self, module, **overrides):
        payload = {
            "first_name": "Ayman",
            "last_name": "Benali",
            "code_massar": "CNE001",
            "cin": "AB111",
            "email": "ayman@edu.umi.ac.ma",
            "phone": "0611111111",
            "module_id": module.id,
        }
        payload.update(overrides)
        return payload


class MultiEnrollmentAPITests(MultiEnrollmentTestMixin, TestCase):
    def test_new_module_same_filiere_reuses_student_and_creates_enrollment(self):
        response = self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(self.module2),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 2
        )
        self.assertEqual(
            set(
                StudentModuleEnrollment.objects.filter(
                    student=self.student
                ).values_list("module_id", flat=True)
            ),
            {self.module1.id, self.module2.id},
        )
        # Les identifiants du compte sont inchangés.
        self.student.refresh_from_db()
        self.assertEqual(self.student.code_massar, "CNE001")
        self.assertEqual(self.student.cin, "AB111")
        self.assertEqual(self.student.email, "ayman@edu.umi.ac.ma")
        self.assertEqual(self.student.user_id, self.account.id)
        # La classe courante suit la dernière inscription, dans la même filière.
        self.assertEqual(self.student.classe_id, self.classe2.id)
        self.assertTrue(
            same_filiere(self.student.classe.filiere, self.filiere1)
        )

    def test_add_student_form_persists_phone(self):
        response = self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(
                self.module1,
                first_name="Nadia",
                last_name="Amrani",
                code_massar="CNE999",
                cin="AB999",
                email="nadia@edu.umi.ac.ma",
                phone="0699999999",
                password="StrongPass123!",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        student = Student.objects.get(code_massar="CNE999")
        self.assertEqual(student.phone, "0699999999")
        self.assertEqual(student.user.phone, "0699999999")

    def test_all_six_semesters_of_the_same_filiere_are_allowed(self):
        """S1 à S6 d'une même filière : un seul compte, six inscriptions."""
        for name in ("S2", "S3", "S4", "S5", "S6"):
            semestre = (
                Semestre.objects.filter(name=name).first()
                or Semestre.objects.create(name=name)
            )
            filiere = Filiere.objects.create(
                name="Génie Informatique", semestre=semestre, niveau="LIC"
            )
            module = Module.objects.create(
                name=f"Module {name}", code=f"MOD{name}", filiere=filiere
            )
            Classe.objects.create(
                name=f"Groupe A - {name}",
                niveau="LIC",
                filiere=filiere,
                semestre=semestre,
                module=module,
                academic_year="2025-2026",
            )

            response = self._admin_client().post(
                "/api/v1/students/",
                self._enroll_payload(module),
                format="json",
            )
            self.assertEqual(response.status_code, 201, response.data)

        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 6
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.code_massar, "CNE001")
        self.assertEqual(self.student.cin, "AB111")
        self.assertEqual(self.student.email, "ayman@edu.umi.ac.ma")
        self.assertEqual(self.student.user_id, self.account.id)

    def test_other_filiere_enrollment_is_rejected(self):
        response = self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(self.module_other),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("module_id", response.data)
        self.assertEqual(response.data["module_id"][0], SINGLE_FILIERE_MESSAGE)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 1
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.classe_id, self.classe1.id)

    def test_same_module_cannot_be_enrolled_twice(self):
        response = self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(self.module1),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 1
        )

    def test_class_change_to_another_filiere_is_rejected(self):
        response = self._admin_client().patch(
            f"/api/v1/students/{self.student.id}/",
            {"classe": self.classe_other.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("classe", response.data)
        self.student.refresh_from_db()
        self.assertEqual(self.student.classe_id, self.classe1.id)

    def test_me_exposes_each_module_with_its_own_semester_and_filiere(self):
        self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(self.module2),
            format="json",
        )

        response = self._student_client().get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        modules = {
            module["id"]: module
            for module in response.data["student_profile"]["modules"]
        }
        self.assertEqual(set(modules), {self.module1.id, self.module2.id})
        self.assertEqual(modules[self.module1.id]["semestre_name"], "S1")
        self.assertEqual(modules[self.module1.id]["filiere_name"], "Génie Informatique")
        self.assertEqual(modules[self.module2.id]["semestre_name"], "S4")
        self.assertEqual(modules[self.module2.id]["filiere_name"], "Génie Informatique")

    def test_schedule_contains_sessions_of_all_enrolled_modules(self):
        self._admin_client().post(
            "/api/v1/students/",
            self._enroll_payload(self.module2),
            format="json",
        )
        teacher = User.objects.create_user(
            email="teacher@umi.ac.ma",
            password="TeacherPass123!",
            first_name="Prof",
            last_name="Test",
            role="teacher",
        )
        session1 = Session.objects.create(
            subject="Algorithmique",
            module=self.module1,
            teacher=teacher,
            classe=self.classe1,
            date=date.today(),
        )
        session2 = Session.objects.create(
            subject="Bases de données",
            module=self.module2,
            teacher=teacher,
            classe=self.classe2,
            date=date.today(),
        )

        response = self._student_client().get("/api/v1/attendance/my-schedule/")
        self.assertEqual(response.status_code, 200)
        payload = response.data
        sessions = payload if isinstance(payload, list) else payload.get("results", [])
        ids = {item["id"] for item in sessions}
        self.assertIn(session1.id, ids)
        self.assertIn(session2.id, ids)


class MultiEnrollmentImportTests(MultiEnrollmentTestMixin, TestCase):
    def _csv_file(self, content: str):
        buffer = io.BytesIO(content.encode("utf-8"))
        buffer.name = "students.csv"
        return buffer

    def test_import_into_another_module_keeps_single_account(self):
        content = (
            "Student Code,Last Name,First Name,Email,Phone\n"
            "CNE001,Benali,Ayman,ayman@edu.umi.ac.ma,0611111111\n"
        )

        report = import_students_for_module(
            self.module2.id, self._csv_file(content)
        )

        self.assertEqual(report["created"], 0)
        self.assertEqual(report["linked"], 1)
        self.assertEqual(report["errors"], [])
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 2
        )
        self.assertTrue(
            StudentModuleEnrollment.objects.filter(
                student=self.student, module=self.module1
            ).exists()
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.code_massar, "CNE001")
        self.assertEqual(self.student.cin, "AB111")
        self.assertEqual(self.student.email, "ayman@edu.umi.ac.ma")

    def test_import_into_another_filiere_is_rejected(self):
        content = (
            "Student Code,Last Name,First Name,Email,Phone\n"
            "CNE001,Benali,Ayman,ayman@edu.umi.ac.ma,0611111111\n"
        )

        report = import_students_for_module(
            self.module_other.id, self._csv_file(content)
        )

        self.assertEqual(report["created"], 0)
        self.assertEqual(report["linked"], 0)
        messages = [
            message
            for error in report["errors"]
            for message in error["messages"]
        ]
        self.assertIn(SINGLE_FILIERE_MESSAGE, messages)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(
            StudentModuleEnrollment.objects.filter(student=self.student).count(), 1
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.classe_id, self.classe1.id)
