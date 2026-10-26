"""Tests du démarrage immédiat d'une séance.

La date et l'heure de début sont imposées par le serveur (heure réelle de
création). Le client ne peut plus choisir une date ou une heure de début
future ; il ne fournit que l'heure de fin.
"""
from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from curriculum.models import Filiere, Module, Semestre
from users.models import Block, Classe, Room, User

from .models import Session

# Instant serveur figé pour rendre les assertions déterministes.
FIXED_NOW = timezone.make_aware(
    datetime(2026, 5, 12, 10, 0, 0), timezone.get_current_timezone()
)


class ImmediateSessionCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.semestre = Semestre.objects.create(name="S1")
        cls.filiere = Filiere.objects.create(
            name="SDIA", semestre=cls.semestre, niveau="LIC"
        )
        cls.module = Module.objects.create(name="Logique", filiere=cls.filiere)
        cls.classe = Classe.objects.create(
            name="SDIA S1",
            niveau="LIC",
            filiere=cls.filiere,
            semestre=cls.semestre,
            module=cls.module,
            academic_year="2025-2026",
            location_type="BLOC",
        )
        cls.teacher = User.objects.create_user(
            email="teacher.immediate@example.com",
            password="test1234",
            first_name="Test",
            last_name="Teacher",
            role="teacher",
        )
        cls.admin = User.objects.create_user(
            email="admin.immediate@example.com",
            password="test1234",
            first_name="Test",
            last_name="Admin",
            role="admin",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.url = "/api/v1/sessions/"

    def _payload(self, **overrides):
        data = {
            "module_id": self.module.id,
            "niveau": "LIC",
            "semestre_id": self.semestre.id,
            "filiere_id": self.filiere.id,
            "classe": self.classe.id,
            "teacher": self.teacher.id,
            "end_time": "12:00",
            "session_type": "Cours",
        }
        data.update(overrides)
        return data

    @patch("django.utils.timezone.now", return_value=FIXED_NOW)
    def test_create_records_real_server_time_and_starts_immediately(self, _now):
        # Valeurs futures/incohérentes envoyées par le client : elles doivent
        # être ignorées au profit de l'heure réelle du serveur.
        response = self.client.post(
            self.url,
            self._payload(date="2030-01-01", start_time="08:00"),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

        session = Session.objects.get(pk=response.data["id"])
        self.assertEqual(session.date, FIXED_NOW.date())
        self.assertEqual(
            session.start_time,
            FIXED_NOW.time().replace(microsecond=0),
        )
        self.assertEqual(session.end_time, datetime.strptime("12:00", "%H:%M").time())

        # Aucun champ de lieu envoyé : le lieu par défaut de la classe (ou le
        # type par défaut du modèle) est appliqué, sans bloquer la création.
        self.assertEqual(session.location_type, "block")
        self.assertIsNone(session.block_id)
        self.assertIsNone(session.room_id)

        # La séance est utilisable immédiatement, QR compris.
        self.assertTrue(session.is_within_session_window)
        self.assertTrue(session.can_generate_qr)

    @patch("django.utils.timezone.now", return_value=FIXED_NOW)
    def test_create_without_location_fields_uses_class_default_location(self, _now):
        block = Block.objects.create(name="Bloc immédiat")
        room = Room.objects.create(block=block, name="Salle immédiate")
        Classe.objects.filter(pk=self.classe.pk).update(
            block=block, room=room, location_type="BLOC"
        )
        self.classe.refresh_from_db()

        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

        session = Session.objects.get(pk=response.data["id"])
        self.assertEqual(session.location_type, "block")
        self.assertEqual(session.block_id, block.id)
        self.assertEqual(session.room_id, room.id)

    @patch("django.utils.timezone.now", return_value=FIXED_NOW)
    def test_end_time_before_server_start_is_rejected(self, _now):
        response = self.client.post(
            self.url,
            self._payload(end_time="09:00"),
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("end_time", response.data)
        self.assertEqual(Session.objects.count(), 0)

    @patch("django.utils.timezone.now", return_value=FIXED_NOW)
    def test_qr_can_be_generated_right_after_creation(self, _now):
        created = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)

        response = self.client.post(
            f"/api/v1/sessions/{created.data['id']}/generate-qr/",
            {"expiry_minutes": 20},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["qr_token"])
        self.assertTrue(response.data["is_qr_valid"])
