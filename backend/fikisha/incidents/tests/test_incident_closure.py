"""Closing an incident (trust-and-disputes plan A1): outside a dispute by
staff, one closure record per incident when a dispute is resolved, and the
closure note kept from the parties."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.incidents.constants import ClosureReason, IncidentStatus, IncidentType
from fikisha.incidents.errors import (
    ClosureNoteRequired,
    IncidentAlreadyResolved,
    IncidentInOpenDispute,
    InvalidClosureReason,
    NotAuthorisedForBindingResolution,
    NotAuthorisedForIncidentReview,
)
from fikisha.incidents.models import IncidentClosure
from fikisha.incidents.services import (
    close_incident,
    open_dispute,
    report_incident,
    resolve_dispute,
)
from fikisha.outbox.models import OutboxEvent

pytestmark = pytest.mark.django_db

NOTE = "Sender paid the operator by M-Pesa this morning."


@pytest.fixture
def an_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    return report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DELAY)


def test_ops_closes_a_standard_incident_with_a_reason(an_incident: Any, ops_actor: Any) -> None:
    incident = close_incident(
        actor=ops_actor,
        incident_id=an_incident.id,
        reason_code=ClosureReason.RESOLVED_BETWEEN_PARTIES,
        note=NOTE,
    )
    assert incident.status == IncidentStatus.RESOLVED
    closure = IncidentClosure.objects.get(incident=an_incident)
    assert closure.reason_code == ClosureReason.RESOLVED_BETWEEN_PARTIES
    assert closure.closed_by_id == ops_actor.user.id
    assert closure.dispute_id is None
    assert AuditLogEntry.objects.filter(
        action="incident.closed", entity_id=str(an_incident.id)
    ).exists()
    assert OutboxEvent.objects.filter(
        event_type="IncidentClosed", aggregate_id=str(an_incident.id)
    ).exists()


def test_closing_changes_no_job_status(an_incident: Any, ops_actor: Any) -> None:
    before = an_incident.job.status
    close_incident(
        actor=ops_actor,
        incident_id=an_incident.id,
        reason_code=ClosureReason.NO_ACTION_NEEDED,
        note=NOTE,
    )
    an_incident.job.refresh_from_db()
    assert an_incident.job.status == before


def test_a_party_may_not_close(an_incident: Any, business_owner_actor: Any) -> None:
    with pytest.raises(NotAuthorisedForIncidentReview):
        close_incident(
            actor=business_owner_actor,
            incident_id=an_incident.id,
            reason_code=ClosureReason.WITHDRAWN,
            note=NOTE,
        )


@pytest.mark.parametrize(
    ("reason", "note", "error"),
    [
        ("", NOTE, InvalidClosureReason),
        ("NOT_A_REASON", NOTE, InvalidClosureReason),
        (ClosureReason.DISPUTE_RESOLVED, NOTE, InvalidClosureReason),
        (ClosureReason.OTHER, "too short", ClosureNoteRequired),
    ],
)
def test_reason_and_note_are_checked(
    an_incident: Any, ops_actor: Any, reason: str, note: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        close_incident(actor=ops_actor, incident_id=an_incident.id, reason_code=reason, note=note)


def test_closing_twice_is_refused(an_incident: Any, ops_actor: Any) -> None:
    kwargs = {"reason_code": ClosureReason.OTHER, "note": NOTE}
    close_incident(actor=ops_actor, incident_id=an_incident.id, **kwargs)
    with pytest.raises(IncidentAlreadyResolved):
        close_incident(actor=ops_actor, incident_id=an_incident.id, **kwargs)


def test_above_standard_needs_a_platform_admin(
    make_assigned_job: Callable, business_owner_actor: Any, ops_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job(declared_value_kes=10_000_000)  # KES 100,000 → ELEVATED
    assert job.value_band == "ELEVATED"
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DELAY)
    with pytest.raises(NotAuthorisedForBindingResolution):
        close_incident(
            actor=ops_actor, incident_id=incident.id, reason_code=ClosureReason.OTHER, note=NOTE
        )
    close_incident(
        actor=admin_actor, incident_id=incident.id, reason_code=ClosureReason.OTHER, note=NOTE
    )
    assert IncidentClosure.objects.get(incident=incident).closed_by_is_platform_admin is True


def test_an_incident_in_an_open_dispute_closes_only_with_the_dispute(
    an_incident: Any, business_owner_actor: Any, admin_actor: Any
) -> None:
    dispute, _ = open_dispute(
        actor=business_owner_actor, job_id=an_incident.job_id, incident_ids=[an_incident.id]
    )
    with pytest.raises(IncidentInOpenDispute):
        close_incident(
            actor=admin_actor,
            incident_id=an_incident.id,
            reason_code=ClosureReason.OTHER,
            note=NOTE,
        )
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Driver delayed by a road closure; job cancelled by agreement.",
        routed_job_status="CANCELLED",
    )
    closure = IncidentClosure.objects.get(incident=an_incident)
    assert closure.reason_code == ClosureReason.DISPUTE_RESOLVED
    assert closure.dispute_id == dispute.id


def test_resolving_writes_one_closure_per_open_incident(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job()
    first = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DELAY)
    second = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE)
    dispute, _ = open_dispute(
        actor=business_owner_actor, job_id=job.id, incident_ids=[first.id, second.id]
    )
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Both issues settled; the job is cancelled.",
        routed_job_status="CANCELLED",
    )
    assert IncidentClosure.objects.filter(dispute=dispute).count() == 2
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == second.status == IncidentStatus.RESOLVED


def test_closure_is_append_only(an_incident: Any, ops_actor: Any) -> None:
    close_incident(
        actor=ops_actor, incident_id=an_incident.id, reason_code=ClosureReason.OTHER, note=NOTE
    )
    closure = IncidentClosure.objects.get(incident=an_incident)
    closure.note = "changed"
    with pytest.raises(AppendOnlyModelError):
        closure.save()


def test_the_reporters_side_is_stored(an_incident: Any) -> None:
    assert an_incident.reporter_party == "BUSINESS"


class TestCloseApi:
    def test_staff_close_and_parties_see_the_reason_not_the_note(
        self, client_for: Callable, an_incident: Any, ops_actor: Any, business_owner_actor: Any
    ) -> None:
        r = client_for(ops_actor.user).post(
            f"/api/v1/incidents/{an_incident.id}/close",
            {"reason_code": "PAYMENT_MADE", "note": NOTE},
            format="json",
        )
        assert r.status_code == 200, r.content
        assert r.json()["closure"] == {
            "reason_code": "PAYMENT_MADE",
            "note": NOTE,
            "created_at": r.json()["closure"]["created_at"],
        }
        party = client_for(business_owner_actor.user).get(f"/api/v1/incidents/{an_incident.id}")
        assert party.status_code == 200
        assert party.json()["status"] == "RESOLVED"
        assert party.json()["closure"]["reason_code"] == "PAYMENT_MADE"
        assert "note" not in party.json()["closure"]

    def test_a_party_gets_403(
        self, client_for: Callable, an_incident: Any, business_owner_actor: Any
    ) -> None:
        r = client_for(business_owner_actor.user).post(
            f"/api/v1/incidents/{an_incident.id}/close",
            {"reason_code": "WITHDRAWN", "note": NOTE},
            format="json",
        )
        assert r.status_code == 403

    def test_a_short_note_is_422(
        self, client_for: Callable, an_incident: Any, ops_actor: Any
    ) -> None:
        r = client_for(ops_actor.user).post(
            f"/api/v1/incidents/{an_incident.id}/close",
            {"reason_code": "OTHER", "note": ""},
            format="json",
        )
        assert r.status_code == 422
        assert r.json()["code"] == "closure_note_required"
