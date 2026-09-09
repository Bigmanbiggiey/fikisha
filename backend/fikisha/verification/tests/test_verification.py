"""Verification — lifecycle, reviewer authorization, expiry, history (Phase 2C §28)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.audit.models import AuditLogEntry
from fikisha.common.exceptions import ConflictError, DomainError
from fikisha.identity.authz.actors import actor_from_user
from fikisha.operators import services as op_services
from fikisha.outbox.models import OutboxEvent
from fikisha.verification import services
from fikisha.verification.models import Domain, State, VerificationDecision, VerificationRecord

pytestmark = pytest.mark.django_db


def _actor(u: Any) -> Any:
    return actor_from_user(u)


@pytest.fixture
def operator_profile(user: Any) -> Any:
    return op_services.create_profile(actor=_actor(user), full_name="Op One")


@pytest.fixture
def id_record(user: Any, operator_profile: Any) -> Any:
    return services.submit(
        actor=_actor(user),
        subject=operator_profile,
        domain=Domain.IDENTITY,
        evidence_items=[
            {"data": b"national-id", "content_type": "image/jpeg", "kind": "NATIONAL_ID"}
        ],
    )


class TestLifecycle:
    def test_submit_creates_pending_record_with_history_and_event(self, id_record: Any) -> None:
        assert id_record.state == State.SUBMITTED
        assert id_record.domain == Domain.IDENTITY
        assert id_record.decisions.filter(action="SUBMIT").exists()
        assert id_record.evidence.filter(superseded_at__isnull=True).count() == 1
        assert AuditLogEntry.objects.filter(action="verification.submitted").exists()
        assert OutboxEvent.objects.filter(event_type="verification.submitted").exists()

    def test_full_approve_flow(self, ops_officer: Any, id_record: Any) -> None:
        reviewer = _actor(ops_officer)
        rec = services.start_review(reviewer=reviewer, record=id_record)
        assert rec.state == State.IN_REVIEW
        assert rec.owner_admin_id == ops_officer.id
        rec = services.approve(reviewer=reviewer, record=rec, reason="looks good")
        assert rec.state == State.VERIFIED
        assert rec.reviewer_id == ops_officer.id
        assert rec.verified_at is not None
        assert OutboxEvent.objects.filter(event_type="verification.decided").exists()

    def test_reject_requires_a_reason(self, ops_officer: Any, id_record: Any) -> None:
        reviewer = _actor(ops_officer)
        services.start_review(reviewer=reviewer, record=id_record)
        with pytest.raises(DomainError):
            services.reject(reviewer=reviewer, record=id_record, reason="  ")
        rec = services.reject(reviewer=reviewer, record=id_record, reason="blurry scan")
        assert rec.state == State.REJECTED

    def test_request_info_then_resubmit(self, user: Any, ops_officer: Any, id_record: Any) -> None:
        reviewer = _actor(ops_officer)
        services.start_review(reviewer=reviewer, record=id_record)
        rec = services.request_info(reviewer=reviewer, record=id_record, note="send the back page")
        assert rec.state == State.INFO_REQUESTED
        rec = services.submit(
            actor=_actor(user),
            subject=rec.subject_operator,
            domain=Domain.IDENTITY,
            evidence_items=[
                {"data": b"id-v2", "content_type": "image/jpeg", "kind": "NATIONAL_ID"}
            ],
        )
        assert rec.state == State.SUBMITTED

    def test_cannot_review_before_starting(self, ops_officer: Any, id_record: Any) -> None:
        with pytest.raises(ConflictError):
            services.approve(reviewer=_actor(ops_officer), record=id_record)

    def test_cannot_resubmit_while_pending(self, user: Any, id_record: Any) -> None:
        with pytest.raises(ConflictError):
            services.submit(
                actor=_actor(user),
                subject=id_record.subject_operator,
                domain=Domain.IDENTITY,
                evidence_items=[
                    {"data": b"x", "content_type": "image/jpeg", "kind": "NATIONAL_ID"}
                ],
            )


class TestReviewerRules:
    def test_the_submitter_may_not_review(self, platform_admin: Any, operator_profile: Any) -> None:
        admin_actor = _actor(platform_admin)
        rec = services.submit(
            actor=admin_actor,  # admin submits on the operator's behalf
            subject=operator_profile,
            domain=Domain.IDENTITY,
            evidence_items=[{"data": b"id", "content_type": "image/jpeg", "kind": "NATIONAL_ID"}],
        )
        with pytest.raises(DomainError) as exc:
            services.start_review(reviewer=admin_actor, record=rec)
        assert exc.value.code == "reviewer_is_submitter"


class TestExpiry:
    def test_effective_state_folds_expiry_without_a_sweep(
        self, ops_officer: Any, id_record: Any
    ) -> None:
        reviewer = _actor(ops_officer)
        services.start_review(reviewer=reviewer, record=id_record)
        rec = services.approve(
            reviewer=reviewer,
            record=id_record,
            expires_at=timezone.now() - timedelta(days=1),
        )
        assert rec.state == State.VERIFIED  # the stored cache
        assert rec.effective_state() == State.EXPIRED  # deterministic from data
        assert rec.is_currently_valid() is False

    def test_expire_due_materialises_the_decision(self, ops_officer: Any, id_record: Any) -> None:
        reviewer = _actor(ops_officer)
        services.start_review(reviewer=reviewer, record=id_record)
        services.approve(
            reviewer=reviewer, record=id_record, expires_at=timezone.now() - timedelta(hours=1)
        )
        n = services.expire_due()
        assert n == 1
        id_record.refresh_from_db()
        assert id_record.state == State.EXPIRED
        assert id_record.decisions.filter(action="EXPIRE").exists()
        assert OutboxEvent.objects.filter(event_type="verification.expired").exists()


class TestEvidenceHistory:
    def test_replacing_evidence_supersedes_but_keeps_history(
        self, user: Any, operator_profile: Any
    ) -> None:
        actor = _actor(user)
        rec = services.get_or_create_record(subject=operator_profile, domain=Domain.LICENCE)
        services.add_evidence(
            actor=actor,
            record=rec,
            item={"data": b"v1", "content_type": "image/jpeg", "kind": "DRIVING_LICENCE"},
        )
        services.add_evidence(
            actor=actor,
            record=rec,
            item={"data": b"v2", "content_type": "image/jpeg", "kind": "DRIVING_LICENCE"},
        )
        assert rec.evidence.count() == 2
        assert rec.evidence.filter(superseded_at__isnull=True).count() == 1
        assert rec.evidence.filter(superseded_at__isnull=False).count() == 1


class TestRequirements:
    def test_operator_required_domains(self, operator_profile: Any) -> None:
        from fikisha.verification.requirements import required_domains_for_subject

        assert set(required_domains_for_subject(operator_profile)) == {
            "IDENTITY",
            "LICENCE",
            "GOOD_CONDUCT",
        }

    def test_heavy_vehicle_needs_heavy_class_compliance(self, user: Any, client_for: Any) -> None:
        from fikisha.verification.requirements import required_domains

        assert "HEAVY_CLASS_COMPLIANCE" in required_domains("VEHICLE", vehicle_is_heavy=True)
        assert "HEAVY_CLASS_COMPLIANCE" not in required_domains("VEHICLE", vehicle_is_heavy=False)

    def test_wrong_domain_for_subject_is_rejected(self, operator_profile: Any) -> None:
        with pytest.raises(DomainError):
            services.get_or_create_record(subject=operator_profile, domain=Domain.VEHICLE)


def test_decisions_are_append_only(ops_officer: Any, id_record: Any) -> None:
    services.start_review(reviewer=_actor(ops_officer), record=id_record)
    d = VerificationDecision.objects.filter(record=id_record).first()
    assert d is not None
    from fikisha.common.models import AppendOnlyModelError

    d.reason = "tampered"
    with pytest.raises(AppendOnlyModelError):
        d.save()
    with pytest.raises(AppendOnlyModelError):
        VerificationDecision.objects.filter(record=id_record).update(reason="x")


def test_record_check_constraint(db: Any, operator_profile: Any) -> None:
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        VerificationRecord.objects.create(subject_type="OPERATOR", domain="IDENTITY")
