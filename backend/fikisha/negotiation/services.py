"""Negotiation domain services (negotiation-architecture.md §3).

Two-way propose / counter / accept / reject over an **immutable append-only**
history. On mutual acceptance in one thread this calls
``JobLifecycleService.transition(job, CONFIRMED, …)`` — the only writer of
``job.status`` — which creates the frozen ``Agreement`` inside the same
transaction; this service then closes the winning thread and supersedes its
siblings in that same transaction (ADR-007 / ADR-2D-12).

The platform never sets, recommends, or aggregates a price (D-NEG-4). A tenfold
mistype produces a **non-blocking** ``warning`` in the response, never a
rejection (pricing-and-negotiation.md §6).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.jobs.constants import JobStatus, OperatorParty
from fikisha.jobs.selectors import job_for_update
from fikisha.jobs.service import TransitionContext, peek_idempotent
from fikisha.jobs.service import transition as job_transition
from fikisha.negotiation import authz
from fikisha.negotiation.constants import (
    OFFER_TYPES,
    EntryActorRole,
    EntryType,
    ThreadStatus,
)
from fikisha.negotiation.errors import (
    InvalidOffer,
    JobNotOpenForNegotiation,
    NotANegotiationParty,
    NothingToAccept,
    NoThreadYet,
    ThreadNotActive,
)
from fikisha.negotiation.models import NegotiationEntry, NegotiationThread
from fikisha.negotiation.selectors import (
    annotate_entries,
    counterparty_figure_to_accept,
    mutual_acceptance,
    standing_offer,
)
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config

_OPEN_STATES: set[str] = {JobStatus.REQUESTED, JobStatus.NEGOTIATING}
_SIDE_TOKEN: dict[str, str] = {
    EntryActorRole.BUSINESS: "BUSINESS_PARTY",
    EntryActorRole.OPERATOR: "OPERATOR_PARTY",
    EntryActorRole.ADMIN: "ADMIN",
}


# ─── helpers ───────────────────────────────────────────────────────────
def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def _offer_expiry() -> Any:
    hours = int(config.get("timeouts.offer_expiry_hours", 4) or 4)
    return timezone.now() + timedelta(hours=hours)


def _validate_amount(amount_kes: Any) -> int:
    if not isinstance(amount_kes, int) or isinstance(amount_kes, bool) or amount_kes <= 0:
        raise InvalidOffer("The offer amount must be a positive integer (KES minor units).")
    return amount_kes


def _mistype_warning(baseline_kes: int | None, amount_kes: int) -> str | None:
    """A non-blocking nudge when the new figure is >=10x or <=1/10 the figure it
    is responding to. Never a rejection (pricing-and-negotiation.md §6)."""
    if baseline_kes and (amount_kes >= baseline_kes * 10 or amount_kes * 10 <= baseline_kes):
        return (
            "This amount is an order of magnitude from the previous offer - "
            "please double-check it. The platform does not reject prices."
        )
    return None


def _operator_profile_for(thread: NegotiationThread) -> Any:
    if thread.operator_id is None:
        return None
    from fikisha.operators.models import OperatorProfile

    return OperatorProfile.objects.filter(id=thread.operator_id).first()


def _get_thread(thread_id: Any, *, lock: bool = False) -> NegotiationThread:
    qs = NegotiationThread.objects.select_related("job")
    if lock:
        qs = qs.select_for_update(of=("self",))
    obj = qs.filter(id=thread_id).first()
    if obj is None:
        raise NoThreadYet()
    return obj


def _existing_thread(job: Any, operator_id: Any, group_id: Any) -> NegotiationThread | None:
    q = NegotiationThread.objects.filter(job=job)
    if operator_id is not None:
        return q.filter(operator_id=operator_id).first()
    if group_id is not None:
        return q.filter(group_id=group_id).first()
    return None


def _seed_business_proposal(thread: NegotiationThread, job: Any, actor: Any) -> None:
    """Materialise the business's posted price as the first entry so every thread
    carries a complete history (negotiation-architecture.md §3.1)."""
    if job.proposed_price_kes is None or job.proposed_price_kes <= 0:
        return
    NegotiationEntry.objects.create(
        thread=thread,
        job=job,
        actor_user_id=job.created_by_id,
        actor_role=EntryActorRole.BUSINESS,
        type=EntryType.PROPOSE,
        amount_kes=job.proposed_price_kes,
        note="Posted price at publication.",
        expires_at=_offer_expiry(),
    )


def _write_entry(
    *,
    thread: NegotiationThread,
    job: Any,
    actor: Any,
    side: str,
    entry_type: str,
    amount_kes: int | None,
    note: str,
    in_response_to: NegotiationEntry | None = None,
) -> NegotiationEntry:
    entry = NegotiationEntry.objects.create(
        thread=thread,
        job=job,
        actor_user=_actor_user(actor),
        actor_role=side,
        type=entry_type,
        amount_kes=amount_kes,
        note=note.strip(),
        in_response_to=in_response_to,
        expires_at=_offer_expiry() if entry_type in OFFER_TYPES else None,
    )
    audit.record(
        actor=actor,
        action=f"negotiation.{entry_type.lower()}",
        entity_type="negotiation_entry",
        entity_id=entry.id,
        after={
            "thread_id": str(thread.id),
            "job_id": str(job.id),
            "type": entry_type,
            "actor_role": side,
            "amount_kes": amount_kes,
        },
    )
    events: dict[str, str] = {
        EntryType.ACCEPT: "OfferAccepted",
        EntryType.REJECT: "ThreadClosed",
    }
    event = events.get(entry_type, "OfferPlaced")
    emit(
        event_type=event,
        aggregate_type="negotiation_thread",
        aggregate_id=str(thread.id),
        payload={
            "thread_id": str(thread.id),
            "job_id": str(job.id),
            "entry_id": str(entry.id),
            "type": entry_type,
            "actor_role": side,
            "amount_kes": amount_kes,
        },
    )
    return entry


def _to_negotiating(job: Any, actor: Any, thread: NegotiationThread, side: str) -> None:
    if job.status != JobStatus.REQUESTED:
        return
    job_transition(
        job_id=job.id,
        to=JobStatus.NEGOTIATING,
        actor=actor,
        context=TransitionContext(
            data={
                "initiator_tokens": [_SIDE_TOKEN[side]],
                "operator_profile": _operator_profile_for(thread),
            }
        ),
    )


def _close_threads_on_confirm(job: Any, winning: NegotiationThread) -> None:
    now = timezone.now()
    winning.status = ThreadStatus.CLOSED
    winning.closed_at = now
    winning.save(update_fields=["status", "closed_at", "updated_at"])
    NegotiationThread.objects.filter(job=job, status=ThreadStatus.ACTIVE).exclude(
        id=winning.id
    ).update(status=ThreadStatus.SUPERSEDED, closed_at=now)


def _operator_display_name(thread: NegotiationThread) -> str | None:
    """Resolved via the sibling modules' public services, not a direct model
    import (module boundary rule) — the thread's own `operator`/`group` FKs
    already scope this to a party of *this* thread, so it doesn't reopen the
    `operator.read`/`group.read` policies which stay closed to arbitrary ids."""
    if thread.operator_id:
        from fikisha.operators import services as operators_services

        return operators_services.display_name_for(thread.operator_id)
    if thread.group_id:
        from fikisha.groups import services as groups_services

        return groups_services.display_name_for(thread.group_id)
    return None


def _thread_payload(
    thread: NegotiationThread, job: Any, *, viewer_side: str | None = None
) -> dict[str, Any]:
    offer = standing_offer(thread)
    reached, amount, ids = mutual_acceptance(thread)
    # What *this viewer* could accept right now — the UI needs this to decide
    # whether to show "Accept KSh X" at all, and the exact amount to send as
    # AcceptBody's defence-in-depth confirmation. `standing_offer` above is
    # viewer-agnostic (whoever posted last, either side) and is NOT the same
    # thing: if the viewer's own offer is the most recent, there is nothing
    # for *them* to accept yet. Computed here (once, server-side) rather than
    # re-derived in the frontend, matching this module's own "derived, never
    # stored — and never re-derived downstream" selectors.py convention.
    counterparty_offer = None
    if viewer_side in (EntryActorRole.BUSINESS, EntryActorRole.OPERATOR):
        target = counterparty_figure_to_accept(thread, for_role=viewer_side)
        if target is not None:
            counterparty_offer = {"entry_id": str(target.id), "amount_kes": target.amount_kes}
    return {
        "thread_id": str(thread.id),
        "job_id": str(job.id),
        "job_status": job.status,
        "status": thread.status,
        "operator_party": thread.operator_party,
        "operator_id": str(thread.operator_id) if thread.operator_id else None,
        "group_id": str(thread.group_id) if thread.group_id else None,
        "operator_display_name": _operator_display_name(thread),
        "standing_offer": (
            {
                "entry_id": str(offer.id),
                "actor_role": offer.actor_role,
                "amount_kes": offer.amount_kes,
            }
            if offer
            else None
        ),
        "counterparty_offer": counterparty_offer,
        "mutual_acceptance": {"reached": reached, "amount_kes": amount, "entry_ids": ids},
        "entries": annotate_entries(thread),
    }


# ─── reads ─────────────────────────────────────────────────────────────
def view_thread(*, actor: Any, thread_id: Any) -> dict[str, Any]:
    thread = _get_thread(thread_id)
    job = thread.job
    side = authz.actor_side_for_thread(actor, job, thread)
    if side is None:
        raise NotANegotiationParty()
    return _thread_payload(thread, job, viewer_side=side)


def list_threads(*, actor: Any, job_id: Any) -> list[dict[str, Any]]:
    from fikisha.jobs.selectors import get_job

    job = get_job(job_id)
    threads = list(NegotiationThread.objects.filter(job=job).order_by("created_at"))
    sides = [authz.actor_side_for_thread(actor, job, t) for t in threads]
    visible = [(t, side) for t, side in zip(threads, sides, strict=True) if side is not None]
    if not visible and threads:
        # a non-party sees an empty list, not a 403 (existence is not leaked)
        return []
    return [_thread_payload(t, job, viewer_side=side) for t, side in visible]


# ─── writes ────────────────────────────────────────────────────────────
@transaction.atomic
def propose(
    *,
    actor: Any,
    job_id: Any,
    operator_id: Any = None,
    group_id: Any = None,
    amount_kes: int,
    note: str = "",
) -> dict[str, Any]:
    """Put a figure on the table. An operator-side call opens the thread (seeding
    the business's posted price); a business-side call needs an existing thread."""
    amount_kes = _validate_amount(amount_kes)
    job = job_for_update(job_id)
    if job.status not in _OPEN_STATES:
        raise JobNotOpenForNegotiation()

    if authz.business_can_negotiate(actor, job):
        side = EntryActorRole.BUSINESS
        thread = _existing_thread(job, operator_id, group_id)
        if thread is None:
            raise NoThreadYet()
    elif authz.operator_may_open(actor, operator_id=operator_id, group_id=group_id):
        side = EntryActorRole.OPERATOR
        party = OperatorParty.OPERATOR if operator_id is not None else OperatorParty.GROUP
        thread, created = NegotiationThread.objects.get_or_create(
            job=job,
            operator_id=operator_id,
            group_id=group_id,
            defaults={"operator_party": party},
        )
        if created:
            _seed_business_proposal(thread, job, actor)
    elif authz.is_admin(actor):
        side = EntryActorRole.ADMIN
        thread = _existing_thread(job, operator_id, group_id)
        if thread is None:
            raise NoThreadYet()
    else:
        raise NotANegotiationParty()

    if thread.status != ThreadStatus.ACTIVE:
        raise ThreadNotActive()

    _current = standing_offer(thread)
    baseline = _current.amount_kes if _current is not None else job.proposed_price_kes
    warning = _mistype_warning(baseline, amount_kes)
    _write_entry(
        thread=thread,
        job=job,
        actor=actor,
        side=side,
        entry_type=EntryType.PROPOSE,
        amount_kes=amount_kes,
        note=note,
    )
    _to_negotiating(job, actor, thread, side)
    job.refresh_from_db()
    payload = _thread_payload(thread, job, viewer_side=side)
    if warning:
        payload["warning"] = warning
    return payload


@transaction.atomic
def counter(*, actor: Any, thread_id: Any, amount_kes: int, note: str = "") -> dict[str, Any]:
    amount_kes = _validate_amount(amount_kes)
    thread = _get_thread(thread_id, lock=True)
    job = job_for_update(thread.job_id)
    if job.status not in _OPEN_STATES:
        raise JobNotOpenForNegotiation()
    side = authz.actor_side_for_thread(actor, job, thread)
    if side is None:
        raise NotANegotiationParty()
    if thread.status != ThreadStatus.ACTIVE:
        raise ThreadNotActive()

    current = standing_offer(thread)
    warning = _mistype_warning(current.amount_kes if current is not None else None, amount_kes)
    _write_entry(
        thread=thread,
        job=job,
        actor=actor,
        side=side,
        entry_type=EntryType.COUNTER,
        amount_kes=amount_kes,
        note=note,
        in_response_to=current,
    )
    _to_negotiating(job, actor, thread, side)
    job.refresh_from_db()
    payload = _thread_payload(thread, job, viewer_side=side)
    if warning:
        payload["warning"] = warning
    return payload


@transaction.atomic
def accept(
    *,
    actor: Any,
    thread_id: Any,
    amount_kes: int | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Accept the counterparty's standing offer. On mutual acceptance this
    confirms the job (creates the frozen Agreement) and closes the threads, all
    in this transaction."""
    thread = _get_thread(thread_id, lock=True)
    job = job_for_update(thread.job_id)
    side = authz.actor_side_for_thread(actor, job, thread)

    replay = peek_idempotent(actor=actor, job_id=job.id, idempotency_key=idempotency_key)
    if replay is not None:
        payload = _thread_payload(thread, job, viewer_side=side)
        payload["confirmed"] = True
        payload["job"] = replay
        return payload

    if side not in (EntryActorRole.BUSINESS, EntryActorRole.OPERATOR):
        # admin "record-only" intervention accepts are deferred to the disputes increment
        raise NotANegotiationParty()
    if job.status not in _OPEN_STATES:
        raise JobNotOpenForNegotiation()
    if thread.status != ThreadStatus.ACTIVE:
        raise ThreadNotActive()

    target = counterparty_figure_to_accept(thread, for_role=side)
    if target is None:
        raise NothingToAccept()
    if amount_kes is not None and amount_kes != target.amount_kes:
        raise InvalidOffer("The amount does not match the other party's standing offer.")

    _write_entry(
        thread=thread,
        job=job,
        actor=actor,
        side=side,
        entry_type=EntryType.ACCEPT,
        amount_kes=target.amount_kes,
        note="",
        in_response_to=target,
    )

    reached, agreed_amount, accepting_ids = mutual_acceptance(thread)
    if not reached:
        payload = _thread_payload(thread, job, viewer_side=side)
        payload["confirmed"] = False
        return payload

    ctx = TransitionContext(
        data={
            "initiator_tokens": [_SIDE_TOKEN[side]],
            "operator_party": thread.operator_party,
            "operator_id": str(thread.operator_id) if thread.operator_id else None,
            "group_id": str(thread.group_id) if thread.group_id else None,
            "agreed_price_kes": agreed_amount,
            "accepting_entry_ids": accepting_ids,
            "operator_profile": _operator_profile_for(thread),
        }
    )
    job_view = job_transition(
        job_id=job.id,
        to=JobStatus.CONFIRMED,
        actor=actor,
        context=ctx,
        idempotency_key=idempotency_key,
    )
    _close_threads_on_confirm(job, winning=thread)
    thread.refresh_from_db()
    job.refresh_from_db()
    payload = _thread_payload(thread, job, viewer_side=side)
    payload["confirmed"] = True
    payload["job"] = job_view
    return payload


@transaction.atomic
def decline(*, actor: Any, thread_id: Any, note: str = "") -> dict[str, Any]:
    """Reject this thread. The job stays open for other operators
    (pricing-and-negotiation.md §3); the business withdraws it with
    ``job.transition(CANCELLED)`` separately."""
    thread = _get_thread(thread_id, lock=True)
    job = job_for_update(thread.job_id)
    side = authz.actor_side_for_thread(actor, job, thread)
    if side is None:
        raise NotANegotiationParty()
    if thread.status != ThreadStatus.ACTIVE:
        raise ThreadNotActive()

    _write_entry(
        thread=thread,
        job=job,
        actor=actor,
        side=side,
        entry_type=EntryType.REJECT,
        amount_kes=None,
        note=note,
    )
    thread.status = ThreadStatus.CLOSED
    thread.closed_at = timezone.now()
    thread.save(update_fields=["status", "closed_at", "updated_at"])
    return _thread_payload(thread, job, viewer_side=side)
