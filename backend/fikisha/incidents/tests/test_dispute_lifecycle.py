"""Dispute opening: freezes the job via ``JobLifecycleService.transition()``
only, valid creation, duplicate/concurrent-open handling, party authorization,
recipient-initiated disputes, cross-job isolation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import IncidentType
from fikisha.incidents.errors import DisputeAlreadyOpen, IncidentNotFound, NotIncidentParty
from fikisha.incidents.models import Dispute
from fikisha.incidents.services import open_dispute, report_incident
from fikisha.jobs.constants import JobStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def job_with_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    incident = report_incident(
        actor=business_owner_actor, job_id=job.id, type=IncidentType.BREAKDOWN
    )
    return job, incident


def test_opening_a_dispute_freezes_the_job_via_the_lifecycle_service(
    job_with_incident: Any, business_owner_actor: Any
) -> None:
    job, incident = job_with_incident
    dispute, view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    assert view["status"] == JobStatus.DISPUTED
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED
    assert dispute.job_id == job.id
    assert dispute.pre_dispute_status == JobStatus.ASSIGNED
    assert dispute.incident_ids == [str(incident.id)]


def test_dispute_records_the_locked_pre_dispute_status_exactly(
    job_with_incident: Any, business_owner_actor: Any
) -> None:
    job, incident = job_with_incident
    assert job.status == JobStatus.ASSIGNED
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    assert dispute.pre_dispute_status == "ASSIGNED"


def test_a_second_open_dispute_on_the_same_job_is_refused(
    job_with_incident: Any, business_owner_actor: Any
) -> None:
    job, incident = job_with_incident
    open_dispute(actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id])
    with pytest.raises(DisputeAlreadyOpen):
        open_dispute(actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id])


def test_the_db_constraint_backstops_the_one_open_dispute_rule(job_with_incident: Any) -> None:
    """Bypassing the service entirely, a second concurrently-committed
    ``Dispute`` row for the same job still cannot exist (ADR-2D-20's partial
    unique index) — this is the actual concurrency backstop, not merely a
    service-level pre-check."""
    from django.db import IntegrityError, transaction

    job, incident = job_with_incident
    Dispute.objects.create(job=job, incident_ids=[str(incident.id)], pre_dispute_status=job.status)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Dispute.objects.create(
                job=job, incident_ids=[str(incident.id)], pre_dispute_status=job.status
            )


def test_an_unrelated_actor_may_not_open_a_dispute(
    job_with_incident: Any, other_business_actor: Any
) -> None:
    job, incident = job_with_incident
    with pytest.raises(NotIncidentParty):
        open_dispute(actor=other_business_actor, job_id=job.id, incident_ids=[incident.id])


def test_an_admin_may_open_a_dispute(job_with_incident: Any, admin_actor: Any) -> None:
    job, incident = job_with_incident
    dispute, view = open_dispute(actor=admin_actor, job_id=job.id, incident_ids=[incident.id])
    assert view["status"] == JobStatus.DISPUTED
    assert dispute.opened_by_admin_id == admin_actor.user.id


def test_opening_without_a_real_open_incident_is_refused(
    make_assigned_job: Callable, business_owner_actor: Any
) -> None:
    job = make_assigned_job()
    with pytest.raises(IncidentNotFound):
        open_dispute(actor=business_owner_actor, job_id=job.id, incident_ids=[])


def test_an_incident_belonging_to_another_job_cannot_be_used_to_dispute(
    make_assigned_job: Callable, business_owner_actor: Any
) -> None:
    job_a = make_assigned_job()
    job_b = make_assigned_job()
    incident_on_b = report_incident(
        actor=business_owner_actor, job_id=job_b.id, type=IncidentType.LOSS
    )
    with pytest.raises(IncidentNotFound):
        open_dispute(actor=business_owner_actor, job_id=job_a.id, incident_ids=[incident_on_b.id])
    job_a.refresh_from_db()
    assert job_a.status == JobStatus.ASSIGNED  # untouched


def test_a_recipient_may_open_a_dispute_on_its_own_job(
    make_assigned_job: Callable, driver_actor: Any, business_owner_actor: Any
) -> None:
    from fikisha.jobs import custody
    from fikisha.jobs import recipient as recipient_service

    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    custody.start_transit(actor=driver_actor, job_id=job.id)
    out = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    principal = recipient_service.resolve_recipient(out["recipient_link_token"])
    incident = report_incident(
        actor=business_owner_actor, job_id=job.id, type=IncidentType.WRONG_RECIPIENT
    )

    dispute, view = open_dispute(actor=principal, job_id=job.id, incident_ids=[incident.id])
    assert view["status"] == JobStatus.DISPUTED
    assert dispute.pre_dispute_status == JobStatus.AT_DESTINATION


def test_dispute_opening_is_audited(job_with_incident: Any, business_owner_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    job, incident = job_with_incident
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id]
    )
    assert AuditLogEntry.objects.filter(action="dispute.opened", entity_id=dispute.id).exists()
