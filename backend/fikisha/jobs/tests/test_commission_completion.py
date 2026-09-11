"""Commission creation as a domain-side effect of the authoritative
``DELIVERED -> COMPLETED`` (and ``DISPUTED -> COMPLETED``) transition
(Step 9 brief §4/§7/§15/§16)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import commission
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import CommissionConfigInvalid
from fikisha.jobs.models import CommissionRecord

pytestmark = pytest.mark.django_db


def test_no_commission_exists_merely_because_the_job_is_delivered(
    delivered_job: Callable,
) -> None:
    job = delivered_job()
    assert job.status == JobStatus.DELIVERED
    assert not CommissionRecord.objects.filter(job=job).exists()


def test_completion_creates_exactly_one_commission_record(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job()
    view = complete_job(job)
    assert view["status"] == JobStatus.COMPLETED
    assert CommissionRecord.objects.filter(job=job).count() == 1


def test_commission_uses_the_frozen_agreement_price_not_anything_else(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job(declared_value_kes=1_200_000)
    agreed_price = job.agreement.agreed_price_kes
    complete_job(job)
    record = CommissionRecord.objects.get(job=job)
    assert record.agreed_price_kes == agreed_price
    assert record.agreement_id == job.agreement_id
    # 10% of the agreed price, within [min, cap] — the approved MVP rule.
    assert record.commission_kes == commission.calculate_commission_kes(
        agreed_price, rate=0.10, min_fee_kes=4000, cap_kes=500000
    )


def test_completion_is_audited_with_the_calculation_detail(
    delivered_job: Callable, complete_job: Callable
) -> None:
    from decimal import Decimal

    from fikisha.audit.models import AuditLogEntry

    job = delivered_job()
    complete_job(job)
    record = CommissionRecord.objects.get(job=job)
    entry = AuditLogEntry.objects.get(action="commission.recorded", entity_id=record.id)
    assert entry.after["job_id"] == str(job.id)
    assert entry.after["commission_kes"] == record.commission_kes
    # The audited value and the DB-quantized value are the same number —
    # ``"0.1"`` (recorded pre-save) vs. ``"0.1000"`` (NUMERIC(6,4), read back)
    # — never compare their string forms directly.
    assert Decimal(entry.after["rate"]) == record.rate


def test_completion_emits_an_outbox_event(delivered_job: Callable, complete_job: Callable) -> None:
    from fikisha.outbox.models import OutboxEvent

    job = delivered_job()
    complete_job(job)
    assert OutboxEvent.objects.filter(event_type="CommissionRecorded").exists()


def test_config_version_is_pinned_on_the_record(
    delivered_job: Callable, complete_job: Callable
) -> None:
    from fikisha.platform_config import services as config

    job = delivered_job()
    complete_job(job)
    record = CommissionRecord.objects.get(job=job)
    assert record.config_version is not None
    assert record.config_version.version == config.current_version()


def test_a_later_config_change_does_not_alter_the_historical_record(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    from fikisha.platform_config import services as config

    job = delivered_job(declared_value_kes=1_200_000)
    complete_job(job)
    record = CommissionRecord.objects.get(job=job)
    original_commission_kes = record.commission_kes
    original_rate = record.rate

    config.apply_change(
        patch={
            "commission": {
                "model": "FLAT_WITH_MIN_CAP",
                "rate": 0.20,
                "min_fee_kes": 4000,
                "cap_kes": 500000,
                "party_liable": "OPERATOR",
            }
        },
        changed_by=admin_actor.user,
        rationale="test: rate change must not touch historical commission",
    )

    record.refresh_from_db()
    assert record.commission_kes == original_commission_kes
    assert record.rate == original_rate


def test_completion_via_a_post_completion_dispute_resolution_reuses_the_same_record(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any, business_actor: Any
) -> None:
    """A job that completes once, is later disputed (post-completion), and is
    resolved back to COMPLETED must not get a second CommissionRecord — the
    ``resolve_completed`` apply fn shares ``complete``'s idempotent body."""
    from fikisha.incidents.constants import IncidentType
    from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute

    job = delivered_job()
    complete_job(job)
    first_record = CommissionRecord.objects.get(job=job)

    incident = report_incident(actor=business_actor, job_id=job.id, type=IncidentType.DAMAGE)
    open_dispute(actor=business_actor, job_id=job.id, incident_ids=[incident.id])
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED

    resolve_dispute(
        actor=admin_actor,
        dispute_id=job.disputes.first().id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="post-completion dispute resolved with no commission change",
        routed_job_status=JobStatus.COMPLETED,
    )
    job.refresh_from_db()
    assert job.status == JobStatus.COMPLETED
    assert CommissionRecord.objects.filter(job=job).count() == 1
    assert CommissionRecord.objects.get(job=job).id == first_record.id


def test_an_unimplemented_commission_model_fails_the_whole_completion_atomically(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    """Step 9 brief §16: a commission-creation failure must not partially
    succeed — the job must not end up COMPLETED with no commission record."""
    from fikisha.platform_config import services as config

    job = delivered_job()
    config.apply_change(
        patch={
            "commission": {
                "model": "BANDED_TAPER",  # syntactically valid, not implemented
                "rate": 0.10,
                "min_fee_kes": 4000,
                "cap_kes": 500000,
                "party_liable": "OPERATOR",
            }
        },
        changed_by=admin_actor.user,
        rationale="test: an unimplemented model must refuse, not miscalculate",
    )

    with pytest.raises(CommissionConfigInvalid):
        complete_job(job)

    job.refresh_from_db()
    assert job.status == JobStatus.DELIVERED  # unchanged — rolled back
    assert not CommissionRecord.objects.filter(job=job).exists()


def test_create_commission_record_locked_is_idempotent_when_called_directly(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job()
    complete_job(job)
    job.refresh_from_db()
    first = CommissionRecord.objects.get(job=job)
    second = commission.create_commission_record_locked(job=job, actor=None)
    assert second.id == first.id
    assert CommissionRecord.objects.filter(job=job).count() == 1
