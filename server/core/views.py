import hashlib
import secrets
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    PermissionDenied,
)
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    User,
    Device,
    FocusSession,
    AgentEvent,
    AllowList,
    Schedule,
    Preset,
    Download,
    MissedRun,
)
from .serializers import (
    ProfileSerializer,
    DeviceSerializer,
    SessionSerializer,
    ScheduleSerializer,
    PresetSerializer,
    DownloadSerializer,
    apps_validator,
)
from .api import ok, paginate

PROTECTED = ["Browsers", "Focus Mode agent", "Windows system and security applications"]


def password_check(password, user=None):
    if not isinstance(password, str):
        raise ValidationError("Password required")
    try:
        validate_password(password, user)
    except DjangoValidationError as e:
        raise ValidationError({"password": e.messages})


def tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh["ver"] = user.token_version
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": ProfileSerializer(user).data,
    }


class AuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, action):
        if action == "refresh":
            try:
                old = RefreshToken(request.data.get("refresh", ""))
                user = User.objects.get(
                    id=old["user_id"], is_active=True, token_version=old.get("ver")
                )
                old.blacklist()
                return ok(tokens(user))
            except Exception:
                raise AuthenticationFailed("Refresh token expired or revoked")
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        if action == "register":
            from django.core.validators import validate_email

            try:
                validate_email(email)
            except DjangoValidationError:
                raise ValidationError({"email": "Enter a valid email"})
            if User.objects.filter(email=email).exists():
                raise ValidationError({"email": "Account already exists"})
            name = str(request.data.get("name", "")).strip()
            if not name or len(name) > 100:
                raise ValidationError({"name": "Name is required (max 100 characters)"})
            password_check(password)
            user = User.objects.create_user(
                username=email, email=email, password=password, first_name=name
            )
            return ok(tokens(user), 201)
        if action != "login":
            raise ValidationError("Unknown authentication action")
        user = authenticate(username=email, password=password)
        if user is None:
            raise AuthenticationFailed("Email or password is incorrect")
        return ok(tokens(user))


class MeView(APIView):
    def get(self, request):
        return ok(ProfileSerializer(request.user).data)

    def patch(self, request):
        s = ProfileSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return ok(s.data)


class LogoutView(APIView):
    def post(self, request):
        request.user.token_version += 1
        request.user.save(update_fields=["token_version"])
        return ok(
            {
                "message": "All account login tokens revoked; paired devices remain paired"
            }
        )


class PasswordView(APIView):
    def post(self, request):
        if not request.user.check_password(request.data.get("old_password", "")):
            raise ValidationError("Current password is incorrect")
        password = request.data.get("password")
        password_check(password, request.user)
        request.user.set_password(password)
        request.user.token_version += 1
        request.user.save()
        return ok({"message": "Password changed. Log in again."})


class DevicesView(APIView):
    def get(self, request):
        return ok(
            paginate(
                Device.objects.filter(owner=request.user, revoked=False).order_by(
                    "-paired_at"
                ),
                request,
                DeviceSerializer,
            )
        )

    def post(self, request):
        name = request.data.get("name")
        platform = request.data.get("os")
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 100
            or platform not in ["windows", "mock"]
        ):
            raise ValidationError("Valid device name and OS required")
        secret = secrets.token_urlsafe(32)
        device = Device.objects.create(
            owner=request.user,
            name=name,
            os=platform,
            credential_hash=hashlib.sha256(secret.encode()).hexdigest(),
        )
        return ok({"device": DeviceSerializer(device).data, "credential": secret}, 201)

    def delete(self, request, pk=None):
        query = Device.objects.filter(owner=request.user, revoked=False)
        if pk:
            query = query.filter(pk=pk)
        query.update(revoked=True)
        return ok({"revoked": True})


def agent_device(request):
    try:
        device = Device.objects.get(
            id=request.headers.get("X-Device-ID"), revoked=False, owner__is_active=True
        )
    except (Device.DoesNotExist, DjangoValidationError, ValueError):
        raise AuthenticationFailed("Device revoked or unknown")
    candidate = hashlib.sha256(
        request.headers.get("X-Device-Key", "").encode()
    ).hexdigest()
    if not secrets.compare_digest(candidate, device.credential_hash):
        raise AuthenticationFailed("Invalid device credential")
    return device


class AgentConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def delete(self, request):
        d = agent_device(request)
        d.revoked = True
        d.save(update_fields=["revoked"])
        return ok({"revoked": True})

    def get(self, request):
        d = agent_device(request)
        d.last_seen = timezone.now()
        d.save(update_fields=["last_seen"])
        allow, _ = AllowList.objects.get_or_create(owner=d.owner)
        return ok(
            {
                "owner_id": d.owner_id,
                "apps": allow.apps,
                "schedules": ScheduleSerializer(
                    Schedule.objects.filter(device=d), many=True
                ).data,
            }
        )


class AgentEventsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        device = agent_device(request)
        try:
            event_id = uuid.UUID(request.data["event_id"])
        except (KeyError, ValueError, TypeError):
            raise ValidationError("Valid event_id required")
        _, created = AgentEvent.objects.get_or_create(
            id=event_id, defaults={"device": device}
        )
        if not created:
            if not AgentEvent.objects.filter(id=event_id, device=device).exists():
                raise PermissionDenied()
            return ok({"duplicate": True})
        kind = request.data.get("kind")
        data = request.data.get("data", {})
        if not isinstance(data, dict):
            raise ValidationError("Invalid event data")

        def date(key):
            try:
                result = parse_datetime(data[key])
            except (KeyError, TypeError, ValueError):
                result = None
            if not result or timezone.is_naive(result):
                raise ValidationError("Timezone-aware timestamp required")
            if result > timezone.now() + timedelta(minutes=5):
                raise ValidationError("Future event timestamp")
            return result

        if kind == "missed":
            occurrence = data.get("occurrence", "")
            if not isinstance(occurrence, str) or not 1 <= len(occurrence) <= 120:
                raise ValidationError("Invalid occurrence")
            MissedRun.objects.get_or_create(
                device=device,
                occurrence=occurrence,
                defaults={
                    "reason": str(data.get("reason", "offline"))[:100],
                    "at": date("at"),
                },
            )
        elif kind in ["started", "ended"]:
            try:
                sid = uuid.UUID(data["session_id"])
            except (KeyError, ValueError, TypeError):
                raise ValidationError("Invalid session ID")
            if kind == "started":
                minutes = data.get("planned_minutes")
                if type(minutes) != int or not 1 <= minutes <= 240:
                    raise ValidationError("Duration must be 1–240 minutes")
                if data.get("source") not in ["MANUAL", "SCHEDULE"] or data.get(
                    "mode"
                ) not in ["mock", "windows"]:
                    raise ValidationError("Invalid source/mode")
                existing = FocusSession.objects.filter(id=sid).first()
                if existing and existing.device_id != device.id:
                    raise PermissionDenied()
                FocusSession.objects.get_or_create(
                    id=sid,
                    defaults={
                        "device": device,
                        "started_at": date("started_at"),
                        "planned_minutes": minutes,
                        "source": data["source"],
                        "mode": data["mode"],
                    },
                )
            else:
                session = get_object_or_404(FocusSession, id=sid, device=device)
                if not session.ended_at:
                    ended = date("ended_at")
                    if ended < session.started_at:
                        raise ValidationError("End precedes start")
                    session.ended_at = ended
                    session.actual_seconds = min(
                        int((ended - session.started_at).total_seconds()),
                        session.planned_minutes * 60,
                    )
                    reason = str(data.get("reason", "manual"))[:100]
                    session.status = "COMPLETED" if reason == "timer" else "CANCELLED"
                    session.reason = reason
                    session.save()
        else:
            raise ValidationError("Unknown event kind")
        return ok({"stored": True})


class SessionsView(APIView):
    def get(self, request):
        q = (
            FocusSession.objects.filter(device__owner=request.user)
            .select_related("device")
            .order_by("-started_at")
        )
        if request.query_params.get("status"):
            q = q.filter(status=request.query_params["status"])
        for key, lookup in [
            ("from", "started_at__date__gte"),
            ("to", "started_at__date__lte"),
        ]:
            if request.query_params.get(key):
                value = parse_date(request.query_params[key])
                if not value:
                    raise ValidationError("Use YYYY-MM-DD dates")
                q = q.filter(**{lookup: value})
        if request.query_params.get("search"):
            q = q.filter(device__name__icontains=request.query_params["search"])
        return ok(paginate(q, request, SessionSerializer))


class AllowListView(APIView):
    def get(self, request):
        a, _ = AllowList.objects.get_or_create(owner=request.user)
        return ok(
            {
                "protected": PROTECTED,
                "apps": a.apps,
                "presets": PresetSerializer(Preset.objects.all(), many=True).data,
            }
        )

    def put(self, request):
        if "protected" in request.data:
            raise ValidationError("Protected entries cannot be changed")
        apps = apps_validator(request.data.get("apps"))
        AllowList.objects.update_or_create(owner=request.user, defaults={"apps": apps})
        return self.get(request)


