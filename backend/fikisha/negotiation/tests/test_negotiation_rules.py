"""Negotiation edge cases + invariants (FR-N-6..N-8, D-NEG-3/4)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.jobs.constants import JobStatus
from fikisha.negotiation import services
from fikisha.negotiation.constants import EntryStatus, EntryType, ThreadStatus
from fikisha.negotiation.errors import (
    InvalidOffer,
    JobNotOpenForNegotiation,
    NothingToAccept,
    NoThreadYet,
    ThreadNotActive,
)
from fikisha.negotiation.models import NegotiationEntry, NegotiationThread
from fikisha.negotiation.selectors import effective_entry_status, mutual_acceptance

pytestmark = pytest.mark.django_db


def _open_thread(job: Any, operator: Any, actor_factory: Any, amount: int = 240_000) -> Any:
    services.propose(
        actor=actor_factory(operator.user),
        job_id=job.id,
        operator_id=operator.id,
        amount_kes=amount,
    )
    return NegotiationThread.objects.get(job=job, operator=operator)


def test_amount_must_be_a_positive_integer(
    requested_job: Any, operator_a: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    for bad in (0, -5, 1.5, "100", True):
        with pytest.raises(InvalidOffer):
            services.propose(
                actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=bad
            )


def test_platform_never_rejects_a_price_but_warns_on_a_tenfold_mistype(
    requested_job: Any, operator_a: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=240_000
    )
    thread = NegotiationThread.objects.get(job=requested_job, operator=operator_a)
    out = services.counter(actor=op, thread_id=thread.id, amount_kes=2_400_000)  # 10x
    assert "warning" in out
    assert out["entries"][-1]["amount_kes"] == 2_400_000  # accepted, not rejected


def test_business_cannot_cold_open_a_thread(requested_job: Any, owner_actor: Any) -> None:
    with pytest.raises(NoThreadYet):
        services.propose(
            actor=owner_actor,
            job_id=requested_job.id,
            operator_id=None,
            group_id=None,
            amount_kes=200_000,
        )


def test_expired_offer_cannot_be_accepted(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any, monkeypatch: Any
) -> None:
    thread = _open_thread(requested_job, operator_a, _actor)
    for e in NegotiationEntry.objects.filter(
        thread=thread, type__in=[EntryType.PROPOSE, EntryType.COUNTER]
    ):
        assert e.expires_at is not None

    # advance the clock past every offer's expiry (house style: inject `now`)
    future = timezone.now() + timedelta(hours=999)
    monkeypatch.setattr("django.utils.timezone.now", lambda: future)

    for e in NegotiationEntry.objects.filter(
        thread=thread, type__in=[EntryType.PROPOSE, EntryType.COUNTER]
    ):
        assert effective_entry_status(e, thread_status=thread.status) == EntryStatus.EXPIRED
    with pytest.raises(NothingToAccept):
        services.accept(actor=owner_actor, thread_id=thread.id)


def test_accept_amount_must_match_the_standing_offer(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    thread = _open_thread(requested_job, operator_a, _actor, amount=240_000)
    with pytest.raises(InvalidOffer):
        services.accept(actor=owner_actor, thread_id=thread.id, amount_kes=999_999)


def test_racing_confirms_first_wins_second_gets_conflict(
    requested_job: Any, operator_a: Any, operator_b: Any, owner_actor: Any, _actor: Any
) -> None:
    a, b = _actor(operator_a.user), _actor(operator_b.user)
    ta = _open_thread(requested_job, operator_a, _actor, amount=250_000)
    tb = _open_thread(requested_job, operator_b, _actor, amount=250_000)

    services.accept(actor=a, thread_id=ta.id)
    services.accept(actor=owner_actor, thread_id=ta.id)  # job now CONFIRMED

    # thread B was superseded by the confirm; no further action can land on it
    with pytest.raises((ThreadNotActive, JobNotOpenForNegotiation)):
        services.accept(actor=b, thread_id=tb.id)
    with pytest.raises((ThreadNotActive, JobNotOpenForNegotiation)):
        services.counter(actor=owner_actor, thread_id=tb.id, amount_kes=200_000)

    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.CONFIRMED
    assert requested_job.agreement.operator_id == operator_a.id


def test_decline_closes_the_thread_and_leaves_the_job_open(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    thread = _open_thread(requested_job, operator_a, _actor)
    services.decline(actor=owner_actor, thread_id=thread.id, note="not this time")
    thread.refresh_from_db()
    assert thread.status == ThreadStatus.CLOSED
    assert NegotiationEntry.objects.filter(thread=thread, type=EntryType.REJECT).exists()

    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.NEGOTIATING  # still open for other operators

    with pytest.raises(ThreadNotActive):
        services.counter(actor=owner_actor, thread_id=thread.id, amount_kes=100_000)


def test_accept_is_idempotent_on_replay(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    thread = _open_thread(requested_job, operator_a, _actor, amount=250_000)
    services.accept(actor=op, thread_id=thread.id)

    first = services.accept(actor=owner_actor, thread_id=thread.id, idempotency_key="k1")
    accepts_after_first = NegotiationEntry.objects.filter(
        thread=thread, type=EntryType.ACCEPT
    ).count()
    second = services.accept(actor=owner_actor, thread_id=thread.id, idempotency_key="k1")

    assert first["job"]["version"] == second["job"]["version"]
    assert (
        NegotiationEntry.objects.filter(thread=thread, type=EntryType.ACCEPT).count()
        == accepts_after_first
    )
    requested_job.refresh_from_db()
    assert requested_job.agreement.agreed_price_kes == 250_000


def test_mutual_acceptance_is_invalidated_by_a_later_counter(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    thread = _open_thread(requested_job, operator_a, _actor, amount=250_000)
    services.accept(actor=op, thread_id=thread.id)  # operator accepts 250k
    # business counters instead of accepting — operator's ACCEPT is now stale
    services.counter(actor=owner_actor, thread_id=thread.id, amount_kes=240_000)
    reached, _amount, _ids = mutual_acceptance(thread)
    assert reached is False
