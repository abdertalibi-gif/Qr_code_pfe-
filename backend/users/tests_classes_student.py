"""Tests de synchronisation des classes entre administration et etudiants."""
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User, Student, Classe, Department
from curriculum.models import Filiere, Semestre, Module


class StudentClassVisibilityTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Dept Test")
        from users.models import Block, Room
        self.block = Block.objects.create(name="Block Test")
        self.room = Room.objects.create(block=self.block, name="Room Test")
        self.sem = Semestre.objects.create(name="S5")
        self.filiere = Filiere.objects.create(
            name="Filiere Test", niveau="LIC", semestre=self.sem, department=self.dept
        )
        self.module = Module.objects.create(name="Module Test", filiere=self.filiere)
        self.classe_a = Classe.objects.create(
            filiere=self.filiere, semestre=self.sem, module=self.module,
            niveau="LIC", academic_year="2025-2026",
        )
        self.classe_b = Classe.objects.create(
            filiere=self.filiere, semestre=self.sem, module=self.module,
            niveau="LIC", academic_year="2025-2026",
        )

        self.admin = User.objects.create_user(
            email="admin@test.local", password="adminpass", role="admin",
            is_staff=True, is_superuser=True,
        )
        self.student_user = User.objects.create_user(
            email="student@test.local", password="studpass", role="student",
            first_name="Etudiant", last_name="Test",
        )
        self.student = Student.objects.create(
            user=self.student_user, first_name="Etudiant", last_name="Test",
            code_massar="C001", classe=self.classe_a,
        )

    def _client_for(self, user, password):
        c = APIClient()
        r = c.post("/api/v1/auth/login/", {"email": user.email, "password": password})
        self.assertEqual(r.status_code, 200, r.content)
        c.credentials(HTTP_AUTHORIZATION="Bearer " + r.json()["access"])
        return c

    def test_student_me_exposes_own_class(self):
        c = self._client_for(self.student_user, "studpass")
        r = c.get("/api/v1/auth/me/")
        self.assertEqual(r.status_code, 200)
        sp = r.json().get("student_profile")
        self.assertIsNotNone(sp)
        self.assertEqual(sp["classe_id"], self.classe_a.id)
        self.assertEqual(sp["classe_name"], str(self.classe_a))

    def test_student_list_classes_only_own(self):
        c = self._client_for(self.student_user, "studpass")
        r = c.get("/api/v1/classes/")
        self.assertEqual(r.status_code, 200)
        ids = [x["id"] for x in r.json()] if isinstance(r.json(), list) else [x["id"] for x in r.json().get("results", [])]
        self.assertEqual(ids, [self.classe_a.id])

    def test_student_cannot_retrieve_other_class(self):
        c = self._client_for(self.student_user, "studpass")
        r = c.get(f"/api/v1/classes/{self.classe_b.id}/")
        # Either 404 (filtered out) or 403; never 200 with foreign class.
        self.assertIn(r.status_code, (403, 404))

    def test_admin_can_create_class(self):
        c = self._client_for(self.admin, "adminpass")
        payload = {
            "niveau_id": "LIC",
            "filiere_id": self.filiere.id,
            "semestre_id": self.sem.id,
            "module_id": self.module.id,
            "academic_year": "2026-2027",
            "location_type": "BLOC",
            "block_id": self.block.id,
            "room_id": self.room.id,
        }
        r = c.post("/api/v1/classes/", payload, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["filiere_id"], self.filiere.id)
        self.assertEqual(r.json()["semestre_id"], self.sem.id)
        self.assertEqual(r.json()["module_id"], self.module.id)

    def test_unauthenticated_cannot_list_classes(self):
        c = APIClient()
        r = c.get("/api/v1/classes/")
        self.assertIn(r.status_code, (401, 403))
