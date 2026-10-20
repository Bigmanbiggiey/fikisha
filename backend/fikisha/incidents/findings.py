"""Fikisha's findings on incidents and unfounded-report records
(trust-and-disputes plan A2, A3).

A finding says who, if anyone, Fikisha found at fault. It is separate from
closing an incident (``services.close_incident``) and never changes a job's
status, a tier or a standing by itself. The parties a finding may name are
built here from the job — the business, the assigned driver (the operator
on a solo job), the group — never taken from the client. Naming the group
never names the driver, nor the reverse.

Wording on screens: "Fikisha's finding on this job", never a legal
liability determination (dispute-and-liability §1, §7).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from fikisha.audit import services as audit
from fikisha.identity.authz.step_up import require_step_up
from fikisha.incidents import authz as incidents_authz
from fikisha.incidents.constants import (
    FINDING_REASON_MIN_LENGTH,
    FindingOutcome,
    FindingPartyKind,
    IncidentStatus,
)
from fikisha.incidents.errors import (
    FindingReasonRequired,
    IncidentNotFound,
    InvalidFinding,
    NotAuthorisedForBindingResolution,
    NotAuthorisedForIncidentReview,
    UnfoundedNotAllowed,
)
from fikisha.incidents.models import (
    Incident,
    IncidentFinding,
    IncidentFindingParty,
    UnfoundedReport,
)
from fikisha.outbox.services import emit


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def candidates(incident: Incident) -> dict[str, str]:
    """``{kind: subject_id}`` an AT_FAULT finding on this incident may name."""
    job = incident.job
    out = {FindingPartyKind.BUSINESS.value: str(job.business_id)}
    assignment = getattr(job, "assignment", None)
    if assignment is not None:
        out[FindingPartyKind.DRIVER.value] = str(assignment.assigned_driver_profile_id)
        if assignment.group_id is not None:
            out[FindingPartyKind.GROUP.value] = str(assignment.group_id)
    return out


def current_finding(incident_id: Any) -> IncidentFinding | None:
    """The finding nothing supersedes, or ``None``."""
    return (
        IncidentFinding.objects.filter(incident_id=incident_id, superseded_by__isnull=True)
        .prefetch_related("parties")
        .first()
    )


def finding_view(finding: IncidentFinding, *, staff: bool) -> dict[str, Any]:
    """Parties see the outcome and who was named; staff also the reason and
    who decided."""
    view: dict[str, Any] = {
        "id": str(finding.id),
        "outcome": finding.outcome,
        "parties": sorted(p.kind for p in finding.parties.all()),
        "created_at": finding.created_at.isoformat(),
    }
    if staff:
        view["reason"] = finding.reason
        view["decided_by_is_platform_admin"] = finding.decided_by_is_platform_admin
        view["supersedes_id"] = str(finding.supersedes_id) if finding.supersedes_id else None
    return view


def history(incident_id: Any) -> list[IncidentFinding]:
    return list(
        IncidentFinding.objects.filter(incident_id=incident_id)
        .prefetch_related("parties")
        .order_by("created_at")
    )


@transaction.atomic
def record_finding(
    *, actor: Any, incident_id: Any, outcome: str, parties: list[str], reason: str
) -> IncidentFinding:
    """Record Fikisha's finding, superseding the current one if any. Staff
    with ``incident.intake``; above the Standard band an AT_FAULT finding
    needs a Platform Admin. An AT_FAULT finding names at least one party of
    this job; the others name none."""
    if not incidents_authz.actor_has_permission(actor, "incident.intake"):
        raise NotAuthorisedForIncidentReview()
    if outcome not in FindingOutcome.values:
        raise InvalidFinding(f"{outcome!r} is not a recognised finding.")
    reason = (reason or "").strip()
    if len(reason) < FINDING_REASON_MIN_LENGTH:
        raise FindingReasonRequired()
    try:
        incident = Incident.objects.select_for_update().select_related("job").get(id=incident_id)
    except Incident.DoesNotExist as exc:
        raise IncidentNotFound() from exc

    named = sorted(set(parties or []))
    allowed = candidates(incident)
    if outcome == FindingOutcome.AT_FAULT:
        if not named or any(kind not in allowed for kind in named):
            raise InvalidFinding()
        band = getattr(incident.job, "value_band", "") or "STANDARD"
        if band != "STANDARD" and not incidents_authz.is_platform_admin(actor):
            raise NotAuthorisedForBindingResolution(
                "A fault finding above the Standard band requires a Platform Administrator."
            )
    elif named:
        raise InvalidFinding("Only an at-fault finding names parties.")

    previous = current_finding(incident.id)
    finding = IncidentFinding.objects.create(
        incident=incident,
        outcome=outcome,
        reason=reason,
        decided_by=_actor_user(actor),
        decided_by_is_platform_admin=incidents_authz.is_platform_admin(actor),
        supersedes=previous,
    )
    for kind in named:
        IncidentFindingParty.objects.create(finding=finding, kind=kind, subject_id=allowed[kind])

    audit.record(
        actor=actor,
        action="incident.finding.superseded" if previous else "incident.finding.recorded",
        entity_type="incident",
        entity_id=incident.id,
        before={"finding_id": str(previous.id), "outcome": previous.outcome} if previous else None,
        after={"finding_id": str(finding.id), "outcome": outcome, "parties": named},
    )
    emit(
        event_type="IncidentFindingRecorded",
        aggregate_type="incident",
        aggregate_id=str(incident.id),
        payload={
            "job_id": str(incident.job_id),
            "incident_id": str(incident.id),
            "finding_id": str(finding.id),
            "outcome": outcome,
            "parties": named,
            "supersedes_id": str(previous.id) if previous else None,
        },
    )
    return finding


@transaction.atomic
def record_unfounded(*, actor: Any, incident_id: Any, reason: str) -> UnfoundedReport:
    """A Platform Admin records that a report was unfounded (UF-1): only on
    a closed incident whose current finding is NO_FAULT. Recorded against
    the reporter; no automatic effect."""
    if not incidents_authz.is_platform_admin(actor):
        raise NotAuthorisedForIncidentReview(
            "Only a Platform Administrator may mark a report unfounded."
        )
    require_step_up(actor)
    reason = (reason or "").strip()
    if len(reason) < FINDING_REASON_MIN_LENGTH:
        raise FindingReasonRequired()
    try:
        incident = Incident.objects.select_for_update().get(id=incident_id)
    except Incident.DoesNotExist as exc:
        raise IncidentNotFound() from exc
    finding = current_finding(incident.id)
    if (
        incident.status != IncidentStatus.RESOLVED
        or finding is None
        or finding.outcome != FindingOutcome.NO_FAULT
        or UnfoundedReport.objects.filter(incident=incident).exists()
    ):
        raise UnfoundedNotAllowed()
    record = UnfoundedReport.objects.create(
        incident=incident,
        finding=finding,
        reporter_party=incident.reporter_party,
        reporter_user=incident.reported_by_user,
        reporter_link_id=incident.reported_by_link_id,
        reason=reason,
        decided_by=_actor_user(actor),
    )
    audit.record(
        actor=actor,
        action="incident.report_unfounded",
        entity_type="incident",
        entity_id=incident.id,
        after={"finding_id": str(finding.id), "reporter_party": incident.reporter_party},
    )
    emit(
        event_type="IncidentReportUnfounded",
        aggregate_type="incident",
        aggregate_id=str(incident.id),
        payload={"job_id": str(incident.job_id), "incident_id": str(incident.id)},
    )
    return record
