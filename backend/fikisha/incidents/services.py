"""Incidents & Disputes domain services (plan §19 Step 8,
``docs/phase-0/dispute-and-liability.md``, FR-D-1..D-10).

**Never writes ``job.status`` directly.** Every path that must move a Job into
or out of ``DISPUTED`` calls ``JobLifecycleService.transition()`` — the sole
writer — exactly as the negotiation / assignment / custody / recipient services
already do. ``Dispute`` / ``Resolution`` rows are created **by this module**
(never by ``jobs.apply_fns`` — see that module's docstring for why), inside the
*same* outer ``transaction.atomic()`` that also locks the Job row and calls the
transition, so the row lock makes both reads/writes mutually consistent
(ADR-2D-20 / ADR-2D-07).

No HTTP routes here (plan §19 Step 10 owns the API boundary).

Every public function that writes a domain row and calls ``audit.record()``
is ``@transaction.atomic`` (Phase 2D final-verification BLOCKER-1 fix):
``audit.record()`` itself asserts it is running inside an open transaction
and raises loudly if not — a correct, fail-loud check, but ``open_dispute``/
``resolve_dispute`` were the only two functions here that actually supplied
one. Outside a caller's own already-atomic context (in production, with no
``ATOMIC_REQUESTS`` configured, that means *every* real HTTP call), the other
seven functions raised ``RuntimeError`` immediately after already committing
their domain row — a real write with no audit trail. Fixed by decorating
each one, the same one-line pattern already used by
``jobs.creation.submit_job``/``cancel_job`` for the identical defect class.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from fikisha.audit import services as audit
from fikisha.evidence import services as evidence_services
from fikisha.evidence.models import EvidencePurpose, PiiClass, UploaderKind
from fikisha.incidents import authz as incidents_authz
from fikisha.incidents.constants import (
    DEFAULT_SEVERITY,
    ROUTABLE_JOB_STATUSES,
    CommissionTreatment,
    DisputeStatus,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    PartyKind,
    ReportedByKind,
    ResolutionOutcome,
)
from fikisha.incidents.errors import (
    DisputeAlreadyOpen,
    DisputeAlreadyResolved,
    DisputeNotFound,
    IncidentAlreadyResolved,
    IncidentNotFound,
    InvalidIncidentSeverity,
    InvalidIncidentType,
    InvalidResolutionOutcome,
    InvalidResolutionRouting,
    NotAuthorisedForBindingResolution,
    NotAuthorisedForIncidentReview,
    NotIncidentParty,
    RationaleRequired,
    StatementTextRequired,
)
from fikisha.incidents.models import (
    Dispute,
    Escalation,
    Incident,
    IncidentEvidence,
    IncidentStatement,
    Resolution,
)
from fikisha.jobs import commission as commission_service
from fikisha.jobs.constants import CommissionAdjustmentKind, JobStatus, RecipientIssueCategory
from fikisha.jobs.errors import (
    InvalidCommissionAdjustmentAmount,
    NotAuthorisedForCommissionAdjustment,
)
from fikisha.jobs.selectors import get_job, get_recipient_reported_issue, job_for_update
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config

#: incidents.constants.CommissionTreatment values that require an actual
#: CommissionAdjustment (APPLY never does — Step 9 brief §11: not every
#: dispute reduces commission, only an explicit authorized resolution).
_COMMISSION_TREATMENTS_REQUIRING_ADJUSTMENT = frozenset({"REDUCE", "WAIVE"})

# RecipientReportedIssue.category -> IncidentType (Founder-confirmed mapping;
# WRONG_GOODS has no dedicated incident type — recorded as OTHER + a label).
_RECIPIENT_CATEGORY_TO_INCIDENT_TYPE: dict[str, tuple[str, str]] = {
    RecipientIssueCategory.WRONG_RECIPIENT: (IncidentType.WRONG_RECIPIENT, ""),
    RecipientIssueCategory.DAMAGE: (IncidentType.DAMAGE, ""),
    RecipientIssueCategory.MISSING_GOODS: (IncidentType.MISSING_GOODS, ""),
    RecipientIssueCategory.WRONG_GOODS: (IncidentType.OTHER, "Wrong goods"),
    RecipientIssueCategory.OTHER: (IncidentType.OTHER, ""),
}


# ─── helpers ───────────────────────────────────────────────────────────
def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def _is_recipient_principal(actor: Any) -> bool:
    return str(getattr(actor, "audit_role", "") or "") == "RECIPIENT"


def _party_kind_for_actor(actor: Any, job: Any) -> str | None:
    """Like :func:`incidents.authz.party_kind_for_job`, plus the job-scoped
    ``RecipientPrincipal`` case (Increment 5) — a recipient may only act on
    *its own* job, never another."""
    if _is_recipient_principal(actor):
        return PartyKind.RECIPIENT if str(getattr(actor, "job_id", "")) == str(job.id) else None
    return incidents_authz.party_kind_for_job(actor, job)


def _sla_due_at(severity: str) -> dict[str, Any]:
    from datetime import timedelta

    from django.utils import timezone

    targets = config.get(f"sla_targets.{severity}", {}) or {}
    now = timezone.now()
    out: dict[str, Any] = {}
    if targets.get("ack_hours") is not None:
        out["sla_ack_due_at"] = now + timedelta(hours=float(targets["ack_hours"]))
    if targets.get("action_hours") is not None:
        out["sla_action_due_at"] = now + timedelta(hours=float(targets["action_hours"]))
    if targets.get("resolution_days") is not None:
        out["sla_resolution_due_at"] = now + timedelta(days=float(targets["resolution_days"]))
    return out


# evidence.EvidencePurpose's UploaderKind has no "GROUP" member (that module
# predates Incidents and knows nothing about operator groups) — a GROUP-party
# actor is still "the operator side" for evidence-storage purposes. Passing
# PartyKind.GROUP straight through would silently write an UploaderKind value
# outside its own choices (no DB CHECK constraint catches this — Django
# `choices=` isn't enforced by `.create()`).
_EVIDENCE_UPLOADER_KIND: dict[str, str] = {
    PartyKind.BUSINESS: UploaderKind.BUSINESS,
    PartyKind.OPERATOR: UploaderKind.OPERATOR,
    PartyKind.GROUP: UploaderKind.OPERATOR,
    PartyKind.RECIPIENT: UploaderKind.RECIPIENT,
    PartyKind.ADMIN: UploaderKind.ADMIN,
}


def _load_incident(incident_id: Any) -> Incident:
    try:
        return Incident.objects.select_related("job").get(id=incident_id)
    except Incident.DoesNotExist as exc:
        raise IncidentNotFound() from exc


# ─── incident creation ─────────────────────────────────────────────────
@transaction.atomic
def report_incident(
    *,
    actor: Any,
    job_id: Any,
    type: str,
    severity: str = "",
    description: str = "",
    other_label: str = "",
) -> Incident:
    """A platform user (business / operator / admin) reports an incident on a
    job they are a party to. A recipient's report flows through
    :func:`intake_recipient_report` instead — see ``jobs.recipient.report_issue``
    (ADR-2D-17), which this function never calls directly."""
    if type not in IncidentType.values:
        raise InvalidIncidentType(f"{type!r} is not a recognised incident type.")
    if severity and severity not in IncidentSeverity.values:
        raise InvalidIncidentSeverity(f"{severity!r} is not a recognised incident severity.")
    job = get_job(job_id)
    party_kind = _party_kind_for_actor(actor, job)
    if party_kind is None:
        raise NotIncidentParty()

    incident = Incident.objects.create(
        job=job,
        type=type,
        other_label=(other_label or "").strip()[:120] if type == IncidentType.OTHER else "",
        severity=severity or DEFAULT_SEVERITY,
        reported_by_kind=ReportedByKind.ADMIN
        if party_kind == PartyKind.ADMIN
        else ReportedByKind.USER,
        reported_by_user=_actor_user(actor),
        description=(description or "").strip(),
        status=IncidentStatus.OPEN,
        **_sla_due_at(severity or DEFAULT_SEVERITY),
    )
    audit.record(
        actor=actor,
        action="incident.reported",
        entity_type="incident",
        entity_id=incident.id,
        after={"job_id": str(job.id), "type": incident.type, "severity": incident.severity},
    )
    emit(
        event_type="IncidentReported",
        aggregate_type="incident",
        aggregate_id=str(incident.id),
        payload={"job_id": str(job.id), "incident_id": str(incident.id), "type": incident.type},
    )
    return incident


@transaction.atomic
def intake_recipient_report(*, report_id: Any, actor: Any = None) -> Incident:
    """Promote an already-captured, append-only ``RecipientReportedIssue``
    (ADR-2D-17) into a full triage-able ``Incident`` — a **plain callable**
    (Founder-confirmed: not auto-wired to an outbox consumer in Step 8). Never
    mutates the original report. Idempotent: replaying the same ``report_id``
    returns the existing Incident rather than creating a duplicate."""
    report = get_recipient_reported_issue(report_id)
    existing = Incident.objects.filter(source_report_id=report.id).first()
    if existing is not None:
        return existing

    incident_type, other_label = _RECIPIENT_CATEGORY_TO_INCIDENT_TYPE.get(
        report.category, (IncidentType.OTHER, "")
    )
    incident = Incident.objects.create(
        job=report.job,
        type=incident_type,
        other_label=other_label or (report.other_label or "")[:120],
        severity=DEFAULT_SEVERITY,
        reported_by_kind=ReportedByKind.RECIPIENT_LINK,
        reported_by_link_id=report.reported_via_link_id,
        source_report_id=report.id,
        description=(report.description or "").strip(),
        status=IncidentStatus.OPEN,
        **_sla_due_at(DEFAULT_SEVERITY),
    )
    from fikisha.evidence.models import EvidenceObject

    for evidence_id in report.photo_evidence_ids or []:
        obj = EvidenceObject.objects.filter(id=evidence_id).first()
        if obj is None:
            continue
        IncidentEvidence.objects.create(
            incident=incident,
            evidence_object=obj,
            uploaded_by_kind=PartyKind.RECIPIENT,
            caption="Attached with the original recipient report.",
        )
    audit.record(
        actor=actor,
        action="incident.intake_from_recipient_report",
        entity_type="incident",
        entity_id=incident.id,
        after={
            "job_id": str(report.job_id),
            "report_id": str(report.id),
            "type": incident.type,
        },
    )
    emit(
        event_type="IncidentReported",
        aggregate_type="incident",
        aggregate_id=str(incident.id),
        payload={
            "job_id": str(report.job_id),
            "incident_id": str(incident.id),
            "type": incident.type,
            "source": "recipient_report",
        },
    )
    return incident


# ─── evidence + statements ──────────────────────────────────────────────
@transaction.atomic
def attach_evidence(
    *,
    actor: Any,
    incident_id: Any,
    data: bytes,
    content_type: str,
    caption: str = "",
) -> IncidentEvidence:
    incident = _load_incident(incident_id)
    party_kind = _party_kind_for_actor(actor, incident.job)
    if party_kind is None:
        raise NotIncidentParty()
    if incident.status == IncidentStatus.RESOLVED:
        raise IncidentAlreadyResolved()

    obj = evidence_services.store(
        data=data,
        content_type=content_type,
        purpose=EvidencePurpose.INCIDENT_EVIDENCE,
        pii_class=PiiClass.MEDIUM,
        linked_entity_type="incident",
        linked_entity_id=incident.id,
        uploaded_by=_actor_user(actor),
        uploaded_by_kind=_EVIDENCE_UPLOADER_KIND[party_kind],
    )
    row = IncidentEvidence.objects.create(
        incident=incident,
        evidence_object=obj,
        uploaded_by_kind=party_kind,
        uploaded_by_user=_actor_user(actor),
        caption=(caption or "").strip()[:200],
    )
    audit.record(
        actor=actor,
        action="incident.evidence.attached",
        entity_type="incident_evidence",
        entity_id=row.id,
        after={"incident_id": str(incident.id), "evidence_object_id": str(obj.id)},
    )
    return row


@transaction.atomic
def add_statement(*, actor: Any, incident_id: Any, text: str) -> IncidentStatement:
    incident = _load_incident(incident_id)
    party_kind = _party_kind_for_actor(actor, incident.job)
    if party_kind is None:
        raise NotIncidentParty()
    if incident.status == IncidentStatus.RESOLVED:
        raise IncidentAlreadyResolved()
    text = (text or "").strip()
    if not text:
        raise StatementTextRequired()

    statement = IncidentStatement.objects.create(
        incident=incident,
        party_kind=party_kind,
        party_user=_actor_user(actor),
        text=text,
    )
    audit.record(
        actor=actor,
        action="incident.statement.added",
        entity_type="incident_statement",
        entity_id=statement.id,
        after={"incident_id": str(incident.id), "party_kind": party_kind},
    )
    return statement


# ─── incident review workflow (Ops-Officer / Admin) ─────────────────────
def _require_review_permission(actor: Any, *, permission: str) -> None:
    """Config-driven only — deliberately **not** ``if incidents_authz.is_admin
    (actor): return`` first, which would let any actor with a bare
    ``AdminProfile`` through regardless of role (STRIDE: elevation of
    privilege). A Platform Admin already passes via ``role_permissions``'
    ``"*"`` wildcard entry; an Operations Officer passes only for the specific
    actions ``role_permissions.OPERATIONS_OFFICER`` actually lists — "Ops
    Officer remains operational/read-oriented unless explicitly granted a
    specific action" (plan §19 Step 8 brief)."""
    if not incidents_authz.actor_has_permission(actor, permission):
        raise NotAuthorisedForIncidentReview()


