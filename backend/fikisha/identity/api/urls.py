from __future__ import annotations

from django.urls import path

from fikisha.identity.api import views

app_name = "identity"

urlpatterns = [
    # ─── Auth ────────────────────────────────────────────────────────
    path("auth/otp/request", views.OtpRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify", views.OtpVerifyView.as_view(), name="otp-verify"),
    path("auth/refresh", views.RefreshView.as_view(), name="refresh"),
    path("auth/logout", views.LogoutView.as_view(), name="logout"),
    # ─── Profile / sessions ─────────────────────────────────────────
    path("me", views.MeView.as_view(), name="me"),
    path("me/sessions", views.SessionListView.as_view(), name="session-list"),
    path("me/sessions/<uuid:session_id>", views.SessionRevokeView.as_view(), name="session-revoke"),
    # ─── Foundation ────────────────────────────────────────────────
    path("reference", views.ConfigPublicView.as_view(), name="reference"),
    path("admin/ping", views.AdminPingView.as_view(), name="admin-ping"),
    # ─── Dev-only demo (also DEBUG + feature-flag gated) ───────────
    path("_demo/atomic-outbox", views.DemoAtomicOutboxView.as_view(), name="demo-atomic-outbox"),
]
