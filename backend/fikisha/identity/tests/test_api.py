"""End-to-end API foundation tests (Phase 2A brief sections 29-30 and 40).

Covers: the full OTP -> verify -> authenticated request flow, the problem+json
error contract, unauthenticated + malformed-auth rejection, vertical privilege
escalation (admin route), horizontal privilege escalation / IDOR (another user's
session), and the demo endpoint proving audit + outbox atomicity.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from fikisha.audit.models import AuditLogEntry
from fikisha.outbox.models import OutboxEvent, OutboxStatus
from fikisha.outbox.tasks import drain_outbox

pytestmark = pytest.mark.django_db

OTP_REQUEST = "/api/v1/auth/otp/request"
OTP_VERIFY = "/api/v1/auth/otp/verify"


def _login(api: APIClient, phone: str = "+254799000123") -> dict:
    r = api.post(OTP_REQUEST, {"phone": phone}, format="json")
    assert r.status_code == 202, r.content
    challenge_id = r.data["challenge_id"]
    code = r.data["dev_code"]  # present because OTP_DEV_EXPOSE in test settings
    r = api.post(OTP_VERIFY, {"challenge_id": challenge_id, "code": code}, format="json")
    assert r.status_code == 200, r.content
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access_token']}")
    return r.data


class TestAuthFlow:
    def test_full_flow_reaches_me(self, api: APIClient) -> None:
        data = _login(api)
        assert data["user"]["phone"] == "+254799000123"
        r = api.get("/api/v1/me")
        assert r.status_code == 200
        assert r.data["phone"] == "+254799000123"
        assert r.data["is_admin"] is False
        assert r.data["roles"] == []

    def test_refresh_returns_new_access_token(self, api: APIClient) -> None:
        from fikisha.identity.models import RefreshToken

        r = api.post(OTP_REQUEST, {"phone": "+254799000124"}, format="json")
        code, cid = r.data["dev_code"], r.data["challenge_id"]
        r = api.post(OTP_VERIFY, {"challenge_id": cid, "code": code}, format="json")
        assert RefreshToken.objects.filter(used_at__isnull=True).count() == 1

        # The refresh cookie is HttpOnly and scoped to /api/v1/auth/.
        r2 = api.post("/api/v1/auth/refresh", format="json")
        assert r2.status_code == 200
        assert r2.data["access_token"]
        # The refresh token rotated: exactly one live token, and the first is spent.
        assert RefreshToken.objects.filter(used_at__isnull=False).count() == 1
        assert RefreshToken.objects.filter(used_at__isnull=True).count() == 1
        # The new access token still resolves to the same user.
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {r2.data['access_token']}")
        assert api.get("/api/v1/me").data["phone"] == "+254799000124"

    def test_logout_revokes_session(self, api: APIClient) -> None:
        _login(api)
        assert api.post("/api/v1/auth/logout", format="json").status_code == 204
        assert api.get("/api/v1/me").status_code == 401

    def test_bad_otp_returns_problem_json(self, api: APIClient) -> None:
        r = api.post(OTP_REQUEST, {"phone": "+254799000125"}, format="json")
        r = api.post(
            OTP_VERIFY, {"challenge_id": r.data["challenge_id"], "code": "999999"}, format="json"
        )
        assert r.status_code == 401
        assert r["content-type"] == "application/problem+json"
        assert r.data["code"] == "otp.invalid"
        assert "request_id" in r.data


class TestUnauthenticated:
    def test_me_requires_auth(self, api: APIClient) -> None:
        r = api.get("/api/v1/me")
        assert r.status_code == 401
        assert r["content-type"] == "application/problem+json"
        assert r.data["status"] == 401

    def test_malformed_bearer_rejected(self, api: APIClient) -> None:
        api.credentials(HTTP_AUTHORIZATION="Bearer not.a.valid.token")
        r = api.get("/api/v1/me")
        assert r.status_code == 401
        assert r.data["code"] in {"auth.token_invalid", "auth.token_expired"}

    def test_bearer_with_extra_parts_rejected(self, api: APIClient) -> None:
        api.credentials(HTTP_AUTHORIZATION="Bearer a b c")
        r = api.get("/api/v1/me")
        assert r.status_code == 401


class TestPrivilegeEscalation:
    def test_plain_user_cannot_hit_admin_route(self, api: APIClient) -> None:
        _login(api, "+254799000200")
        r = api.get("/api/v1/admin/ping")
        assert r.status_code == 403
        assert r.data["code"] == "authz.forbidden"

    def test_platform_admin_can_hit_admin_route(self, admin_client: APIClient) -> None:
        r = admin_client.get("/api/v1/admin/ping")
        assert r.status_code == 200
        assert r.data["pong"] is True
        assert "PLATFORM_ADMIN" in r.data["roles"]

    def test_anonymous_cannot_hit_admin_route(self, api: APIClient) -> None:
        assert api.get("/api/v1/admin/ping").status_code == 401


class TestSessionIDOR:
    def test_user_lists_only_own_sessions(self, api: APIClient) -> None:
        _login(api, "+254799000300")
        r = api.get("/api/v1/me/sessions")
        assert r.status_code == 200
        assert len(r.data["data"]) == 1
        assert r.data["data"][0]["current"] is True

    def test_user_cannot_revoke_another_users_session(
        self, api: APIClient, other_user: object
    ) -> None:
        from datetime import timedelta

        from django.utils import timezone

        from fikisha.identity.models import AuthSession

        victim = AuthSession.objects.create(
            user=other_user, expires_at=timezone.now() + timedelta(days=1)
        )
        _login(api, "+254799000301")
        r = api.delete(f"/api/v1/me/sessions/{victim.id}")
        assert r.status_code == 404  # scoped queryset -> existence not revealed
        victim.refresh_from_db()
        assert victim.revoked_at is None

    def test_user_can_revoke_own_session(self, api: APIClient) -> None:
        _login(api, "+254799000302")
        r = api.get("/api/v1/me/sessions")
        session_id = r.data["data"][0]["id"]
        assert api.delete(f"/api/v1/me/sessions/{session_id}").status_code == 204


class TestReferenceAndConfig:
    def test_reference_available_to_authed_user(self, api: APIClient) -> None:
        _login(api, "+254799000400")
        r = api.get("/api/v1/reference")
        assert r.status_code == 200
        assert r.data["locales"]["supported"] == ["en", "sw"]
        assert r.data["config_version"] == 1
        assert "MOTORCYCLE" in r.data["vehicle_types"]

    def test_reference_requires_auth(self, api: APIClient) -> None:
        assert api.get("/api/v1/reference").status_code == 401


class TestDemoAtomicOutbox:
    URL = "/api/v1/_demo/atomic-outbox"

    def test_demo_writes_audit_and_outbox_atomically(self, admin_client: APIClient) -> None:
        audit_before = AuditLogEntry.objects.count()
        r = admin_client.post(self.URL, {"note": "hello 2A"}, format="json")
        assert r.status_code == 201, r.content
        assert AuditLogEntry.objects.count() == audit_before + 1
        assert OutboxEvent.objects.filter(pk=r.data["outbox_event_id"]).exists()

        stats = drain_outbox()
        assert stats["published"] >= 1
        OutboxEvent.objects.get(pk=r.data["outbox_event_id"]).refresh_from_db()
        assert (
            OutboxEvent.objects.get(pk=r.data["outbox_event_id"]).status == OutboxStatus.PUBLISHED
        )

    def test_demo_failure_rolls_back_both_rows(self, admin_client: APIClient) -> None:
        admin_client.raise_request_exception = False  # let the 500 be a response
        audit_before = AuditLogEntry.objects.count()
        outbox_before = OutboxEvent.objects.count()
        r = admin_client.post(self.URL + "?fail=1", {"note": "should vanish"}, format="json")
        assert r.status_code == 500
        assert AuditLogEntry.objects.count() == audit_before
        assert OutboxEvent.objects.count() == outbox_before

    def test_demo_requires_admin_permission(self, auth_client: APIClient) -> None:
        assert auth_client.post(self.URL, {}, format="json").status_code == 403
