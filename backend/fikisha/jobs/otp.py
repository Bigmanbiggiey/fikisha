"""Job-scoped OTP generation + verification (chain-of-custody.md §4, D-CUS-2).

Two challenge kinds — ``PickupOtpChallenge`` (sent to the pickup contact) and
``RecipientOtpChallenge`` (sent to ``job.recipient_phone``). Both:

* 6-digit code (config ``OTP_LENGTH``), **hashed at rest** with Django's password
  hasher, 5-minute TTL (config ``OTP_TTL_SECONDS``);
* the **driver enters the code the contact reads out** — no self-confirmation;
* single-use (``consumed_at``), attempt-capped (``max_attempts``), replay-safe;
* re-issue is rate-limited per job; every issue and every attempt is audited;
* delivery is a provider-neutral seam (``_deliver`` + an outbox event) — **no**
  SMS/WhatsApp provider is wired (E-3). In dev/test the code is returned so a
  developer can proceed without a gateway, exactly like ``identity`` auth OTP.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.logging_setup import get_logger
from fikisha.common.ratelimit import RateLimiter
from fikisha.jobs.errors import OtpExpired, OtpInvalid, OtpLocked, OtpNotIssued
from fikisha.jobs.models import PickupOtpChallenge, RecipientOtpChallenge

log = get_logger("fikisha.jobs.otp")

_CHALLENGE_MODEL: dict[str, Any] = {
    "PICKUP_HANDOVER": PickupOtpChallenge,
    "RECIPIENT_VERIFY": RecipientOtpChallenge,
}


@dataclass(frozen=True, slots=True)
class IssuedOtp:
    challenge_id: str
    sent_to_phone: str
    dev_code: str | None  # populated only when OTP_DEV_EXPOSE is on


def _cfg() -> dict[str, Any]:
    return settings.AUTH_CONFIG


def _generate_code() -> str:
    fixed = _cfg().get("OTP_DEV_FIXED_CODE") or ""
    length = int(_cfg().get("OTP_LENGTH", 6))
    if fixed:
        return fixed.zfill(length)[:length]
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def _mask(phone: str) -> str:
    return f"***{phone[-3:]}" if phone else "***"


def _deliver(phone: str, code: str, *, purpose: str, job_id: Any) -> None:
    """Phase-2A delivery seam: log + dev-expose. A real SmsGateway plugs in here;
    the outbox event (emitted by the caller) is the provider-neutral signal a
    notification worker will consume later."""
    log.info("job.otp.issued", purpose=purpose, job_id=str(job_id), phone=_mask(phone))
    if _cfg().get("OTP_DEV_EXPOSE"):
        log.debug("job.otp.dev_code", job_id=str(job_id), dev_code=code)


def issue_otp(*, job: Any, purpose: str, phone: str, actor: Any = None, **extra: Any) -> IssuedOtp:
    """Create a fresh challenge for ``(job, purpose)``. Rate-limited per job so a
    caller cannot spam re-issues."""
    if not phone:
        raise OtpNotIssued(
            "No contact phone is on file for this step; use in-app confirmation instead."
        )
    model = _CHALLENGE_MODEL[purpose]
    RateLimiter(scope=f"job_otp_issue:{purpose}", limit=5, window_seconds=3600).check(str(job.id))

    code = _generate_code()
    now = timezone.now()
    challenge = model.objects.create(
        job=job,
        purpose=purpose,
        code_hash=make_password(code),
        sent_to_phone=phone,
        max_attempts=int(_cfg().get("OTP_MAX_ATTEMPTS", 5)),
        expires_at=now + timedelta(seconds=int(_cfg().get("OTP_TTL_SECONDS", 300))),
        **extra,
    )
    audit.record(
        actor=actor,
        action="job.otp.issued",
        entity_type=model._meta.db_table,
        entity_id=challenge.id,
        after={"job_id": str(job.id), "purpose": purpose, "phone": _mask(phone)},
    )
    _deliver(phone, code, purpose=purpose, job_id=job.id)
    return IssuedOtp(
        challenge_id=str(challenge.id),
        sent_to_phone=phone,
        dev_code=code if _cfg().get("OTP_DEV_EXPOSE") else None,
    )


def verify_otp(
    *, job: Any, purpose: str, code: str, actor: Any = None, consume: bool = True
) -> str:
    """Validate the newest usable challenge for ``(job, purpose)`` and return its
    id.

    A failed attempt increments ``attempts`` and **persists** even though the call
    then raises (identity OTP pattern) — so brute force is capped. With
    ``consume=False`` the code is validated but ``consumed_at`` is left unset, so
    the caller can consume it atomically with a later transaction (via
    :func:`consume_otp`) and a failed guard afterwards does not burn the code.
    Raises :class:`OtpNotIssued` / :class:`OtpInvalid` / :class:`OtpExpired` /
    :class:`OtpLocked`.
    """
    model = _CHALLENGE_MODEL[purpose]
    failure: str | None = None
    ok_id: str | None = None

    with transaction.atomic():
        challenge = (
            model.objects.select_for_update()
            .filter(job=job, purpose=purpose, consumed_at__isnull=True)
            # `-seq`, not `-created_at`: two challenges issued in quick
            # succession can share a timestamp under auto_now_add's clock
            # resolution, and `seq` is the only strictly-monotonic column.
            .order_by("-seq")
            .first()
        )
        if challenge is None:
            failure = "not_issued"
        elif challenge.is_locked:
            failure = "locked"
        elif challenge.is_expired():
            failure = "expired"
        elif not check_password(str(code), challenge.code_hash):
            challenge.attempts += 1
            challenge.save(update_fields=["attempts", "updated_at"])
            audit.record(
                actor=actor,
                action="job.otp.attempt_failed",
                entity_type=model._meta.db_table,
                entity_id=challenge.id,
                after={"job_id": str(job.id), "purpose": purpose, "attempts": challenge.attempts},
            )
            failure = "locked" if challenge.is_locked else "invalid"
        else:
            ok_id = str(challenge.id)
            if consume:
                challenge.consumed_at = timezone.now()
                challenge.save(update_fields=["consumed_at", "updated_at"])
            audit.record(
                actor=actor,
                action="job.otp.verified",
                entity_type=model._meta.db_table,
                entity_id=challenge.id,
                after={"job_id": str(job.id), "purpose": purpose, "consumed": consume},
            )

    if failure is not None:
        raise {
            "not_issued": OtpNotIssued(),
            "invalid": OtpInvalid(),
            "expired": OtpExpired(),
            "locked": OtpLocked(),
        }[failure]
    return ok_id  # type: ignore[return-value]  # set on the success branch


def consume_otp(*, purpose: str, challenge_id: str) -> None:
    """Mark a previously-validated challenge consumed. Call inside the
    transaction that acts on the validated OTP so a rollback leaves it reusable."""
    model = _CHALLENGE_MODEL[purpose]
    model.objects.filter(id=challenge_id, consumed_at__isnull=True).update(
        consumed_at=timezone.now(), updated_at=timezone.now()
    )


def has_consumed_otp(*, job: Any, purpose: str) -> bool:
    return (
        _CHALLENGE_MODEL[purpose]
        .objects.filter(job=job, purpose=purpose, consumed_at__isnull=False)
        .exists()
    )
