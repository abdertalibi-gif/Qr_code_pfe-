"""Synchronisation des classes : creation admin -> espace etudiant.

Couvre le scenario fonctionnel :
1. l'admin cree une classe (niveau, semestre, filiere, module) ;
2. la classe est persistee en base ;
3. apres affectation, l'etudiant concerne la voit via /classes/ et /auth/me/ ;
4. un etudiant non affecte ne la voit jamais ;
5. une modification de classe est visible au rafraichissement suivant ;
6. un etudiant ne peut pas creer/modifier une classe.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from curriculum.models import Filiere, Module, Semestre
from users.models import Block, Classe, Department, Room, Student, User


class ClassSyncTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Dept Test")
        self.block = Block.objects.create(name="Block Test")
        self.room = Room.objects.create(block=self.block, name="Room Test")
        self.semestre = Semestre.objects.create(name="S5")
        self.filiere = Filiere.objects.create(
            name="Filiere Test",
            niveau="LIC",
            semestre=self.semestre,
            department=self.dept,
        )
        self.module = Module.objects.create(
            name="Module Test", filiere=self.filiere
        )

        self.old_class_1 = Classe.objects.create(
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            niveau="LIC",
            academic_year="2025-2026",
            location_type="BLOC",
            block=self.block,
            room=self.room,
        )
        self.old_class_2 = Classe.objects.create(
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            niveau="LIC",
            academic_year="2024-2025",
            location_type="BLOC",
            block=self.block,
            room=self.room,
        )

        self.admin = User.objects.create_user(
            email="admin-sync@test.local",
            password="adminpass",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.student_user_1 = User.objects.create_user(
            email="student1-sync@test.local",
            password="studpass",
            role="student",
            first_name="Etudiant",
            last_name="Un",
        )
        self.student_1 = Student.objects.create(
            user=self.student_user_1,
            first_name="Etudiant",
            last_name="Un",
            code_massar="SYNC001",
            classe=self.old_class_1,
        )
        self.student_user_2 = User.objects.create_user(
            email="student2-sync@test.local",
            password="studpass",
            role="student",
            first_name="Etudiant",
            last_name="Deux",
        )
        self.student_2 = Student.objects.create(
            user=self.student_user_2,
            first_name="Etudiant",
            last_name="Deux",
            code_massar="SYNC002",
            classe=self.old_class_2,
        )

    def _client_for(self, user, password):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.content)
        client.credentials(
            HTTP_AUTHORIZATION="Bearer " + response.json()["access"]
        )
        return client

    def _create_class(self, academic_year="2026-2027"):
        admin = self._client_for(self.admin, "adminpass")
        response = admin.post(
            "/api/v1/classes/",
            {
                "niveau_id": "LIC",
                "filiere_id": self.filiere.id,
                "semestre_id": self.semestre.id,
                "module_id": self.module.id,
                "academic_year": academic_year,
                "location_type": "BLOC",
                "block_id": self.block.id,
                "room_id": self.room.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def _assign_student(self, student, classe_id):
        admin = self._client_for(self.admin, "adminpass")
        response = admin.patch(
            f"/api/v1/students/{student.id}/",
            {"classe": classe_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def _class_ids(self, response):
        payload = response.json()
        rows = payload if isinstance(payload, list) else payload.get("results", [])
        return [row["id"] for row in rows]

    def test_admin_creates_class_with_all_academic_fields(self):
        created = self._create_class()

        classe = Classe.objects.get(pk=created["id"])
        self.assertEqual(classe.niveau, "LIC")
        self.assertEqual(classe.filiere_id, self.filiere.id)
        self.assertEqual(classe.semestre_id, self.semestre.id)
        self.assertEqual(classe.module_id, self.module.id)
        self.assertEqual(classe.academic_year, "2026-2027")
        self.assertTrue(classe.name)
        self.assertEqual(created["filiere_id"], self.filiere.id)
        self.assertEqual(created["semestre_id"], self.semestre.id)
        self.assertEqual(created["module_id"], self.module.id)

    def test_assigned_student_sees_new_class_on_web_and_mobile_apis(self):
        created = self._create_class()
        self._assign_student(self.student_1, created["id"])

        student = self._client_for(self.student_user_1, "studpass")

        # Endpoint utilise par le Web et le Mobile pour lister la classe.
        response = student.get("/api/v1/classes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._class_ids(response), [created["id"]])

        # Endpoint /auth/me/ utilise par le profil Web et l'application Flutter.
        me = student.get("/api/v1/auth/me/")
        self.assertEqual(me.status_code, 200)
        profile = me.json()["student_profile"]
        self.assertEqual(profile["classe_id"], created["id"])
        self.assertEqual(profile["classe_name"], created["name"])
        self.assertEqual(profile["filiere_id"], self.filiere.id)
        self.assertEqual(profile["filiere_name"], self.filiere.name)
        self.assertEqual(profile["semestre_id"], self.semestre.id)
        self.assertEqual(profile["semestre_name"], self.semestre.name)
        self.assertEqual(profile["module_id"], self.module.id)
        self.assertEqual(profile["module_name"], self.module.name)
        self.assertEqual(profile["niveau"], "LIC")
        self.assertEqual(profile["academic_year"], "2026-2027")

    def test_unassigned_student_never_sees_another_class(self):
        created = self._create_class()
        student = self._client_for(self.student_user_2, "studpass")

        listing = student.get("/api/v1/classes/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(self._class_ids(listing), [self.old_class_2.id])

        # Meme en forcant un id de classe dans l'URL, le backend ignore le
        # client et renvoie uniquement la classe de l'etudiant.
        forced = student.get(f"/api/v1/classes/?classe_id={created['id']}")
        self.assertEqual(forced.status_code, 200)
        self.assertEqual(self._class_ids(forced), [self.old_class_2.id])

        detail = student.get(f"/api/v1/classes/{created['id']}/")
        self.assertIn(detail.status_code, (403, 404))

        me = student.get("/api/v1/auth/me/")
        self.assertEqual(me.json()["student_profile"]["classe_id"], self.old_class_2.id)

    def test_new_empty_class_is_not_visible_to_any_student(self):
        created = self._create_class()

        for user, own_class in (
            (self.student_user_1, self.old_class_1),
            (self.student_user_2, self.old_class_2),
        ):
            client = self._client_for(user, "studpass")
            response = client.get("/api/v1/classes/")
            self.assertEqual(self._class_ids(response), [own_class.id])
            self.assertNotIn(created["id"], self._class_ids(response))

    def test_class_update_is_visible_on_next_student_refresh(self):
        created = self._create_class()
        self._assign_student(self.student_1, created["id"])

        admin = self._client_for(self.admin, "adminpass")
        response = admin.patch(
            f"/api/v1/classes/{created['id']}/",
            {"academic_year": "2027-2028"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        student = self._client_for(self.student_user_1, "studpass")
        me = student.get("/api/v1/auth/me/")
        self.assertEqual(
            me.json()["student_profile"]["academic_year"], "2027-2028"
        )

    def test_student_cannot_create_update_or_delete_class(self):
        student = self._client_for(self.student_user_1, "studpass")
        payload = {
            "niveau_id": "LIC",
            "filiere_id": self.filiere.id,
            "semestre_id": self.semestre.id,
            "academic_year": "2026-2027",
            "location_type": "BLOC",
            "block_id": self.block.id,
            "room_id": self.room.id,
        }

        create = student.post("/api/v1/classes/", payload, format="json")
        self.assertIn(create.status_code, (401, 403))

        update = student.patch(
            f"/api/v1/classes/{self.old_class_1.id}/",
            {"academic_year": "2026-2027"},
            format="json",
        )
        self.assertIn(update.status_code, (401, 403))

        delete = student.delete(f"/api/v1/classes/{self.old_class_1.id}/")
        self.assertIn(delete.status_code, (401, 403))

    def test_reassigning_same_student_twice_does_not_duplicate(self):
        created = self._create_class()
        self._assign_student(self.student_1, created["id"])
        self._assign_student(self.student_1, created["id"])

        self.assertEqual(
            Student.objects.filter(pk=self.student_1.id).count(), 1
        )
        self.student_1.refresh_from_db()
        self.assertEqual(self.student_1.classe_id, created["id"])
