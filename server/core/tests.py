import uuid
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Device, FocusSession


class APITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="one@example.com",
            email="one@example.com",
            password="StrongPass!2026",
        )
        self.other = User.objects.create_user(
            username="two@example.com",
            email="two@example.com",
            password="StrongPass!2026",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        r = self.client.post(
            "/api/v1/devices/pair", {"name": "Test PC", "os": "mock"}, format="json"
        ).data["data"]
        self.device = r["device"]["id"]
        self.secret = r["credential"]

    def test_ownership_and_roles(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/devices").data["data"]["total"], 0)
        self.assertEqual(self.client.get("/api/v1/admin").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/schedules",
                {
                    "name": "Bad",
                    "device": self.device,
                    "days": [0],
                    "start_time": "09:00",
                    "timezone": "UTC",
                    "duration_minutes": 25,
                    "consent": True,
                    "enabled": True,
                },
                format="json",
            ).status_code,
            400,
        )
        self.client.delete("/api/v1/devices/" + self.device)
        self.assertFalse(Device.objects.get(id=self.device).revoked)

    def test_logout_revokes_access_and_refresh(self):
        client = APIClient()
        data = client.post(
            "/api/v1/auth/login",
            {"email": self.user.email, "password": "StrongPass!2026"},
            format="json",
        ).data["data"]
        client.credentials(HTTP_AUTHORIZATION="Bearer " + data["access"])
        self.assertEqual(client.get("/api/v1/auth/me").status_code, 200)
        self.assertEqual(client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(client.get("/api/v1/auth/me").status_code, 401)
        client.credentials()
        self.assertEqual(
            client.post(
                "/api/v1/auth/refresh", {"refresh": data["refresh"]}, format="json"
            ).status_code,
            401,
        )

    def test_protected_and_schedule_validation(self):
        self.assertEqual(
            self.client.put(
                "/api/v1/allowlist", {"apps": [], "protected": []}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/allowlist", {"apps": ["../../bad"]}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/allowlist", {"apps": ["Code.exe"]}, format="json"
            ).status_code,
            200,
        )
        body = {
            "name": "Study",
            "device": self.device,
            "days": [0, 2],
            "start_time": "09:00",
            "timezone": "Bad/Zone",
            "duration_minutes": 25,
            "consent": True,
            "enabled": True,
        }
        self.assertEqual(
            self.client.post("/api/v1/schedules", body, format="json").status_code, 400
        )
        body.update(timezone="Asia/Kolkata", consent=False)
        self.assertEqual(
            self.client.post("/api/v1/schedules", body, format="json").status_code, 400
        )

    def test_agent_event_retry_and_revocation(self):
        client = APIClient()
        client.credentials(HTTP_X_DEVICE_ID=self.device, HTTP_X_DEVICE_KEY=self.secret)
        start = timezone.now() - timedelta(minutes=25)
        sid = str(uuid.uuid4())
        event = {
            "event_id": str(uuid.uuid4()),
            "kind": "started",
            "data": {
                "session_id": sid,
                "started_at": start.isoformat(),
                "planned_minutes": 25,
                "source": "MANUAL",
                "mode": "windows",
            },
        }
        for _ in range(2):
            self.assertEqual(
                client.post("/api/v1/agent/events", event, format="json").status_code,
                200,
            )
        event = {
            "event_id": str(uuid.uuid4()),
            "kind": "ended",
            "data": {
                "session_id": sid,
                "ended_at": timezone.now().isoformat(),
                "reason": "timer",
            },
        }
        for _ in range(2):
            self.assertEqual(
                client.post("/api/v1/agent/events", event, format="json").status_code,
                200,
            )
        self.assertEqual(FocusSession.objects.count(), 1)
        stats = self.client.get("/api/v1/insights").data["data"]
        self.assertEqual(stats["total_seconds"], 1500)
        self.assertEqual(stats["completion_rate"], 100)
        self.client.delete("/api/v1/devices/" + self.device)
        self.assertEqual(client.get("/api/v1/agent/config").status_code, 403)

    def test_mock_excluded_and_filters(self):
        FocusSession.objects.create(
            id=uuid.uuid4(),
            device_id=self.device,
            started_at=timezone.now() - timedelta(minutes=3),
            ended_at=timezone.now(),
            planned_minutes=25,
            actual_seconds=180,
            status="CANCELLED",
            mode="mock",
        )
        self.assertEqual(
            self.client.get("/api/v1/insights").data["data"]["total_seconds"], 0
        )
        self.assertEqual(
            self.client.get("/api/v1/sessions?status=CANCELLED").data["data"]["total"],
            1,
        )
        self.assertEqual(
            self.client.get("/api/v1/sessions?status=COMPLETED").data["data"]["total"],
            0,
        )

    def test_registration_password_hash_and_public_boundaries(self):
        c = APIClient()
        self.assertEqual(c.get("/api/v1/sessions").status_code, 401)
        self.assertEqual(
            c.post(
                "/api/v1/auth/register",
                {"name": "New", "email": "new@example.com", "password": "short"},
                format="json",
            ).status_code,
            400,
        )
        self.assertTrue(self.user.password.startswith("bcrypt_sha256$"))
