"""Unicité des identifiants étudiants : CIN, CNE (code Massar) et email.

Ces trois identifiants sont distincts et chacun possède sa propre contrainte
UNIQUE (Django + base de données). Les tests couvrent :

1. les contraintes de base (doublons rejetés même sans passer par l'API) ;
2. la normalisation (espaces supprimés, email en minuscules) ;
3. les messages d'erreur précis renvoyés par l'API DRF ;
4. l'interdiction de modifier automatiquement un identifiant existant.
"""
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, Student, User


class StudentIdentifierTestMixin:
    def setUp(self):
        self.semestre = Semestre.objects.create(name="S1")
        self.filiere = Filiere.objects.create(
            name="L1 Info", semestre=self.semestre, niveau="LIC"
        )
        self.module = Module.objects.create(
            name="Algorithmique", filiere=self.filiere
        )
        self.classe = Classe.objects.create(
            name="Groupe A",
            niveau="LIC",
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            academic_year="2025-2026",
        )

        self.account1 = User.objects.create_user(
            email="ayman@edu.umi.ac.ma",
            password="Pass12345!",
            first_name="Ayman",
            last_name="Benali",
            role="student",
        )
        self.student1 = Student.objects.create(
            user=self.account1,
            code_massar="CNE001",
            cin="AB111",
            first_name="Ayman",
            last_name="Benali",
            email="ayman@edu.umi.ac.ma",
            classe=self.classe,
        )
        self.student2 = Student.objects.create(
            code_massar="CNE002",
            cin="AB222",
            first_name="Sara",
            last_name="Alami",
            email="sara@edu.umi.ac.ma",
            classe=self.classe,
        )


class StudentIdentifierDatabaseTests(StudentIdentifierTestMixin, TestCase):
    def test_duplicate_cne_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(
                    code_massar="CNE001",
                    cin="AB999",
                    first_name="Autre",
                    last_name="Étudiant",
                    email="autre@edu.umi.ac.ma",
                    classe=self.classe,
                )
        self.assertEqual(Student.objects.count(), 2)

    def test_duplicate_cin_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(
                    code_massar="CNE003",
                    cin="AB111",
                    first_name="Autre",
                    last_name="Étudiant",
                    email="autre@edu.umi.ac.ma",
                    classe=self.classe,
                )
        self.assertEqual(Student.objects.count(), 2)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(
                    code_massar="CNE004",
                    cin="AB444",
                    first_name="Autre",
                    last_name="Étudiant",
                    email="AYMAN@EDU.UMI.AC.MA",
                    classe=self.classe,
                )
        self.assertEqual(Student.objects.count(), 2)

    def test_identifiers_are_trimmed_and_email_is_lowercased(self):
        student = Student.objects.create(
            code_massar="  CNE005  ",
            cin="  ab555  ",
            first_name="Nouveau",
            last_name="Étudiant",
            email="  New.Student@EDU.UMI.AC.MA  ",
            classe=self.classe,
        )
        self.assertEqual(student.code_massar, "CNE005")
        self.assertEqual(student.cin, "ab555")
        self.assertEqual(student.email, "new.student@edu.umi.ac.ma")

    def test_empty_cin_can_be_shared(self):
        # Un CIN inconnu reste autorisé : seule une valeur réelle est unique.
        Student.objects.create(
            code_massar="CNE006",
            cin="",
            first_name="Sans",
            last_name="CIN",
            email="sans.cin@edu.umi.ac.ma",
            classe=self.classe,
        )
        Student.objects.create(
            code_massar="CNE007",
            cin="",
            first_name="Sans2",
            last_name="CIN",
            email="sans.cin2@edu.umi.ac.ma",
            classe=self.classe,
        )
        self.assertEqual(Student.objects.filter(cin="").count(), 2)


class StudentIdentifierAPITests(StudentIdentifierTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            email="admin@umi.ac.ma",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
            role="admin",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def _student_payload(self, **overrides):
        payload = {
            "first_name": "Nouveau",
            "last_name": "Étudiant",
            "code_massar": "CNE010",
            "cin": "AB010",
            "email": "nouveau@edu.umi.ac.ma",
            "classe": self.classe.id,
        }
        payload.update(overrides)
        return payload

    def test_api_rejects_duplicate_cin(self):
        response = self.client.post(
            "/api/v1/students/", self._student_payload(cin="AB111"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cin", response.data)
        self.assertIn("CIN", str(response.data["cin"]))
        self.assertEqual(Student.objects.count(), 2)

    def test_api_rejects_duplicate_cne(self):
        response = self.client.post(
            "/api/v1/students/",
            self._student_payload(
                code_massar="CNE001", cin="AB010", email="autre@edu.umi.ac.ma"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("code_massar", response.data)
        self.assertIn("CNE", str(response.data["code_massar"]))
        self.assertEqual(Student.objects.count(), 2)

    def test_api_rejects_duplicate_email_regardless_of_case(self):
        response = self.client.post(
            "/api/v1/students/",
            self._student_payload(
                code_massar="CNE011",
                cin="AB011",
                email="  AYMAN@EDU.UMI.AC.MA  ",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(Student.objects.count(), 2)

    def test_api_normalizes_values_on_creation(self):
        response = self.client.post(
            "/api/v1/students/",
            self._student_payload(
                code_massar="  CNE012 ",
                cin="  ab777 ",
                email="  New.Student@EDU.UMI.AC.MA ",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        student = Student.objects.get(code_massar="CNE012")
        self.assertEqual(student.code_massar, "CNE012")
        self.assertEqual(student.cin, "ab777")
        self.assertEqual(student.email, "new.student@edu.umi.ac.ma")

    def test_api_rejects_duplicate_cin_on_update(self):
        response = self.client.patch(
            f"/api/v1/students/{self.student1.id}/",
            {"cin": "AB222"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cin", response.data)
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.cin, "AB111")

    def test_api_does_not_overwrite_existing_identifiers(self):
        response = self.client.patch(
            f"/api/v1/students/{self.student1.id}/",
            {"code_massar": "CNE003", "email": "sara@edu.umi.ac.ma"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.code_massar, "CNE001")
        self.assertEqual(self.student1.email, "ayman@edu.umi.ac.ma")

    def test_user_creation_rejects_duplicate_student_cin(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "first_name": "Nouveau",
                "last_name": "Compte",
                "email": "brand.new@edu.umi.ac.ma",
                "role": "student",
                "password": "StrongPass123!",
                "cin": "AB111",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cin", response.data)

    def test_user_creation_rejects_email_case_duplicate(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "first_name": "Nouveau",
                "last_name": "Compte",
                "email": "ADMIN@UMI.AC.MA",
                "role": "teacher",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_user_update_rejects_email_of_another_student(self):
        response = self.client.patch(
            f"/api/v1/users/{self.account1.id}/",
            {"email": "SARA@EDU.UMI.AC.MA"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.email, "ayman@edu.umi.ac.ma")
