"""Resuming a disputed job (trust-and-disputes plan Part B, ADR-2D-54;
DR-1..DR-8, FN-1)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from fikisha.audit.models import AuditLogEntry
from fikisha.identity.authz.step_up import StepUpRequired
from fikisha.incidents import findings, resume
from fikisha.incidents.errors import DisputeAlreadyResolved, NotAuthorisedForBindingResolution
from fikisha.incidents.models import IncidentClosure, Resolution, ResumeAttestation
from fikisha.incidents.services import open_dispute, report_incident
from fikisha.jobs import confirmations, custody
from fikisha.jobs.constants import JobEventType, JobStatus
from fikisha.jobs.models import JobEvent, RecipientAccessLink
from fikisha.platform_config import services as config_service

pytestmark = pytest.mark.django_db

REASON = "Both sides agreed by phone to carry on today."


@pytest.fixture
def stepped(admin_actor: Any) -> Any:
    return dataclasses.replace(admin_actor, is_step_up_fresh=True)


def _dispute(job: Any, actor: Any, type_: str = "DELAY") -> tuple[Any, Any]:
    incident = report_incident(actor=actor, job_id=job.id, type=type_)
    dispute, _ = open_dispute(actor=actor, job_id=job.id, incident_ids=[incident.id])
    return dispute, incident


def _resume(dispute: Any, actor: Any, **kw: Any) -> Any:
    return resume.resume_dispute(
        actor=actor,
        dispute_id=dispute.id,
        sender_method=kw.pop("sender_method", "PHONE"),
        operator_method=kw.pop("operator_method", "IN_PERSON"),
        reason=kw.pop("reason", REASON),
        **kw,
    )


@pytest.fixture
def at_pickup(make_assigned_job: Callable, driver_actor: Any, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.sender_confirm_pickup(actor=business_owner_actor, job_id=job.id, party_name="S. Sender")
    job.refresh_from_db()
    return job


def test_resume_returns_the_job_to_its_pre_dispute_state(
    at_pickup: Any, business_owner_actor: Any, stepped: Any
) -> None:
    dispute, incident = _dispute(at_pickup, business_owner_actor)
    resolution, view = _resume(dispute, stepped)
    at_pickup.refresh_from_db()
    assert at_pickup.status == JobStatus.AT_PICKUP
    assert view["status"] == JobStatus.AT_PICKUP
    assert resolution.resumed is True
    assert resolution.routed_job_status == JobStatus.AT_PICKUP
    attestation = ResumeAttestation.objects.get(dispute=dispute)
    assert (attestation.sender_method, attestation.operator_method) == ("PHONE", "IN_PERSON")
    assert IncidentClosure.objects.get(incident=incident).reason_code == "DISPUTE_RESOLVED"
    assert JobEvent.objects.filter(job=at_pickup, type=JobEventType.RESUMED).exists()
    assert AuditLogEntry.objects.filter(action="dispute.resumed").exists()
    dispute.refresh_from_db()
    assert dispute.status == "RESOLVED"


def test_confirmations_before_the_resume_stop_counting_and_a_fresh_code_is_issued(
    at_pickup: Any, business_owner_actor: Any, stepped: Any
) -> None:
    assert confirmations.counted(at_pickup, "PICKUP").exists()  # the sender confirmed
    issued_before = JobEvent.objects.filter(job=at_pickup, type="PICKUP_OTP_ISSUED").count()
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    _resume(dispute, stepped)
    assert not confirmations.counted(at_pickup, "PICKUP").exists()
    assert JobEvent.objects.filter(job=at_pickup, type="PICKUP_OTP_ISSUED").count() == (
        issued_before + 1
    )
    # the sender can confirm again
    custody.sender_confirm_pickup(actor=business_owner_actor, job_id=at_pickup.id)
    assert confirmations.counted(at_pickup, "PICKUP").filter(method="IN_APP").exists()


def test_resume_to_the_destination_reissues_the_recipient_link(
    make_assigned_job: Callable, driver_actor: Any, business_owner_actor: Any, stepped: Any
) -> None:
    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.confirm_pickup(
        actor=driver_actor, job_id=job.id, code="000000", photo_evidence_ids=["ev-goods"]
    )
    custody.start_transit(actor=driver_actor, job_id=job.id)
    custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    old = RecipientAccessLink.objects.get(job=job)
    dispute, _ = _dispute(job, business_owner_actor)
    _resume(dispute, stepped)
    # revoked and replaced (the audit entry keeps the revoked row's record)
    fresh = RecipientAccessLink.objects.get(job=job)
    assert fresh.id != old.id
    assert fresh.revoked_at is None and fresh.used_at is None
    assert fresh.allowed_actions == old.allowed_actions  # never wider
    assert AuditLogEntry.objects.filter(
        action="job.recipient_link.revoked", entity_id=str(old.id)
    ).exists()


@pytest.mark.parametrize("who", ["ops", "plain_admin"])
def test_only_a_stepped_up_platform_admin_resumes(
    at_pickup: Any, business_owner_actor: Any, ops_actor: Any, admin_actor: Any, who: str
) -> None:
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    if who == "ops":
        with pytest.raises(NotAuthorisedForBindingResolution):
            _resume(dispute, ops_actor)
    else:
        with pytest.raises(StepUpRequired):
            _resume(dispute, admin_actor)


def test_a_serious_incident_needs_a_finding_and_undetermined_is_enough(
    at_pickup: Any, business_owner_actor: Any, stepped: Any, ops_actor: Any
) -> None:
    dispute, incident = _dispute(at_pickup, business_owner_actor, type_="DAMAGE")
    with pytest.raises(resume.ResumeNotAllowed, match="serious_findings"):
        _resume(dispute, stepped)
    findings.record_finding(
        actor=ops_actor,
        incident_id=incident.id,
        outcome="UNDETERMINED",
        parties=[],
        reason="Photos don't show where the scratch came from.",
    )
    _resume(dispute, stepped)


def test_after_the_window_the_job_stays_disputed(
    at_pickup: Any, business_owner_actor: Any, stepped: Any, platform_admin: Any
) -> None:
    config_service.apply_change(
        patch={"disputes": {"resume_window_days": 0}},
        changed_by=platform_admin,
        rationale="No resume window in this test.",
    )
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    with pytest.raises(resume.ResumeNotAllowed, match="within_window"):
        _resume(dispute, stepped)
    at_pickup.refresh_from_db()
    assert at_pickup.status == JobStatus.DISPUTED


def test_a_driver_no_longer_eligible_blocks_resume(
    at_pickup: Any, business_owner_actor: Any, stepped: Any, eligible_driver: Any
) -> None:
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    eligible_driver.status = "SUSPENDED"
    eligible_driver.save(update_fields=["status"])
    with pytest.raises(resume.ResumeNotAllowed, match="assignment_eligible"):
        _resume(dispute, stepped)


def test_a_job_disputed_after_completion_is_never_resumed(
    delivered_job: Callable, complete_job: Callable, business_owner_actor: Any, stepped: Any
) -> None:
    job = delivered_job()
    complete_job(job)
    job.refresh_from_db()
    dispute, _ = _dispute(job, business_owner_actor, type_="MISSING_GOODS")
    with pytest.raises(resume.ResumeNotAllowed):
        _resume(dispute, stepped)


def test_resolved_disputes_cannot_be_resumed_and_a_resumed_job_can_be_disputed_again(
    at_pickup: Any, business_owner_actor: Any, stepped: Any
) -> None:
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    _resume(dispute, stepped)
    with pytest.raises(DisputeAlreadyResolved):
        _resume(dispute, stepped)
    second, _ = _dispute(at_pickup, business_owner_actor)  # DR-6
    assert second.id != dispute.id


def test_the_agreement_methods_and_reason_are_checked(
    at_pickup: Any, business_owner_actor: Any, stepped: Any
) -> None:
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    with pytest.raises(resume.InvalidAgreementMethod):
        _resume(dispute, stepped, sender_method="WHATSAPP")
    from fikisha.incidents.errors import RationaleRequired

    with pytest.raises(RationaleRequired):
        _resume(dispute, stepped, reason="ok")


def test_a_resume_resolution_must_go_back_to_a_resumable_state(
    at_pickup: Any, business_owner_actor: Any, platform_admin: Any
) -> None:
    dispute, _ = _dispute(at_pickup, business_owner_actor)
    with pytest.raises(IntegrityError), transaction.atomic():
        Resolution.objects.create(
            dispute=dispute,
            outcome_code="ADMIN_DETERMINATION",
            rationale=REASON,
            routed_job_status="AT_PICKUP",
            resolved_by_admin=platform_admin,
            resumed=False,
        )


class TestApi:
    def test_ops_reads_the_checklist_but_cannot_resume(
        self, client_for: Callable, at_pickup: Any, business_owner_actor: Any, ops_officer: Any
    ) -> None:
        dispute, _ = _dispute(at_pickup, business_owner_actor)
        client = client_for(ops_officer)
        r = client.get(f"/api/v1/disputes/{dispute.id}/resume")
        assert r.status_code == 200, r.content
        assert r.json()["target_status"] == "AT_PICKUP"
        assert r.json()["ok"] is True
        post = client.post(
            f"/api/v1/disputes/{dispute.id}/resume",
            {"sender_method": "PHONE", "operator_method": "PHONE", "reason": REASON},
            format="json",
        )
        assert post.status_code == 403

    def test_a_party_cannot_read_the_checklist(
        self, client_for: Callable, at_pickup: Any, business_owner_actor: Any
    ) -> None:
        dispute, _ = _dispute(at_pickup, business_owner_actor)
        assert (
            client_for(business_owner_actor.user)
            .get(f"/api/v1/disputes/{dispute.id}/resume")
            .status_code
            == 403
        )
