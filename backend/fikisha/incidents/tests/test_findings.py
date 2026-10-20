"""Fikisha's findings on incidents and unfounded-report records
(trust-and-disputes plan A2, A3)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.identity.authz.step_up import StepUpRequired
from fikisha.incidents import findings
from fikisha.incidents.constants import ClosureReason, IncidentType
from fikisha.incidents.errors import (
    FindingReasonRequired,
    InvalidFinding,
    NotAuthorisedForBindingResolution,
    NotAuthorisedForIncidentReview,
    UnfoundedNotAllowed,
)
from fikisha.incidents.models import IncidentFinding, UnfoundedReport
from fikisha.incidents.services import close_incident, report_incident

pytestmark = pytest.mark.django_db

REASON = "Photos show the box crushed at pickup, before loading."


@pytest.fixture
def an_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    return report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE)


@pytest.fixture
def stepped_admin(admin_actor: Any) -> Any:
    return dataclasses.replace(admin_actor, is_step_up_fresh=True)


def test_an_at_fault_finding_names_parties_derived_from_the_job(
    an_incident: Any, ops_actor: Any
) -> None:
    finding = findings.record_finding(
        actor=ops_actor,
        incident_id=an_incident.id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    party = finding.parties.get()
    assert party.kind == "DRIVER"
    assert str(party.subject_id) == str(an_incident.job.assignment.assigned_driver_profile_id)
    assert AuditLogEntry.objects.filter(
        action="incident.finding.recorded", entity_id=str(an_incident.id)
    ).exists()


def test_candidates_follow_the_assignment_not_membership() -> None:
    solo = SimpleNamespace(
        job=SimpleNamespace(
            business_id="b1",
            assignment=SimpleNamespace(assigned_driver_profile_id="d1", group_id=None),
        )
    )
    assert findings.candidates(solo) == {"BUSINESS": "b1", "DRIVER": "d1"}  # type: ignore[arg-type]
    group = SimpleNamespace(
        job=SimpleNamespace(
            business_id="b1",
            assignment=SimpleNamespace(assigned_driver_profile_id="d1", group_id="g1"),
        )
    )
    assert findings.candidates(group) == {  # type: ignore[arg-type]
        "BUSINESS": "b1",
        "DRIVER": "d1",
        "GROUP": "g1",
    }


@pytest.mark.parametrize(
    ("outcome", "parties"),
    [
        ("AT_FAULT", []),
        ("AT_FAULT", ["GROUP"]),  # a solo job has no group
        ("AT_FAULT", ["SOMEONE"]),
        ("NO_FAULT", ["DRIVER"]),
        ("GUILTY", []),
    ],
)
def test_invalid_findings_are_refused(
    an_incident: Any, ops_actor: Any, outcome: str, parties: list[str]
) -> None:
    with pytest.raises(InvalidFinding):
        findings.record_finding(
            actor=ops_actor,
            incident_id=an_incident.id,
            outcome=outcome,
            parties=parties,
            reason=REASON,
        )


def test_a_reason_is_required(an_incident: Any, ops_actor: Any) -> None:
    with pytest.raises(FindingReasonRequired):
        findings.record_finding(
            actor=ops_actor, incident_id=an_incident.id, outcome="NO_FAULT", parties=[], reason=""
        )


def test_a_party_may_not_record_a_finding(an_incident: Any, business_owner_actor: Any) -> None:
    with pytest.raises(NotAuthorisedForIncidentReview):
        findings.record_finding(
            actor=business_owner_actor,
            incident_id=an_incident.id,
            outcome="NO_FAULT",
            parties=[],
            reason=REASON,
        )


def test_at_fault_above_standard_needs_a_platform_admin(
    make_assigned_job: Callable, business_owner_actor: Any, ops_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job(declared_value_kes=10_000_000)
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type="DAMAGE")
    with pytest.raises(NotAuthorisedForBindingResolution):
        findings.record_finding(
            actor=ops_actor,
            incident_id=incident.id,
            outcome="AT_FAULT",
            parties=["DRIVER"],
            reason=REASON,
        )
    # Ops may still record a finding that names nobody
    findings.record_finding(
        actor=ops_actor, incident_id=incident.id, outcome="UNDETERMINED", parties=[], reason=REASON
    )
    findings.record_finding(
        actor=admin_actor,
        incident_id=incident.id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )


def test_a_correction_supersedes_and_keeps_history(an_incident: Any, ops_actor: Any) -> None:
    first = findings.record_finding(
        actor=ops_actor,
        incident_id=an_incident.id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    second = findings.record_finding(
        actor=ops_actor,
        incident_id=an_incident.id,
        outcome="NO_FAULT",
        parties=[],
        reason="The damage was already there when the goods were handed over.",
    )
    assert second.supersedes_id == first.id
    assert findings.current_finding(an_incident.id) == second
    assert [f.id for f in findings.history(an_incident.id)] == [first.id, second.id]
    assert AuditLogEntry.objects.filter(action="incident.finding.superseded").exists()


def test_only_one_first_finding_per_incident(an_incident: Any, ops_actor: Any) -> None:
    findings.record_finding(
        actor=ops_actor, incident_id=an_incident.id, outcome="NO_FAULT", parties=[], reason=REASON
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        IncidentFinding.objects.create(
            incident=an_incident,
            outcome="AT_FAULT",
            reason=REASON,
            decided_by=ops_actor.user,
        )


def test_findings_are_append_only(an_incident: Any, ops_actor: Any) -> None:
    finding = findings.record_finding(
        actor=ops_actor, incident_id=an_incident.id, outcome="NO_FAULT", parties=[], reason=REASON
    )
    finding.outcome = "AT_FAULT"
    with pytest.raises(AppendOnlyModelError):
        finding.save()


def test_a_finding_changes_no_job_status_and_does_not_close(
    an_incident: Any, ops_actor: Any
) -> None:
    before = an_incident.job.status
    findings.record_finding(
        actor=ops_actor,
        incident_id=an_incident.id,
        outcome="AT_FAULT",
        parties=["BUSINESS"],
        reason=REASON,
    )
    an_incident.refresh_from_db()
    an_incident.job.refresh_from_db()
    assert an_incident.status == "OPEN"
    assert an_incident.job.status == before


class TestUnfounded:
    def _closed_with(self, incident: Any, ops_actor: Any, outcome: str) -> None:
        findings.record_finding(
            actor=ops_actor, incident_id=incident.id, outcome=outcome, parties=[], reason=REASON
        )
        close_incident(
            actor=ops_actor,
            incident_id=incident.id,
            reason_code=ClosureReason.NO_ACTION_NEEDED,
            note="Nothing to act on after review.",
        )

    def test_platform_admin_marks_a_closed_no_fault_report_unfounded(
        self, an_incident: Any, ops_actor: Any, stepped_admin: Any
    ) -> None:
        self._closed_with(an_incident, ops_actor, "NO_FAULT")
        record = findings.record_unfounded(
            actor=stepped_admin, incident_id=an_incident.id, reason=REASON
        )
        assert record.reporter_party == "BUSINESS"
        assert record.reporter_user_id == an_incident.reported_by_user_id

    def test_needs_step_up(self, an_incident: Any, ops_actor: Any, admin_actor: Any) -> None:
        self._closed_with(an_incident, ops_actor, "NO_FAULT")
        with pytest.raises(StepUpRequired):
            findings.record_unfounded(actor=admin_actor, incident_id=an_incident.id, reason=REASON)

    def test_ops_may_not(self, an_incident: Any, ops_actor: Any) -> None:
        self._closed_with(an_incident, ops_actor, "NO_FAULT")
        with pytest.raises(NotAuthorisedForIncidentReview):
            findings.record_unfounded(actor=ops_actor, incident_id=an_incident.id, reason=REASON)

    def test_undetermined_is_not_unfounded(
        self, an_incident: Any, ops_actor: Any, stepped_admin: Any
    ) -> None:
        self._closed_with(an_incident, ops_actor, "UNDETERMINED")
        with pytest.raises(UnfoundedNotAllowed):
            findings.record_unfounded(
                actor=stepped_admin, incident_id=an_incident.id, reason=REASON
            )

    def test_an_open_incident_cannot_be_unfounded(
        self, an_incident: Any, ops_actor: Any, stepped_admin: Any
    ) -> None:
        findings.record_finding(
            actor=ops_actor,
            incident_id=an_incident.id,
            outcome="NO_FAULT",
            parties=[],
            reason=REASON,
        )
        with pytest.raises(UnfoundedNotAllowed):
            findings.record_unfounded(
                actor=stepped_admin, incident_id=an_incident.id, reason=REASON
            )
        assert not UnfoundedReport.objects.exists()


class TestFindingApi:
    def test_staff_record_and_parties_see_outcome_without_reason(
        self, client_for: Callable, an_incident: Any, ops_actor: Any, business_owner_actor: Any
    ) -> None:
        r = client_for(ops_actor.user).post(
            f"/api/v1/incidents/{an_incident.id}/findings",
            {"outcome": "AT_FAULT", "parties": ["DRIVER"], "reason": REASON},
            format="json",
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["finding"]["outcome"] == "AT_FAULT"
        assert body["finding"]["reason"] == REASON
        assert body["finding_candidates"] == ["BUSINESS", "DRIVER"]
        party = client_for(business_owner_actor.user).get(f"/api/v1/incidents/{an_incident.id}")
        seen = party.json()
        assert seen["finding"]["parties"] == ["DRIVER"]
        assert "reason" not in seen["finding"]
        assert "finding_history" not in seen
        assert "unfounded" not in seen

    def test_a_party_cannot_record(
        self, client_for: Callable, an_incident: Any, business_owner_actor: Any
    ) -> None:
        r = client_for(business_owner_actor.user).post(
            f"/api/v1/incidents/{an_incident.id}/findings",
            {"outcome": "NO_FAULT", "reason": REASON},
            format="json",
        )
        assert r.status_code == 403
