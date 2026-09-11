"""Recipient actions: minimal-disclosure view, CONFIRM_RECEIPT (through the
authoritative delivery transition), REPORT_ISSUE (the append-only boundary),
and cross-job / IDOR isolation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import custody
from fikisha.jobs import recipient as recipient_service
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import (
    DeliveryProofIncomplete,
    OtpInvalid,
    RecipientActionNotAllowed,
)
from fikisha.jobs.models import ProofOfDelivery, RecipientReportedIssue

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000


@pytest.fixture
def resolved_recipient(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, declared_value_kes: int = 1_200_000) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
        custody.start_transit(actor=driver_actor, job_id=job.id)
        out = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
        job.refresh_from_db()
        principal = recipient_service.resolve_recipient(out["recipient_link_token"])
        return job, principal

    return _make


# ─── minimal disclosure ────────────────────────────────────────────
def test_view_exposes_only_the_approved_field_set(resolved_recipient: Callable) -> None:
    job, principal = resolved_recipient()
    out = recipient_service.view(principal=principal)

    expected_keys = {
        "delivery_reference",
        "recipient_display_name",
        "cargo_summary",
        "status",
        "status_label",
        "driver_first_name",
        "vehicle_class",
        "vehicle_plate",
        "operator_identity_verified",
        "allowed_actions",
    }
    assert set(out.keys()) == expected_keys
    assert out["status"] == JobStatus.AT_DESTINATION
    assert out["driver_first_name"] and " " not in out["driver_first_name"]  # first name only
    assert out["operator_identity_verified"] is True

    # never leaked, in any form
    dump = str(out).lower()
    for forbidden in (
        "phone",  # no driver/business/recipient phone
        "+2547",
        "declared_value",
        "value_band",
        "standard",
        "elevated",  # no price/band
        "trust",
        "verification_record",  # no trust/verification internals
        job.business.trading_name.lower(),  # no org info
    ):
        assert forbidden not in dump, forbidden


def test_recipient_name_is_first_name_plus_last_initial(resolved_recipient: Callable) -> None:
    job, principal = resolved_recipient()
    job.recipient_name = "Amina Wanjiku"
    job.save(update_fields=["recipient_name"])
    out = recipient_service.view(principal=principal)
    assert out["recipient_display_name"] == "Amina W."


def test_view_is_audited(resolved_recipient: Callable) -> None:
    from fikisha.audit.models import AuditLogEntry

    _job, principal = resolved_recipient()
    recipient_service.view(principal=principal)
    assert AuditLogEntry.objects.filter(
        action="job.recipient.viewed", actor_role="RECIPIENT"
    ).exists()


# ─── CONFIRM_RECEIPT — same transition + proof model as the driver ──
def test_confirm_receipt_standard_band(resolved_recipient: Callable) -> None:
    job, principal = resolved_recipient()
    out = recipient_service.confirm_receipt(
        principal=principal, code="000000", party_name="A. Wanjiku"
    )
    assert out["status"] == JobStatus.DELIVERED
    pod = ProofOfDelivery.objects.get(job=job)
    assert pod.captured_by == "RECIPIENT" and pod.otp_verified is True


def test_confirm_receipt_elevated_needs_a_photo_too(resolved_recipient: Callable) -> None:
    job, principal = resolved_recipient(declared_value_kes=ELEVATED)
    with pytest.raises(DeliveryProofIncomplete):
        recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
    out = recipient_service.confirm_receipt(
        principal=principal, code="000000", party_name="A. W", photo_evidence_ids=["ev-1"]
    )
    assert out["status"] == JobStatus.DELIVERED


def test_confirm_receipt_requires_the_real_otp_not_a_claim(resolved_recipient: Callable) -> None:
    _job, principal = resolved_recipient()
    with pytest.raises(OtpInvalid):
        recipient_service.confirm_receipt(principal=principal, code="wrong0", party_name="A. W")


def test_confirm_receipt_marks_the_link_used_and_refuses_reuse(
    resolved_recipient: Callable,
) -> None:
    job, principal = resolved_recipient()
    recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
    with pytest.raises(RecipientActionNotAllowed):
        recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")


def test_confirm_receipt_is_audited(resolved_recipient: Callable) -> None:
    from fikisha.audit.models import AuditLogEntry

    job, principal = resolved_recipient()
    recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
    assert AuditLogEntry.objects.filter(
        action="job.transition.delivered", entity_id=job.id
    ).exists()


# ─── REPORT_ISSUE — append-only boundary, no OTP ─────────────────
def test_report_issue_records_append_only_and_does_not_touch_job_status(
    resolved_recipient: Callable,
) -> None:
    job, principal = resolved_recipient()
    out = recipient_service.report_issue(
        principal=principal, category="DAMAGE", description="box was crushed"
    )
    assert out["category"] == "DAMAGE"
    report = RecipientReportedIssue.objects.get(id=out["report_id"])
    assert report.reported_via_link_id == uuid_of(principal.link_id)
    job.refresh_from_db()
    assert job.status == JobStatus.AT_DESTINATION  # unchanged — Incidents app owns triage


def test_report_issue_needs_no_otp(resolved_recipient: Callable) -> None:
    _job, principal = resolved_recipient()
    # no code/OTP argument exists on report_issue at all
    out = recipient_service.report_issue(principal=principal, category="WRONG_GOODS")
    assert out["report_id"]


def test_report_issue_rejects_an_uncurated_category(resolved_recipient: Callable) -> None:
    _job, principal = resolved_recipient()
    with pytest.raises(RecipientActionNotAllowed):
        recipient_service.report_issue(principal=principal, category="MADE_UP_CATEGORY")


def test_report_issue_is_append_only_at_the_database(resolved_recipient: Callable) -> None:
    from django.db import DatabaseError, connection, transaction

    _job, principal = resolved_recipient()
    out = recipient_service.report_issue(principal=principal, category="DAMAGE")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE recipient_reported_issue SET description = 'x' WHERE id = %s",
                    [out["report_id"]],
                )


def test_report_issue_is_rate_limited(resolved_recipient: Callable) -> None:
    from fikisha.common.exceptions import RateLimitedError

    _job, principal = resolved_recipient()
    for _ in range(5):
        recipient_service.report_issue(principal=principal, category="DAMAGE")
    with pytest.raises(RateLimitedError):
        recipient_service.report_issue(principal=principal, category="DAMAGE")


def uuid_of(value: str) -> Any:
    import uuid

    return uuid.UUID(str(value))


# ─── cross-job isolation (IDOR) ────────────────────────────────────
def test_a_recipient_principal_never_reaches_another_job(resolved_recipient: Callable) -> None:
    job_a, principal_a = resolved_recipient()
    job_b, principal_b = resolved_recipient()
    assert principal_a.job_id != principal_b.job_id

    recipient_service.confirm_receipt(principal=principal_a, code="000000", party_name="A")
    job_a.refresh_from_db()
    job_b.refresh_from_db()
    assert job_a.status == JobStatus.DELIVERED
    assert job_b.status == JobStatus.AT_DESTINATION  # untouched by principal_a's action

    view_a = recipient_service.view(principal=principal_a)
    view_b = recipient_service.view(principal=principal_b)
    assert view_a["delivery_reference"] != view_b["delivery_reference"]


def test_a_stale_principal_is_refused_after_its_link_is_reissued(
    resolved_recipient: Callable,
) -> None:
    from fikisha.jobs.errors import RecipientLinkInactive

    job, principal = resolved_recipient()
    recipient_service.reissue_link(job_id=job.id)  # e.g. an admin re-issues
    with pytest.raises(RecipientLinkInactive):
        recipient_service.view(principal=principal)
    with pytest.raises(RecipientLinkInactive):
        recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A")


# ─── Phase 2D final-verification N-6 corrective pass: confirm_receipt()'s
#     transaction boundary. These deliberately use transaction=True — the
#     default django_db marker's implicit atomic wrapper would hide exactly
#     the gap being closed here, same reasoning as BLOCKER-1's own tests. ──
def _boom(*_a: Any, **_kw: Any) -> Any:
    raise RuntimeError("simulated downstream failure")


class TestConfirmReceiptTransactionBoundary:
    @pytest.mark.django_db(transaction=True)
    def test_successful_confirmation_commits_every_side_effect_together(
        self, resolved_recipient: Callable
    ) -> None:
        from fikisha.audit.models import AuditLogEntry
        from fikisha.jobs.models import JobEvent, RecipientAccessLink

        job, principal = resolved_recipient()
        link_id = principal.link_id
        out = recipient_service.confirm_receipt(
            principal=principal, code="000000", party_name="A. Wanjiku"
        )
        assert out["status"] == JobStatus.DELIVERED
        job.refresh_from_db()
        assert job.status == JobStatus.DELIVERED
        assert ProofOfDelivery.objects.filter(job=job, captured_by="RECIPIENT").exists()
        assert JobEvent.objects.filter(job=job, type="RECIPIENT_VERIFIED").exists()
        assert AuditLogEntry.objects.filter(
            action="job.transition.delivered", entity_id=job.id
        ).exists()
        link = RecipientAccessLink.objects.get(id=link_id)
        assert link.used_at is not None  # committed in the same transaction, not a later one

    @pytest.mark.django_db(transaction=True)
    def test_a_failed_transition_does_not_irreversibly_consume_the_otp(
        self, resolved_recipient: Callable, monkeypatch: Any
    ) -> None:
        """Force a downstream failure *inside* the transition itself (after
        the delivery apply fn has already called ``consume_otp()``) and
        prove the whole thing rolls back — the OTP is not left permanently
        burned by a doomed attempt, and a retry with the identical code
        then succeeds."""
        from fikisha.jobs import service as jobs_service

        job, principal = resolved_recipient()
        real_record = jobs_service.audit.record
        monkeypatch.setattr(jobs_service.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
        job.refresh_from_db()
        assert job.status == JobStatus.AT_DESTINATION  # unchanged, not half-applied
        assert not ProofOfDelivery.objects.filter(job=job).exists()

        monkeypatch.setattr(jobs_service.audit, "record", real_record)
        out = recipient_service.confirm_receipt(
            principal=principal, code="000000", party_name="A. W"
        )
        assert out["status"] == JobStatus.DELIVERED  # the "burned" code still worked on retry

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_confirmations_still_produce_exactly_one_delivery(
        self, resolved_recipient: Callable
    ) -> None:
        """Re-proves the pre-existing concurrency guarantee (already covered
        by ``test_api_recipient.py``'s HTTP-level version) directly against
        the service function, after wrapping it in its own
        ``@transaction.atomic`` — confirms the new outer transaction doesn't
        change the locking behaviour `transition()` already provides."""
        import threading

        from django.db import connection

        job, principal = resolved_recipient()
        results: list[int] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def _confirm() -> None:
            try:
                out = recipient_service.confirm_receipt(
                    principal=principal, code="000000", party_name="A. W"
                )
                with lock:
                    results.append(1 if out.get("status") == JobStatus.DELIVERED else 0)
            except BaseException as exc:  # recorded, not swallowed
                with lock:
                    errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_confirm) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sum(results) == 1, (results, errors)
        job.refresh_from_db()
        assert job.status == JobStatus.DELIVERED
        assert ProofOfDelivery.objects.filter(job=job).count() == 1
