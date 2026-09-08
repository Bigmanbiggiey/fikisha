"""Session lifecycle: start, refresh (with rotation + reuse detection), logout,
revoke, and resolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from fikisha.audit import services as audit
from fikisha.common.logging_setup import get_logger
from fikisha.identity.models import AuthSession, RefreshToken, User, UserStatus
from fikisha.identity.services import tokens

log = get_logger("fikisha.identity.auth")


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_at: object
    session: AuthSession


def _cfg() -> dict:
    return settings.AUTH_CONFIG


def _is_admin(user: User) -> bool:
    return getattr(getattr(user, "admin_profile", None), "active", False) is True


def _new_refresh(
    session: AuthSession, *, rotated_from: RefreshToken | None = None
) -> tuple[str, RefreshToken]:
    raw = tokens.new_refresh_token()
    ttl = _cfg()["REFRESH_TOKEN_TTL_SECONDS"]
    expires_at = min(session.expires_at, timezone.now() + timedelta(seconds=ttl))
    row = RefreshToken.objects.create(
        session=session,
        token_hash=tokens.hash_refresh_token(raw),
        rotated_from=rotated_from,
        expires_at=expires_at,
    )
    return raw, row


@transaction.atomic
def start_session(
    *, user: User, device_label: str = "", user_agent: str = "", ip: str | None = None
) -> IssuedSession:
    is_admin = _is_admin(user)
    lifetime = (
        _cfg()["ADMIN_SESSION_TTL_SECONDS"] if is_admin else _cfg()["REFRESH_TOKEN_TTL_SECONDS"]
    )
    session = AuthSession.objects.create(
        user=user,
        device_label=device_label[:120],
        user_agent=(user_agent or "")[:400],
        ip=ip,
        is_admin_session=is_admin,
        expires_at=timezone.now() + timedelta(seconds=lifetime),
    )
    raw_refresh, refresh_row = _new_refresh(session)
    access = tokens.make_access_token(session_id=str(session.id), user_id=str(user.id))
    audit.record(
        actor=user,
        action="auth.session.started",
        entity_type="auth_session",
        entity_id=session.id,
        after={"is_admin_session": is_admin},
        source_ip=ip,
    )
    return IssuedSession(
        access_token=access,
        access_expires_in=_cfg()["ACCESS_TOKEN_TTL_SECONDS"],
        refresh_token=raw_refresh,
        refresh_expires_at=refresh_row.expires_at,
        session=session,
    )


def refresh(*, raw_refresh: str, ip: str | None = None) -> IssuedSession:
    """Rotate a refresh token.

    Reuse of an already-spent token revokes the whole session family — and that
    revocation must persist even though this call then raises, so it commits in
    its own ``atomic`` block and the exception is raised afterwards.
    """
    token_hash = tokens.hash_refresh_token(raw_refresh or "")
    try:
        row = RefreshToken.objects.select_related("session", "session__user").get(
            token_hash=token_hash
        )
    except RefreshToken.DoesNotExist as exc:
        raise AuthenticationFailed("Invalid refresh token.", code="auth.refresh_invalid") from exc

    if row.is_spent:
        with transaction.atomic():
            locked_row = (
                RefreshToken.objects.select_for_update().select_related("session").get(pk=row.pk)
            )
            session = locked_row.session
            _revoke_session(session, reason="refresh_reuse")
            audit.record(
                actor=session.user,
                action="auth.refresh_reuse_detected",
                entity_type="auth_session",
                entity_id=session.id,
                source_ip=ip,
            )
        raise AuthenticationFailed(
            "Refresh token reuse detected; session revoked.", code="auth.refresh_reuse"
        )

    with transaction.atomic():
        row = (
            RefreshToken.objects.select_for_update()
            .select_related("session", "session__user")
            .get(pk=row.pk)
        )
        session = row.session
        if row.is_spent:  # a concurrent refresh won the race
            raise AuthenticationFailed("Refresh token already used.", code="auth.refresh_reuse")
        if row.is_expired or not session.is_active or session.user.status != UserStatus.ACTIVE:
            raise AuthenticationFailed("Session is no longer valid.", code="auth.session_invalid")

        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        raw_new, new_row = _new_refresh(session, rotated_from=row)
        session.last_seen_at = timezone.now()
        session.save(update_fields=["last_seen_at"])

        access = tokens.make_access_token(session_id=str(session.id), user_id=str(session.user_id))
        audit.record(
            actor=session.user,
            action="auth.session.refreshed",
            entity_type="auth_session",
            entity_id=session.id,
            source_ip=ip,
        )
    return IssuedSession(
        access_token=access,
        access_expires_in=_cfg()["ACCESS_TOKEN_TTL_SECONDS"],
        refresh_token=raw_new,
        refresh_expires_at=new_row.expires_at,
        session=session,
    )


def _revoke_session(session: AuthSession, *, reason: str) -> None:
    now = timezone.now()
    if session.revoked_at is None:
        session.revoked_at = now
        session.save(update_fields=["revoked_at"])
    RefreshToken.objects.filter(session=session, used_at__isnull=True).update(used_at=now)


@transaction.atomic
def logout(*, session: AuthSession, ip: str | None = None) -> None:
    _revoke_session(session, reason="logout")
    audit.record(
        actor=session.user,
        action="auth.session.logout",
        entity_type="auth_session",
        entity_id=session.id,
        source_ip=ip,
    )


@transaction.atomic
def revoke_session(*, session_id: str, requesting_user: User, ip: str | None = None) -> bool:
    """Revoke one of the requesting user's own sessions. Returns False if not owned."""
    try:
        session = AuthSession.objects.select_for_update().get(pk=session_id, user=requesting_user)
    except (AuthSession.DoesNotExist, ValueError, TypeError):
        return False
    _revoke_session(session, reason="user_revoked")
    audit.record(
        actor=requesting_user,
        action="auth.session.revoked",
        entity_type="auth_session",
        entity_id=session.id,
        source_ip=ip,
    )
    return True


def resolve_session(access_token: str) -> tuple[User, AuthSession]:
    """Used by the DRF authentication class. Raises AuthenticationFailed on any problem."""
    from django.core import signing

    try:
        data = tokens.read_access_token(access_token)
    except signing.SignatureExpired as exc:
        raise AuthenticationFailed("Access token expired.", code="auth.token_expired") from exc
    except signing.BadSignature as exc:
        raise AuthenticationFailed("Invalid access token.", code="auth.token_invalid") from exc

    sid = data.get("sid")
    uid = data.get("uid")
    if not sid or not uid:
        raise AuthenticationFailed("Malformed access token.", code="auth.token_invalid")

    try:
        session = AuthSession.objects.select_related("user").get(pk=sid)
    except (AuthSession.DoesNotExist, ValueError, TypeError) as exc:
        raise AuthenticationFailed("Unknown session.", code="auth.session_invalid") from exc

    if str(session.user_id) != str(uid):
        raise AuthenticationFailed("Token/session mismatch.", code="auth.token_invalid")
    if not session.is_active:
        raise AuthenticationFailed("Session revoked or expired.", code="auth.session_invalid")
    if session.user.status != UserStatus.ACTIVE:
        raise AuthenticationFailed("Account is not active.", code="auth.account_inactive")

    # Throttled last_seen bump (avoid a write on every request).
    if (timezone.now() - session.last_seen_at).total_seconds() > 60:
        AuthSession.objects.filter(pk=session.pk).update(last_seen_at=timezone.now())

    return session.user, session
