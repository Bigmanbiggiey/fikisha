"""``JobLifecycleService`` — the single authoritative writer of ``job.status``.

Every API endpoint, admin action, scheduled sweep and event handler that
advances a job calls :func:`transition`. The ``BEFORE UPDATE OF status ON job``
trigger (migration ``0002``) is the backstop; this service sets the
``app.lifecycle_service`` GUC after its guards pass so the trigger lets the
write through.

Algorithm — job-state-machine.md §2.1, executed inside one ``transaction.atomic``:

  1. lock the job row (``SELECT … FOR UPDATE``) — serialises transitions
  2. idempotency replay check (scoped ``actor_key, job, key``)
  3. ``If-Match`` optimistic-concurrency check → 412
  4. allowed-transition lookup → 422
  5. initiator authorisation → 403
  6. guards (each raises 409/422 on failure)
  7. side effects (``apply_fns``) — rows created in this transaction
  8. ``status`` / ``version`` / the relevant ``*_at`` stamp
  9. ``job_event`` rows (per-job monotonic ``seq``; + custody row if ``is_custody``)
 10. hash-chained ``audit_log_entry``
 11. ``outbox_event`` rows (async fan-out — never external I/O in-txn)
 12. store the ``JobView`` for idempotent replay

Anything raised in 3-7 rolls the whole transaction back with **no** side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import connection, transaction
from django.db.models import Max
from django.http import Http404
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.jobs.apply_fns import APPLY
from fikisha.jobs.constants import (
    CUSTODY_EVENT_TYPES,
    TERMINAL_STATES,
    GeoState,
    JobEventCategory,
    JobEventType,
    JobStatus,
)
from fikisha.jobs.dto import job_view
from fikisha.jobs.errors import (
    NotAuthorisedToInitiate,
    StaleJob,
    TransitionNotAllowed,
)
from fikisha.jobs.guards import GUARDS
from fikisha.jobs.models import Job, JobEvent, JobTransitionIdempotency
from fikisha.jobs.transitions import Rule, rule_for
from fikisha.outbox.services import emit

# ``to`` status → the lifecycle timestamp column the service stamps.
_TIMESTAMP_COLUMN: dict[str, str] = {
    JobStatus.REQUESTED: "published_at",
    JobStatus.CONFIRMED: "confirmed_at",
    JobStatus.ASSIGNED: "assigned_at",
    JobStatus.PICKED_UP: "picked_up_at",
    JobStatus.DELIVERED: "delivered_at",
    JobStatus.COMPLETED: "completed_at",
}

_PARTICIPANT_TOKENS = frozenset(
    {
        "BUSINESS_OWNER_OR_DISPATCHER",
        "BUSINESS_PARTY",
        "OPERATOR_PARTY",
        "GROUP_MANAGER",
        "ASSIGNED_DRIVER",
        "RECIPIENT",
        "ADMIN",
        "PLATFORM_ADMIN",
        "SCHEDULER",
    }
)


@dataclass(frozen=True)
class TransitionContext:
    """Everything a transition's guards / side effects need that is not on the
    ``Job`` row. The initiating service or API view fills it in.

    ``data`` well-known keys (all optional unless a guard requires them):
      * ``initiator_tokens``: set[str] — participant roles the caller has
        already resolved for this actor + job (e.g. ``{"BUSINESS_PARTY"}``).
        Admin / Platform-Admin / Scheduler are derived from the ``Actor`` and
        need not be asserted here.
      * ``reason_text`` / ``reason_code`` — cancellation / failure reasons.
      * negotiation: ``operator_party``, ``operator_id`` | ``group_id``,
        ``agreed_price_kes``, ``accepting_entry_ids``.
      * assignment: ``driver_profile``, ``vehicle``, ``assigned_by``,
        ``admin_override_reason``.
      * pickup proof: ``pickup_method`` (``OTP`` | ``BUSINESS_CONFIRM`` |
        ``ATTESTED``), ``pickup_contact_name``, ``fallback_photo_id`` …
      * delivery proof: ``party_name``, ``otp_verified``,
        ``signature_evidence_id``, ``photo_evidence_ids``.
      * dispute: ``blocking_incident_id``, ``resolution_id``,
        ``routed_job_status``.
      * ``recipient_principal`` — set when the caller is a recipient link.
    """

    data: dict[str, Any] = field(default_factory=dict)
    if_match_version: int | None = None


def _actor_key(actor: Any) -> str:
    user = getattr(actor, "user", actor)
    pk = getattr(user, "pk", None)
    return str(pk) if pk is not None else "system"


def _actor_matches(actor: Any, rule: Rule, job: Job, data: dict[str, Any]) -> bool:
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    audit_role = str(getattr(actor, "audit_role", "") or "")
    granted: set[str] = {str(t) for t in (data.get("initiator_tokens") or [])}

    if (
        getattr(actor, "is_admin", False)
        or roles & {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"}
        or audit_role
        in {
            "PLATFORM_ADMIN",
            "OPERATIONS_OFFICER",
        }
    ):
        granted.add("ADMIN")
    if "PLATFORM_ADMIN" in roles or audit_role == "PLATFORM_ADMIN":
        granted.add("PLATFORM_ADMIN")
    if audit_role == "SYSTEM" or data.get("scheduler"):
        granted.add("SCHEDULER")

    user = getattr(actor, "user", None)
    assignment = job.assignment
    if assignment is not None and user is not None and getattr(user, "pk", None) is not None:
        driver = assignment.assigned_driver_profile
        if getattr(driver, "user_id", None) == user.pk:
            granted.add("ASSIGNED_DRIVER")
    if data.get("recipient_principal"):
        granted.add("RECIPIENT")

    if "BUSINESS_OWNER_OR_DISPATCHER" in granted:
        granted.add("BUSINESS_PARTY")
    if granted & _PARTICIPANT_TOKENS:
        granted.add("ANY_PARTICIPANT")

    return bool(granted & set(rule.initiators))


def _set_session_guards(actor_key: str) -> None:
    """Tell the DB backstop trigger this UPDATE is sanctioned, and record who for
    a future Row-Level-Security policy (Q-7 seam)."""
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.lifecycle_service', 'on', true)")
        cur.execute("SELECT set_config('app.actor_id', %s, true)", [actor_key])


def _next_seq(job: Job) -> int:
    current = JobEvent.objects.filter(job=job).aggregate(m=Max("seq"))["m"] or 0
    return int(current) + 1


# Custody rows for these transition targets carry a single event-based location
# reading if the client provided one (chain-of-custody.md §5 — no continuous GPS).
_GEO_CAPTURE_EVENTS = frozenset(
    {
        JobEventType.ARRIVED_AT_PICKUP,
        JobEventType.GOODS_RECEIVED,
        JobEventType.ARRIVED_AT_DESTINATION,
        JobEventType.DELIVERY_CONFIRMED,
    }
)


def _geo_fields(ctx: dict[str, Any], event_type: str) -> dict[str, Any]:
    if event_type not in _GEO_CAPTURE_EVENTS:
        return {}
    geo = ctx.get("geo")
    if not geo:
        return {"geo_state": GeoState.NOT_CAPTURED}
    return {
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
        "geo_accuracy_m": geo.get("accuracy_m"),
        "geo_state": GeoState.CAPTURED,
    }


def _write_events(
    *,
    job: Job,
    rule: Rule,
    from_status: str,
    to_status: str,
    actor: Any,
    config_version_id: Any,
    ctx: dict[str, Any],
) -> None:
    user = getattr(actor, "user", actor)
    actor_user = user if getattr(user, "pk", None) else None
    actor_role = str(getattr(actor, "audit_role", "") or "")
    seq = _next_seq(job)

    rows: list[dict[str, Any]] = [
        {
            "category": JobEventCategory.STATUS_TRANSITION,
            "type": rule.event_type,
            "is_custody": False,
            "from_status": from_status,
            "to_status": to_status,
        }
    ]
    if rule.is_custody:
        rows.append(
            {
                "category": JobEventCategory.CUSTODY,
                "type": rule.event_type,
                "is_custody": True,
                "from_status": from_status,
                "to_status": to_status,
                **_geo_fields(ctx, rule.event_type),
            }
        )
    for extra in rule.extra_events:
        is_custody = extra in CUSTODY_EVENT_TYPES
        rows.append(
            {
                "category": JobEventCategory.CUSTODY if is_custody else JobEventCategory.SYSTEM,
                "type": extra,
                "is_custody": is_custody,
                "from_status": None,
                "to_status": None,
                **(_geo_fields(ctx, extra) if is_custody else {}),
            }
        )

    for offset, row in enumerate(rows):
        JobEvent.objects.create(
            job=job,
            seq=seq + offset,
            actor_user=actor_user,
            actor_role=actor_role,
            config_version_id=config_version_id,
            **row,
        )


def transition(
    *,
    job_id: Any,
    to: str,
    actor: Any,
    context: TransitionContext | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Move ``job_id`` to ``to``. Returns the :func:`job_view` dict.

    Raises (all before any write, transaction rolled back):
      * :class:`Http404` — no such job
      * :class:`StaleJob` (412) — ``If-Match`` mismatch
      * :class:`TransitionNotAllowed` (422) — ``(from, to)`` not in the table
      * :class:`NotAuthorisedToInitiate` (403) — actor not an allowed initiator
      * :class:`~fikisha.jobs.errors.GuardFailed` / :class:`ConflictError` — a guard
      * :class:`~fikisha.jobs.errors.NotImplementedInThisIncrement` (501) — a
        transition whose side-effect service is a later Phase 2D increment
    """
    ctx = context or TransitionContext()
    to = str(to)
    if to not in JobStatus.values:
        raise TransitionNotAllowed(f"{to!r} is not a job status.")
    actor_key = _actor_key(actor)

    # Fast path: a committed replay is visible without taking the row lock.
    prior = (
        JobTransitionIdempotency.objects.filter(
            actor_key=actor_key, job_id=job_id, idempotency_key=idempotency_key
        ).first()
        if idempotency_key
        else None
    )
    if prior is not None:
        return dict(prior.stored_response)

    with transaction.atomic():
        try:
            job = Job.objects.select_for_update().get(id=job_id)
        except Job.DoesNotExist as exc:
            raise Http404("No such job.") from exc

        if idempotency_key:
            locked_prior = JobTransitionIdempotency.objects.filter(
                actor_key=actor_key, job_id=job.id, idempotency_key=idempotency_key
            ).first()
            if locked_prior is not None:
                return dict(locked_prior.stored_response)

        if ctx.if_match_version is not None and ctx.if_match_version != job.version:
            raise StaleJob(
                f"Job is at version {job.version}, not {ctx.if_match_version}; refetch and retry."
            )

        from_status = job.status
        rule = rule_for(from_status, to)
        if rule is None:
            raise TransitionNotAllowed(f"{from_status} → {to} is not an allowed job transition.")

        if not _actor_matches(actor, rule, job, ctx.data):
            raise NotAuthorisedToInitiate(f"This actor may not initiate {from_status} → {to}.")

        _set_session_guards(actor_key)

        for guard_name in rule.guards:
            GUARDS[guard_name](job, actor, ctx.data)

        APPLY[rule.apply](job, actor, ctx.data)

        from_version = job.version
        job.status = to
        job.version = from_version + 1
        now = timezone.now()
        update_fields = {"status", "version", "updated_at"}
        stamp_column = _TIMESTAMP_COLUMN.get(to)
        if stamp_column and getattr(job, stamp_column) is None:
            setattr(job, stamp_column, now)
            update_fields.add(stamp_column)
        if to in TERMINAL_STATES and job.terminal_at is None:
            job.terminal_at = now
            update_fields.add("terminal_at")
        # apply_fns may have set domain fields / linked rows — persist the lot.
        job.save(
            update_fields=sorted(
                update_fields
                | {
                    "value_band",
                    "required_trust_level",
                    "is_high_value",
                    "config_version",
                    "agreement",
                    "assignment",
                    "proposed_price_kes",
                }
            )
        )

        _write_events(
            job=job,
            rule=rule,
            from_status=from_status,
            to_status=to,
            actor=actor,
            config_version_id=job.config_version_id,
            ctx=ctx.data,
        )

        audit.record(
            actor=actor,
            action=f"job.transition.{to.lower()}",
            entity_type="job",
            entity_id=job.id,
            before={"status": from_status, "version": from_version},
            after={"status": to, "version": job.version},
        )

        for event_type in rule.events:
            emit(
                event_type=event_type,
                aggregate_type="job",
                aggregate_id=str(job.id),
                payload={
                    "job_id": str(job.id),
                    "from_status": from_status,
                    "to_status": to,
                    "version": job.version,
                    "actor_role": str(getattr(actor, "audit_role", "") or ""),
                },
            )

        view = job_view(job)
        if idempotency_key:
            JobTransitionIdempotency.objects.create(
                actor_key=actor_key,
                job=job,
                idempotency_key=idempotency_key,
                stored_response=view,
            )
        return view


def peek_idempotent(*, actor: Any, job_id: Any, idempotency_key: str) -> dict[str, Any] | None:
    """Return a previously stored transition response for ``(actor, job, key)``,
    or ``None``. Lets a calling service short-circuit a retried multi-step
    operation (e.g. ``negotiation.accept``) before it re-does its own writes."""
    if not idempotency_key:
        return None
    row = JobTransitionIdempotency.objects.filter(
        actor_key=_actor_key(actor), job_id=job_id, idempotency_key=idempotency_key
    ).first()
    return dict(row.stored_response) if row is not None else None


class JobLifecycleService:
    """Namespace wrapper (job-state-machine.md §2 spells the call
    ``JobLifecycleService.transition(...)``)."""

    transition = staticmethod(transition)
    peek_idempotent = staticmethod(peek_idempotent)
    TransitionContext = TransitionContext
