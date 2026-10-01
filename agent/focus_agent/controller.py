import time
import uuid
from datetime import datetime, timezone
from .allowlist import validate_apps, PROTECTED


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


class Controller:
    def __init__(self, adapter, store, clock=time.time):
        self.adapter = adapter
        self.store = store
        self.clock = clock
        self.session = store.get("session")
        self.last_result = {}
        self.last_result = adapter.exit_focus("restart")
        if self.session and self.session.get("activated"):
            self.exit_focus("restart")
        elif self.session:
            self.session = None
            self.store.set("session", None)

    def enter_focus(self, options):
        if self.session:
            raise ValueError("A session is already active")
        if self.adapter.get_state()["pending_restore"]:
            raise ValueError("Restore pending windows before starting another session")
        duration = options.get("durationMin")
        if type(duration) != int or not 1 <= duration <= 240:
            raise ValueError("Duration must be 1–240 whole minutes")
        if options.get("confirmed") is not True:
            raise ValueError("Explicit confirmation is required")
        apps = validate_apps(options.get("apps", []))
        now = self.clock()
        self.session = {
            "session_id": str(uuid.uuid4()),
            "started_at": iso(now),
            "start": now,
            "deadline": now + duration * 60,
            "planned_minutes": duration,
            "apps": apps,
            "source": options.get("source", "MANUAL"),
            "mode": self.adapter.mode,
        }
        self.store.set("session", self.session)
        try:
            self.last_result = self.adapter.enter_focus({"apps": apps})
        except Exception:
            self.last_result = self.adapter.exit_focus("activation_failed")
            self.session = None
            self.store.set("session", None)
            raise
        self.session["activated"] = True
        self.store.transition(
            self.session,
            "started",
            {
                k: self.session[k]
                for k in [
                    "session_id",
                    "started_at",
                    "planned_minutes",
                    "source",
                    "mode",
                ]
            },
        )
        return self.get_state()

    def exit_focus(self, reason="manual"):
        self.last_result = self.adapter.exit_focus(reason)
        if self.session:
            end = (
                min(self.clock(), self.session["deadline"])
                if reason == "timer"
                else self.clock()
            )
            self.store.transition(
                None,
                "ended",
                {
                    "session_id": self.session["session_id"],
                    "ended_at": iso(max(end, self.session["start"])),
                    "reason": reason,
                },
            )
            self.session = None
        return self.get_state()

    def tick(self):
        if self.session and self.clock() >= self.session["deadline"]:
            self.exit_focus("timer")
            return True
        return False

    def get_state(self):
        return {
            "focus": "FOCUSING" if self.session else "IDLE",
            "session": self.session,
            "remaining": (
                max(0, int(self.session["deadline"] - self.clock()))
                if self.session
                else 0
            ),
            "protected": sorted(PROTECTED),
            "result": self.last_result,
            **self.adapter.get_state(),
        }
