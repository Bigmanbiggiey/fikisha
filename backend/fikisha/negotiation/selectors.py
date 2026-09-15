"""Derived reads over the immutable ``negotiation_entry`` history (ADR-2D-11).

An entry's status is **computed**, never stored:

* thread not ACTIVE                         → SUPERSEDED
* ``expires_at`` in the past                → EXPIRED
* PROPOSE / COUNTER: a later PROPOSE/COUNTER **from the same side** exists
  (that side revised its figure)            → SUPERSEDED
* ACCEPT: a later PROPOSE/COUNTER from **either** side exists (the terms moved),
  or a later ACCEPT from the same side      → SUPERSEDED
* otherwise                                 → ACTIVE

Each side's "standing offer" is its latest ACTIVE PROPOSE/COUNTER; you accept the
*other* side's standing offer. Mutual acceptance = an ACTIVE ACCEPT from each
side for the same amount.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from fikisha.negotiation.constants import (
    OFFER_TYPES,
    EntryActorRole,
    EntryStatus,
    EntryType,
    ThreadStatus,
)
from fikisha.negotiation.models import NegotiationEntry, NegotiationThread


def _entries(thread: NegotiationThread) -> list[NegotiationEntry]:
    # `seq`, not `(created_at, id)`: two entries written back-to-back can tie
    # on `created_at`, and `id` (UUIDv7) is only time-ordered at millisecond
    # granularity — neither reliably preserves insertion order under a tie.
    # `seq` is the only strictly-monotonic column. Phase 2D final-verification
    # finding, 2026-09-11.
    return list(thread.entries.all().order_by("seq"))


def _effective_status(
    entry: NegotiationEntry,
    entries: list[NegotiationEntry],
    *,
    now: Any,
    thread_status: str,
) -> str:
    if thread_status != ThreadStatus.ACTIVE:
        return EntryStatus.SUPERSEDED
    if entry.expires_at is not None and entry.expires_at <= now:
        return EntryStatus.EXPIRED

    later = [e for e in entries if e.seq > entry.seq]
    if entry.type in OFFER_TYPES:
        if any(e.type in OFFER_TYPES and e.actor_role == entry.actor_role for e in later):
            return EntryStatus.SUPERSEDED
    elif entry.type == EntryType.ACCEPT:
        if any(e.type in OFFER_TYPES for e in later):
            return EntryStatus.SUPERSEDED
        if any(e.type == EntryType.ACCEPT and e.actor_role == entry.actor_role for e in later):
            return EntryStatus.SUPERSEDED
    return EntryStatus.ACTIVE


def effective_entry_status(
    entry: NegotiationEntry, *, now: Any = None, thread_status: str | None = None
) -> str:
    now = now or timezone.now()
    status = thread_status if thread_status is not None else entry.thread.status
    return _effective_status(entry, _entries(entry.thread), now=now, thread_status=status)


def annotate_entries(thread: NegotiationThread, *, now: Any = None) -> list[dict[str, Any]]:
    now = now or timezone.now()
    entries = _entries(thread)
    out: list[dict[str, Any]] = []
    for e in entries:
        out.append(
            {
                "id": str(e.id),
                "actor_role": e.actor_role,
                "type": e.type,
                "amount_kes": e.amount_kes,
                "note": e.note,
                "in_response_to_id": str(e.in_response_to_id) if e.in_response_to_id else None,
                "created_at": e.created_at.isoformat(),
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                "effective_status": _effective_status(
                    e, entries, now=now, thread_status=thread.status
                ),
            }
        )
    return out


def _active_offers(thread: NegotiationThread, *, now: Any) -> list[NegotiationEntry]:
    entries = _entries(thread)
    return [
        e
        for e in entries
        if e.type in OFFER_TYPES
        and _effective_status(e, entries, now=now, thread_status=thread.status)
        == EntryStatus.ACTIVE
    ]


def side_standing_offer(
    thread: NegotiationThread, *, side: str, now: Any = None
) -> NegotiationEntry | None:
    now = now or timezone.now()
    offers = [e for e in _active_offers(thread, now=now) if e.actor_role == side]
    return offers[-1] if offers else None


def standing_offer(thread: NegotiationThread, *, now: Any = None) -> NegotiationEntry | None:
    """The most recent live figure on the table, from whichever side (display)."""
    now = now or timezone.now()
    offers = _active_offers(thread, now=now)
    return offers[-1] if offers else None


def _other_role(role: str) -> str:
    return EntryActorRole.BUSINESS if role == EntryActorRole.OPERATOR else EntryActorRole.OPERATOR


def counterparty_figure_to_accept(
    thread: NegotiationThread, *, for_role: str, now: Any = None
) -> NegotiationEntry | None:
    """The counterparty's current committed figure that ``for_role`` would accept:
    their latest ACTIVE amount-bearing entry (PROPOSE / COUNTER **or** a pending
    ACCEPT — so the second party can finalise a figure the first already said yes
    to)."""
    now = now or timezone.now()
    other = _other_role(for_role)
    entries = _entries(thread)
    for e in reversed(entries):
        if e.actor_role != other or e.amount_kes is None:
            continue
        if e.type not in OFFER_TYPES and e.type != EntryType.ACCEPT:
            continue
        if (
            _effective_status(e, entries, now=now, thread_status=thread.status)
            == EntryStatus.ACTIVE
        ):
            return e
    return None


def mutual_acceptance(
    thread: NegotiationThread, *, now: Any = None
) -> tuple[bool, int | None, list[str]]:
    """``(reached, amount_kes, [operator_accept_id, business_accept_id])`` —
    an ACTIVE ACCEPT from each side for the same amount."""
    now = now or timezone.now()
    entries = _entries(thread)

    def latest_active_accept(role: str) -> NegotiationEntry | None:
        for e in reversed(entries):
            if e.type != EntryType.ACCEPT or e.actor_role != role:
                continue
            if (
                _effective_status(e, entries, now=now, thread_status=thread.status)
                == EntryStatus.ACTIVE
            ):
                return e
        return None

    op = latest_active_accept(EntryActorRole.OPERATOR)
    biz = latest_active_accept(EntryActorRole.BUSINESS)
    if op and biz and op.amount_kes and op.amount_kes == biz.amount_kes:
        return True, int(op.amount_kes), [str(op.id), str(biz.id)]
    return False, None, []
