"""Admin TOTP MFA and step-up (Phase 1 ``authentication-authorization.md``
§1.2, ``security-architecture.md`` item 17; Increment 9a, ADR-2D-39).

- First login: phone OTP, then **forced TOTP enrolment**. Until a session
  has passed MFA, an admin's roles don't apply (``authz.actors``).
- Every later admin login: phone OTP + a TOTP code (or a one-time backup
  code).
- **Step-up**: a fresh code before sensitive actions; it stays fresh for
  ``STEP_UP_TTL_SECONDS``.

The secret is stored Fernet-encrypted with ``TOTP_ENCRYPTION_KEY`` (in dev
and test, derived from ``SECRET_KEY``; production must set its own). Backup
codes are stored only as password hashes and burn on use. A code's time step
is remembered so the same code can't be used twice. Repeated failures lock
MFA for the user for a while.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from fikisha.audit import services as audit
from fikisha.common.exceptions import DomainError
from fikisha.common.logging_setup import get_logger
from fikisha.identity.models import AuthSession, TotpDevice, User

log = get_logger("fikisha.identity.mfa")

ISSUER = "Fikisha"
BACKUP_CODE_COUNT = 10
STEP_SECONDS = 30


class MfaNotRequired(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "mfa_not_required"
    default_detail = "Only admin accounts use MFA."


class MfaAlreadyEnrolled(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "mfa_already_enrolled"
    default_detail = "This account already has an authenticator."


class MfaNotEnrolled(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "mfa_not_enrolled"
    default_detail = "Set up an authenticator first."


class MfaInvalidCode(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "mfa_invalid_code"
    default_detail = "That code isn't right."


class MfaLocked(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "mfa_locked"
    default_detail = "Too many wrong codes. Wait a few minutes and try again."


class MfaNotVerified(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "mfa_required"
    default_detail = "Enter your authenticator code first."


def _cfg() -> dict[str, Any]:
    return settings.AUTH_CONFIG  # type: ignore[no-any-return]


def is_admin_user(user: Any) -> bool:
    return getattr(getattr(user, "admin_profile", None), "active", False) is True


# ─── secret storage ────────────────────────────────────────────────────
def _fernet() -> Fernet:
    key = _cfg().get("TOTP_ENCRYPTION_KEY") or ""
    if not key:
        # dev / test only (prod settings require an explicit key)
        digest = hashlib.sha256(("fikisha-totp:" + settings.SECRET_KEY).encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(secret: str) -> bytes:
    return _fernet().encrypt(secret.encode())


def _decrypt(blob: Any) -> str:
    return _fernet().decrypt(bytes(blob)).decode()


# ─── status ────────────────────────────────────────────────────────────
def step_up_fresh(session: AuthSession | None) -> bool:
    if session is None or session.step_up_at is None:
        return False
    ttl = int(_cfg().get("STEP_UP_TTL_SECONDS", 300))
    return timezone.now() - session.step_up_at < timedelta(seconds=ttl)


def status_for(user: Any, session: AuthSession | None) -> dict[str, Any]:
    """What the client needs to route an admin: must they enrol, verify, or
    nothing? ``required`` is false for everyone who isn't an admin."""
    if not is_admin_user(user):
        return {"required": False, "enrolled": False, "verified": False, "step_up_fresh": False}
    device = TotpDevice.objects.filter(user=user).first()
    return {
        "required": True,
        "enrolled": bool(device and device.confirmed_at),
        "verified": bool(session and session.mfa_verified_at),
        "step_up_fresh": step_up_fresh(session),
    }


# ─── code checking ─────────────────────────────────────────────────────
def _lock_key(user: User) -> str:
    return f"mfa-fail:{user.id}"


def _check_not_locked(user: User) -> None:
    if cache.get(_lock_key(user), 0) >= int(_cfg().get("MFA_MAX_ATTEMPTS", 5)):
        raise MfaLocked()


def _record_failure(user: User) -> None:
    key = _lock_key(user)
    window = int(_cfg().get("MFA_LOCK_SECONDS", 900))
    if cache.add(key, 1, timeout=window):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)


def _normalise(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isalnum()).upper()


