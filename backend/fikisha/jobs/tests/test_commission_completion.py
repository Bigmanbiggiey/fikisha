"""Commission creation as a domain-side effect of the authoritative
``DELIVERED -> COMPLETED`` (and ``DISPUTED -> COMPLETED``) transition
(Step 9 brief §4/§7/§15/§16), one record per paying side since the
commission split (ADR-2D-55), at the rates fixed on the agreement (D-4)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest

from fikisha.jobs import commission
from fikisha.jobs.constants import CommissionParty, JobStatus
from fikisha.jobs.errors import CommissionConfigInvalid
from fikisha.jobs.models import CommissionRecord

pytestmark = pytest.mark.django_db


def _set_rates(admin_actor: Any, business: float, operator: float) -> None:
    from fikisha.platform_config import services as config

    config.apply_change(
        patch={"commission": {"business_rate": business, "operator_rate": operator}},
        changed_by=admin_actor.user,
        rationale="test: change the commission rates",
    )


def _unpin_rates(job: Any) -> None:
    """Make the job's agreement look like one made before the split (no rates
    fixed). The append-only trigger is bypassed for this test setup only."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SET LOCAL session_replication_role = replica")
        cur.execute(
            "UPDATE agreement SET business_rate = NULL, operator_rate = NULL WHERE id = %s",
            [job.agreement_id],
        )
        cur.execute("SET LOCAL session_replication_role = DEFAULT")


def test_no_commission_exists_merely_because_the_job_is_delivered(
    delivered_job: Callable,
) -> None:
    job = delivered_job()
    assert job.status == JobStatus.DELIVERED
    assert not CommissionRecord.objects.filter(job=job).exists()


