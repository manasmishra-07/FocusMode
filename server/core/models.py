import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    email = models.EmailField(unique=True)
    default_duration = models.PositiveIntegerField(default=25)
    notifications = models.BooleanField(default=True)
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    token_version = models.PositiveIntegerField(default=0)


class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    os = models.CharField(max_length=32)
    credential_hash = models.CharField(max_length=64)
    paired_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    revoked = models.BooleanField(default=False)


class FocusSession(models.Model):
    id = models.UUIDField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    planned_minutes = models.PositiveIntegerField()
    actual_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, default="ACTIVE")
    source = models.CharField(max_length=16, default="MANUAL")
    mode = models.CharField(max_length=16, default="windows")
    reason = models.CharField(max_length=100, blank=True)


class AgentEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    received_at = models.DateTimeField(auto_now_add=True)


class AllowList(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    apps = models.JSONField(default=list)


class Schedule(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    days = models.JSONField(default=list)
    start_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    duration_minutes = models.PositiveIntegerField(default=25)
    enabled = models.BooleanField(default=False)
    consent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class MissedRun(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    occurrence = models.CharField(max_length=120)
    reason = models.CharField(max_length=100)
    at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["device", "occurrence"], name="unique_missed_run"
            )
        ]


class Preset(models.Model):
    name = models.CharField(max_length=80)
    apps = models.JSONField(default=list)


class Download(models.Model):
    platform = models.CharField(max_length=32, unique=True)
    url = models.URLField(blank=True)
    version = models.CharField(max_length=30, default="1.0.0")
