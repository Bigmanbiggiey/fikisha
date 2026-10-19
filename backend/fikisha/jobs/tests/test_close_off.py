"""Closing a delivered job (founder 2026-10-20, PD-3 / PD-4 / PD-5).

A job completes when the sender confirms the goods arrived and records paying
the operator. Fikisha never takes or moves the money; the record is the
sender's statement. No timer completes a job. The recipient's close-off stays
(founder instruction 2026-10-20) until SMS brings every party's input. The
operator can answer "I haven't been paid" by disputing, at any time while the
job waits.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import custody
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import GuardFailed
from fikisha.jobs.models import CommissionRecord, Job, JobPaymentRecord

pytestmark = pytest.mark.django_db


def test_the_sender_closes_with_a_payment_record(
    client_for: Callable, delivered_job: Callable, business_actor: Any
) -> None:
    job = delivered_job()
    r = client_for(business_actor.user).post(
        f"/api/v1/jobs/{job.id}/close",
        {"payment_method": "MPESA", "mpesa_reference": "sgh7k2l9pq"},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.data["status"] == JobStatus.COMPLETED
    record = JobPaymentRecord.objects.get(job=job)
    assert (record.method, record.mpesa_reference) == ("MPESA", "SGH7K2L9PQ")
    assert record.recorded_by_id == business_actor.user.id
    assert CommissionRecord.objects.filter(job=job).exists()  # same completion side effects

    detail = client_for(business_actor.user).get(f"/api/v1/jobs/{job.id}").data
    assert detail["payment_record"]["method"] == "MPESA"


def test_cash_needs_no_reference(delivered_job: Callable, business_actor: Any) -> None:
    job = delivered_job()
    out = custody.sender_close_job(actor=business_actor, job_id=job.id, method="CASH")
    assert out["status"] == JobStatus.COMPLETED


def test_a_sender_cannot_close_without_recording_payment(
    delivered_job: Callable, business_actor: Any, do_transition: Callable
) -> None:
    job = delivered_job()
    with pytest.raises(GuardFailed, match="paid the operator"):
        do_transition(
            job, JobStatus.COMPLETED, business_actor, data={"initiator_tokens": ["BUSINESS_PARTY"]}
        )
    job.refresh_from_db()
    assert job.status == JobStatus.DELIVERED


def test_the_driver_cannot_close_the_job(
    client_for: Callable, delivered_job: Callable, eligible_driver: Any
) -> None:
    job = delivered_job()
    r = client_for(eligible_driver.user).post(
        f"/api/v1/jobs/{job.id}/close", {"payment_method": "CASH"}, format="json"
    )
    assert r.status_code in (403, 422)
    assert Job.objects.get(id=job.id).status == JobStatus.DELIVERED
    assert not JobPaymentRecord.objects.filter(job=job).exists()


def test_an_open_dispute_blocks_close_off_and_rolls_back_the_record(
    delivered_job: Callable, business_actor: Any, driver_actor: Any
) -> None:
    from fikisha.incidents import services as incidents_services

    job = delivered_job()
    incident = incidents_services.report_incident(
        actor=driver_actor, job_id=job.id, type="NON_PAYMENT"
    )
    incidents_services.open_dispute(actor=driver_actor, job_id=job.id, incident_ids=[incident.id])
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED
    with pytest.raises(GuardFailed):
        custody.sender_close_job(actor=business_actor, job_id=job.id, method="CASH")
    assert not JobPaymentRecord.objects.filter(job=job).exists()


def test_the_operator_can_dispute_non_payment_long_after_delivery(
    delivered_job: Callable, driver_actor: Any
) -> None:
    """No auto-complete, so no closing window either (PD-5)."""
    from datetime import timedelta

    from django.utils import timezone

    from fikisha.incidents import services as incidents_services

    job = delivered_job()
    Job.objects.filter(id=job.id).update(delivered_at=timezone.now() - timedelta(days=10))
    incident = incidents_services.report_incident(
        actor=driver_actor, job_id=job.id, type="NON_PAYMENT"
    )
    incidents_services.open_dispute(actor=driver_actor, job_id=job.id, incident_ids=[incident.id])
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED


def test_the_recipients_close_off_is_kept(delivered_job: Callable, do_transition: Callable) -> None:
    """The recipient may still close a delivered job without a payment record
    (founder instruction 2026-10-20), until SMS wiring brings every party in."""
    from fikisha.jobs.transitions import ALLOWED_TRANSITIONS

    rule = ALLOWED_TRANSITIONS[(JobStatus.DELIVERED, JobStatus.COMPLETED)]
    assert "RECIPIENT" in rule.initiators
    assert "SCHEDULER" not in rule.initiators


def test_ops_sees_jobs_awaiting_the_sender(
    client_for: Callable, delivered_job: Callable, platform_admin: Any
) -> None:
    from datetime import timedelta

    from django.utils import timezone

    job = delivered_job()
    fresh = delivered_job()
    Job.objects.filter(id=job.id).update(delivered_at=timezone.now() - timedelta(hours=30))
    r = client_for(platform_admin).get("/api/v1/ops/jobs?attention=awaiting_sender")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(job.id) in ids and str(fresh.id) not in ids