@transaction.atomic
def start_review(*, actor: Any, incident_id: Any) -> Incident:
    _require_review_permission(actor, permission="incident.intake")
    incident = _load_incident(incident_id)
    if incident.status == IncidentStatus.RESOLVED:
        raise IncidentAlreadyResolved()
    incident.status = IncidentStatus.UNDER_REVIEW
    if incident.owner_admin_id is None:
        incident.owner_admin = _actor_user(actor)
    incident.save(update_fields=["status", "owner_admin", "updated_at"])
    audit.record(
        actor=actor,
        action="incident.review.started",
        entity_type="incident",
        entity_id=incident.id,
        after={"status": incident.status},
    )
    return incident


@transaction.atomic
def start_amicable_window(*, actor: Any, incident_id: Any) -> Incident:
    """Amicable-first resolution attempt (dispute-and-liability.md §4). An
    Operations Officer may facilitate this (``incident.amicable.facilitate``,
    already-approved ``role_permissions`` config) without full admin review
    being mandatory for every incident."""
    _require_review_permission(actor, permission="incident.amicable.facilitate")
    incident = _load_incident(incident_id)
    if incident.status == IncidentStatus.RESOLVED:
        raise IncidentAlreadyResolved()
    incident.status = IncidentStatus.AMICABLE_PENDING
    incident.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="incident.amicable_window.started",
        entity_type="incident",
        entity_id=incident.id,
        after={"status": incident.status},
    )
    return incident


