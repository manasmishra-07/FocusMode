import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from rest_framework import serializers
from .models import Device, FocusSession, Schedule, Preset, Download, User


def apps_validator(value):
    if (
        not isinstance(value, list)
        or len(value) > 50
        or any(
            not isinstance(a, str)
            or not re.fullmatch(r"[\w .-]{1,80}\.exe", a, re.ASCII)
            for a in value
        )
    ):
        raise serializers.ValidationError(
            "Use up to 50 executable names, for example Code.exe."
        )
    return sorted(set(a.lower() for a in value))


def timezone_validator(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise serializers.ValidationError("Unknown IANA timezone")
    return value


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        return "ADMIN" if obj.is_staff else "USER"

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "role",
            "default_duration",
            "notifications",
            "timezone",
            "is_active",
        ]
        read_only_fields = ["id", "email", "role", "is_active"]

    def validate_default_duration(self, v):
        if not 1 <= v <= 240:
            raise serializers.ValidationError("Choose 1–240 minutes")
        return v

    validate_timezone = staticmethod(timezone_validator)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "name", "os", "paired_at", "last_seen", "revoked"]


class SessionSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name")

    class Meta:
        model = FocusSession
        fields = [
            "id",
            "device",
            "device_name",
            "started_at",
            "ended_at",
            "planned_minutes",
            "actual_seconds",
            "status",
            "source",
            "mode",
            "reason",
        ]


class ScheduleSerializer(serializers.ModelSerializer):
    next_at = serializers.SerializerMethodField()

    def get_next_at(self, obj):
        from datetime import datetime, timedelta
        from django.utils import timezone

        if not obj.enabled or not obj.consent:
            return None
        zone = ZoneInfo(obj.timezone)
        now = timezone.now()
        today = now.astimezone(zone).date()
        for offset in range(8):
            day = today + timedelta(days=offset)
            if day.weekday() not in obj.days:
                continue
            candidate = datetime.combine(day, obj.start_time, tzinfo=zone)
            if candidate > now:
                return candidate.isoformat()
        return None

    class Meta:
        model = Schedule
        fields = [
            "id",
            "device",
            "name",
            "days",
            "start_time",
            "timezone",
            "duration_minutes",
            "enabled",
            "consent",
            "created_at",
            "next_at",
        ]
        read_only_fields = ["created_at"]

    def validate_device(self, v):
        if v.owner_id != self.context["request"].user.id or v.revoked:
            raise serializers.ValidationError("Select your own paired device")
        return v

    def validate_days(self, v):
        if (
            not isinstance(v, list)
            or not v
            or any(type(d) != int or d not in range(7) for d in v)
        ):
            raise serializers.ValidationError(
                "Choose weekdays 0 (Monday) through 6 (Sunday)"
            )
        return sorted(set(v))

    def validate_duration_minutes(self, v):
        if not 1 <= v <= 240:
            raise serializers.ValidationError("Choose 1–240 minutes")
        return v

    validate_timezone = staticmethod(timezone_validator)

    def validate(self, attrs):
        if attrs.get(
            "enabled", getattr(self.instance, "enabled", False)
        ) and not attrs.get("consent", getattr(self.instance, "consent", False)):
            raise serializers.ValidationError("Explicit schedule consent required")
        return attrs


class PresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preset
        fields = ["id", "name", "apps"]

    validate_apps = staticmethod(apps_validator)


class DownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Download
        fields = ["id", "platform", "url", "version"]

    def validate_url(self, v):
        if v and not v.startswith("https://"):
            raise serializers.ValidationError("Use an HTTPS download URL")
        return v
