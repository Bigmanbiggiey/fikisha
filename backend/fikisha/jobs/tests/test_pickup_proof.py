"""Two-party pickup (founder assessment 2026-10-20 L-5, LD-4 / LD-5).

The driver completes pickup; the sender takes part by giving the code,
signing on the driver's phone, or confirming in their own app. What each value
band needs (config ``custody_proof_rules.pickup``):

  STANDARD    one of: code, signature, photo, the sender's in-app confirmation
  ELEVATED    code or in-app confirmation, plus the driver's photo
  HIGH, VERY_HIGH  code + signature + photo

This replaces chain-of-custody §4's list and retires the operator-only
STANDARD fallback.
"""

from __future__ import annotations

import uuid
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
from fikisha.jobs.models import CustodyConfirmation, PickupOtpChallenge, ProofOfPickup

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000  # KES 60,000
HIGH = 50_000_000  # KES 500,000
SIGNATURE = str(uuid.uuid4())


@pytest.fixture
def at_pickup(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, declared_value_kes: int = 1_200_000, **kw: Any) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes, **kw)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        job.refresh_from_db()
        return job

    return _make


@pytest.fixture
def high_at_pickup(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    admin_actor: Any,
    driver_actor: Any,
) -> Callable[[], Any]:
    """A HIGH-band job: approved by staff, assigned (interim trust-ceiling
    override, ADR-2D-05), driver at pickup."""
    import dataclasses

    from fikisha.jobs.assignment import assign_job
    from fikisha.jobs.high_value import decide_high_value

    def _make() -> Any:
        job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
        job.pickup_location.contact_phone = "+254700900001"  # the code goes here
        job.pickup_location.save(update_fields=["contact_phone"])
        staff = dataclasses.replace(admin_actor, is_step_up_fresh=True)
        decide_high_value(actor=staff, job_id=job.id, decision="APPROVED", rationale="cover ok")
        assign_job(
            actor=staff,
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=eligible_vehicle.id,
            admin_override_reason="test: interim trust-ceiling override",
        )
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        job.refresh_from_db()
        return job

    return _make


@pytest.fixture
def owner(verified_business: Any, actor_for: Callable) -> Any:
    return actor_for(verified_business.owner_user)


def _status(job: Any) -> str:
    job.refresh_from_db()
    return str(job.status)


# ─── STANDARD ────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "proof",
    [
        {"code": "000000"},
        {"signature_evidence_id": SIGNATURE},
    ],
)
def test_standard_needs_any_one_proof(
    at_pickup: Callable, driver_actor: Any, proof: dict[str, Any]
) -> None:
    job = at_pickup()
    out = custody.confirm_pickup(actor=driver_actor, job_id=job.id, **proof)
    assert out["status"] == JobStatus.PICKED_UP
    assert ProofOfPickup.objects.get(job=job).attestation == "VERIFIED"


def test_standard_the_drivers_photo_alone_is_not_enough(
    at_pickup: Callable, driver_actor: Any
) -> None:
    """The sender takes part at every band (founder 2026-10-20, PD-1): the
    photo is proof, never a stand-in for the sender."""
    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired):
        custody.confirm_pickup(actor=driver_actor, job_id=job.id, photo_evidence_ids=["ev-1"])
    assert _status(job) == JobStatus.AT_PICKUP


def test_standard_with_nothing_is_refused(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired, match="Pickup still needs"):
        custody.confirm_pickup(actor=driver_actor, job_id=job.id)
    assert _status(job) == JobStatus.AT_PICKUP


def test_the_senders_in_app_confirmation_counts_but_does_not_complete_alone(
    at_pickup: Callable, driver_actor: Any, owner: Any
) -> None:
    job = at_pickup()
    view = custody.sender_confirm_pickup(actor=owner, job_id=job.id)
    # Recorded, not completed: the driver's call completes it (both parties).
    assert view["status"] == JobStatus.AT_PICKUP
    assert CustodyConfirmation.objects.filter(job=job, stage="PICKUP", method="IN_APP").count() == 1
    custody.sender_confirm_pickup(actor=owner, job_id=job.id)  # idempotent
    assert CustodyConfirmation.objects.filter(job=job).count() == 1

    out = custody.confirm_pickup(actor=driver_actor, job_id=job.id)
    assert out["status"] == JobStatus.PICKED_UP
    proof = ProofOfPickup.objects.get(job=job)
    assert proof.methods == ["IN_APP"] and proof.otp_verified is False


