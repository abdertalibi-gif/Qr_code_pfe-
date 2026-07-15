import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import ContactMessage

User = get_user_model()


class ContactMessageAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.ma",
            password="test1234",
            role="admin",
            first_name="Admin",
            last_name="Test",
        )
        self.teacher = User.objects.create_user(
            email="teacher@test.ma",
            password="test1234",
            role="teacher",
            first_name="Teacher",
            last_name="Test",
        )

    # ── Public submission ──

    def test_create_message_success(self):
        data = {
            "name": "Jean Dupont",
            "email": "jean@example.com",
            "subject": "Question test",
            "message": "Ceci est un message de test.",
        }
        response = self.client.post(
            "/api/v1/contact-messages/create/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("envoyé avec succès", response.data["detail"])
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, "Jean Dupont")
        self.assertEqual(msg.email, "jean@example.com")
        self.assertEqual(msg.subject, "Question test")
        self.assertEqual(msg.message, "Ceci est un message de test.")
        self.assertEqual(msg.status, "Nouveau")

    def test_create_message_missing_fields(self):
        response = self.client.post(
            "/api/v1/contact-messages/create/",
            {"name": "", "email": "", "subject": "", "message": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertIn("email", response.data)
        self.assertIn("subject", response.data)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["name"][0], "Le nom est obligatoire.")
        self.assertEqual(response.data["email"][0], "L'email est obligatoire.")
        self.assertEqual(response.data["subject"][0], "Le sujet est obligatoire.")
        self.assertEqual(response.data["message"][0], "Le message est obligatoire.")

    def test_create_message_invalid_email(self):
        response = self.client.post(
            "/api/v1/contact-messages/create/",
            {"name": "Test", "email": "pas-un-email", "subject": "Sujet", "message": "Message"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_create_message_requires_no_auth(self):
        response = self.client.post(
            "/api/v1/contact-messages/create/",
            {"name": "Test", "email": "test@test.com", "subject": "S", "message": "M"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    @patch("users.views.send_mail")
    def test_create_message_sends_email(self, mock_send_mail):
        data = {
            "name": "Jean Dupont",
            "email": "jean@example.com",
            "subject": "Test",
            "message": "Message test",
        }
        response = self.client.post("/api/v1/contact-messages/create/", data, format="json")
        self.assertEqual(response.status_code, 201)
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertIn("Nouveau message", kwargs["subject"])
        self.assertEqual(kwargs["recipient_list"], ["admin@umi.ac.ma"])
        self.assertIn("Jean Dupont", kwargs["message"])

    # ── Admin list ──

    def test_admin_list_messages(self):
        ContactMessage.objects.create(
            name="A", email="a@a.com", subject="S1", message="M1"
        )
        ContactMessage.objects.create(
            name="B", email="b@b.com", subject="S2", message="M2", status="Lu"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/contact-messages/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_admin_list_filter_nouveau(self):
        ContactMessage.objects.create(
            name="A", email="a@a.com", subject="S1", message="M1"
        )
        ContactMessage.objects.create(
            name="B", email="b@b.com", subject="S2", message="M2", status="Lu"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/contact-messages/?status=Nouveau")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)

    def test_admin_list_search(self):
        ContactMessage.objects.create(
            name="Jean", email="jean@test.com", subject="Question", message="M1"
        )
        ContactMessage.objects.create(
            name="Pierre", email="pierre@test.com", subject="Info", message="M2"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/contact-messages/?search=jean")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Jean")

    def test_admin_list_requires_auth(self):
        response = self.client.get("/api/v1/contact-messages/")
        self.assertEqual(response.status_code, 401)

    def test_admin_list_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/v1/contact-messages/")
        self.assertEqual(response.status_code, 403)

    # ── Admin detail / PATCH / DELETE ──

    def test_admin_get_detail(self):
        msg = ContactMessage.objects.create(
            name="Test", email="t@t.com", subject="S", message="M"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/v1/contact-messages/{msg.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test")
        self.assertIn("status", response.data)

    def test_admin_mark_as_traite(self):
        msg = ContactMessage.objects.create(
            name="Test", email="t@t.com", subject="S", message="M"
        )
        self.assertEqual(msg.status, "Nouveau")
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/v1/contact-messages/{msg.id}/",
            {"status": "Traité"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, "Traité")

    def test_admin_mark_as_lu(self):
        msg = ContactMessage.objects.create(
            name="Test", email="t@t.com", subject="S", message="M"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/v1/contact-messages/{msg.id}/",
            {"status": "Lu"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, "Lu")

    def test_admin_delete_message(self):
        msg = ContactMessage.objects.create(
            name="Test", email="t@t.com", subject="S", message="M"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/v1/contact-messages/{msg.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_admin_detail_not_found(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/contact-messages/999/")
        self.assertEqual(response.status_code, 404)


class LandingStatsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_landing_stats_returns_all_keys(self):
        response = self.client.get("/api/v1/landing-stats/")
        self.assertEqual(response.status_code, 200)
        expected = {"students", "teachers", "classes", "modules", "sessions",
                    "departments", "filieres", "attendances", "present",
                    "absent", "attendance_rate", "total_hours"}
        self.assertEqual(set(response.data.keys()), expected)

    def test_landing_stats_requires_no_auth(self):
        response = self.client.get("/api/v1/landing-stats/")
        self.assertEqual(response.status_code, 200)

    def test_landing_stats_counts_are_non_negative(self):
        response = self.client.get("/api/v1/landing-stats/")
        for key, val in response.data.items():
            with self.subTest(key=key):
                self.assertGreaterEqual(val, 0, f"{key} should be >= 0")
