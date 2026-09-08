"""Session lifecycle tests: rotation, reuse detection, logout, resolve."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from fikisha.audit.models import AuditLogEntry
from fikisha.identity.models import AuthSession, RefreshToken, UserStatus
from fikisha.identity.services import auth as auth_service

pytestmark = pytest.mark.django_db


class TestStartAndResolve:
    def test_start_issues_access_and_refresh(self, user: object) -> None:
        issued = auth_service.start_session(user=user, device_label="phone")
        assert issued.access_token
        assert issued.refresh_token
        assert AuthSession.objects.filter(user=user).count() == 1
        resolved_user, session = auth_service.resolve_session(issued.access_token)
        assert resolved_user.pk == user.pk
        assert session.pk == issued.session.pk

    def test_resolve_rejects_garbage(self) -> None:
        with pytest.raises(AuthenticationFailed):
            auth_service.resolve_session("not-a-real-token")

    def test_resolve_rejects_revoked_session(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        auth_service.logout(session=issued.session)
        with pytest.raises(AuthenticationFailed) as exc:
            auth_service.resolve_session(issued.access_token)
        assert exc.value.detail.code == "auth.session_invalid"

    def test_resolve_rejects_inactive_account(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        user.status = UserStatus.SUSPENDED
        user.save(update_fields=["status"])
        with pytest.raises(AuthenticationFailed) as exc:
            auth_service.resolve_session(issued.access_token)
        assert exc.value.detail.code == "auth.account_inactive"


class TestRefreshRotation:
    def test_refresh_rotates_token(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        first_refresh = issued.refresh_token
        rotated = auth_service.refresh(raw_refresh=first_refresh)
        assert rotated.refresh_token != first_refresh
        # Old token is now spent.
        old = RefreshToken.objects.get(
            token_hash=auth_service.tokens.hash_refresh_token(first_refresh)
        )
        assert old.is_spent

    def test_reuse_detection_revokes_family(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        first = issued.refresh_token
        auth_service.refresh(raw_refresh=first)  # legitimate rotation
        with pytest.raises(AuthenticationFailed) as exc:
            auth_service.refresh(raw_refresh=first)  # replay the spent token
        assert exc.value.detail.code == "auth.refresh_reuse"

        issued.session.refresh_from_db()
        assert issued.session.revoked_at is not None
        assert AuditLogEntry.objects.filter(action="auth.refresh_reuse_detected").exists()
        # The access token minted for that session no longer resolves.
        with pytest.raises(AuthenticationFailed):
            auth_service.resolve_session(issued.access_token)

    def test_refresh_rejects_expired(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        RefreshToken.objects.filter(session=issued.session).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with pytest.raises(AuthenticationFailed):
            auth_service.refresh(raw_refresh=issued.refresh_token)


class TestRevoke:
    def test_user_can_revoke_own_session(self, user: object) -> None:
        issued = auth_service.start_session(user=user)
        other = auth_service.start_session(user=user)
        assert auth_service.revoke_session(session_id=str(other.session.id), requesting_user=user)
        other.session.refresh_from_db()
        assert other.session.revoked_at is not None
        issued.session.refresh_from_db()
        assert issued.session.revoked_at is None

    def test_user_cannot_revoke_another_users_session(
        self, user: object, other_user: object
    ) -> None:
        victim = auth_service.start_session(user=other_user)
        ok = auth_service.revoke_session(session_id=str(victim.session.id), requesting_user=user)
        assert ok is False
        victim.session.refresh_from_db()
        assert victim.session.revoked_at is None
