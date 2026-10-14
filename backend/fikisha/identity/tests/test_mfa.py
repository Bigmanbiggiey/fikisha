"""Admin MFA and step-up (Increment 9a, ADR-2D-39; Phase 1
authentication-authorization.md §1.2).

Covers: admin roles don't apply until the session passes MFA; enrolment
(secret stored encrypted, first code confirms, ten one-time backup codes);
sign-in verification by TOTP or backup code; replay and lockout; step-up and
its expiry; non-admins never touch MFA.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pyotp
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from fikisha.audit.models import AuditLogEntry
from fikisha.identity.models import AuthSession, TotpDevice
from fikisha.identity.services import auth as auth_service

pytestmark = pytest.mark.django_db

API = "/api/v1"


def fresh_client(user: Any) -> tuple[APIClient, AuthSession]:
    """A signed-in client whose session has NOT passed MFA."""
    issued = auth_service.start_session(user=user, device_label="pytest-mfa")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issued.access_token}")
    return client, issued.session


def code_for(secret: str, offset_steps: int = 0) -> str:
    return pyotp.TOTP(secret).at(time.time() + 30 * offset_steps)


def enrol(client: APIClient) -> tuple[str, list[str]]:
    r = client.post(f"{API}/auth/mfa/enroll")
    assert r.status_code == 200, r.content
    secret = r.data["secret"]
    r = client.post(f"{API}/auth/mfa/enroll/confirm", {"code": code_for(secret)}, format="json")
    assert r.status_code == 200, r.content
    return secret, r.data["backup_codes"]


def test_admin_roles_wait_for_mfa(platform_admin: Any) -> None:
    client, _ = fresh_client(platform_admin)
    me = client.get(f"{API}/me").data
    assert me["mfa"] == {
        "required": True,
        "enrolled": False,
        "verified": False,
        "step_up_fresh": False,
    }
    assert client.get(f"{API}/ops/jobs").status_code == 403

    enrol(client)
    assert client.get(f"{API}/ops/jobs").status_code == 200
    assert client.get(f"{API}/me").data["mfa"]["verified"] is True


def test_enrolment_stores_the_secret_encrypted_and_gives_backup_codes(platform_admin: Any) -> None:
    client, _ = fresh_client(platform_admin)
    secret, codes = enrol(client)
    device = TotpDevice.objects.get(user=platform_admin)
    assert device.confirmed_at is not None
    assert secret.encode() not in bytes(device.secret_encrypted)
    assert len(codes) == 10 and len(set(codes)) == 10
    assert all(c not in "".join(device.backup_codes_hash) for c in codes)
    assert AuditLogEntry.objects.filter(action="auth.mfa.enrolled").exists()
    # can't enrol twice
    assert client.post(f"{API}/auth/mfa/enroll").status_code == 409


def test_a_wrong_first_code_does_not_confirm(platform_admin: Any) -> None:
    client, _ = fresh_client(platform_admin)
    client.post(f"{API}/auth/mfa/enroll")
    r = client.post(f"{API}/auth/mfa/enroll/confirm", {"code": "000000"}, format="json")
    assert r.status_code == 400
    assert r.json()["code"] == "mfa_invalid_code"
    assert TotpDevice.objects.get(user=platform_admin).confirmed_at is None


def test_next_sign_in_needs_a_code_and_backup_codes_burn(platform_admin: Any) -> None:
    first, _ = fresh_client(platform_admin)
    secret, codes = enrol(first)

    second, _ = fresh_client(platform_admin)
    assert second.get(f"{API}/ops/jobs").status_code == 403
    r = second.post(f"{API}/auth/mfa/verify", {"code": code_for(secret, 1)}, format="json")
    assert r.status_code == 200, r.content
    assert r.data["method"] == "totp"
    assert second.get(f"{API}/ops/jobs").status_code == 200

    third, _ = fresh_client(platform_admin)
    r = third.post(f"{API}/auth/mfa/verify", {"code": codes[0].lower()}, format="json")
    assert r.status_code == 200, r.content
    assert (r.data["method"], r.data["backup_codes_left"]) == ("backup_code", 9)

    fourth, _ = fresh_client(platform_admin)
    r = fourth.post(f"{API}/auth/mfa/verify", {"code": codes[0]}, format="json")
    assert r.status_code == 400


def test_a_code_cannot_be_replayed(platform_admin: Any) -> None:
    client, _ = fresh_client(platform_admin)
    secret = client.post(f"{API}/auth/mfa/enroll").data["secret"]
    code = code_for(secret)
    assert (
        client.post(f"{API}/auth/mfa/enroll/confirm", {"code": code}, format="json").status_code
        == 200
    )
    r = client.post(f"{API}/auth/step-up", {"code": code}, format="json")
    assert r.status_code == 400
    assert r.json()["code"] == "mfa_invalid_code"


def test_repeated_wrong_codes_lock_mfa(platform_admin: Any) -> None:
    first, _ = fresh_client(platform_admin)
    secret, _ = enrol(first)
    client, _ = fresh_client(platform_admin)
    for _ in range(5):
        assert (
            client.post(f"{API}/auth/mfa/verify", {"code": "123456"}, format="json").status_code
            == 400
        )
    r = client.post(f"{API}/auth/mfa/verify", {"code": code_for(secret, 1)}, format="json")
    assert r.status_code == 429
    assert r.json()["code"] == "mfa_locked"


def test_step_up_needs_mfa_first_and_expires(platform_admin: Any, settings: Any) -> None:
    first, _ = fresh_client(platform_admin)
    secret, _ = enrol(first)

    client, session = fresh_client(platform_admin)
    r = client.post(f"{API}/auth/step-up", {"code": code_for(secret, 1)}, format="json")
    assert r.status_code == 403
    assert r.json()["code"] == "mfa_required"

    client.post(f"{API}/auth/mfa/verify", {"code": code_for(secret, 1)}, format="json")
    session.refresh_from_db()
    assert client.get(f"{API}/me").data["mfa"]["step_up_fresh"] is True

    ttl = settings.AUTH_CONFIG["STEP_UP_TTL_SECONDS"]
    AuthSession.objects.filter(id=session.id).update(
        step_up_at=timezone.now() - timedelta(seconds=ttl + 1)
    )
    assert client.get(f"{API}/me").data["mfa"]["step_up_fresh"] is False


def test_non_admins_never_use_mfa(user: Any) -> None:
    client, _ = fresh_client(user)
    assert client.get(f"{API}/me").data["mfa"]["required"] is False
    r = client.post(f"{API}/auth/mfa/enroll")
    assert r.status_code == 403
    assert r.json()["code"] == "mfa_not_required"
