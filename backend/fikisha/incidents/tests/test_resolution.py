"""Dispute resolution: admin-only, above-Standard binding requires a Platform
Admin (D-ADM-1), immutable + audited, financial-adjustment boundary
(commission_treatment / reduced / agreed_compensation are recorded fields, not
a commission engine), RESUME_PRIOR is never a valid routing, actions are
recorded-only (ADR-2D-21), a resolved dispute cannot be reopened."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import DisputeStatus, IncidentStatus, IncidentType
from fikisha.incidents.errors import (
    DisputeAlreadyResolved,
    InvalidResolutionOutcome,
    InvalidResolutionRouting,
    NotAuthorisedForBindingResolution,
    RationaleRequired,
)
from fikisha.incidents.models import Resolution
from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import GuardFailed, NotAuthorisedToInitiate

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000


@pytest.fixture
def open_standard_dispute(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    incident = report_incident(
        actor=business_owner_actor, job_id=job.id, type=IncidentType.BREAKDOWN
    )
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    return job, incident, dispute


def test_admin_resolves_a_standard_band_dispute_to_completed(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    job, incident, dispute = open_standard_dispute
    resolution, view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="Driver replaced the part; parties agreed to proceed.",
        routed_job_status="COMPLETED",
    )
    assert view["status"] == JobStatus.COMPLETED
    job.refresh_from_db()
    assert job.status == JobStatus.COMPLETED
    dispute.refresh_from_db()
    assert dispute.status == DisputeStatus.RESOLVED
    incident.refresh_from_db()
    assert incident.status == IncidentStatus.RESOLVED
    assert resolution.routed_job_status == "COMPLETED"


def test_resolution_requires_a_rationale(open_standard_dispute: Any, admin_actor: Any) -> None:
    _job, _incident, dispute = open_standard_dispute
    with pytest.raises(RationaleRequired):
        resolve_dispute(
            actor=admin_actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="   ",
            routed_job_status="FAILED",
        )


def test_resume_prior_is_never_a_valid_routing(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    _job, _incident, dispute = open_standard_dispute
    with pytest.raises(InvalidResolutionRouting):
        resolve_dispute(
            actor=admin_actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="attempting a resume",
            routed_job_status="ASSIGNED",  # the pre-dispute status - not routable
        )


def test_an_invalid_outcome_code_is_rejected(open_standard_dispute: Any, admin_actor: Any) -> None:
    _job, _incident, dispute = open_standard_dispute
    with pytest.raises(InvalidResolutionOutcome):
        resolve_dispute(
            actor=admin_actor,
            dispute_id=dispute.id,
            outcome_code="DRIVER_AT_FAULT",  # not a recognised outcome
            rationale="inventing a liability finding",
            routed_job_status="FAILED",
        )


def test_a_non_admin_may_not_resolve(open_standard_dispute: Any, business_owner_actor: Any) -> None:
    _job, _incident, dispute = open_standard_dispute
    with pytest.raises(NotAuthorisedForBindingResolution):
        resolve_dispute(
            actor=business_owner_actor,
            dispute_id=dispute.id,
            outcome_code="AMICABLE_AGREEMENT",
            rationale="trying to self-resolve",
            routed_job_status="COMPLETED",
        )


def test_above_standard_band_binding_resolution_requires_platform_admin(
    make_assigned_job: Callable, business_owner_actor: Any, ops_actor: Any
) -> None:
    job = make_assigned_job(declared_value_kes=ELEVATED)
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.LOSS)
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    # An Operations Officer is an admin, but not a Platform Admin — D-ADM-1
    # requires Platform Admin above the Standard band. The Resolution row is
    # created, but the transition's own guard refuses it, and the outer
    # transaction rolls back the Resolution too (no orphaned append-only row).
    with pytest.raises(GuardFailed):
        resolve_dispute(
            actor=ops_actor,
            dispute_id=dispute.id,
            outcome_code="ADMIN_DETERMINATION",
            rationale="Ops Officer attempting a binding elevated-band resolution",
            routed_job_status="COMPLETED",
        )
    assert not Resolution.objects.filter(dispute=dispute).exists()
    dispute.refresh_from_db()
    assert dispute.status == DisputeStatus.OPEN  # unchanged


def test_above_standard_band_binding_resolution_by_platform_admin_succeeds(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job(declared_value_kes=ELEVATED)
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.LOSS)
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    resolution, view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Platform Admin binding determination on an elevated-band job.",
        routed_job_status="FAILED",
    )
    assert view["status"] == JobStatus.FAILED
    assert resolution.resolved_by_is_platform_admin is True


def test_a_resolved_dispute_cannot_be_reopened_or_re_resolved(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    _job, _incident, dispute = open_standard_dispute
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="first resolution",
        routed_job_status="COMPLETED",
    )
    with pytest.raises(DisputeAlreadyResolved):
        resolve_dispute(
            actor=admin_actor,
            dispute_id=dispute.id,
            outcome_code="WITHDRAWN",
            rationale="trying again",
            routed_job_status="CANCELLED",
        )


def test_resolution_is_append_only_at_the_database(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    from django.db import DatabaseError, connection, transaction

    _job, _incident, dispute = open_standard_dispute
    resolution, _view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="original decision",
        routed_job_status="COMPLETED",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE resolution SET rationale = 'changed' WHERE id = %s",
                    [str(resolution.id)],
                )


def test_financial_adjustment_fields_are_recorded_not_executed(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    """The resolution records the *decision* about commission — Step 8 builds no
    CommissionRecord/adjustment engine (none exists yet; Step 9)."""
    _job, _incident, dispute = open_standard_dispute
    resolution, _view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Waiving commission and recording agreed compensation.",
        routed_job_status="COMPLETED",
        commission_treatment="WAIVE",
        agreed_compensation_kes=50_000,
    )
    assert resolution.commission_treatment == "WAIVE"
    assert resolution.agreed_compensation_kes == 50_000
    assert resolution.reduced_amount_kes is None


def test_resolution_actions_are_recorded_only_never_executed(
    open_standard_dispute: Any, admin_actor: Any
) -> None:
    """ADR-2D-21: ``actions`` are admin-declared intent flags. Step 8 executes
    none of them — no trust/rating/suspension side effect anywhere in this
    call. We assert the flag is merely stored, and (by omission) that nothing
    else observable changed on the operator/driver as a result."""
    job, _incident, dispute = open_standard_dispute
    operator = job.agreement.operator
    original_status = operator.status

    resolution, _view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Recording a trust-change intent only.",
        routed_job_status="FAILED",
        actions=["TRUST_CHANGE", "RATING_IMPACT"],
    )
    assert resolution.actions == ["TRUST_CHANGE", "RATING_IMPACT"]
    operator.refresh_from_db()
    assert operator.status == original_status  # nothing executed


def test_resolution_generates_an_audit_entry(open_standard_dispute: Any, admin_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    _job, _incident, dispute = open_standard_dispute
    resolution, _view = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="on the record",
        routed_job_status="COMPLETED",
    )
    assert AuditLogEntry.objects.filter(action="dispute.resolved", entity_id=resolution.id).exists()


def test_only_admin_or_platform_admin_may_initiate_the_resolving_transition(
    open_standard_dispute: Any, driver_actor: Any
) -> None:
    """Defence in depth: even bypassing the service's own admin check, the
    ``jobs.service`` initiator match for ``DISPUTED -> COMPLETED`` still refuses
    a non-admin actor (initiators=(ADMIN, PLATFORM_ADMIN)) — the assigned
    driver on this very job is still not an allowed initiator of this
    transition."""
    from fikisha.jobs.service import TransitionContext
    from fikisha.jobs.service import transition as job_transition

    job, _incident, _dispute = open_standard_dispute
    with pytest.raises(NotAuthorisedToInitiate):
        job_transition(
            job_id=job.id,
            to="COMPLETED",
            actor=driver_actor,
            context=TransitionContext(data={"initiator_tokens": []}),
        )
