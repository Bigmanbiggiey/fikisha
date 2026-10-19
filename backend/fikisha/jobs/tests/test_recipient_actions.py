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
from fikisha.jobs.models import CustodyConfirmation, ProofOfDelivery, RecipientReportedIssue

pytestmark = pytest.mark.django_db

ELEVATED = 6_000_000


@pytest.fixture
def resolved_recipient(make_assigned_job: Callable, driver_actor: Any) -> Callable[..., Any]:
    def _make(*, declared_value_kes: int = 1_200_000) -> Any:
        job = make_assigned_job(declared_value_kes=declared_value_kes)
        custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
        custody.confirm_pickup(
            actor=driver_actor, job_id=job.id, code="000000", photo_evidence_ids=["ev-goods"]
        )
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


# ─── CONFIRM_RECEIPT — the recipient's part; the driver completes ────
# (founder assessment 2026-10-20 L-5: both parties take part)
def _complete(job: Any, driver_actor: Any, **kw: Any) -> dict[str, Any]:
    return custody.confirm_delivery(
        actor=driver_actor, job_id=job.id, party_name="A. Wanjiku", **kw
    )


def test_confirm_receipt_records_the_code_and_the_driver_completes(
    resolved_recipient: Callable, driver_actor: Any
) -> None:
    job, principal = resolved_recipient()
    out = recipient_service.confirm_receipt(
        principal=principal, code="000000", party_name="A. Wanjiku"
    )
    # Recorded, not delivered: the driver's call completes it.
    assert out["status"] == JobStatus.AT_DESTINATION
    row = CustodyConfirmation.objects.get(job=job, stage="DELIVERY")
    assert (row.method, row.captured_by, row.party_name) == ("OTP", "RECIPIENT", "A. Wanjiku")

    # no code needed: the recipient gave it; the driver adds the photo (PD-2)
    out = _complete(job, driver_actor, photo_evidence_ids=["ev-1"])
    assert out["status"] == JobStatus.DELIVERED
    pod = ProofOfDelivery.objects.get(job=job)
    assert pod.otp_verified is True and pod.methods == ["OTP", "PHOTO"]


def test_a_recipients_signature_counts_too(resolved_recipient: Callable, driver_actor: Any) -> None:
    import uuid

    job, principal = resolved_recipient()
    sig = str(uuid.uuid4())
    recipient_service.confirm_receipt(
        principal=principal, code="000000", party_name="A. W", signature_evidence_id=sig
    )
    _complete(job, driver_actor, photo_evidence_ids=["ev-1"])
    pod = ProofOfDelivery.objects.get(job=job)
    assert pod.methods == ["OTP", "SIGNATURE", "PHOTO"]
    assert str(pod.signature_evidence_id) == sig


def test_elevated_still_needs_the_drivers_photo(
    resolved_recipient: Callable, driver_actor: Any
) -> None:
    job, principal = resolved_recipient(declared_value_kes=ELEVATED)
    recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
    with pytest.raises(DeliveryProofIncomplete, match="a photo"):
        _complete(job, driver_actor)
    out = _complete(job, driver_actor, photo_evidence_ids=["ev-1"])
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
        action="job.custody.recipient_confirmed", entity_id=job.id
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
    assert CustodyConfirmation.objects.filter(job=job_a).count() == 1
    assert not CustodyConfirmation.objects.filter(job=job_b).exists()  # untouched

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
    """The recipient's confirmation commits all-or-nothing (the record, the
    audit row, the consumed code, the used link), and concurrent attempts
    record exactly once."""

    @pytest.mark.django_db(transaction=True)
    def test_successful_confirmation_commits_every_side_effect_together(
        self, resolved_recipient: Callable
    ) -> None:
        from fikisha.audit.models import AuditLogEntry
        from fikisha.jobs.models import RecipientAccessLink, RecipientOtpChallenge

        job, principal = resolved_recipient()
        recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
        assert CustodyConfirmation.objects.filter(job=job, method="OTP").exists()
        assert AuditLogEntry.objects.filter(
            action="job.custody.recipient_confirmed", entity_id=job.id
        ).exists()
        assert RecipientAccessLink.objects.get(id=principal.link_id).used_at is not None
        challenge = RecipientOtpChallenge.objects.filter(job=job).latest("seq")
        assert challenge.consumed_at is not None

    @pytest.mark.django_db(transaction=True)
    def test_a_failure_rolls_everything_back_and_the_code_still_works(
        self, resolved_recipient: Callable, monkeypatch: Any
    ) -> None:
        job, principal = resolved_recipient()
        real_record = recipient_service.audit.record
        monkeypatch.setattr(recipient_service.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
        assert not CustodyConfirmation.objects.filter(job=job).exists()

        monkeypatch.setattr(recipient_service.audit, "record", real_record)
        recipient_service.confirm_receipt(principal=principal, code="000000", party_name="A. W")
        assert CustodyConfirmation.objects.filter(job=job).count() == 1

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_confirmations_record_exactly_once(
        self, resolved_recipient: Callable
    ) -> None:
        import threading

        from django.db import connection

        job, principal = resolved_recipient()
        errors: list[BaseException] = []
        lock = threading.Lock()

        def _confirm() -> None:
            try:
                recipient_service.confirm_receipt(
                    principal=principal, code="000000", party_name="A. W"
                )
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

        assert CustodyConfirmation.objects.filter(job=job, method="OTP").count() == 1
        assert len(errors) == 4, errors
