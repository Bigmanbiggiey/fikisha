"""OTP request + verification.

Dev/test only: when ``OTP_DEV_EXPOSE`` is set the generated code is returned in
the response and logged at DEBUG so a developer can sign in without an SMS
provider. Production settings force ``OTP_DEV_EXPOSE=False`` and
``OTP_DEV_FIXED_CODE=""`` — see config/settings/prod.py.

There is intentionally **no** real SMS delivery in Phase 2A. The delivery seam
is ``_deliver()``; a real ``SmsGateway`` adapter plugs in there later.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from fikisha.audit import services as audit
from fikisha.common.logging_setup import get_logger
from fikisha.common.ratelimit import RateLimiter
from fikisha.identity.models import OtpChallenge, OtpPurpose, User
from fikisha.identity.phone import mask_phone, normalize_phone

log = get_logger("fikisha.identity.otp")


@dataclass(frozen=True, slots=True)
class OtpRequestResult:
    challenge_id: str
    dev_code: str | None  # populated only when OTP_DEV_EXPOSE is on


def _cfg() -> dict:
    return settings.AUTH_CONFIG


def _generate_code() -> str:
    fixed = _cfg().get("OTP_DEV_FIXED_CODE") or ""
    length = _cfg()["OTP_LENGTH"]
    if fixed:
        return fixed.zfill(length)[:length]
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def _deliver(phone: str, code: str) -> None:
    """Delivery seam. Phase 2A: log only (+ expose in dev). Later: SmsGateway."""
    log.info("otp.issued", phone=mask_phone(phone))
    if _cfg().get("OTP_DEV_EXPOSE"):
        log.debug("otp.dev_code", phone=mask_phone(phone), dev_code=code)


def request_otp(
    *, phone: str, purpose: str = OtpPurpose.LOGIN, request_ip: str | None = None
) -> OtpRequestResult:
    norm = normalize_phone(phone)

    RateLimiter(
        scope="otp_req_min", limit=_cfg()["OTP_REQUEST_RATE_PER_MINUTE"], window_seconds=60
    ).check(norm)
    RateLimiter(
        scope="otp_req_hour", limit=_cfg()["OTP_REQUEST_RATE_PER_HOUR"], window_seconds=3600
    ).check(norm)
    if request_ip:
        RateLimiter(scope="otp_req_ip_min", limit=10, window_seconds=60).check(request_ip)

    code = _generate_code()
    now = timezone.now()
    with transaction.atomic():
        challenge = OtpChallenge.objects.create(
            phone=norm,
            purpose=purpose,
            code_hash=make_password(code),
            max_attempts=_cfg()["OTP_MAX_ATTEMPTS"],
            expires_at=now + timedelta(seconds=_cfg()["OTP_TTL_SECONDS"]),
            request_ip=request_ip,
        )
        audit.record(
            actor=None,
            action="auth.otp.requested",
            entity_type="otp_challenge",
            entity_id=challenge.id,
            after={"phone": mask_phone(norm), "purpose": purpose},
            source_ip=request_ip,
        )

    _deliver(norm, code)
    return OtpRequestResult(
        challenge_id=str(challenge.id),
        dev_code=code if _cfg().get("OTP_DEV_EXPOSE") else None,
    )


def verify_otp(*, challenge_id: str, code: str, request_ip: str | None = None) -> User:
    """Verify an OTP.

    A *failed* attempt increments ``attempts`` and that increment must persist
    even though the call then raises — so the failure path commits its own
    transaction and the exception is raised **after** the ``atomic`` block.
    """
    failure_code: str | None = None

    with transaction.atomic():
        try:
            challenge = OtpChallenge.objects.select_for_update().get(pk=challenge_id)
        except (OtpChallenge.DoesNotExist, ValueError, TypeError):
            challenge = None

        if challenge is None:
            failure_code = "otp.invalid"
        elif challenge.is_consumed:
            failure_code = "otp.already_used"
        elif challenge.is_expired:
            failure_code = "otp.expired"
        elif challenge.is_locked:
            failure_code = "otp.too_many_attempts"
        elif not check_password(code, challenge.code_hash):
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            audit.record(
                actor=None,
                action="auth.otp.attempt_failed",
                entity_type="otp_challenge",
                entity_id=challenge.id,
                after={"attempts": challenge.attempts},
                source_ip=request_ip,
            )
            failure_code = "otp.too_many_attempts" if challenge.is_locked else "otp.invalid"
        else:
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=["consumed_at"])
            user, created = User.objects.get_or_create_by_phone(challenge.phone)
            audit.record(
                actor=user,
                action="auth.otp.verified",
                entity_type="user",
                entity_id=user.id,
                after={"created": created, "purpose": challenge.purpose},
                source_ip=request_ip,
            )
            return user

    # Reached only on a failure path; the increment/audit above is committed.
    messages = {
        "otp.invalid": "Incorrect or unknown code.",
        "otp.already_used": "This code has already been used.",
        "otp.expired": "This code has expired.",
        "otp.too_many_attempts": "Too many attempts. Request a new code.",
    }
    raise AuthenticationFailed(messages[failure_code], code=failure_code)
