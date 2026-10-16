"""High-value approval — the pre-assignment gate for HIGH / VERY_HIGH jobs
(trust-architecture.md §1, D-TRU-5, plan §7 / §9.5).

An Operations Officer may decide a HIGH job; only a Platform Admin may decide a
VERY_HIGH job (and the ``HighValueApproved`` guard independently re-checks that
a VERY_HIGH approval was made by a Platform Admin). The decision is
append-only and immutable (``high_value_approval`` is ``U(job_id)``). A
**rejection** can be reversed by a Platform Admin with a reason (founder
decision 2026-10-14): an append-only ``high_value_reversal`` row, after which
the job counts as approved by a Platform Admin. Readers use
:func:`effective_decision`.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from fikisha.audit import services as audit
from fikisha.common.exceptions import DomainError
from fikisha.jobs.constants import HIGH_VALUE_BANDS, HighValueDecision, ValueBand
from fikisha.jobs.errors import (
    HighValueAlreadyDecided,
    NotAHighValueJob,
    NotAuthorisedToAssign,
)
from fikisha.jobs.models import HighValueApproval, HighValueReversal
from fikisha.jobs.selectors import get_job
from fikisha.outbox.services import emit


def _roles(actor: Any) -> set[str]:
    return {str(r) for r in (getattr(actor, "roles", None) or [])}


def _is_platform_admin(actor: Any) -> bool:
    return (
        "PLATFORM_ADMIN" in _roles(actor)
        or str(getattr(actor, "audit_role", "")) == "PLATFORM_ADMIN"
    )


def _is_ops_officer(actor: Any) -> bool:
    return (
        "OPERATIONS_OFFICER" in _roles(actor)
        or str(getattr(actor, "audit_role", "")) == "OPERATIONS_OFFICER"
        or bool(getattr(actor, "is_admin", False))
    )


@transaction.atomic
def decide_high_value(
    *, actor: Any, job_id: Any, decision: str, rationale: str = ""
) -> dict[str, Any]:
    job = get_job(job_id)
    if job.value_band not in HIGH_VALUE_BANDS:
        raise NotAHighValueJob()
    if decision not in HighValueDecision.values:
        raise NotAHighValueJob(f"{decision!r} is not a valid high-value decision.")

    is_platform_admin = _is_platform_admin(actor)
    if job.value_band == ValueBand.VERY_HIGH:
        if not is_platform_admin:
            raise NotAuthorisedToAssign("Only a Platform Admin may decide a very-high-value job.")
    elif not (is_platform_admin or _is_ops_officer(actor)):
        raise NotAuthorisedToAssign(
            "Only an Operations Officer or Platform Admin may decide a high-value job."
        )

    user = getattr(actor, "user", actor)
    try:
        approval = HighValueApproval.objects.create(
            job=job,
            decided_by_admin=user,
            decided_by_is_platform_admin=is_platform_admin,
            decision=decision,
            rationale=rationale.strip(),
        )
    except IntegrityError as exc:  # U(job_id) — one decision per job
        raise HighValueAlreadyDecided() from exc

    audit.record(
        actor=actor,
        action="job.highvalue.decided",
        entity_type="high_value_approval",
        entity_id=approval.id,
        after={
            "job_id": str(job.id),
            "value_band": job.value_band,
            "decision": decision,
            "decided_by_is_platform_admin": is_platform_admin,
        },
    )
    emit(
        event_type="HighValueDecision",
        aggregate_type="job",
        aggregate_id=str(job.id),
        payload={
            "job_id": str(job.id),
            "value_band": job.value_band,
            "decision": decision,
            "decided_by_is_platform_admin": is_platform_admin,
        },
    )
    return {
        "job_id": str(job.id),
        "value_band": job.value_band,
        "decision": decision,
        "decided_by_is_platform_admin": is_platform_admin,
    }


# ─── effective decision and reversal (founder decision 2026-10-14) ────────
REASON_MIN_LENGTH = 10


class NotReversible(DomainError):
    default_code = "high_value_not_reversible"
    default_detail = "Only a rejected high-value decision can be reversed."


def effective_decision(job: Any) -> tuple[str | None, bool]:
    """``(decision, by_platform_admin)`` for a job: ``(None, False)`` when
    nothing is decided yet; a reversed rejection reads as APPROVED by a
    Platform Admin."""
    approval = HighValueApproval.objects.filter(job=job).select_related("reversal").first()
    if approval is None:
        return None, False
    if getattr(approval, "reversal", None) is not None:
        return HighValueDecision.APPROVED, True
    return approval.decision, approval.decided_by_is_platform_admin


@transaction.atomic
def reverse_rejection(*, actor: Any, job_id: Any, reason: str) -> dict[str, Any]:
    """A Platform Admin reverses a rejection. Needs a reason (step-up is
    checked at the API view, like the decision itself)."""
    if not _is_platform_admin(actor):
        raise NotAuthorisedToAssign("Only a Platform Admin may reverse a high-value rejection.")
    reason = (reason or "").strip()
    if len(reason) < REASON_MIN_LENGTH:
        raise NotReversible(f"Give a reason of at least {REASON_MIN_LENGTH} characters.")
    job = get_job(job_id)
    approval = HighValueApproval.objects.select_for_update().filter(job=job).first()
    if approval is None or approval.decision != HighValueDecision.REJECTED:
        raise NotReversible()
    if HighValueReversal.objects.filter(approval=approval).exists():
        raise HighValueAlreadyDecided("This rejection was already reversed.")
    user = getattr(actor, "user", actor)
    reversal = HighValueReversal.objects.create(approval=approval, reversed_by=user, reason=reason)
    audit.record(
        actor=actor,
        action="job.highvalue.rejection_reversed",
        entity_type="high_value_approval",
        entity_id=approval.id,
        before={"decision": HighValueDecision.REJECTED},
        after={
            "effective_decision": HighValueDecision.APPROVED,
            "reason": reason,
            "reversal_id": str(reversal.id),
        },
    )
    emit(
        event_type="HighValueDecision",
        aggregate_type="job",
        aggregate_id=str(job.id),
        payload={
            "job_id": str(job.id),
            "value_band": job.value_band,
            "decision": HighValueDecision.APPROVED,
            "decided_by_is_platform_admin": True,
            "reversal": True,
        },
    )
    return {"job_id": str(job.id), "decision": HighValueDecision.APPROVED, "reversed": True}