# ─── dispute open / resolve (writes job.status only via transition()) ───
@transaction.atomic
def open_dispute(
    *,
    actor: Any,
    job_id: Any,
    incident_ids: list[Any],
    idempotency_key: str = "",
) -> tuple[Dispute, dict[str, Any]]:
    """Freeze the job into ``DISPUTED`` behind at least one open,
    progression-blocking Incident. Creates the ``Dispute`` row under the same
    Job row lock the transition itself takes (ADR-2D-20) — ``job.status`` here
    is still the authoritative *pre*-dispute value, persisted verbatim to
    ``Dispute.pre_dispute_status`` (ADR-2D-07)."""
    job = job_for_update(job_id)

    incidents = list(Incident.objects.filter(job_id=job.id, id__in=incident_ids))
    if not incidents:
        raise IncidentNotFound("No matching incident for this job.")
    blocking = [i for i in incidents if i.is_blocking_eligible]
    if not blocking:
        raise IncidentAlreadyResolved("The supplied incident(s) are already resolved.")

    if Dispute.objects.filter(job=job).exclude(status=DisputeStatus.RESOLVED).exists():
        raise DisputeAlreadyOpen()

    initiator_tokens: list[str] = []
    recipient_principal: Any = None
    if _is_recipient_principal(actor):
        if str(getattr(actor, "job_id", "")) != str(job.id):
            raise NotIncidentParty()
        recipient_principal = actor
    else:
        token = incidents_authz.initiator_token_for_job(actor, job)
        if token:
            initiator_tokens = [token]
        elif not incidents_authz.is_admin(actor):
            raise NotIncidentParty()

    dispute = Dispute.objects.create(
        job=job,
        incident_ids=[str(i.id) for i in incidents],
        opened_by_admin=_actor_user(actor) if incidents_authz.is_admin(actor) else None,
        pre_dispute_status=job.status,
    )

    ctx_data: dict[str, Any] = {
        "initiator_tokens": initiator_tokens,
        "blocking_incident_id": str(blocking[0].id),
    }
    if recipient_principal is not None:
        ctx_data["recipient_principal"] = recipient_principal

    view = job_transition(
        job_id=job.id,
        to=JobStatus.DISPUTED,
        actor=actor,
        context=TransitionContext(data=ctx_data),
        idempotency_key=idempotency_key,
    )
    audit.record(
        actor=actor,
        action="dispute.opened",
        entity_type="dispute",
        entity_id=dispute.id,
        after={"job_id": str(job.id), "incident_ids": dispute.incident_ids},
    )
    emit(
        event_type="DisputeOpened",
        aggregate_type="dispute",
        aggregate_id=str(dispute.id),
        payload={"job_id": str(job.id), "dispute_id": str(dispute.id)},
    )
    return dispute, view


