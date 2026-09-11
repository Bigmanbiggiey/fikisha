"""Step 9's commission-adjustment mechanism, integrated through
``incidents.services.resolve_dispute()`` — the *only* authorized entry point
(Step 9 brief §11/§12/§19). Covers authorized/unauthorized adjustment, the
Platform-Admin-only boundary (distinct from "may resolve this dispute at
all"), source association, and that the original CommissionRecord never
changes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import IncidentType
from fikisha.incidents.errors import NotAuthorisedForBindingResolution
from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute
from fikisha.jobs import commission
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import (
    InvalidCommissionAdjustmentAmount,
    NotAuthorisedForCommissionAdjustment,
)
from fikisha.jobs.models import CommissionAdjustment, CommissionRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def completed_job_with_open_dispute(
    delivered_job: Callable, complete_job: Callable, business_owner_actor: Any
) -> Any:
    job = delivered_job()
    complete_job(job)
    job.refresh_from_db()
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE)
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    return job, dispute


def test_platform_admin_may_waive_commission_on_resolution(
    completed_job_with_open_dispute: Any, admin_actor: Any
) -> None:
    job, dispute = completed_job_with_open_dispute
    original = CommissionRecord.objects.get(job=job)
    original_commission_kes = original.commission_kes

    resolution, view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Goods confirmed damaged in transit; waiving our commission.",
        routed_job_status=JobStatus.COMPLETED,
        commission_treatment="WAIVE",
    )
    assert view["status"] == JobStatus.COMPLETED
    adjustment = CommissionAdjustment.objects.get(commission_record=original)
    assert adjustment.kind == "WAIVER"
    assert adjustment.amount_kes == -original.commission_kes
    assert adjustment.reason == resolution.rationale
    assert adjustment.source_dispute_id == dispute.id
    assert adjustment.source_resolution_id == resolution.id
    assert adjustment.authorized_by_is_platform_admin is True

    original.refresh_from_db()
    assert original.commission_kes == original_commission_kes  # the original row is untouched
    assert commission.effective_commission_kes(original) == 0


def test_platform_admin_may_partially_reduce_commission(
    completed_job_with_open_dispute: Any, admin_actor: Any
) -> None:
    job, dispute = completed_job_with_open_dispute
    original = CommissionRecord.objects.get(job=job)
    reduce_by = original.commission_kes // 2 or 1

    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Partial damage; reducing our commission proportionally.",
        routed_job_status=JobStatus.COMPLETED,
        commission_treatment="REDUCE",
        reduced_amount_kes=reduce_by,
    )
    adjustment = CommissionAdjustment.objects.get(commission_record=original)
    assert adjustment.kind == "REDUCTION"
    assert adjustment.amount_kes == -reduce_by
    assert commission.effective_commission_kes(original) == original.commission_kes - reduce_by


def test_apply_treatment_never_creates_an_adjustment(
    completed_job_with_open_dispute: Any, admin_actor: Any
) -> None:
    job, dispute = completed_job_with_open_dispute
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="Resolved amicably; commission applies as normal.",
        routed_job_status=JobStatus.COMPLETED,
        commission_treatment="APPLY",
    )
    record = CommissionRecord.objects.get(job=job)
    assert not CommissionAdjustment.objects.filter(commission_record=record).exists()


def test_an_ops_officer_may_resolve_a_dispute_but_not_reduce_commission(
    completed_job_with_open_dispute: Any, ops_actor: Any
) -> None:
    """The authority to resolve a Standard-band dispute (``is_admin``) and the
    authority to adjust commission (Platform-Admin-only) are separate —
    an Ops Officer has the first but not the second (Step 9 brief §12)."""
    _job, dispute = completed_job_with_open_dispute
    with pytest.raises(NotAuthorisedForCommissionAdjustment):
        resolve_dispute(
            actor=ops_actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="Ops Officer attempting to waive commission",
            routed_job_status=JobStatus.COMPLETED,
            commission_treatment="WAIVE",
        )


def test_an_ops_officer_may_still_resolve_with_apply(
    completed_job_with_open_dispute: Any, ops_actor: Any
) -> None:
    """Confirms the block above is specific to commission adjustment, not a
    blanket re-litigation of resolve authority Step 8 already approved."""
    job, dispute = completed_job_with_open_dispute
    resolution, view = resolve_dispute(
        actor=ops_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="Ops Officer resolves with no commission change.",
        routed_job_status=JobStatus.COMPLETED,
        commission_treatment="APPLY",
    )
    assert view["status"] == JobStatus.COMPLETED
    assert resolution.commission_treatment == "APPLY"


@pytest.mark.parametrize(
    "actor_fixture", ["business_owner_actor", "driver_actor", "other_business_actor"]
)
def test_non_admin_parties_cannot_resolve_or_adjust_commission_at_all(
    completed_job_with_open_dispute: Any, actor_fixture: str, request: Any
) -> None:
    _job, dispute = completed_job_with_open_dispute
    actor = request.getfixturevalue(actor_fixture)
    with pytest.raises(NotAuthorisedForBindingResolution):
        resolve_dispute(
            actor=actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="a non-admin party trying to adjust commission",
            routed_job_status=JobStatus.COMPLETED,
            commission_treatment="WAIVE",
        )


def test_reduce_requires_a_positive_reduced_amount(
    completed_job_with_open_dispute: Any, admin_actor: Any
) -> None:
    _job, dispute = completed_job_with_open_dispute
    with pytest.raises(InvalidCommissionAdjustmentAmount):
        resolve_dispute(
            actor=admin_actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="reduce with no amount supplied",
            routed_job_status=JobStatus.COMPLETED,
            commission_treatment="REDUCE",
        )


def test_waiving_a_job_with_no_commission_record_creates_no_adjustment_and_does_not_error(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    """A dispute opened (and resolved to FAILED) before the job ever completed
    has nothing to adjust — the Resolution still records the admin's stated
    treatment, but no CommissionAdjustment is created."""
    job = make_assigned_job()
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.LOSS)
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    assert not CommissionRecord.objects.filter(job=job).exists()

    resolution, view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="job never completed; waiving a commission that never existed",
        routed_job_status=JobStatus.FAILED,
        commission_treatment="WAIVE",
    )
    assert view["status"] == JobStatus.FAILED
    assert resolution.commission_treatment == "WAIVE"
    assert not CommissionAdjustment.objects.exists()


def test_adjustment_is_audited(completed_job_with_open_dispute: Any, admin_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    job, dispute = completed_job_with_open_dispute
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="on the record",
        routed_job_status=JobStatus.COMPLETED,
        commission_treatment="WAIVE",
    )
    record = CommissionRecord.objects.get(job=job)
    adjustment = CommissionAdjustment.objects.get(commission_record=record)
    entry = AuditLogEntry.objects.get(action="commission.adjusted", entity_id=adjustment.id)
    assert entry.after["commission_record_id"] == str(record.id)
    assert entry.after["amount_kes"] == adjustment.amount_kes
