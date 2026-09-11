"""The custody chain ASSIGNED -> ... -> DELIVERED (chain-of-custody.md §2, §3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from fikisha.jobs import custody
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import JobEvent, ProofOfDelivery, ProofOfPickup

pytestmark = pytest.mark.django_db


def _custody_types(job: Any) -> list[str]:
    return list(
        JobEvent.objects.filter(job=job, is_custody=True)
        .order_by("seq")
        .values_list("type", flat=True)
    )


def test_full_custody_chain_standard_band(make_assigned_job: Callable, driver_actor: Any) -> None:
    job = make_assigned_job()

    ap = custody.arrive_at_pickup(
        actor=driver_actor, job_id=job.id, geo={"lat": "-1.47", "lng": "36.96", "accuracy_m": 12}
    )
    assert ap["status"] == JobStatus.AT_PICKUP
    assert ap["pickup_otp"] == "000000"  # OTP_DEV_FIXED_CODE in test settings

    # a pickup OTP challenge exists and was sent to the pickup contact
    arr = JobEvent.objects.get(job=job, type="ARRIVED_AT_PICKUP", is_custody=True)
    assert arr.geo_state == "CAPTURED" and str(arr.lat) == "-1.470000"
    assert JobEvent.objects.filter(job=job, type="PICKUP_OTP_ISSUED").exists()

    pu = custody.confirm_pickup_with_otp(
        actor=driver_actor, job_id=job.id, code="000000", condition_note="sealed"
    )
    assert pu["status"] == JobStatus.PICKED_UP
    pop = ProofOfPickup.objects.get(job=job)
    assert pop.otp_verified is True and pop.attestation == "VERIFIED"
    assert "PICKUP_OTP_CONFIRMED" in _custody_types(job)

    custody.start_transit(actor=driver_actor, job_id=job.id)
    ad = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    assert ad["recipient_otp"] == "000000"
    assert JobEvent.objects.filter(job=job, type="RECIPIENT_OTP_ISSUED").exists()

    dl = custody.confirm_delivery(
        actor=driver_actor,
        job_id=job.id,
        party_name="J. Mwangi",
        code="000000",
        photo_evidence_ids=["ev-photo-1"],
    )
    assert dl["status"] == JobStatus.DELIVERED
    pod = ProofOfDelivery.objects.get(job=job)
    assert pod.otp_verified is True and pod.party_name == "J. Mwangi"

    # custody trail is complete, gapless, and readable through the view
    types = _custody_types(job)
    for expected in (
        "OPERATOR_ASSIGNED",
        "ARRIVED_AT_PICKUP",
        "PICKUP_OTP_CONFIRMED",
        "GOODS_RECEIVED",
        "IN_TRANSIT",
        "ARRIVED_AT_DESTINATION",
        "RECIPIENT_VERIFIED",
        "DELIVERY_CONFIRMED",
    ):
        assert expected in types

    seqs = list(JobEvent.objects.filter(job=job).order_by("seq").values_list("seq", flat=True))
    assert seqs == list(range(1, len(seqs) + 1))
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM chain_of_custody WHERE job_id = %s", [str(job.id)])
        assert cur.fetchone()[0] == len(types)

    from fikisha.audit.services import verify_chain

    assert verify_chain() == []


def test_arrival_without_pickup_contact_phone_still_transitions(
    make_assigned_job: Callable, driver_actor: Any
) -> None:
    job = make_assigned_job(pickup_contact_phone="")
    out = custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    assert out["status"] == JobStatus.AT_PICKUP
    assert out["pickup_otp"] is None  # nothing issued, but the step succeeded
    assert not JobEvent.objects.filter(job=job, type="PICKUP_OTP_ISSUED").exists()


def test_geo_not_captured_is_acceptable(make_assigned_job: Callable, driver_actor: Any) -> None:
    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)  # no geo
    arr = JobEvent.objects.get(job=job, type="ARRIVED_AT_PICKUP", is_custody=True)
    assert arr.geo_state == "NOT_CAPTURED"


def test_only_the_assigned_driver_may_advance_custody(
    make_assigned_job: Callable, make_user: Any, actor_for: Callable
) -> None:
    from fikisha.jobs.errors import NotAuthorisedToInitiate

    job = make_assigned_job()
    stranger = actor_for(make_user("+254700900500"))
    with pytest.raises(NotAuthorisedToInitiate):
        custody.arrive_at_pickup(actor=stranger, job_id=job.id)


def test_custody_events_are_append_only_at_the_database(
    make_assigned_job: Callable, driver_actor: Any
) -> None:
    from django.db import DatabaseError, transaction

    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    ev = JobEvent.objects.filter(job=job).first()
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("UPDATE job_event SET note = 'x' WHERE id = %s", [str(ev.id)])
