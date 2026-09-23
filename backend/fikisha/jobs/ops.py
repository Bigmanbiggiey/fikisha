"""Operations Officer surfaces over the Jobs module (Design Phase 6
Increment 8, P3 §18.2 / §18.3 / §14).

Read-side: the job monitor (filters + job-reference quick jump), the
high-value review queue, the staff event log. Write-side: the operational
note (``JobEventType.NOTE``, founder decision 2026-09-23: visible to the job's
parties) and the audited contact reveal. **None of these change
``job.status``** — staff cancel stays on the lifecycle engine
(``AdminCancelBandAuthorised``); reassign / force-fail are deferred.

Contacts are deliberately *not* on any list row here: the only way staff
read a party's phone is :func:`reveal_contacts`, which writes an audit row.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import CharField, Max, QuerySet
from django.db.models.functions import Cast
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.business import services as business_services
from fikisha.common.exceptions import AuthorizationError, DomainError
from fikisha.groups import services as groups_services
from fikisha.jobs.constants import (
    HIGH_VALUE_BANDS,
    JobEventCategory,
    JobEventType,
    JobStatus,
    ValueBand,
)
from fikisha.jobs.models import Job, JobEvent
from fikisha.jobs.selectors import get_job, job_for_update
from fikisha.operators import services as operators_services

NOTE_MAX_LENGTH = 2000
#: What a job party sees as a note's author — minimum disclosure (the staff
#: member's own name/role is shown to staff only).
NOTE_AUTHOR_LABEL = "Fikisha Operations"

_ACTIVE_STATUSES: tuple[str, ...] = (
    JobStatus.REQUESTED,
    JobStatus.NEGOTIATING,
    JobStatus.CONFIRMED,
    JobStatus.ASSIGNED,
    JobStatus.AT_PICKUP,
    JobStatus.PICKED_UP,
    JobStatus.IN_TRANSIT,
    JobStatus.AT_DESTINATION,
    JobStatus.DELIVERED,
)
ATTENTION_FILTERS = ("disputed", "failed", "high_value_pending", "stale")
_HEX = re.compile(r"[^0-9a-f]")


def job_reference(job_id: Any) -> str:
    """The short reference the business/operator UI shows (last 6 of the
    id, upper-case — ``jobHelpers.jobReference`` on the frontend)."""
    return str(job_id)[-6:].upper()


class InvalidFilter(DomainError):
    default_code = "invalid_filter"


# ─── Job monitor (§18.2) + quick jump (§18.4, founder-scoped) ──────────
def monitored_jobs(
    *,
    statuses: list[str] | None = None,
    value_band: str | None = None,
    ref: str | None = None,
    attention: str | None = None,
    stale_hours: int | None = None,
) -> QuerySet[Job]:
    """Every job (staff see all — the endpoint's ``job.monitor.view`` policy
    is the gate), narrowed by the filters. ``ref`` matches the job id by
    suffix, so both the 6-char UI reference and the recipient page's 8-char
    ``delivery_reference`` resolve."""
    qs = Job.objects.select_related("pickup_location", "destination_location")

    if statuses:
        bad = [s for s in statuses if s not in JobStatus.values]
        if bad:
            raise InvalidFilter(f"Unknown status filter: {', '.join(bad)}.")
        qs = qs.filter(status__in=statuses)
    if value_band:
        if value_band not in ValueBand.values:
            raise InvalidFilter(f"Unknown value band: {value_band}.")
        qs = qs.filter(value_band=value_band)
    if ref:
        suffix = _HEX.sub("", ref.lower())
        if len(suffix) < 4:
            raise InvalidFilter("A job reference needs at least 4 characters.")
        qs = qs.annotate(id_text=Cast("id", CharField())).filter(id_text__endswith=suffix)
    if attention:
        if attention not in ATTENTION_FILTERS:
            raise InvalidFilter(f"Unknown attention filter: {attention}.")
        if attention == "disputed":
            qs = qs.filter(status=JobStatus.DISPUTED)
        elif attention == "failed":
            qs = qs.filter(status=JobStatus.FAILED)
        elif attention == "high_value_pending":
            qs = high_value_pending(qs)
        elif attention == "stale":
            qs = qs.filter(status__in=_ACTIVE_STATUSES)
            stale_hours = stale_hours or 24
    if stale_hours:
        if stale_hours < 1:
            raise InvalidFilter("stale_hours must be at least 1.")
        cutoff = timezone.now() - timedelta(hours=stale_hours)
        qs = qs.filter(updated_at__lt=cutoff)
    return qs


def high_value_pending(qs: QuerySet[Job] | None = None) -> QuerySet[Job]:
    """HIGH / VERY_HIGH jobs at ``CONFIRMED`` with no recorded decision —
    exactly the jobs the ``HighValueApproved`` guard would currently block
    from assignment (§18.3)."""
    base = qs if qs is not None else Job.objects.all()
    return base.filter(
        status=JobStatus.CONFIRMED,
        value_band__in=HIGH_VALUE_BANDS,
        high_value_approval__isnull=True,
    )


def ops_rows(jobs: list[Job]) -> list[dict[str, Any]]:
    """Slim monitor rows — no contact names or phones (see module docstring)."""
    names = business_services.display_names_for({j.business_id for j in jobs})
    return [
        {
            "id": str(job.id),
            "reference": job_reference(job.id),
            "status": job.status,
            "value_band": job.value_band,
            "is_high_value": job.is_high_value,
            "business_name": names.get(str(job.business_id), ""),
            "pickup_area": _area(job.pickup_location),
            "destination_area": _area(job.destination_location),
            "created_at": job.created_at.isoformat(),
            "last_changed_at": job.updated_at.isoformat(),
        }
        for job in jobs
    ]


def high_value_rows(jobs: list[Job]) -> list[dict[str, Any]]:
    rows = ops_rows(jobs)
    for row, job in zip(rows, jobs, strict=True):
        row["declared_value_kes"] = job.declared_value_kes
        row["needs_platform_admin"] = job.value_band == ValueBand.VERY_HIGH
        row["operator_name"] = _agreement_party_name(job)
    return rows


def _area(location: Any) -> str:
    return (location.address_text if location is not None else "") or ""


def _agreement_party_name(job: Job) -> str | None:
    agreement = job.agreement
    if agreement is None:
        return None
    if agreement.operator_id:
        return operators_services.display_name_for(agreement.operator_id)
    if agreement.group_id:
        return groups_services.display_name_for(agreement.group_id)
    return None


# ─── Operational notes (§18.2 "nudge") ─────────────────────────────────
def _require_permission(actor: Any, permission: str) -> None:
    from fikisha.identity.authz.policies import actor_has_permission

    if not actor_has_permission(actor, permission):
        raise AuthorizationError(f"missing permission {permission!r}")


@transaction.atomic
def add_note(*, actor: Any, job_id: Any, text: str) -> dict[str, Any]:
    """Append an operational note to the job's event log. Never touches
    ``job.status``; allowed in any state (a frozen or terminal job can still
    carry a note). The row lock serialises the ``seq`` with any concurrent
    transition, which holds the same lock."""
    _require_permission(actor, "job.intervene")
    body = (text or "").strip()
    if not body:
        raise DomainError("A note cannot be empty.", code="note_empty")
    if len(body) > NOTE_MAX_LENGTH:
        raise DomainError(
            f"A note is limited to {NOTE_MAX_LENGTH} characters.", code="note_too_long"
        )
    job = job_for_update(job_id)
    seq = (JobEvent.objects.filter(job=job).aggregate(m=Max("seq"))["m"] or 0) + 1
    user = getattr(actor, "user", actor)
    event = JobEvent.objects.create(
        job=job,
        seq=seq,
        category=JobEventCategory.ADMIN_ACTION,
        type=JobEventType.NOTE,
        is_custody=False,
        actor_user=user if getattr(user, "pk", None) else None,
        actor_role=str(getattr(actor, "audit_role", "") or ""),
        note=body,
        config_version_id=job.config_version_id,
    )
    audit.record(
        actor=actor,
        action="job.note.added",
        entity_type="job",
        entity_id=job.id,
        after={"event_id": str(event.id), "seq": seq, "length": len(body)},
    )
    return _note_view(event, staff=True)


def notes_for(job: Job, *, staff: bool) -> list[dict[str, Any]]:
    events = JobEvent.objects.filter(
        job=job, category=JobEventCategory.ADMIN_ACTION, type=JobEventType.NOTE
    ).order_by("seq")
    return [_note_view(e, staff=staff) for e in events]


def _note_view(event: JobEvent, *, staff: bool) -> dict[str, Any]:
    view: dict[str, Any] = {
        "id": str(event.id),
        "text": event.note,
        "created_at": event.server_time.isoformat(),
        "author_label": NOTE_AUTHOR_LABEL,
    }
    if staff:
        view["author_role"] = event.actor_role
        view["author_user_id"] = str(event.actor_user_id) if event.actor_user_id else None
    return view


# ─── Staff event log (§14 raw-event drawer) ────────────────────────────
def events_for(job: Job) -> list[dict[str, Any]]:
    """The full append-only event log, in ``seq`` order. ``source_meta`` is
    deliberately left out (free-form, may carry provider detail)."""
    return [
        {
            "seq": e.seq,
            "category": e.category,
            "type": e.type,
            "is_custody": e.is_custody,
            "actor_role": e.actor_role,
            "from_status": e.from_status,
            "to_status": e.to_status,
            "server_time": e.server_time.isoformat(),
            "confirmation_method": e.confirmation_method,
            "geo_state": e.geo_state,
            "evidence_count": len(e.evidence_ids or []),
            "note": e.note,
        }
        for e in JobEvent.objects.filter(job=job).order_by("seq")
    ]


# ─── Contact parties (§18.2) — every reveal is audited ────────────────
@transaction.atomic
def reveal_contacts(*, actor: Any, job_id: Any) -> dict[str, Any]:
    """The job's parties' names + phones, for staff to call/WhatsApp them —
    digitising existing practice, not an in-app messaging channel. One audit
    row per reveal, naming which parties were revealed — **never the phone
    numbers themselves**."""
    _require_permission(actor, "job.intervene")
    job = get_job(job_id)
    contacts: dict[str, dict[str, str] | None] = {
        "business": business_services.contact_for(job.business_id),
        "pickup": _location_contact(job.pickup_location),
        "destination": _location_contact(job.destination_location),
        "recipient": (
            {"name": job.recipient_name, "phone": job.recipient_phone}
            if job.recipient_name or job.recipient_phone
            else None
        ),
        "operator": _operator_contact(job),
        "driver": (
            operators_services.contact_for(job.assignment.assigned_driver_profile_id)
            if job.assignment is not None
            else None
        ),
    }
    revealed = sorted(k for k, v in contacts.items() if v and v.get("phone"))
    audit.record(
        actor=actor,
        action="job.contacts.revealed",
        entity_type="job",
        entity_id=job.id,
        after={"parties": revealed},
    )
    return {"job_id": str(job.id), "contacts": contacts}


def _location_contact(location: Any) -> dict[str, str] | None:
    if location is None or not (location.contact_name or location.contact_phone):
        return None
    return {"name": location.contact_name, "phone": location.contact_phone}


def _operator_contact(job: Job) -> dict[str, str] | None:
    agreement = job.agreement
    if agreement is None:
        return None
    if agreement.operator_id:
        return operators_services.contact_for(agreement.operator_id)
    if agreement.group_id:
        # Groups have no phone of their own; the assigned driver (above) is
        # the reachable person once a group job is assigned.
        name = groups_services.display_name_for(agreement.group_id)
        return {"name": name or "", "phone": ""} if name else None
    return None
