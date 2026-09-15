"""Pickup proof band matrix (D-CUS-2, chain-of-custody.md §4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import custody
from fikisha.jobs.constants import JobStatus, ValueBand
from fikisha.jobs.errors import (
    GuardFailed,
    OtpInvalid,
    OtpLocked,
    OtpNotIssued,
    PickupConfirmationRequired,
    TransitionNotAllowed,
)
from fikisha.jobs.models import PickupOtpChallenge, ProofOfPickup

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000  # KES 60,000 -> ELEVATED band


@pytest.fixture
def at_pickup(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, declared_value_kes: int = 1_200_000, **kw: Any) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes, **kw)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        job.refresh_from_db()
        return job

    return _make


# ─── STANDARD band ────────────────────────────────────────────────
def test_standard_otp_path(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    out = custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    assert out["status"] == JobStatus.PICKED_UP
    assert ProofOfPickup.objects.get(job=job).attestation == "VERIFIED"


def test_standard_business_confirmation_is_server_confirmed(
    at_pickup: Callable, verified_business: Any, actor_for: Callable, make_user: Any
) -> None:
    job = at_pickup()
    # the business owner may confirm in-app
    owner_actor = actor_for(verified_business.owner_user)
    out = custody.confirm_pickup_by_business(actor=owner_actor, job_id=job.id)
    assert out["status"] == JobStatus.PICKED_UP
    p = ProofOfPickup.objects.get(job=job)
    assert p.otp_verified is False and "IN_APP" in p.methods


def test_business_confirmation_rejects_a_non_business_actor(
    at_pickup: Callable, driver_actor: Any
) -> None:
    job = at_pickup()
    with pytest.raises(GuardFailed):  # the driver is not a business owner/dispatcher
        custody.confirm_pickup_by_business(actor=driver_actor, job_id=job.id)


def test_standard_attested_fallback_caps_band_and_flags_unverified(
    at_pickup: Callable, driver_actor: Any
) -> None:
    job = at_pickup()
    out = custody.confirm_pickup_attested(
        actor=driver_actor,
        job_id=job.id,
        fallback_photo_id="ev-goods-1",
        pickup_contact_name="A. Contact",
    )
    assert out["status"] == JobStatus.PICKED_UP
    assert out["value_band"] == ValueBand.STANDARD
    p = ProofOfPickup.objects.get(job=job)
    assert p.attestation == "OPERATOR_ATTESTED_UNVERIFIED"


def test_attested_fallback_needs_photo_and_name(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired):
        custody.confirm_pickup_attested(
            actor=driver_actor, job_id=job.id, fallback_photo_id="", pickup_contact_name=""
        )


# ─── ELEVATED+ band: no fallback ──────────────────────────────────
def test_elevated_rejects_the_attested_fallback(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup(declared_value_kes=ELEVATED)
    assert job.value_band == ValueBand.ELEVATED
    with pytest.raises(PickupConfirmationRequired):
        custody.confirm_pickup_attested(
            actor=driver_actor,
            job_id=job.id,
            fallback_photo_id="ev-goods-1",
            pickup_contact_name="A. Contact",
        )
    job.refresh_from_db()
    assert job.status == JobStatus.AT_PICKUP


def test_elevated_otp_path_works(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup(declared_value_kes=ELEVATED)
    out = custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    assert out["status"] == JobStatus.PICKED_UP


# ─── OTP integrity ───────────────────────────────────────────────
def test_wrong_code_increments_attempts_then_locks(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    for _ in range(5):
        with pytest.raises((OtpInvalid, OtpLocked)):
            custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="999999")
    challenge = PickupOtpChallenge.objects.filter(job=job).latest("seq")
    assert challenge.attempts >= 5 and challenge.is_locked
    # a subsequently-correct code is now refused
    with pytest.raises(OtpLocked):
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    job.refresh_from_db()
    assert job.status == JobStatus.AT_PICKUP


def test_missing_pickup_method_is_refused(at_pickup: Callable, driver_actor: Any) -> None:
    from fikisha.jobs.service import TransitionContext, transition

    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired):
        transition(
            job_id=job.id,
            to=JobStatus.PICKED_UP,
            actor=driver_actor,
            context=TransitionContext(data={"initiator_tokens": []}),
        )


def test_first_valid_pickup_proof_wins(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    # a second attempt fails (the OTP is consumed and the job has left AT_PICKUP)
    with pytest.raises((TransitionNotAllowed, OtpNotIssued)):
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    # and a business confirmation on the already-picked-up job is refused too
    with pytest.raises(TransitionNotAllowed):
        from fikisha.identity.authz.actors import actor_from_user

        custody.confirm_pickup_by_business(
            actor=actor_from_user(job.business.owner_user), job_id=job.id
        )
    assert ProofOfPickup.objects.filter(job=job).count() == 1