class SchedulesView(APIView):
    def get(self, request):
        return ok(
            ScheduleSerializer(
                Schedule.objects.filter(owner=request.user).order_by("start_time"),
                many=True,
            ).data
        )

    def post(self, request):
        s = ScheduleSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save(owner=request.user)
        return ok(s.data, 201)

    def patch(self, request, pk):
        s = ScheduleSerializer(
            get_object_or_404(Schedule, pk=pk, owner=request.user),
            data=request.data,
            partial=True,
            context={"request": request},
        )
        s.is_valid(raise_exception=True)
        s.save()
        return ok(s.data)

    def delete(self, request, pk):
        get_object_or_404(Schedule, pk=pk, owner=request.user).delete()
        return ok()


class InsightsView(APIView):
    def get(self, request):
        tz = ZoneInfo(request.user.timezone)
        today = timezone.now().astimezone(tz).date()
        rows = list(
            FocusSession.objects.filter(
                device__owner=request.user, ended_at__isnull=False, mode="windows"
            )
        )
        days = {}
        hours = {}
        for row in rows:
            local = row.started_at.astimezone(tz)
            day = local.date()
            days[day] = days.get(day, 0) + row.actual_seconds
            hours[local.hour] = hours.get(local.hour, 0) + row.actual_seconds
        streak = 0
        cursor = today if days.get(today, 0) > 0 else today - timedelta(days=1)
        while days.get(cursor, 0) > 0:
            streak += 1
            cursor -= timedelta(days=1)
        return ok(
            {
                "total_seconds": sum(x.actual_seconds for x in rows),
                "today_seconds": days.get(today, 0),
                "sessions": len(rows),
                "streak": streak,
                "completion_rate": (
                    round(100 * sum(x.status == "COMPLETED" for x in rows) / len(rows))
                    if rows
                    else 0
                ),
                "best_hour": max(hours, key=hours.get) if hours else None,
                "daily": [
                    {
                        "date": str(today - timedelta(days=i)),
                        "seconds": days.get(today - timedelta(days=i), 0),
                    }
                    for i in reversed(range(7))
                ],
                "missed": list(
                    MissedRun.objects.filter(device__owner=request.user)
                    .order_by("-at")
                    .values("occurrence", "at", "reason")[:20]
                ),
            }
        )


class DownloadsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return ok(DownloadSerializer(Download.objects.all(), many=True).data)


class AdminView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.order_by("id")
        if request.query_params.get("search"):
            users = users.filter(email__icontains=request.query_params["search"])
        return ok(
            {
                "users": paginate(users, request, ProfileSerializer),
                "presets": PresetSerializer(Preset.objects.all(), many=True).data,
                "downloads": DownloadSerializer(Download.objects.all(), many=True).data,
                "stats": {
                    "users": User.objects.count(),
                    "devices": Device.objects.filter(revoked=False).count(),
                    "sessions": FocusSession.objects.count(),
                    "seconds": FocusSession.objects.filter(
                        mode="windows", ended_at__isnull=False
                    ).aggregate(total=Sum("actual_seconds"))["total"]
                    or 0,
                },
            }
        )

    def post(self, request, resource):
        cls = {"presets": PresetSerializer, "downloads": DownloadSerializer}.get(
            resource
        )
        if not cls:
            raise ValidationError("Unknown resource")
        s = cls(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return ok(s.data, 201)

    def patch(self, request, resource, pk):
        if resource == "users":
            u = get_object_or_404(User, pk=pk)
            if u == request.user:
                raise ValidationError("Cannot deactivate your own admin account")
            active = request.data.get("is_active")
            if type(active) != bool:
                raise ValidationError("is_active must be boolean")
            u.is_active = active
            u.token_version += 1
            u.save()
            return ok(ProfileSerializer(u).data)
        cls, model = {
            "presets": (PresetSerializer, Preset),
            "downloads": (DownloadSerializer, Download),
        }.get(resource, (None, None))
        if not cls:
            raise ValidationError("Unknown resource")
        s = cls(get_object_or_404(model, pk=pk), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return ok(s.data)

    def delete(self, request, resource, pk):
        model = {"presets": Preset, "downloads": Download}.get(resource)
        if not model:
            raise ValidationError("Unknown resource")
        get_object_or_404(model, pk=pk).delete()
        return ok()
