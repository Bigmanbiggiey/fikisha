"""Delivery proof by band (founder assessment 2026-10-20 L-5, LD-4): the
recipient's name, plus STANDARD code or signature; ELEVATED code and the
driver's photo; HIGH and VERY_HIGH code, signature and photo."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import custody
from fikisha.jobs.constants import JobStatus, ValueBand
from fikisha.jobs.errors import DeliveryProofIncomplete
from fikisha.jobs.models import ProofOfDelivery

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000


@pytest.fixture
def at_destination(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, declared_value_kes: int = 1_200_000) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        custody.confirm_pickup(
            actor=driver_actor, job_id=job.id, code="000000", photo_evidence_ids=["ev-goods"]
        )
        custody.start_transit(actor=driver_actor, job_id=job.id)
        custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
        job.refresh_from_db()
        return job

    return _make


# ─── STANDARD: name + the code or a signature ────────────────────
def test_standard_a_photo_alone_is_not_enough(at_destination: Callable, driver_actor: Any) -> None:
    """The recipient has to take part: the driver's photo alone no longer
    completes a delivery (LD-4)."""
    job = at_destination()
    with pytest.raises(DeliveryProofIncomplete, match="the code or a signature"):
        custody.confirm_delivery(
            actor=driver_actor,
            job_id=job.id,
            party_name="R. Recipient",
            photo_evidence_ids=["ev-1"],
        )


def test_standard_signature_only(at_destination: Callable, driver_actor: Any) -> None:
    job = at_destination()
    out = custody.confirm_delivery(
        actor=driver_actor,
        job_id=job.id,
        party_name="R. Recipient",
        signature_evidence_id=str(__import__("uuid").uuid4()),
    )
    assert out["status"] == JobStatus.DELIVERED


def test_standard_otp_only(at_destination: Callable, driver_actor: Any) -> None:
    job = at_destination()
    out = custody.confirm_delivery(
        actor=driver_actor, job_id=job.id, party_name="R. Recipient", code="000000"
    )
    assert out["status"] == JobStatus.DELIVERED
    assert ProofOfDelivery.objects.get(job=job).otp_verified is True


def test_standard_needs_the_recipient_name(at_destination: Callable, driver_actor: Any) -> None:
    job = at_destination()
    with pytest.raises(DeliveryProofIncomplete):
        custody.confirm_delivery(
            actor=driver_actor, job_id=job.id, party_name="  ", photo_evidence_ids=["ev-1"]
        )


def test_standard_needs_at_least_one_method(at_destination: Callable, driver_actor: Any) -> None:
    job = at_destination()
    with pytest.raises(DeliveryProofIncomplete):
        custody.confirm_delivery(actor=driver_actor, job_id=job.id, party_name="R. Recipient")


# ─── ELEVATED+: name + recipient OTP AND >=1 photo ────────────────
def test_elevated_needs_otp_and_photo(at_destination: Callable, driver_actor: Any) -> None:
    job = at_destination(declared_value_kes=ELEVATED)
    assert job.value_band == ValueBand.ELEVATED

    with pytest.raises(DeliveryProofIncomplete):  # OTP without a photo
        custody.confirm_delivery(
            actor=driver_actor, job_id=job.id, party_name="R. Recipient", code="000000"
        )
    with pytest.raises(DeliveryProofIncomplete):  # photo without the OTP
        custody.confirm_delivery(
            actor=driver_actor,
            job_id=job.id,
            party_name="R. Recipient",
            photo_evidence_ids=["ev-1"],
        )
    out = custody.confirm_delivery(
        actor=driver_actor,
        job_id=job.id,
        party_name="R. Recipient",
        code="000000",
        photo_evidence_ids=["ev-1"],
    )
    assert out["status"] == JobStatus.DELIVERED


def test_claimed_otp_without_a_verified_challenge_is_rejected(
    at_destination: Callable, driver_actor: Any
) -> None:
    from fikisha.jobs.service import TransitionContext, transition

    job = at_destination()
    # bypass the custody service and assert otp_verified=True without a consumed challenge
    with pytest.raises(DeliveryProofIncomplete):
        transition(
            job_id=job.id,
            to=JobStatus.DELIVERED,
            actor=driver_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": [],
                    "party_name": "R. Recipient",
                    "otp_verified": True,
                    "photo_evidence_ids": ["ev-1"],
                }
            ),
        )


def test_first_valid_delivery_proof_wins(at_destination: Callable, driver_actor: Any) -> None:
    from fikisha.jobs.errors import TransitionNotAllowed

    job = at_destination()
    custody.confirm_delivery(
        actor=driver_actor, job_id=job.id, party_name="R. Recipient", code="000000"
    )
    with pytest.raises((TransitionNotAllowed, DeliveryProofIncomplete)):
        custody.confirm_delivery(
            actor=driver_actor,
            job_id=job.id,
            party_name="R. Recipient",
            signature_evidence_id=str(__import__("uuid").uuid4()),
        )
    assert ProofOfDelivery.objects.filter(job=job).count() == 1