def test_completion_creates_one_record_per_side(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job()
    view = complete_job(job)
    assert view["status"] == JobStatus.COMPLETED
    parties = sorted(CommissionRecord.objects.filter(job=job).values_list("party", flat=True))
    assert parties == [CommissionParty.BUSINESS, CommissionParty.OPERATOR]


def test_each_side_is_five_percent_of_the_frozen_agreement_price(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job(declared_value_kes=1_200_000)
    agreed_price = job.agreement.agreed_price_kes
    complete_job(job)
    for record in CommissionRecord.objects.filter(job=job):
        assert record.agreed_price_kes == agreed_price
        assert record.agreement_id == job.agreement_id
        assert record.rate == Decimal("0.05")
        assert record.commission_kes == commission.calculate_fee_kes(agreed_price, rate=0.05)
        # no minimum or cap under the split
        assert record.min_fee_kes is None
        assert record.cap_kes is None


def test_the_rates_are_fixed_when_the_price_is_agreed(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    """D-4: a rate change after agreement doesn't change what the job pays."""
    job = delivered_job()
    assert job.agreement.business_rate == Decimal("0.05")
    assert job.agreement.operator_rate == Decimal("0.05")
    assert job.agreement.rates_config_version is not None

    _set_rates(admin_actor, 0.08, 0.02)
    complete_job(job)
    for record in CommissionRecord.objects.filter(job=job):
        assert record.rate == Decimal("0.05")


def test_an_agreement_without_fixed_rates_uses_the_rates_at_completion(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    """An agreement made before the split has no rates fixed on it."""
    job = delivered_job()
    _unpin_rates(job)
    _set_rates(admin_actor, 0.04, 0.06)
    job.refresh_from_db()
    complete_job(job)
    rates = dict(CommissionRecord.objects.filter(job=job).values_list("party", "rate"))
    assert rates == {
        CommissionParty.BUSINESS: Decimal("0.0400"),
        CommissionParty.OPERATOR: Decimal("0.0600"),
    }


def test_a_side_with_a_zero_rate_gets_no_record(
    admin_actor: Any, delivered_job: Callable, complete_job: Callable
) -> None:
    _set_rates(admin_actor, 0, 0.05)
    job = delivered_job()
    complete_job(job)
    parties = list(CommissionRecord.objects.filter(job=job).values_list("party", flat=True))
    assert parties == [CommissionParty.OPERATOR]


def test_completion_is_audited_per_side_with_the_calculation_detail(
    delivered_job: Callable, complete_job: Callable
) -> None:
    from fikisha.audit.models import AuditLogEntry

    job = delivered_job()
    complete_job(job)
    for record in CommissionRecord.objects.filter(job=job):
        entry = AuditLogEntry.objects.get(action="commission.recorded", entity_id=record.id)
        assert entry.after["job_id"] == str(job.id)
        assert entry.after["party"] == record.party
        assert entry.after["commission_kes"] == record.commission_kes
        assert Decimal(entry.after["rate"]) == record.rate


def test_completion_emits_an_outbox_event_per_side(
    delivered_job: Callable, complete_job: Callable
) -> None:
    from fikisha.outbox.models import OutboxEvent

    job = delivered_job()
    complete_job(job)
    payloads = OutboxEvent.objects.filter(event_type="CommissionRecorded").values_list(
        "payload", flat=True
    )
    assert sorted(p["party"] for p in payloads if p["job_id"] == str(job.id)) == [
        "BUSINESS",
        "OPERATOR",
    ]


def test_config_version_is_pinned_on_the_record(
    delivered_job: Callable, complete_job: Callable
) -> None:
    from fikisha.platform_config import services as config

    job = delivered_job()
    complete_job(job)
    for record in CommissionRecord.objects.filter(job=job):
        assert record.config_version is not None
        assert record.config_version.version == config.current_version()


def test_a_later_config_change_does_not_alter_the_historical_record(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    job = delivered_job(declared_value_kes=1_200_000)
    complete_job(job)
    before = {r.id: (r.commission_kes, r.rate) for r in CommissionRecord.objects.filter(job=job)}
    _set_rates(admin_actor, 0.20, 0.20)
    after = {r.id: (r.commission_kes, r.rate) for r in CommissionRecord.objects.filter(job=job)}
    assert after == before


def test_completion_via_a_post_completion_dispute_resolution_reuses_the_same_records(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any, business_actor: Any
) -> None:
    """A job that completes once, is later disputed (post-completion), and is
    resolved back to COMPLETED gets no new records — the
    ``resolve_completed`` apply fn shares ``complete``'s idempotent body."""
    from fikisha.incidents.constants import IncidentType
    from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute

    job = delivered_job()
    complete_job(job)
    first = set(CommissionRecord.objects.filter(job=job).values_list("id", flat=True))

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
    assert set(CommissionRecord.objects.filter(job=job).values_list("id", flat=True)) == first


def test_an_unimplemented_commission_model_fails_the_whole_completion_atomically(
    delivered_job: Callable, complete_job: Callable
) -> None:
    """Step 9 brief §16: a commission-creation failure must not partially
    succeed — the job must not end up COMPLETED with no commission record.
    Validation refuses such a config, so it's written straight to the row
    here, as a corrupted or legacy config would be."""
    from fikisha.platform_config.models import PlatformConfig

    job = delivered_job()
    _unpin_rates(job)  # so completion reads the live config
    job.refresh_from_db()
    cfg = PlatformConfig.objects.get(pk=1)
    cfg.data = {**cfg.data, "commission": {"model": "FLAT_WITH_MIN_CAP", "rate": 0.10}}
    cfg.save(update_fields=["data"])

    with pytest.raises(CommissionConfigInvalid):
        complete_job(job)

    job.refresh_from_db()
    assert job.status == JobStatus.DELIVERED  # unchanged — rolled back
    assert not CommissionRecord.objects.filter(job=job).exists()


def test_create_commission_records_locked_is_idempotent_when_called_directly(
    delivered_job: Callable, complete_job: Callable
) -> None:
    job = delivered_job()
    complete_job(job)
    job.refresh_from_db()
    first = sorted(CommissionRecord.objects.filter(job=job).values_list("id", flat=True))
    second = sorted(r.id for r in commission.create_commission_records_locked(job=job, actor=None))
    assert second == first
    assert CommissionRecord.objects.filter(job=job).count() == 2
