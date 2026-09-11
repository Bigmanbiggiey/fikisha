"""RecipientReportedIssue -> Incident intake (ADR-2D-17 boundary + Step 8):
creates/attaches an incident, the original report is never mutated, a
recipient cannot modify incident state, cross-job isolation holds."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import IncidentType
from fikisha.incidents.models import Incident
from fikisha.incidents.services import intake_recipient_report
from fikisha.jobs import custody
from fikisha.jobs import recipient as recipient_service
from fikisha.jobs.models import RecipientReportedIssue

pytestmark = pytest.mark.django_db


@pytest.fixture
def reported_issue(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, category: str = "DAMAGE", declared_value_kes: int = 1_200_000) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
        custody.start_transit(actor=driver_actor, job_id=job.id)
        out = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
        principal = recipient_service.resolve_recipient(out["recipient_link_token"])
        report_out = recipient_service.report_issue(
            principal=principal, category=category, description="the goods were damaged"
        )
        report = RecipientReportedIssue.objects.get(id=report_out["report_id"])
        job.refresh_from_db()
        return job, principal, report

    return _make


@pytest.mark.parametrize(
    ("category", "expected_type"),
    [
        ("WRONG_RECIPIENT", IncidentType.WRONG_RECIPIENT),
        ("DAMAGE", IncidentType.DAMAGE),
        ("MISSING_GOODS", IncidentType.MISSING_GOODS),
        ("WRONG_GOODS", IncidentType.OTHER),
        ("OTHER", IncidentType.OTHER),
    ],
)
def test_intake_maps_recipient_categories_to_incident_types(
    reported_issue: Callable, category: str, expected_type: str
) -> None:
    _job, _principal, report = reported_issue(category=category)
    incident = intake_recipient_report(report_id=report.id)
    assert incident.type == expected_type
    assert incident.source_report_id == report.id
    assert incident.reported_by_kind == "RECIPIENT_LINK"
    assert incident.reported_by_link_id == report.reported_via_link_id


def test_intake_preserves_the_original_report_unmutated(reported_issue: Callable) -> None:
    from django.db import DatabaseError, connection, transaction

    _job, _principal, report = reported_issue()
    original_description = report.description
    intake_recipient_report(report_id=report.id)

    report.refresh_from_db()
    assert report.description == original_description
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE recipient_reported_issue SET description = 'x' WHERE id = %s",
                    [str(report.id)],
                )


def test_intake_is_idempotent_and_does_not_duplicate(reported_issue: Callable) -> None:
    _job, _principal, report = reported_issue()
    first = intake_recipient_report(report_id=report.id)
    second = intake_recipient_report(report_id=report.id)
    assert first.id == second.id
    assert Incident.objects.filter(source_report_id=report.id).count() == 1


def test_intake_does_not_touch_job_status(reported_issue: Callable) -> None:
    from fikisha.jobs.constants import JobStatus

    job, _principal, report = reported_issue()
    intake_recipient_report(report_id=report.id)
    job.refresh_from_db()
    assert job.status == JobStatus.AT_DESTINATION  # unchanged by intake alone


def test_a_recipient_cannot_intake_or_modify_incident_state_itself(
    reported_issue: Callable,
) -> None:
    """``intake_recipient_report`` is a plain callable for ops/an admin/a worker
    to invoke (Founder-confirmed: not auto-wired) — a bare ``RecipientPrincipal``
    has no capability to call it or any incident-review action at all; nothing
    in its fixed ``allowed_actions`` ceiling names an incident capability."""
    from fikisha.jobs.constants import RecipientAllowedAction

    _job, principal, _report = reported_issue()
    assert set(principal.allowed_actions) == {
        RecipientAllowedAction.VIEW,
        RecipientAllowedAction.CONFIRM_RECEIPT,
        RecipientAllowedAction.REPORT_ISSUE,
    }


def test_intake_is_scoped_to_its_own_job_only(reported_issue: Callable) -> None:
    job_a, _pa, report_a = reported_issue()
    job_b, _pb, report_b = reported_issue()
    incident_a = intake_recipient_report(report_id=report_a.id)
    incident_b = intake_recipient_report(report_id=report_b.id)
    assert incident_a.job_id == job_a.id
    assert incident_b.job_id == job_b.id
    assert incident_a.id != incident_b.id


def test_intake_attaches_the_reports_own_photo_evidence_without_copying(
    make_assigned_job: Callable, driver_actor: Any
) -> None:
    from fikisha.evidence.models import EvidenceObject, EvidencePurpose, UploaderKind
    from fikisha.incidents.models import IncidentEvidence

    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    custody.start_transit(actor=driver_actor, job_id=job.id)
    out = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    principal = recipient_service.resolve_recipient(out["recipient_link_token"])

    photo = EvidenceObject.objects.create(
        storage_key="evidence/test/photo.jpg",
        content_type="image/jpeg",
        size_bytes=10,
        sha256="x" * 64,
        purpose=EvidencePurpose.INCIDENT_EVIDENCE,
        uploaded_by_kind=UploaderKind.RECIPIENT,
    )
    report_out = recipient_service.report_issue(
        principal=principal, category="DAMAGE", photo_evidence_ids=[str(photo.id)]
    )
    report = RecipientReportedIssue.objects.get(id=report_out["report_id"])
    incident = intake_recipient_report(report_id=report.id)

    row = IncidentEvidence.objects.get(incident=incident)
    assert row.evidence_object_id == photo.id  # same object, not a copy
    assert EvidenceObject.objects.filter(id=photo.id).count() == 1