@transaction.atomic
def resolve_dispute(
    *,
    actor: Any,
    dispute_id: Any,
    outcome_code: str,
    rationale: str,
    routed_job_status: str,
    commission_treatment: str = "APPLY",
    reduced_amount_kes: int | None = None,
    agreed_compensation_kes: int | None = None,
    actions: list[str] | None = None,
    idempotency_key: str = "",
) -> tuple[Resolution, dict[str, Any]]:
    """Binding administrative resolution (dispute-and-liability.md §4 / FR-D-6).
    Admin-only; above the Standard value band the job-lifecycle
    ``AdminBandAuthorised`` guard additionally requires a Platform Admin
    (D-ADM-1) — enforced by the transition itself, not duplicated here.

    ``Resolution.actions`` records admin-declared intent flags **only**
    (``RATING_IMPACT`` / ``TRUST_CHANGE`` / ``SUSPENSION`` / ``NONE``) — this
    function executes none of them; no rating, trust, or suspension side
    effect happens in Step 8 (ADR-2D-21).

    Step 9: a ``commission_treatment`` other than ``APPLY`` is a **separate**
    authority from resolving the dispute itself — a Platform Admin only
    (``jobs.commission.can_adjust_commission``); an Operations Officer may
    still resolve a Standard-band dispute (``incidents_authz.is_admin``) but
    may not reduce or waive commission while doing it (Step 9 brief §12).
    Only ``REDUCE``/``WAIVE`` ever create a ``CommissionAdjustment`` — never
    automatically, and never for a job that has no ``CommissionRecord`` at
    all (nothing to adjust)."""
    if not incidents_authz.is_admin(actor):
        raise NotAuthorisedForBindingResolution()
    if routed_job_status not in ROUTABLE_JOB_STATUSES:
        raise InvalidResolutionRouting()
    if outcome_code not in ResolutionOutcome.values:
        raise InvalidResolutionOutcome()
    if commission_treatment not in CommissionTreatment.values:
        raise InvalidResolutionRouting(
            f"{commission_treatment!r} is not a recognised commission treatment."
        )
    if commission_treatment in _COMMISSION_TREATMENTS_REQUIRING_ADJUSTMENT:
        if not commission_service.can_adjust_commission(actor):
            raise NotAuthorisedForCommissionAdjustment()
        if commission_treatment == CommissionTreatment.REDUCE and (
            reduced_amount_kes is None or reduced_amount_kes <= 0
        ):
            raise InvalidCommissionAdjustmentAmount(
                "A positive reduced_amount_kes is required to reduce commission."
            )
    rationale = (rationale or "").strip()
    if not rationale:
        raise RationaleRequired()

    try:
        dispute = Dispute.objects.select_for_update().select_related("job").get(id=dispute_id)
    except Dispute.DoesNotExist as exc:
        raise DisputeNotFound() from exc
    if dispute.status == DisputeStatus.RESOLVED:
        raise DisputeAlreadyResolved()

    job = job_for_update(dispute.job_id)

    resolution = Resolution.objects.create(
        dispute=dispute,
        outcome_code=outcome_code,
        rationale=rationale,
        commission_treatment=commission_treatment,
        reduced_amount_kes=reduced_amount_kes,
        agreed_compensation_kes=agreed_compensation_kes,
        actions=list(actions or []),
        routed_job_status=routed_job_status,
        resolved_by_admin=_actor_user(actor),
        resolved_by_is_platform_admin=incidents_authz.is_platform_admin(actor),
    )

    view = job_transition(
        job_id=job.id,
        to=routed_job_status,
        actor=actor,
        context=TransitionContext(
            data={
                "initiator_tokens": [],
                "resolution_id": str(resolution.id),
                "routed_job_status": routed_job_status,
            }
        ),
        idempotency_key=idempotency_key,
    )

    dispute.status = DisputeStatus.RESOLVED
    dispute.officer_admin = _actor_user(actor)
    dispute.save(update_fields=["status", "officer_admin", "updated_at"])
    Incident.objects.filter(id__in=dispute.incident_ids).exclude(
        status=IncidentStatus.RESOLVED
    ).update(status=IncidentStatus.RESOLVED)

    if commission_treatment in _COMMISSION_TREATMENTS_REQUIRING_ADJUSTMENT:
        commission_record = commission_service.get_commission_record(job)
        if commission_record is not None:
            if commission_treatment == CommissionTreatment.WAIVE:
                kind = CommissionAdjustmentKind.WAIVER
                amount_kes = -commission_service.effective_commission_kes(commission_record)
            else:  # REDUCE — validated positive above
                kind = CommissionAdjustmentKind.REDUCTION
                amount_kes = -int(reduced_amount_kes)  # type: ignore[arg-type]
            if amount_kes < 0:
                commission_service.create_adjustment(
                    commission_record=commission_record,
                    actor=actor,
                    kind=kind,
                    amount_kes=amount_kes,
                    reason=rationale,
                    source_dispute_id=dispute.id,
                    source_resolution_id=resolution.id,
                )
            # amount_kes == 0 (e.g. a WAIVE on an already-fully-waived
            # record): nothing left to adjust — the Resolution row still
            # records the admin's decision; no adjustment row is created.

    audit.record(
        actor=actor,
        action="dispute.resolved",
        entity_type="resolution",
        entity_id=resolution.id,
        after={
            "dispute_id": str(dispute.id),
            "routed_job_status": routed_job_status,
            "outcome_code": outcome_code,
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
            "routed_job_status": routed_job_status,
        },
    )
    return resolution, view


