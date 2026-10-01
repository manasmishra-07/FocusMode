from django.urls import path
from core import views as v

urlpatterns = [
    path("api/v1/auth/me", v.MeView.as_view()),
    path("api/v1/auth/logout", v.LogoutView.as_view()),
    path("api/v1/auth/password", v.PasswordView.as_view()),
    path("api/v1/auth/<str:action>", v.AuthView.as_view()),
    path("api/v1/devices", v.DevicesView.as_view()),
    path("api/v1/devices/pair", v.DevicesView.as_view()),
    path("api/v1/devices/<uuid:pk>", v.DevicesView.as_view()),
    path("api/v1/agent/config", v.AgentConfigView.as_view()),
    path("api/v1/agent/events", v.AgentEventsView.as_view()),
    path("api/v1/sessions", v.SessionsView.as_view()),
    path("api/v1/allowlist", v.AllowListView.as_view()),
    path("api/v1/schedules", v.SchedulesView.as_view()),
    path("api/v1/schedules/<int:pk>", v.SchedulesView.as_view()),
    path("api/v1/insights", v.InsightsView.as_view()),
    path("api/v1/downloads", v.DownloadsView.as_view()),
    path("api/v1/admin", v.AdminView.as_view()),
    path("api/v1/admin/<str:resource>", v.AdminView.as_view()),
    path("api/v1/admin/<str:resource>/<int:pk>", v.AdminView.as_view()),
]