def _totp_step(secret: str, code: str, now: float | None = None) -> int | None:
    """The time step ``code`` belongs to, allowing one step either side
    for clock drift, or None."""
    if not (len(code) == 6 and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    now = time.time() if now is None else now
    current = int(now // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if secrets.compare_digest(totp.at(step * STEP_SECONDS), code):
            return step
    return None


def _consume_code(device: TotpDevice, code: str, *, allow_backup: bool) -> str:
    """Accept a TOTP code (not seen before) or, if allowed, an unused backup
    code. Returns the method used; raises ``MfaInvalidCode``. The caller
    holds the device row lock."""
    raw = _normalise(code)
    step = _totp_step(_decrypt(device.secret_encrypted), raw)
    if step is not None:
        if device.last_used_step is not None and step <= device.last_used_step:
            raise MfaInvalidCode()  # replay of an already-used code
        device.last_used_step = step
        device.save(update_fields=["last_used_step"])
        return "totp"
    if allow_backup and len(raw) == 10:
        for i, hashed in enumerate(device.backup_codes_hash):
            if check_password(raw, hashed):
                device.backup_codes_hash = (
                    device.backup_codes_hash[:i] + device.backup_codes_hash[i + 1 :]
                )
                device.save(update_fields=["backup_codes_hash"])
                return "backup_code"
    raise MfaInvalidCode()


def _admin_user(actor: Any) -> User:
    user = getattr(actor, "user", None)
    if user is None or not is_admin_user(user):
        raise MfaNotRequired()
    return user  # type: ignore[no-any-return]


def _session(actor: Any) -> AuthSession:
    session = getattr(actor, "session", None)
    if not isinstance(session, AuthSession):
        raise MfaNotRequired("MFA needs a signed-in session.")
    return session


# ─── enrolment ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Enrolment:
    secret: str
    otpauth_uri: str


@transaction.atomic
def begin_enrolment(*, actor: Any) -> Enrolment:
    """A new secret for an admin with no confirmed authenticator. Calling
    again replaces an unconfirmed one (e.g. the QR was never scanned)."""
    user = _admin_user(actor)
    _session(actor)
    device = TotpDevice.objects.select_for_update().filter(user=user).first()
    if device is not None and device.confirmed_at is not None:
        raise MfaAlreadyEnrolled()
    secret = pyotp.random_base32()
    if device is None:
        device = TotpDevice(user=user)
    device.secret_encrypted = _encrypt(secret)
    device.confirmed_at = None
    device.backup_codes_hash = []
    device.last_used_step = None
    device.save()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.phone, issuer_name=ISSUER)
    return Enrolment(secret=secret, otpauth_uri=uri)


def _new_backup_codes() -> list[str]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ["".join(secrets.choice(alphabet) for _ in range(10)) for _ in range(BACKUP_CODE_COUNT)]


@transaction.atomic
def confirm_enrolment(*, actor: Any, code: str) -> list[str]:
    """Confirm the authenticator with its first code. Marks this session as
    MFA-verified and stepped-up, and returns the backup codes, shown once."""
    user = _admin_user(actor)
    session = _session(actor)
    _check_not_locked(user)
    device = TotpDevice.objects.select_for_update().filter(user=user).first()
    if device is None or device.secret_encrypted is None:
        raise MfaNotEnrolled()
    if device.confirmed_at is not None:
        raise MfaAlreadyEnrolled()
    try:
        _consume_code(device, code, allow_backup=False)
    except MfaInvalidCode:
        _record_failure(user)
        raise
    codes = _new_backup_codes()
    now = timezone.now()
    device.confirmed_at = now
    device.backup_codes_hash = [make_password(c) for c in codes]
    device.save(update_fields=["confirmed_at", "backup_codes_hash"])
    _mark(session, mfa=True)
    audit.record(
        actor=user,
        action="auth.mfa.enrolled",
        entity_type="totp_device",
        entity_id=device.id,
        after={"backup_codes": BACKUP_CODE_COUNT},
    )
    return [f"{c[:5]}-{c[5:]}" for c in codes]


def _mark(session: AuthSession, *, mfa: bool) -> None:
    now = timezone.now()
    fields = ["step_up_at"]
    session.step_up_at = now
    if mfa:
        session.mfa_verified_at = now
        fields.append("mfa_verified_at")
    session.save(update_fields=fields)


# ─── sign-in check and step-up ─────────────────────────────────────────
@transaction.atomic
def verify(*, actor: Any, code: str) -> dict[str, Any]:
    """The MFA half of an admin sign-in. A TOTP code or a backup code; a
    fresh check also counts as a step-up."""
    user = _admin_user(actor)
    session = _session(actor)
    _check_not_locked(user)
    device = TotpDevice.objects.select_for_update().filter(user=user).first()
    if device is None or device.confirmed_at is None:
        raise MfaNotEnrolled()
    try:
        method = _consume_code(device, code, allow_backup=True)
    except MfaInvalidCode:
        # a failure can't be audited here: the transaction rolls back
        _record_failure(user)
        log.warning("auth.mfa.failed", user_id=str(user.id))
        raise
    _mark(session, mfa=True)
    audit.record(
        actor=user,
        action="auth.mfa.verified",
        entity_type="auth_session",
        entity_id=session.id,
        after={"method": method, "backup_codes_left": len(device.backup_codes_hash)},
    )
    return {"method": method, "backup_codes_left": len(device.backup_codes_hash)}


@transaction.atomic
def step_up(*, actor: Any, code: str) -> dict[str, Any]:
    """A fresh code before a sensitive action. Needs a session that already
    passed MFA."""
    user = _admin_user(actor)
    session = _session(actor)
    if session.mfa_verified_at is None:
        raise MfaNotVerified()
    _check_not_locked(user)
    device = TotpDevice.objects.select_for_update().filter(user=user).first()
    if device is None or device.confirmed_at is None:
        raise MfaNotEnrolled()
    try:
        method = _consume_code(device, code, allow_backup=True)
    except MfaInvalidCode:
        _record_failure(user)
        log.warning("auth.step_up.failed", user_id=str(user.id))
        raise
    _mark(session, mfa=False)
    audit.record(
        actor=user,
        action="auth.step_up",
        entity_type="auth_session",
        entity_id=session.id,
        after={"method": method},
    )
    ttl = int(_cfg().get("STEP_UP_TTL_SECONDS", 300))
    return {"method": method, "fresh_for_seconds": ttl}