# ─── escalation (Platform-Admin-only; FR-D-8) ───────────────────────────
@transaction.atomic
def escalate(
    *,
    actor: Any,
    incident_id: Any,
    reason: str,
    escalated_to: str = "FOUNDER",
    advised_external_options: bool = False,
) -> Escalation:
    """Escalating to the founder is a Platform-Admin-only action — it is not
    among the specific actions ``role_permissions.OPERATIONS_OFFICER`` grants
    an Ops Officer (only ``incident.intake`` / ``incident.amicable.facilitate``
    are), so it is not an Ops-Officer action either (plan §19 Step 8 brief:
    "Ops Officer remains operational/read-oriented unless explicitly granted a
    specific action")."""
    if not incidents_authz.is_platform_admin(actor):
        raise NotAuthorisedForIncidentReview()
    incident = _load_incident(incident_id)
    reason = (reason or "").strip()
    if not reason:
        raise RationaleRequired("An escalation reason is required.")

    dispute = (
        Dispute.objects.filter(job_id=incident.job_id)
        .exclude(status=DisputeStatus.RESOLVED)
        .first()
    )
    escalation = Escalation.objects.create(
        incident=incident,
        dispute=dispute,
        reason=reason,
        escalated_to=escalated_to,
        advised_external_options=advised_external_options,
    )
    if incident.status != IncidentStatus.RESOLVED:
        incident.status = IncidentStatus.ESCALATED
        incident.save(update_fields=["status", "updated_at"])
    if dispute is not None and dispute.status != DisputeStatus.RESOLVED:
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status", "updated_at"])

    audit.record(
        actor=actor,
        action="incident.escalated",
        entity_type="escalation",
        entity_id=escalation.id,
        after={
            "incident_id": str(incident.id),
            "dispute_id": str(dispute.id) if dispute else None,
            "escalated_to": escalated_to,
        },
    )
    emit(
        event_type="IncidentEscalated",
        aggregate_type="incident",
        aggregate_id=str(incident.id),
        payload={"job_id": str(incident.job_id), "incident_id": str(incident.id)},
    )
    return escalation
