"""Incident creation: valid, per-category, invalid category, correct job
association, unauthorized actor, cross-job isolation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import IncidentSeverity, IncidentStatus, IncidentType
from fikisha.incidents.errors import (
    InvalidIncidentSeverity,
    InvalidIncidentType,
    NotIncidentParty,
)
from fikisha.incidents.models import Incident
from fikisha.incidents.services import report_incident

pytestmark = pytest.mark.django_db


@pytest.fixture
def a_job(make_assigned_job: Callable) -> Any:
    return make_assigned_job()


def test_business_party_reports_an_incident(a_job: Any, business_owner_actor: Any) -> None:
    incident = report_incident(
        actor=business_owner_actor,
        job_id=a_job.id,
        type=IncidentType.DAMAGE,
        description="A carton arrived crushed.",
    )
    assert incident.job_id == a_job.id
    assert incident.type == IncidentType.DAMAGE
    assert incident.status == IncidentStatus.OPEN
    assert incident.severity == IncidentSeverity.MEDIUM  # DEFAULT_SEVERITY fallback


@pytest.mark.parametrize("incident_type", list(IncidentType.values))
def test_every_approved_incident_type_is_accepted(
    a_job: Any, business_owner_actor: Any, incident_type: str
) -> None:
    incident = report_incident(actor=business_owner_actor, job_id=a_job.id, type=incident_type)
    assert incident.type == incident_type


def test_operator_party_may_also_report(a_job: Any, driver_actor: Any) -> None:
    incident = report_incident(actor=driver_actor, job_id=a_job.id, type=IncidentType.BREAKDOWN)
    assert incident.reported_by_kind == "USER"


def test_admin_reported_incident_is_attributed_to_admin(a_job: Any, admin_actor: Any) -> None:
    incident = report_incident(actor=admin_actor, job_id=a_job.id, type=IncidentType.MISCONDUCT)
    assert incident.reported_by_kind == "ADMIN"


def test_invalid_category_is_rejected(a_job: Any, business_owner_actor: Any) -> None:
    with pytest.raises(InvalidIncidentType):
        report_incident(actor=business_owner_actor, job_id=a_job.id, type="PICKUP_PROBLEM")


def test_invalid_severity_is_rejected(a_job: Any, business_owner_actor: Any) -> None:
    with pytest.raises(InvalidIncidentSeverity):
        report_incident(
            actor=business_owner_actor,
            job_id=a_job.id,
            type=IncidentType.DAMAGE,
            severity="URGENT",
        )


def test_an_unrelated_actor_may_not_report_on_a_job(a_job: Any, other_business_actor: Any) -> None:
    with pytest.raises(NotIncidentParty):
        report_incident(actor=other_business_actor, job_id=a_job.id, type=IncidentType.DAMAGE)


def test_incident_is_correctly_associated_with_its_own_job_only(
    make_assigned_job: Callable, business_owner_actor: Any
) -> None:
    job_a = make_assigned_job()
    job_b = make_assigned_job()
    incident = report_incident(actor=business_owner_actor, job_id=job_a.id, type=IncidentType.LOSS)
    assert incident.job_id == job_a.id
    assert incident.job_id != job_b.id
    assert not Incident.objects.filter(job_id=job_b.id).exists()


def test_repeated_reports_on_the_same_job_are_independent_incidents(
    a_job: Any, business_owner_actor: Any
) -> None:
    """No forced dedup at the domain layer — two genuinely distinct incidents on
    one job are both valid (e.g. DAMAGE then, separately, DELAY)."""
    first = report_incident(actor=business_owner_actor, job_id=a_job.id, type=IncidentType.DAMAGE)
    second = report_incident(actor=business_owner_actor, job_id=a_job.id, type=IncidentType.DELAY)
    assert first.id != second.id
    assert Incident.objects.filter(job=a_job).count() == 2


def test_reporting_is_audited(a_job: Any, business_owner_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    incident = report_incident(
        actor=business_owner_actor, job_id=a_job.id, type=IncidentType.DAMAGE
    )
    assert AuditLogEntry.objects.filter(action="incident.reported", entity_id=incident.id).exists()


def test_sla_due_timestamps_are_set_from_approved_config(
    a_job: Any, business_owner_actor: Any
) -> None:
    incident = report_incident(
        actor=business_owner_actor,
        job_id=a_job.id,
        type=IncidentType.ACCIDENT,
        severity=IncidentSeverity.CRITICAL,
    )
    assert incident.sla_ack_due_at is not None
    assert incident.sla_action_due_at is not None
    # CRITICAL has no resolution_days target in the approved sla_targets table.
    assert incident.sla_resolution_due_at is None
