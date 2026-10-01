from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .controller import iso


class Scheduler:
    def __init__(self, store, controller, notice):
        self.store = store
        self.controller = controller
        self.notice = notice
        self.pending = None
        self.cancelled = False

    def cancel(self):
        if self.pending:
            self.missed(self.pending["key"], "cancelled locally", self.pending["at"])
            self.pending = None

    def missed(self, key, reason, at):
        self.store.event("missed", {"occurrence": key, "reason": reason, "at": iso(at)})

    def tick(self, schedules, apps, now):
        previous = self.store.get("schedule_checked", now)
        seen = self.store.get("schedule_seen", [])
        for schedule in schedules:
            if not schedule["enabled"] or not schedule["consent"]:
                continue
            tz = ZoneInfo(schedule["timezone"])
            local = datetime.fromtimestamp(now, tz)
            # Bound offline reconciliation to seven days; never run a past occurrence.
            for offset in range(7):
                day = local.date() - timedelta(days=offset)
                if day.weekday() not in schedule["days"]:
                    continue
                hour, minute = map(int, schedule["start_time"].split(":")[:2])
                at = datetime(
                    day.year, day.month, day.day, hour, minute, tzinfo=tz
                ).timestamp()
                key = f"{schedule['id']}:{day}"
                if key in seen or not previous < at <= now:
                    continue
                seen.append(key)
                if now - at > 15 or self.controller.session or self.pending:
                    self.missed(key, "offline, late or overlapping", at)
                    continue
                self.pending = {
                    "key": key,
                    "at": at,
                    "start": now + 15,
                    "schedule": schedule,
                    "apps": apps,
                }
                self.notice(
                    "Scheduled focus starts in 15 seconds. End Focus cancels it."
                )
        self.store.set("schedule_seen", seen[-2000:])
        self.store.set("schedule_checked", now)
        if self.pending and now >= self.pending["start"]:
            pending = self.pending
            self.pending = None
            current = next(
                (s for s in schedules if s["id"] == pending["schedule"]["id"]), None
            )
            if (
                now - pending["start"] > 15
                or not current
                or not current["enabled"]
                or not current["consent"]
            ):
                self.missed(
                    pending["key"], "late or disabled during heads-up", pending["at"]
                )
                return
            try:
                self.controller.enter_focus(
                    {
                        "durationMin": current["duration_minutes"],
                        "apps": apps,
                        "confirmed": True,
                        "source": "SCHEDULE",
                    }
                )
            except Exception as e:
                self.missed(pending["key"], str(e)[:100], pending["at"])
