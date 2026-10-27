"""Resuming a disputed job (trust-and-disputes plan Part B, ADR-2D-54; lifts
founder decision 10 and supersedes ADR-2D-07).

A Platform Admin, with a fresh step-up, returns a disputed job to the state
it was in before the dispute, when:

- the dispute is unresolved and the job was disputed from ASSIGNED ...
  DELIVERED (a job disputed after COMPLETED is routed, never resumed);
- every serious-type incident in the dispute (loss, damage, missing goods,
  misconduct) has a current finding — "couldn't be determined" counts
  (FN-1); every linked incident is then closed by the resume itself;
- it is within ``disputes.resume_window_days`` of the dispute opening (DR-4;
  afterwards the job stays DISPUTED until routed — no timer changes it);
- the existing assignment would pass today's assignment checks (DR-2). No
  replacement driver or vehicle (DR-3); a high-value approval must still be
  effective, never re-approved (DR-5);
- the admin records that both parties agreed to carry on, and how (DR-1).

One transaction: closures, a *resume* ``Resolution``, the attestation, the
status change through ``JobLifecycleService.transition()`` (which issues
fresh codes for a pending pickup or delivery and makes earlier confirmations
stop counting), audit and outbox. Locks the dispute, then the job, like
``resolve_dispute``. A resumed job may be disputed again (DR-6).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.exceptions import ConflictError, DomainError
from fikisha.identity.authz.step_up import require_step_up
from fikisha.incidents import authz as incidents_authz
from fikisha.incidents import findings
from fikisha.incidents.constants import (
    RESUMABLE_STATUSES,
    AgreementMethod,
    ClosureReason,
    CommissionTreatment,
    DisputeStatus,
    IncidentStatus,
    ResolutionOutcome,
)
from fikisha.incidents.errors import (
    DisputeAlreadyResolved,
    DisputeNotFound,
    NotAuthorisedForBindingResolution,
    RationaleRequired,
)
from fikisha.incidents.models import Dispute, Incident, Resolution, ResumeAttestation
from fikisha.incidents.trust_facts import SERIOUS_TYPES
from fikisha.jobs.selectors import get_job, job_for_update
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config

REASON_MIN_LENGTH = 10


class ResumeNotAllowed(ConflictError):
    default_code = "resume_not_allowed"
    default_detail = "This job can't be resumed."


class InvalidAgreementMethod(DomainError):
    default_code = "invalid_agreement_method"
    default_detail = "Record how each party agreed: by phone, in person or by message in the app."


def _window_days() -> int:
    return int((config.get("disputes", default=None) or {}).get("resume_window_days", 7))


def checks(dispute: Dispute, job: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """The resume checklist for the dispute screen and the service:
    ``{target_status, window_ends_at, checks: [{key, ok, detail}], ok}``."""
    from fikisha.jobs.guards import resume_assignment_reasons

    now = now or timezone.now()
    window_ends = dispute.created_at + timedelta(days=_window_days())
    incidents = list(Incident.objects.filter(id__in=dispute.incident_ids))
    unfound = [
        str(i.id)
        for i in incidents
        if i.type in SERIOUS_TYPES and findings.current_finding(i.id) is None
    ]
    reasons = resume_assignment_reasons(job)
    rows = [
        {"key": "dispute_open", "ok": dispute.status != DisputeStatus.RESOLVED, "detail": ""},
        {
            "key": "resumable_state",
            "ok": dispute.pre_dispute_status in RESUMABLE_STATUSES,
            "detail": dispute.pre_dispute_status,
        },
        {"key": "within_window", "ok": now < window_ends, "detail": window_ends.isoformat()},
        {"key": "serious_findings", "ok": not unfound, "detail": ",".join(unfound)},
        {"key": "assignment_eligible", "ok": not reasons, "detail": " ".join(reasons)},
    ]
    return {
        "target_status": dispute.pre_dispute_status,
        "window_ends_at": window_ends.isoformat(),
        "checks": rows,
        "ok": all(r["ok"] for r in rows),
    }


def resume_view(*, dispute_id: Any) -> dict[str, Any]:
    dispute = Dispute.objects.filter(id=dispute_id).first()
    if dispute is None:
        raise DisputeNotFound()
    return checks(dispute, get_job(dispute.job_id))


def _parse_when(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(str(value))
    if parsed is None:
        raise InvalidAgreementMethod("Give the time as an ISO date and time.")
    return parsed


@transaction.atomic
def resume_dispute(
    *,
    actor: Any,
    dispute_id: Any,
    sender_method: str,
    operator_method: str,
    reason: str,
    sender_confirmed_at: Any = None,
    operator_confirmed_at: Any = None,
    idempotency_key: str = "",
) -> tuple[Resolution, dict[str, Any]]:
    if not incidents_authz.is_platform_admin(actor):
        raise NotAuthorisedForBindingResolution(
            "Only a Platform Administrator can resume a disputed job."
        )
    require_step_up(actor)
    reason = (reason or "").strip()
    if len(reason) < REASON_MIN_LENGTH:
        raise RationaleRequired("Give a reason of at least 10 characters.")
    if sender_method not in AgreementMethod.values or operator_method not in AgreementMethod.values:
        raise InvalidAgreementMethod()
    sender_at = _parse_when(sender_confirmed_at)
    operator_at = _parse_when(operator_confirmed_at)

    try:
        dispute = Dispute.objects.select_for_update().get(id=dispute_id)
    except Dispute.DoesNotExist as exc:
        raise DisputeNotFound() from exc
    if dispute.status == DisputeStatus.RESOLVED:
        existing = getattr(dispute, "resolution", None)
        if existing is not None and existing.resumed and idempotency_key:
            # a replay of the same request: the transition returns its result
            view = job_transition(
                job_id=dispute.job_id,
                to=existing.routed_job_status,
                actor=actor,
                context=TransitionContext(data={}),
                idempotency_key=idempotency_key,
            )
            return existing, view
        raise DisputeAlreadyResolved()

    job = job_for_update(dispute.job_id)
    result = checks(dispute, job)
    failed = [c for c in result["checks"] if not c["ok"]]
    if failed:
        first = failed[0]
        raise ResumeNotAllowed(
            f"Can't resume yet: {first['key']}"
            + (f" ({first['detail']})" if first["detail"] else ""),
        )
    target = dispute.pre_dispute_status

    from fikisha.incidents.services import _close

    for incident in (
        Incident.objects.select_for_update()
        .filter(id__in=dispute.incident_ids)
        .exclude(status=IncidentStatus.RESOLVED)
    ):
        _close(
            actor=actor,
            incident=incident,
            reason_code=ClosureReason.DISPUTE_RESOLVED,
            note=reason,
            dispute=dispute,
        )

    user: Any = getattr(actor, "user", None)
    resolution = Resolution.objects.create(
        dispute=dispute,
        outcome_code=ResolutionOutcome.AMICABLE_AGREEMENT,
        rationale=reason,
        commission_treatment=CommissionTreatment.APPLY,
        business_commission_treatment=CommissionTreatment.APPLY,
        actions=[],
        routed_job_status=target,
        resolved_by_admin=user,
        resolved_by_is_platform_admin=True,
        resumed=True,
    )
    ResumeAttestation.objects.create(
        dispute=dispute,
        resolution=resolution,
        sender_method=sender_method,
        sender_confirmed_at=sender_at,
        operator_method=operator_method,
        operator_confirmed_at=operator_at,
        recorded_by=user,
    )
    view = job_transition(
        job_id=job.id,
        to=target,
        actor=actor,
        context=TransitionContext(
            data={
                "initiator_tokens": [],
                "resolution_id": str(resolution.id),
                "routed_job_status": target,
            }
        ),
        idempotency_key=idempotency_key,
    )
    dispute.status = DisputeStatus.RESOLVED
    dispute.officer_admin = user
    dispute.save(update_fields=["status", "officer_admin", "updated_at"])
    audit.record(
        actor=actor,
        action="dispute.resumed",
        entity_type="resolution",
        entity_id=resolution.id,
        after={
            "dispute_id": str(dispute.id),
            "resumed_to": target,
            "sender_method": sender_method,
            "operator_method": operator_method,
        },
    )
    emit(
        event_type="DisputeResolved",
        aggregate_type="dispute",
        aggregate_id=str(dispute.id),
        payload={
            "job_id": str(job.id),
            "dispute_id": str(dispute.id),
            "resolution_id": str(resolution.id),
            "routed_job_status": target,
            "resumed": True,
        },
    )
    return resolution, view
