"""High-value approval — the pre-assignment gate for HIGH / VERY_HIGH jobs
(trust-architecture.md §1, D-TRU-5, plan §7 / §9.5).

An Operations Officer may decide a HIGH job; only a Platform Admin may decide a
VERY_HIGH job (and the ``HighValueApproved`` guard independently re-checks that
a VERY_HIGH approval was made by a Platform Admin). The decision is
append-only and immutable (``high_value_approval`` is ``U(job_id)``); a
correction would be an admin adjustment, out of scope here.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from fikisha.audit import services as audit
from fikisha.jobs.constants import HIGH_VALUE_BANDS, HighValueDecision, ValueBand
from fikisha.jobs.errors import (
    HighValueAlreadyDecided,
    NotAHighValueJob,
    NotAuthorisedToAssign,
)
from fikisha.jobs.models import HighValueApproval
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
