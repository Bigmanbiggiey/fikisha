"""Phase 2D final-verification BLOCKER-1 corrective pass.

Proves the actual production failure mode can no longer occur: every public
``incidents.services`` function that writes a domain row and calls
``audit.record()`` is genuinely atomic — a downstream failure rolls back
*everything* it wrote, and a real (non-implicitly-wrapped) call succeeds
with its domain row, audit row, and outbox row (where applicable) all
committed together.

Every test here uses ``django_db(transaction=True)`` deliberately — the
default ``django_db`` marker's own implicit atomic wrapper is exactly what
hid the original defect, so it must not be relied on here either."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.incidents import services as incidents_services
from fikisha.incidents.constants import IncidentStatus, IncidentType
from fikisha.incidents.models import Escalation, Incident, IncidentEvidence, IncidentStatement
from fikisha.jobs.constants import RecipientIssueCategory
from fikisha.jobs.models import RecipientReportedIssue
from fikisha.outbox.models import OutboxEvent

pytestmark = pytest.mark.django_db(transaction=True)


def _boom(*_a: Any, **_kw: Any) -> Any:
    raise RuntimeError("simulated downstream failure")


def _audit_exists(entity_type: str, entity_id: Any) -> bool:
    return AuditLogEntry.objects.filter(entity_type=entity_type, entity_id=entity_id).exists()


def _outbox_exists(aggregate_type: str, aggregate_id: Any) -> bool:
    return OutboxEvent.objects.filter(
        aggregate_type=aggregate_type, aggregate_id=str(aggregate_id)
    ).exists()


@pytest.fixture
def an_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    return incidents_services.report_incident(
        actor=business_owner_actor, job_id=job.id, type=IncidentType.MISCONDUCT
    )


class TestReportIncident:
    def test_success_is_fully_atomic(
        self, make_assigned_job: Callable, business_owner_actor: Any
    ) -> None:
        job = make_assigned_job()
        incident = incidents_services.report_incident(
            actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE
        )
        assert Incident.objects.filter(id=incident.id).exists()
        assert _audit_exists("incident", incident.id)
        assert _outbox_exists("incident", incident.id)

    def test_downstream_failure_rolls_back_the_incident_row(
        self, make_assigned_job: Callable, business_owner_actor: Any, monkeypatch: Any
    ) -> None:
        job = make_assigned_job()
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        before = Incident.objects.count()
        with pytest.raises(RuntimeError):
            incidents_services.report_incident(
                actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE
            )
        assert Incident.objects.count() == before
        assert AuditLogEntry.objects.filter(entity_type="incident").count() == 0
        assert OutboxEvent.objects.filter(aggregate_type="incident").count() == 0


class TestIntakeRecipientReport:
    def test_success_is_fully_atomic(self, make_assigned_job: Callable) -> None:
        job = make_assigned_job()
        report = RecipientReportedIssue.objects.create(
            job=job, reported_via_link_id=uuid.uuid4(), category=RecipientIssueCategory.DAMAGE
        )
        incident = incidents_services.intake_recipient_report(report_id=report.id)
        assert Incident.objects.filter(id=incident.id, source_report_id=report.id).exists()
        assert _audit_exists("incident", incident.id)
        assert _outbox_exists("incident", incident.id)

    def test_downstream_failure_rolls_back_the_incident_row(
        self, make_assigned_job: Callable, monkeypatch: Any
    ) -> None:
        job = make_assigned_job()
        report = RecipientReportedIssue.objects.create(
            job=job, reported_via_link_id=uuid.uuid4(), category=RecipientIssueCategory.DAMAGE
        )
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            incidents_services.intake_recipient_report(report_id=report.id)
        assert Incident.objects.filter(source_report_id=report.id).count() == 0
        assert AuditLogEntry.objects.filter(entity_type="incident").count() == 0


class TestAttachEvidence:
    def test_success_is_fully_atomic(self, an_incident: Any, business_owner_actor: Any) -> None:
        row = incidents_services.attach_evidence(
            actor=business_owner_actor,
            incident_id=an_incident.id,
            data=b"\xff\xd8\xff fake",
            content_type="image/jpeg",
        )
        assert IncidentEvidence.objects.filter(id=row.id).exists()
        assert _audit_exists("incident_evidence", row.id)

    def test_downstream_failure_rolls_back_the_evidence_row(
        self, an_incident: Any, business_owner_actor: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        before = IncidentEvidence.objects.count()
        with pytest.raises(RuntimeError):
            incidents_services.attach_evidence(
                actor=business_owner_actor,
                incident_id=an_incident.id,
                data=b"\xff\xd8\xff fake",
                content_type="image/jpeg",
            )
        assert IncidentEvidence.objects.count() == before
        assert AuditLogEntry.objects.filter(entity_type="incident_evidence").count() == 0


class TestAddStatement:
    def test_success_is_fully_atomic(self, an_incident: Any, business_owner_actor: Any) -> None:
        statement = incidents_services.add_statement(
            actor=business_owner_actor, incident_id=an_incident.id, text="here is what happened"
        )
        assert IncidentStatement.objects.filter(id=statement.id).exists()
        assert _audit_exists("incident_statement", statement.id)

    def test_downstream_failure_rolls_back_the_statement_row(
        self, an_incident: Any, business_owner_actor: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        before = IncidentStatement.objects.count()
        with pytest.raises(RuntimeError):
            incidents_services.add_statement(
                actor=business_owner_actor, incident_id=an_incident.id, text="x"
            )
        assert IncidentStatement.objects.count() == before
        assert AuditLogEntry.objects.filter(entity_type="incident_statement").count() == 0


class TestStartReview:
    def test_success_is_fully_atomic(self, an_incident: Any, ops_actor: Any) -> None:
        incident = incidents_services.start_review(actor=ops_actor, incident_id=an_incident.id)
        assert incident.status == IncidentStatus.UNDER_REVIEW
        assert Incident.objects.get(id=incident.id).status == IncidentStatus.UNDER_REVIEW
        assert _audit_exists("incident", incident.id)

    def test_downstream_failure_rolls_back_the_status_change(
        self, an_incident: Any, ops_actor: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            incidents_services.start_review(actor=ops_actor, incident_id=an_incident.id)
        an_incident.refresh_from_db()
        assert an_incident.status == IncidentStatus.OPEN  # unchanged, not half-applied


class TestStartAmicableWindow:
    def test_success_is_fully_atomic(self, an_incident: Any, ops_actor: Any) -> None:
        incident = incidents_services.start_amicable_window(
            actor=ops_actor, incident_id=an_incident.id
        )
        assert incident.status == IncidentStatus.AMICABLE_PENDING
        assert _audit_exists("incident", incident.id)

    def test_downstream_failure_rolls_back_the_status_change(
        self, an_incident: Any, ops_actor: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            incidents_services.start_amicable_window(actor=ops_actor, incident_id=an_incident.id)
        an_incident.refresh_from_db()
        assert an_incident.status == IncidentStatus.OPEN


class TestEscalate:
    def test_success_is_fully_atomic(self, an_incident: Any, admin_actor: Any) -> None:
        escalation = incidents_services.escalate(
            actor=admin_actor, incident_id=an_incident.id, reason="Escalating to the founder"
        )
        assert Escalation.objects.filter(id=escalation.id).exists()
        an_incident.refresh_from_db()
        assert an_incident.status == IncidentStatus.ESCALATED
        assert _audit_exists("escalation", escalation.id)
        assert _outbox_exists("incident", an_incident.id)

    def test_downstream_failure_rolls_back_everything(
        self, an_incident: Any, admin_actor: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(incidents_services.audit, "record", _boom)
        before = Escalation.objects.count()
        with pytest.raises(RuntimeError):
            incidents_services.escalate(
                actor=admin_actor, incident_id=an_incident.id, reason="Escalating to the founder"
            )
        assert Escalation.objects.count() == before
        an_incident.refresh_from_db()
        assert an_incident.status == IncidentStatus.OPEN  # not left ESCALATED without an audit row
        assert AuditLogEntry.objects.filter(entity_type="escalation").count() == 0


class TestOriginalReproductionNoLongerOccurs:
    """The exact scenario the final verification report reproduced: a
    production-style direct call to ``report_incident()`` with no
    surrounding test transaction. BEFORE this fix: RuntimeError, and a
    permanently-committed, unaudited Incident row. AFTER: either a clean
    success with both rows committed, or (on a forced failure) neither row
    exists at all — never one without the other."""

    def test_direct_call_with_no_implicit_wrapper_now_succeeds_atomically(
        self, make_assigned_job: Callable, business_owner_actor: Any
    ) -> None:
        job = make_assigned_job()
        before_incidents = Incident.objects.count()
        before_audit = AuditLogEntry.objects.count()

        incident = incidents_services.report_incident(
            actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE
        )

        assert Incident.objects.count() == before_incidents + 1
        assert _audit_exists("incident", incident.id)
        assert AuditLogEntry.objects.count() == before_audit + 1  # exactly one new audit row
