"""Verification domain services.

Every decision is atomic: the ``VerificationDecision`` row, the ``state`` cache
update, the audit row, and the outbox event commit together (Phase 2C brief §32).
Authorization is run by the API layer first; these functions enforce the state
machine and the "submitter ≠ approver" rule (brief §17).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.exceptions import ConflictError, DomainError
from fikisha.evidence import services as evidence_services
from fikisha.evidence.models import PiiClass
from fikisha.operators.models import OperatingBase, OperatorProfile
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config
from fikisha.vehicles.models import Vehicle
from fikisha.verification.models import (
    VALID_DOMAINS_BY_SUBJECT,
    Action,
    Domain,
    State,
    SubjectType,
    VerificationDecision,
    VerificationEvidence,
    VerificationRecord,
)

SUBMITTED_EVENT = "verification.submitted"
DECIDED_EVENT = "verification.decided"
EXPIRED_EVENT = "verification.expired"

_HIGH_PII_KINDS = {"NATIONAL_ID", "PASSPORT", "SELFIE", "DRIVING_LICENCE", "GOOD_CONDUCT_CERT"}
_HIGH_PII_DOMAINS = {Domain.IDENTITY, Domain.LICENCE, Domain.GOOD_CONDUCT}


def _audit_actor(actor: Any) -> Any:
    return getattr(actor, "user", actor)


def _actor_role(actor: Any) -> str:
    return str(getattr(actor, "audit_role", "") or "")


def _subject_kwargs(subject: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(subject, OperatorProfile):
        return SubjectType.OPERATOR, {"subject_operator": subject}
    if isinstance(subject, Vehicle):
        return SubjectType.VEHICLE, {"subject_vehicle": subject}
    if isinstance(subject, OperatingBase):
        return SubjectType.BASE, {"subject_base": subject}
    raise TypeError(f"unsupported verification subject: {type(subject).__name__}")


def get_or_create_record(*, subject: Any, domain: str) -> VerificationRecord:
    subject_type, kw = _subject_kwargs(subject)
    if domain not in VALID_DOMAINS_BY_SUBJECT.get(subject_type, set()):
        raise DomainError(
            f"{domain} is not a valid verification domain for a {subject_type}.",
            code="validation_error",
        )
    record, _created = VerificationRecord.objects.get_or_create(
        subject_type=subject_type, domain=domain, **kw
    )
    return record


def _pii_class_for(domain: str, kind: str) -> str:
    if domain in _HIGH_PII_DOMAINS or kind in _HIGH_PII_KINDS:
        return PiiClass.HIGH
    return PiiClass.MEDIUM


@transaction.atomic
def add_evidence(
    *, actor: Any, record: VerificationRecord, item: dict[str, Any]
) -> VerificationEvidence:
    """Attach one evidence item (supersedes a prior current item of the same
    ``kind``). Does not change the record's state — call ``mark_submitted``.
    """
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.effective_state() in {State.SUBMITTED, State.IN_REVIEW}:
        raise ConflictError("This verification is already awaiting review.", code="already_pending")
    user = _audit_actor(actor)
    kind = str(item["kind"])
    obj = evidence_services.store(
        data=item["data"],
        content_type=item["content_type"],
        purpose="VERIFICATION_DOC",
        pii_class=_pii_class_for(record.domain, kind),
        linked_entity_type="verification_record",
        linked_entity_id=record.id,
        uploaded_by=user,
        uploaded_by_kind="ADMIN" if getattr(actor, "is_admin", False) else "OPERATOR",
    )
    VerificationEvidence.objects.filter(
        record=record, kind=kind, superseded_at__isnull=True
    ).update(superseded_at=timezone.now())
    ev = VerificationEvidence.objects.create(
        record=record,
        evidence_object=obj,
        kind=kind,
        issued_at=item.get("issued_at"),
        expires_at=item.get("expires_at"),
        submitted_by=user if getattr(user, "pk", None) else None,
    )
    audit.record(
        actor=actor,
        action="verification.evidence.added",
        entity_type="verification_record",
        entity_id=record.id,
        after={"domain": record.domain, "kind": kind, "evidence_id": str(obj.id)},
    )
    return ev


@transaction.atomic
def mark_submitted(
    *, actor: Any, record: VerificationRecord, issuing_authority: str = ""
) -> VerificationRecord:
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.effective_state() in {State.SUBMITTED, State.IN_REVIEW}:
        raise ConflictError("This verification is already awaiting review.", code="already_pending")
    if not record.evidence.filter(superseded_at__isnull=True).exists():
        raise DomainError("Attach at least one evidence item first.", code="validation_error")

    user = _audit_actor(actor)
    if issuing_authority:
        record.issuing_authority = issuing_authority
    decision = VerificationDecision.objects.create(
        record=record,
        action=Action.SUBMIT,
        actor=user if getattr(user, "pk", None) else None,
        actor_role=_actor_role(actor),
    )
    record.state = State.SUBMITTED
    record.last_decision = decision
    record.reviewer = None
    record.owner_admin = None
    record.verified_at = None
    record.save(
        update_fields=[
            "state",
            "last_decision",
            "reviewer",
            "owner_admin",
            "verified_at",
            "issuing_authority",
            "updated_at",
        ]
    )

    current_count = record.evidence.filter(superseded_at__isnull=True).count()
    audit.record(
        actor=actor,
        action="verification.submitted",
        entity_type="verification_record",
        entity_id=record.id,
        after={"domain": record.domain, "evidence_count": current_count},
    )
    emit(
        event_type=SUBMITTED_EVENT,
        aggregate_type="verification_record",
        aggregate_id=str(record.id),
        payload={
            "record_id": str(record.id),
            "subject_type": record.subject_type,
            "subject_id": str(record.subject_id),
            "domain": record.domain,
        },
    )
    return record


@transaction.atomic
def submit(
    *,
    actor: Any,
    subject: Any,
    domain: str,
    evidence_items: list[dict[str, Any]],
    issuing_authority: str = "",
) -> VerificationRecord:
    """Convenience: attach every item then mark the record submitted (one txn)."""
    record = get_or_create_record(subject=subject, domain=domain)
    if not evidence_items:
        raise DomainError("At least one evidence item is required.", code="validation_error")
    for item in evidence_items:
        add_evidence(actor=actor, record=record, item=item)
    return mark_submitted(actor=actor, record=record, issuing_authority=issuing_authority)


def _assert_reviewer_not_submitter(record: VerificationRecord, reviewer_user: Any) -> None:
    if reviewer_user is None:
        return
    if VerificationDecision.objects.filter(
        record=record, action=Action.SUBMIT, actor_id=reviewer_user.id
    ).exists():
        raise DomainError(
            "The person who submitted this evidence may not review it.",
            code="reviewer_is_submitter",
        )


def _record_decision(
    *,
    actor: Any,
    record: VerificationRecord,
    action: str,
    new_state: str,
    reason: str = "",
    note: str = "",
    set_expires_at: Any | None = None,
    verified_at: Any | None = None,
    reviewer: Any | None = None,
) -> VerificationRecord:
    user = _audit_actor(actor)
    prev_state = record.state
    decision = VerificationDecision.objects.create(
        record=record,
        action=action,
        actor=user if getattr(user, "pk", None) else None,
        actor_role=_actor_role(actor),
        reason=reason,
        note=note,
        set_expires_at=set_expires_at,
    )
    record.state = new_state
    record.last_decision = decision
    fields = ["state", "last_decision", "updated_at"]
    if reviewer is not None:
        record.reviewer = reviewer
        fields.append("reviewer")
    if action == Action.START_REVIEW:
        record.owner_admin = user
        fields.append("owner_admin")
    if new_state == State.VERIFIED:
        record.verified_at = verified_at or timezone.now()
        record.expires_at = set_expires_at
        fields += ["verified_at", "expires_at"]
    record.save(update_fields=list(dict.fromkeys(fields)))

    audit.record(
        actor=actor,
        action=f"verification.{action.lower()}",
        entity_type="verification_record",
        entity_id=record.id,
        before={"state": prev_state},
        after={
            "state": new_state,
            "reason": reason,
            "expires_at": set_expires_at.isoformat() if set_expires_at else None,
        },
    )
    if action != Action.START_REVIEW:
        emit(
            event_type=EXPIRED_EVENT if action == Action.EXPIRE else DECIDED_EVENT,
            aggregate_type="verification_record",
            aggregate_id=str(record.id),
            payload={
                "record_id": str(record.id),
                "subject_type": record.subject_type,
                "subject_id": str(record.subject_id),
                "domain": record.domain,
                "action": action,
                "state": new_state,
            },
        )
    return record


@transaction.atomic
def start_review(*, reviewer: Any, record: VerificationRecord) -> VerificationRecord:
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.state not in {State.SUBMITTED, State.INFO_REQUESTED}:
        raise ConflictError(
            f"Cannot start review from state {record.state}.", code="invalid_transition"
        )
    _assert_reviewer_not_submitter(record, _audit_actor(reviewer))
    return _record_decision(
        actor=reviewer, record=record, action=Action.START_REVIEW, new_state=State.IN_REVIEW
    )


@transaction.atomic
def request_info(*, reviewer: Any, record: VerificationRecord, note: str) -> VerificationRecord:
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.state != State.IN_REVIEW:
        raise ConflictError("Start the review first.", code="invalid_transition")
    if not note.strip():
        raise DomainError(
            "A note is required when requesting more information.", code="validation_error"
        )
    return _record_decision(
        actor=reviewer,
        record=record,
        action=Action.REQUEST_INFO,
        new_state=State.INFO_REQUESTED,
        note=note.strip(),
    )


@transaction.atomic
def approve(
    *,
    reviewer: Any,
    record: VerificationRecord,
    expires_at: Any | None = None,
    reason: str = "",
) -> VerificationRecord:
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.state != State.IN_REVIEW:
        raise ConflictError("Start the review before approving.", code="invalid_transition")
    _assert_reviewer_not_submitter(record, _audit_actor(reviewer))

    if expires_at is None:
        expires_at = _suggested_expiry(record)
    return _record_decision(
        actor=reviewer,
        record=record,
        action=Action.APPROVE,
        new_state=State.VERIFIED,
        reason=reason,
        set_expires_at=expires_at,
        reviewer=_audit_actor(reviewer),
    )


@transaction.atomic
def reject(*, reviewer: Any, record: VerificationRecord, reason: str) -> VerificationRecord:
    record = VerificationRecord.objects.select_for_update().get(pk=record.pk)
    if record.state != State.IN_REVIEW:
        raise ConflictError("Start the review before rejecting.", code="invalid_transition")
    if not reason.strip():
        raise DomainError("A reason is required to reject.", code="validation_error")
    _assert_reviewer_not_submitter(record, _audit_actor(reviewer))
    return _record_decision(
        actor=reviewer,
        record=record,
        action=Action.REJECT,
        new_state=State.REJECTED,
        reason=reason.strip(),
        reviewer=_audit_actor(reviewer),
    )


def _suggested_expiry(record: VerificationRecord) -> Any | None:
    current = record.evidence.filter(superseded_at__isnull=True).exclude(expires_at=None)
    earliest = current.order_by("expires_at").values_list("expires_at", flat=True).first()
    if earliest is not None:
        return timezone.make_aware(datetime.combine(earliest, time.min))
    if record.domain == Domain.GOOD_CONDUCT:
        months = int(config.get("verification.good_conduct_recheck_months", 12) or 12)
        return timezone.now() + timedelta(days=30 * months)
    return None


class SystemActor:
    """Actor for the automated expiry sweep — audited as SYSTEM, no user."""

    is_authenticated = False
    is_admin = False
    user = None
    audit_role = "SYSTEM"


@transaction.atomic
def expire_due(*, now: Any | None = None) -> int:
    """Materialise EXPIRED decisions for records whose ``expires_at`` has passed.

    Not required for read correctness (``effective_state`` already folds expiry
    in) — this keeps the append-only history complete and emits the events a
    later notification phase will consume.
    """
    cutoff = now or timezone.now()
    stale = VerificationRecord.objects.select_for_update().filter(
        state=State.VERIFIED, expires_at__isnull=False, expires_at__lte=cutoff
    )
    count = 0
    for record in stale:
        _record_decision(
            actor=SystemActor(),
            record=record,
            action=Action.EXPIRE,
            new_state=State.EXPIRED,
            reason="expiry date passed",
        )
        count += 1
    return count


# ─── Derived read helpers (facts only — no trust / eligibility) ──────
def eligibility(subject: Any) -> dict[str, str]:
    _stype, kw = _subject_kwargs(subject)
    records = VerificationRecord.objects.filter(**kw)
    return {r.domain: r.effective_state() for r in records}


def subject_meets(subject: Any, domains: list[str]) -> bool:
    states = eligibility(subject)
    return all(states.get(d) == State.VERIFIED for d in domains)


def requirements_status(subject: Any) -> list[dict[str, Any]]:
    from fikisha.verification.requirements import required_domains_for_subject

    required = set(required_domains_for_subject(subject))
    states = eligibility(subject)
    rows = [
        {"domain": d, "mandatory": True, "state": states.get(d, State.NOT_SUBMITTED)}
        for d in sorted(required)
    ]
    for d, s in states.items():
        if d not in required:
            rows.append({"domain": d, "mandatory": False, "state": s})
    return rows


@transaction.atomic
def invalidate_association(*, actor: Any, vehicle: Vehicle, reason: str) -> None:
    """Reset a vehicle's ASSOCIATION verification (control changed)."""
    record = (
        VerificationRecord.objects.select_for_update()
        .filter(subject_vehicle=vehicle, domain=Domain.ASSOCIATION)
        .first()
    )
    if record is None or record.state == State.NOT_SUBMITTED:
        return
    _record_decision(
        actor=actor,
        record=record,
        action=Action.REJECT,
        new_state=State.NOT_SUBMITTED,
        reason=reason,
    )