def test_only_the_business_may_confirm_in_app(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    with pytest.raises(GuardFailed):
        custody.sender_confirm_pickup(actor=driver_actor, job_id=job.id)


def test_the_operator_only_fallback_is_retired(
    client_for: Callable, at_pickup: Callable, eligible_driver: Any
) -> None:
    job = at_pickup()
    r = client_for(eligible_driver.user).post(
        f"/api/v1/jobs/{job.id}/custody/confirm-pickup/attested",
        {"pickup_contact_name": "A. Contact"},
        format="json",
    )
    assert r.status_code == 410
    assert r.data["code"] == "pickup_fallback_retired"
    assert _status(job) == JobStatus.AT_PICKUP


# ─── ELEVATED ────────────────────────────────────────────────────
def test_elevated_needs_the_code_and_a_photo(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup(declared_value_kes=ELEVATED)
    assert job.value_band == ValueBand.ELEVATED
    with pytest.raises(PickupConfirmationRequired, match="a photo"):
        custody.confirm_pickup(actor=driver_actor, job_id=job.id, code="000000")
    with pytest.raises(PickupConfirmationRequired, match="the code"):
        custody.confirm_pickup(actor=driver_actor, job_id=job.id, photo_evidence_ids=["ev-1"])
    out = custody.confirm_pickup(
        actor=driver_actor, job_id=job.id, code="000000", photo_evidence_ids=["ev-1"]
    )
    assert out["status"] == JobStatus.PICKED_UP
    assert ProofOfPickup.objects.get(job=job).methods == ["OTP", "PHOTO"]


def test_elevated_in_app_confirmation_replaces_the_code(
    at_pickup: Callable, driver_actor: Any, owner: Any
) -> None:
    job = at_pickup(declared_value_kes=ELEVATED)
    custody.sender_confirm_pickup(actor=owner, job_id=job.id)
    out = custody.confirm_pickup(actor=driver_actor, job_id=job.id, photo_evidence_ids=["ev-1"])
    assert out["status"] == JobStatus.PICKED_UP


# ─── HIGH: all three ─────────────────────────────────────────────
def test_high_value_needs_code_signature_and_photo(
    high_at_pickup: Callable, driver_actor: Any, owner: Any
) -> None:
    job = high_at_pickup()
    assert job.value_band == ValueBand.HIGH
    # In-app confirmation doesn't stand in for the code at this band.
    custody.sender_confirm_pickup(actor=owner, job_id=job.id)
    with pytest.raises(PickupConfirmationRequired):
        custody.confirm_pickup(
            actor=driver_actor,
            job_id=job.id,
            signature_evidence_id=SIGNATURE,
            photo_evidence_ids=["ev-1"],
        )
    with pytest.raises(PickupConfirmationRequired, match="a signature"):
        custody.confirm_pickup(
            actor=driver_actor, job_id=job.id, code="000000", photo_evidence_ids=["ev-1"]
        )
    out = custody.confirm_pickup(
        actor=driver_actor,
        job_id=job.id,
        code="000000",
        signature_evidence_id=SIGNATURE,
        photo_evidence_ids=["ev-1"],
    )
    assert out["status"] == JobStatus.PICKED_UP
    assert ProofOfPickup.objects.get(job=job).methods == ["OTP", "IN_APP", "SIGNATURE", "PHOTO"]


# ─── OTP integrity ───────────────────────────────────────────────
def test_wrong_code_increments_attempts_then_locks(at_pickup: Callable, driver_actor: Any) -> None:
    job = at_pickup()
    for _ in range(5):
        with pytest.raises((OtpInvalid, OtpLocked)):
            custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="999999")
    challenge = PickupOtpChallenge.objects.filter(job=job).latest("seq")
    assert challenge.attempts >= 5 and challenge.is_locked
    with pytest.raises(OtpLocked):
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    assert _status(job) == JobStatus.AT_PICKUP


def test_missing_pickup_proof_is_refused_by_the_engine(
    at_pickup: Callable, driver_actor: Any
) -> None:
    from fikisha.jobs.service import TransitionContext, transition

    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired):
        transition(
            job_id=job.id,
            to=JobStatus.PICKED_UP,
            actor=driver_actor,
            context=TransitionContext(data={"initiator_tokens": []}),
        )


def test_a_claimed_in_app_confirmation_is_not_trusted(
    at_pickup: Callable, driver_actor: Any
) -> None:
    """``IN_APP`` comes from the database, never from the caller's context."""
    from fikisha.jobs.service import TransitionContext, transition

    job = at_pickup()
    with pytest.raises(PickupConfirmationRequired):
        transition(
            job_id=job.id,
            to=JobStatus.PICKED_UP,
            actor=driver_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": [],
                    "pickup_method": "BUSINESS_CONFIRM",
                    "actor_is_business_party": True,
                }
            ),
        )


def test_first_valid_pickup_proof_wins(at_pickup: Callable, driver_actor: Any, owner: Any) -> None:
    job = at_pickup()
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    with pytest.raises((TransitionNotAllowed, OtpNotIssued)):
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    # and the sender can no longer confirm a pickup that already happened
    with pytest.raises(custody.SenderConfirmationNotAllowed):
        custody.sender_confirm_pickup(actor=owner, job_id=job.id)
    assert ProofOfPickup.objects.filter(job=job).count() == 1
