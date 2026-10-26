"""Tests de la règle « une seule séance par créneau pour un enseignant ».

La création impose la date et l'heure de début côté serveur. Les tests
figent donc ``timezone.now()`` pour représenter chaque créneau.
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, User

from .models import Session
from .utils import TEACHER_SESSION_OVERLAP_MESSAGE

FIXED_DATE = datetime(2026, 5, 12).date()


def at(hour, minute=0):
    """Return an aware datetime on the fixed test date."""
    return timezone.make_aware(
        datetime.combine(FIXED_DATE, time(hour, minute)),
        timezone.get_current_timezone(),
    )


class TeacherOverlapTests(TestCase):
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
            email="teacher.overlap@example.com",
            password="test1234",
            first_name="Test",
            last_name="Teacher",
            role="teacher",
        )
        cls.other_teacher = User.objects.create_user(
            email="teacher.other@example.com",
            password="test1234",
            first_name="Other",
            last_name="Teacher",
            role="teacher",
        )

    def setUp(self):
        self.teacher.assigned_classes.add(self.classe)
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)
        self.url = "/api/v1/sessions/"

    def _payload(self, end_time="12:00", **overrides):
        data = {
            "module_id": self.module.id,
            "niveau": "LIC",
            "semestre_id": self.semestre.id,
            "filiere_id": self.filiere.id,
            "classe": self.classe.id,
            "end_time": end_time,
            "session_type": "Cours",
        }
        data.update(overrides)
        return data

    def _post_at(self, hour, minute, end_time, **overrides):
        with patch("django.utils.timezone.now", return_value=at(hour, minute)):
            return self.client.post(
                self.url,
                self._payload(end_time=end_time, **overrides),
                format="json",
            )

    def _patch_at(self, session_id, hour, minute, payload):
        with patch("django.utils.timezone.now", return_value=at(hour, minute)):
            return self.client.patch(
                f"{self.url}{session_id}/", payload, format="json"
            )

    # 1. Deux séances qui se chevauchent : refus.
    def test_overlapping_sessions_are_rejected(self):
        first = self._post_at(10, 0, "12:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(10, 30, "13:00")
        self.assertEqual(second.status_code, 400, second.data)
        self.assertIn(
            TEACHER_SESSION_OVERLAP_MESSAGE,
            second.data.get("non_field_errors", []),
        )
        self.assertEqual(Session.objects.count(), 1)

    # 1 bis. Chevauchement partiel : la nouvelle séance commence avant, mais
    # se termine pendant l'existante.
    def test_partial_overlap_starting_before_existing_is_rejected(self):
        first = self._post_at(10, 0, "11:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(9, 30, "10:30")
        self.assertEqual(second.status_code, 400, second.data)
        self.assertIn(
            TEACHER_SESSION_OVERLAP_MESSAGE,
            second.data.get("non_field_errors", []),
        )
        self.assertEqual(Session.objects.count(), 1)

    # 2. Séances consécutives 10 h–11 h puis 11 h–12 h : autorisées.
    def test_consecutive_sessions_are_allowed(self):
        first = self._post_at(10, 0, "11:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(11, 0, "12:00")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(Session.objects.count(), 2)

    # 3. Nouvelle séance après la fin de la précédente : autorisée.
    def test_new_session_after_previous_end_is_allowed(self):
        first = self._post_at(10, 0, "11:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(11, 30, "12:30")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(Session.objects.count(), 2)

    # 4. Deux séances le même jour à des heures différentes : autorisées.
    def test_two_sessions_same_day_different_hours_are_allowed(self):
        first = self._post_at(8, 0, "9:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(14, 0, "15:00")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(Session.objects.count(), 2)

    # Les séances clôturées ne bloquent plus le créneau.
    def test_closed_session_does_not_block_new_session(self):
        first = self._post_at(10, 0, "11:00")
        self.assertEqual(first.status_code, 201, first.data)
        Session.objects.filter(pk=first.data["id"]).update(
            is_closed=True, is_active=False
        )

        second = self._post_at(10, 30, "12:00")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(Session.objects.count(), 2)

    # Édition : la séance en cours d'édition ne se bloque pas elle-même.
    def test_update_ignores_the_session_being_edited(self):
        created = self._post_at(10, 0, "11:00")
        self.assertEqual(created.status_code, 201, created.data)

        response = self._patch_at(
            created.data["id"], 10, 30, {"end_time": "11:30"}
        )
        self.assertEqual(response.status_code, 200, response.data)

        session = Session.objects.get(pk=created.data["id"])
        self.assertEqual(session.end_time, time(11, 30))

    # Édition : modifier une séance pour la faire chevaucher une autre est refusé.
    def test_update_causing_overlap_is_rejected(self):
        first = self._post_at(10, 0, "11:00")
        self.assertEqual(first.status_code, 201, first.data)

        second = self._post_at(12, 0, "13:00")
        self.assertEqual(second.status_code, 201, second.data)

        response = self._patch_at(
            second.data["id"],
            9,
            0,
            {
                "date": str(FIXED_DATE),
                "start_time": "10:30",
                "end_time": "11:30",
            },
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn(
            TEACHER_SESSION_OVERLAP_MESSAGE,
            response.data.get("non_field_errors", []),
        )

    # Édition : une séance déjà commencée reste modifiable si date/début
    # n'ont pas changé (ex. corriger l'heure de fin).
    def test_started_session_can_still_be_edited(self):
        created = self._post_at(10, 0, "11:00")
        self.assertEqual(created.status_code, 201, created.data)

        response = self._patch_at(
            created.data["id"], 10, 45, {"end_time": "11:45"}
        )
        self.assertEqual(response.status_code, 200, response.data)

    # Édition : l'heure de début stockée contient des secondes, alors que le
    # formulaire ne renvoie que HH:MM. L'édition doit rester possible.
    def test_started_session_with_seconds_can_be_edited_from_minute_input(self):
        with patch(
            "django.utils.timezone.now",
            return_value=at(10, 0).replace(second=27),
        ):
            created = self.client.post(
                self.url, self._payload(end_time="11:00"), format="json"
            )
        self.assertEqual(created.status_code, 201, created.data)

        response = self._patch_at(
            created.data["id"],
            10,
            45,
            {
                "date": str(FIXED_DATE),
                "start_time": "10:00",
                "end_time": "11:45",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)

        session = Session.objects.get(pk=created.data["id"])
        self.assertEqual(session.start_time, time(10, 0, 27))
        self.assertEqual(session.end_time, time(11, 45))

    # Suppression : l'enseignant peut supprimer sa propre séance.
    def test_teacher_can_delete_own_session(self):
        created = self._post_at(10, 0, "11:00")
        self.assertEqual(created.status_code, 201, created.data)

        response = self.client.delete(f"{self.url}{created.data['id']}/")
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(Session.objects.filter(pk=created.data["id"]).exists())

    # Un enseignant ne peut ni modifier ni supprimer la séance d'un autre.
    def test_teacher_cannot_edit_or_delete_another_teachers_session(self):
        created = self._post_at(10, 0, "11:00")
        self.assertEqual(created.status_code, 201, created.data)

        self.client.force_authenticate(self.other_teacher)
        patch_response = self.client.patch(
            f"{self.url}{created.data['id']}/",
            {"end_time": "11:30"},
            format="json",
        )
        delete_response = self.client.delete(f"{self.url}{created.data['id']}/")
        self.assertEqual(patch_response.status_code, 404, patch_response.data)
        self.assertEqual(delete_response.status_code, 404, delete_response.data)


class ConcurrentTeacherOverlapTests(TransactionTestCase):
    """Deux requêtes simultanées pour le même créneau ne créent qu'une séance."""

    def setUp(self):
        self.semestre = Semestre.objects.create(name="S1")
        self.filiere = Filiere.objects.create(
            name="SDIA", semestre=self.semestre, niveau="LIC"
        )
        self.module = Module.objects.create(name="Logique", filiere=self.filiere)
        self.classe = Classe.objects.create(
            name="SDIA S1",
            niveau="LIC",
            filiere=self.filiere,
            semestre=self.semestre,
            module=self.module,
            academic_year="2025-2026",
            location_type="BLOC",
        )
        self.teacher = User.objects.create_user(
            email="teacher.concurrent@example.com",
            password="test1234",
            first_name="Test",
            last_name="Teacher",
            role="teacher",
        )
        self.teacher.assigned_classes.add(self.classe)
        self.url = "/api/v1/sessions/"

    def _payload(self):
        return {
            "module_id": self.module.id,
            "niveau": "LIC",
            "semestre_id": self.semestre.id,
            "filiere_id": self.filiere.id,
            "classe": self.classe.id,
            "end_time": "12:00",
            "session_type": "Cours",
        }

    def test_two_simultaneous_requests_create_only_one_session(self):
        barrier = threading.Barrier(2)
        results = []
        results_lock = threading.Lock()

        def submit():
            close_old_connections()
            client = APIClient()
            client.force_authenticate(self.teacher)
            try:
                barrier.wait(timeout=10)
                response = client.post(
                    self.url, self._payload(), format="json"
                )
                status_code = response.status_code
            except Exception:
                status_code = 500
            finally:
                close_old_connections()
            with results_lock:
                results.append(status_code)

        with patch("django.utils.timezone.now", return_value=at(10, 0)):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(submit) for _ in range(2)]
                for future in futures:
                    future.result(timeout=30)

        self.assertEqual(results.count(201), 1, results)
        self.assertEqual(Session.objects.count(), 1)
