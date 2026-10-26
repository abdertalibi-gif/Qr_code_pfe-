from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, User

from .serializers import SessionSerializer


class SessionAcademicCombinationTests(TestCase):
    """Vérifie la validation serveur Niveau → Semestre → Filière → Module."""

    @classmethod
    def setUpTestData(cls):
        cls.s1 = Semestre.objects.create(name="S1")
        cls.s2 = Semestre.objects.create(name="S2")
        cls.s7 = Semestre.objects.create(name="S7")

        cls.filiere_sdia = Filiere.objects.create(
            name="SDIA", semestre=cls.s1, niveau="LIC"
        )
        cls.filiere_autre = Filiere.objects.create(
            name="Autre Filière", semestre=cls.s2, niveau="LIC"
        )
        cls.filiere_excellence = Filiere.objects.create(
            name="Licence Excellence Test", semestre=cls.s1, niveau="LIC_EXC"
        )

        cls.module_logique = Module.objects.create(
            name="Logique", filiere=cls.filiere_sdia
        )
        cls.module_autre = Module.objects.create(
            name="Module Autre", filiere=cls.filiere_autre
        )

        cls.teacher = User.objects.create_user(
            email="teacher.academic@example.com",
            password="test1234",
            first_name="Test",
            last_name="Teacher",
            role="teacher",
        )

        cls.classe = Classe.objects.create(
            name="SDIA S1",
            niveau="LIC",
            filiere=cls.filiere_sdia,
            semestre=cls.s1,
            module=cls.module_logique,
            academic_year="2025-2026",
            location_type="BLOC",
        )

    def _payload(self, **overrides):
        # Démarrage immédiat : le serveur impose date et heure de début.
        # L'heure de fin doit simplement être postérieure à l'instant présent.
        now = timezone.localtime()
        end = now + timedelta(hours=1)
        if end.date() != now.date():
            end = now.replace(hour=23, minute=59)
        data = {
            "module_id": self.module_logique.id,
            "niveau": "LIC",
            "semestre_id": self.s1.id,
            "filiere_id": self.filiere_sdia.id,
            "classe": self.classe.id,
            "teacher": self.teacher.id,
            "end_time": end.strftime("%H:%M"),
            "session_type": "Cours",
            "location_type": "block",
        }
        data.update(overrides)
        return data

    def test_valid_combination_is_accepted(self):
        serializer = SessionSerializer(data=self._payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        session = serializer.save()
        self.assertEqual(session.niveau, "LIC")
        self.assertEqual(session.semestre_id, self.s1.id)
        self.assertEqual(session.filiere_id, self.filiere_sdia.id)
        self.assertEqual(session.module_id, self.module_logique.id)

    def test_module_from_another_filiere_is_rejected(self):
        serializer = SessionSerializer(
            data=self._payload(module_id=self.module_autre.id)
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("module_id", serializer.errors)

    def test_filiere_from_another_niveau_is_rejected(self):
        serializer = SessionSerializer(
            data=self._payload(niveau="MAS", semestre_id=self.s7.id)
        )
        self.assertFalse(serializer.is_valid())
        self.assertTrue(
            "filiere_id" in serializer.errors or "semestre_id" in serializer.errors
        )

    def test_filiere_from_another_semestre_is_rejected(self):
        serializer = SessionSerializer(
            data=self._payload(semestre_id=self.s2.id)
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("semestre_id", serializer.errors)

    def test_semestre_not_allowed_for_niveau_is_rejected(self):
        # Filière cohérente (niveau LIC_EXC + S1) mais S1 n'est pas un
        # semestre autorisé pour LIC_EXC (S5/S6 uniquement).
        serializer = SessionSerializer(
            data=self._payload(
                niveau="LIC_EXC",
                semestre_id=self.s1.id,
                filiere_id=self.filiere_excellence.id,
                module_id=self.module_logique.id,
                classe=self.classe.id,
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("semestre_id", serializer.errors)

    def test_tampered_values_cannot_bypass_validation(self):
        # Valeurs incohérentes envoyées directement depuis le navigateur.
        serializer = SessionSerializer(
            data=self._payload(
                niveau="MAS",
                semestre_id=self.s7.id,
                filiere_id=self.filiere_sdia.id,
                module_id=self.module_autre.id,
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertTrue(
            {"filiere_id", "semestre_id", "module_id"} & set(serializer.errors.keys())
        )
