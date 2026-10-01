import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from focus_agent.storage import Store, protect
from focus_agent.pairing import Pairing
from focus_agent.controller import Controller
from focus_agent.windows import MockAdapter
from focus_agent.allowlist import protected, validate_apps
from focus_agent.schedules import Scheduler


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.now = 1000000
        self.adapter = MockAdapter(self.store)
        self.controller = Controller(self.adapter, self.store, lambda: self.now)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def start(self):
        return self.controller.enter_focus(
            {"durationMin": 1, "confirmed": True, "apps": ["code.exe"]}
        )

    def test_pair_codes_wrong_expired_reused(self):
        p = Pairing()
        code = p.code
        with self.assertRaises(ValueError):
            p.consume("not-it")
        p.consume(code)
        with self.assertRaises(ValueError):
            p.consume(code)
        p.rotate()
        p.expires = 0
        with self.assertRaises(ValueError):
            p.consume(p.code)
        p.rotate()
        for _ in range(5):
            with self.assertRaises(ValueError):
                p.consume("wrong")
        with self.assertRaises(ValueError):
            p.consume(p.code)

    def test_duplicate_start_repeated_stop_and_timer(self):
        self.start()
        with self.assertRaises(ValueError):
            self.start()
        self.now += 61
        self.assertTrue(self.controller.tick())
        self.controller.exit_focus()
        self.controller.exit_focus()
        self.assertEqual(
            [event["kind"] for _, event in self.store.pending()], ["started", "ended"]
        )
        self.assertEqual(self.controller.get_state()["focus"], "IDLE")

    def test_browser_closed_and_sleep(self):
        self.start()
        self.now += 30
        self.assertFalse(self.controller.tick())
        self.assertEqual(self.controller.get_state()["remaining"], 30)
        self.now += 600
        self.controller.tick()
        self.assertEqual(self.controller.get_state()["focus"], "IDLE")

    def test_restart_recovery_and_outage_queue(self):
        self.start()
        self.now += 10
        recovered = Controller(self.adapter, self.store, lambda: self.now)
        self.assertEqual(recovered.get_state()["focus"], "IDLE")
        events = self.store.pending()
        self.assertEqual(len(events), 2)
        self.store.db.close()
        self.store = Store(self.tmp.name)
        self.assertEqual(len(self.store.pending()), 2)
        self.store.ack(events[0][0])
        self.assertEqual(len(self.store.pending()), 1)

    def test_activation_failure_rolls_back(self):
        with patch.object(
            self.adapter, "enter_focus", side_effect=RuntimeError("failed")
        ), patch.object(
            self.adapter, "exit_focus", return_value={"restore_failures": 0}
        ) as restore:
            with self.assertRaises(RuntimeError):
                self.start()
            restore.assert_called_once()
        self.assertEqual(self.controller.get_state()["focus"], "IDLE")
        self.assertEqual(self.store.pending(), [])

    def test_safety_and_validation(self):
        self.assertTrue(protected(r"C:\Apps\chrome.exe", []))
        self.assertTrue(protected(r"C:\Windows\security.exe", []))
        self.assertTrue(protected(r"C:\Apps\Code.exe", ["code.exe"]))
        with self.assertRaises(ValueError):
            validate_apps(["cmd.exe & do bad"])
        with self.assertRaises(ValueError):
            self.controller.enter_focus({"durationMin": 1, "apps": []})
        with self.assertRaises(ValueError):
            self.controller.enter_focus(
                {"durationMin": True, "confirmed": True, "apps": []}
            )

    def test_schedules_headsup_dedup_missed(self):
        now = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc).timestamp()
        self.now = now
        schedule = {
            "id": 1,
            "enabled": True,
            "consent": True,
            "days": [3],
            "start_time": "09:00:00",
            "timezone": "UTC",
            "duration_minutes": 25,
        }
        self.store.set("schedule_checked", now - 5)
        notices = []
        scheduler = Scheduler(self.store, self.controller, notices.append)
        scheduler.tick([schedule], [], now)
        self.assertEqual(len(notices), 1)
        self.assertIsNone(self.controller.session)
        self.now += 16
        scheduler.tick([schedule], [], self.now)
        self.assertIsNotNone(self.controller.session)
        scheduler.tick([schedule], [], self.now)
        self.assertEqual(len(notices), 1)
        self.controller.exit_focus()
        self.store.set("schedule_checked", now - 86400)
        self.store.set("schedule_seen", [])
        scheduler.tick([schedule], [], now + 100)
        self.assertEqual(self.store.pending()[-1][1]["kind"], "missed")

    def test_dpapi_roundtrip(self):
        import os

        if os.name != "nt":
            self.skipTest("Windows only")
        encrypted = protect(b"secret")
        self.assertNotEqual(encrypted, b"secret")
        self.assertEqual(protect(encrypted, True), b"secret")


if __name__ == "__main__":
    unittest.main()
