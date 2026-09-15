"""The negotiation happy paths (negotiation-architecture.md §3)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.jobs.constants import JobStatus
from fikisha.negotiation import services
from fikisha.negotiation.constants import EntryStatus, ThreadStatus
from fikisha.negotiation.models import NegotiationEntry, NegotiationThread

pytestmark = pytest.mark.django_db


def _by_status(entries: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    return [e for e in entries if e["effective_status"] == status]


def test_operator_engaging_opens_thread_and_seeds_posted_price(
    requested_job: Any, operator_a: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    view = services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=230_000
    )

    assert view["status"] == ThreadStatus.ACTIVE
    assert view["job_status"] == JobStatus.NEGOTIATING  # first operator offer moves the job
    types = [(e["actor_role"], e["type"], e["amount_kes"]) for e in view["entries"]]
    assert types == [
        ("BUSINESS", "PROPOSE", 250_000),  # seeded posted price
        ("OPERATOR", "PROPOSE", 230_000),
    ]
    # the seeded business offer is now superseded by the operator's newer figure
    assert view["standing_offer"] == {
        "entry_id": view["entries"][1]["id"],
        "actor_role": "OPERATOR",
        "amount_kes": 230_000,
    }
    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.NEGOTIATING


def test_entries_stay_correctly_ordered_when_created_at_ties(
    requested_job: Any, operator_a: Any, _actor: Any, monkeypatch: Any
) -> None:
    """Regression for the tiebreak defect found in the Phase 2D final
    verification (2026-09-11): `_entries()` previously ordered by
    `(created_at, id)`, but the seeded business price and the opening operator
    offer are written back-to-back in the same call and can receive an
    identical `auto_now_add` timestamp (measured ~36% under real timing), and
    `id` (UUIDv7) is only time-ordered at millisecond granularity — on a tie,
    the operator's later entry could sort *before* the business's earlier one
    (measured ~18% actual misorder), flipping which offer is "standing".
    `seq` is a strictly-monotonic tiebreaker that never ties."""
    from django.utils import timezone

    frozen = timezone.now()
    monkeypatch.setattr("django.utils.timezone.now", lambda: frozen)

    op = _actor(operator_a.user)
    view = services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=230_000
    )

    thread = NegotiationThread.objects.get(job=requested_job, operator=operator_a)
    entries = list(NegotiationEntry.objects.filter(thread=thread).order_by("seq"))
    assert len(entries) == 2
    assert entries[0].created_at == entries[1].created_at  # the tie was actually forced
    assert entries[0].seq < entries[1].seq

    types = [(e["actor_role"], e["type"], e["amount_kes"]) for e in view["entries"]]
    assert types == [
        ("BUSINESS", "PROPOSE", 250_000),  # seeded posted price, written first
        ("OPERATOR", "PROPOSE", 230_000),  # the opening offer, written second
    ]
    assert view["standing_offer"] == {
        "entry_id": view["entries"][1]["id"],
        "actor_role": "OPERATOR",
        "amount_kes": 230_000,
    }


def test_a_downstream_audit_failure_rolls_back_the_whole_propose_call(
    requested_job: Any, operator_a: Any, _actor: Any, monkeypatch: Any
) -> None:
    """Phase 2D Step 12 (audit/outbox atomicity sweep): ``propose()`` is
    ``@transaction.atomic``, but that was previously true only by inspection.
    Here the thread + seeded business entry are created successfully *before*
    the forced failure (inside the same call) — proving a downstream audit
    failure rolls back not just the entry mid-write, but everything the
    function already committed earlier in its own scope, matching the
    BLOCKER-1 corrective pass's standard for `incidents.services`."""
    from fikisha.negotiation.models import NegotiationEntry, NegotiationThread

    def _boom(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("simulated downstream failure")

    monkeypatch.setattr(services.audit, "record", _boom)
    op = _actor(operator_a.user)
    with pytest.raises(RuntimeError):
        services.propose(
            actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=230_000
        )
    assert NegotiationThread.objects.filter(job=requested_job).count() == 0
    assert NegotiationEntry.objects.filter(job=requested_job).count() == 0
    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.REQUESTED  # unchanged, not NEGOTIATING


def test_operator_accepts_posted_price_then_business_accepts_confirms(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    # open the thread with a matching PROPOSE, then accept the standing business price
    services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=250_000
    )
    thread = NegotiationThread.objects.get(job=requested_job, operator=operator_a)

    op_accept = services.accept(actor=op, thread_id=thread.id)
    assert op_accept["confirmed"] is False  # waiting on the business

    biz_accept = services.accept(
        actor=owner_actor, thread_id=thread.id, idempotency_key="k-confirm"
    )
    assert biz_accept["confirmed"] is True
    assert biz_accept["job"]["status"] == JobStatus.CONFIRMED
    assert biz_accept["job"]["value_band"] == "STANDARD"

    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.CONFIRMED
    assert requested_job.agreement_id is not None
    assert requested_job.agreement.agreed_price_kes == 250_000
    assert requested_job.proposed_price_kes == 250_000
    assert set(requested_job.agreement.accepting_entry_ids) == {
        str(e.id) for e in NegotiationEntry.objects.filter(thread=thread, type="ACCEPT")
    }

    thread.refresh_from_db()
    assert thread.status == ThreadStatus.CLOSED


def test_counter_then_mutual_accept_confirms_at_agreed_price(
    requested_job: Any, operator_a: Any, owner_actor: Any, _actor: Any
) -> None:
    op = _actor(operator_a.user)
    services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=230_000
    )
    thread = NegotiationThread.objects.get(job=requested_job, operator=operator_a)

    services.counter(
        actor=owner_actor, thread_id=thread.id, amount_kes=240_000, note="meet halfway"
    )
    # operator accepts the business's 240k counter
    op_accept = services.accept(actor=op, thread_id=thread.id)
    assert op_accept["confirmed"] is False
    biz_accept = services.accept(actor=owner_actor, thread_id=thread.id)
    assert biz_accept["confirmed"] is True

    requested_job.refresh_from_db()
    assert requested_job.agreement.agreed_price_kes == 240_000


def test_confirming_one_thread_supersedes_the_siblings(
    requested_job: Any, operator_a: Any, operator_b: Any, owner_actor: Any, _actor: Any
) -> None:
    a, b = _actor(operator_a.user), _actor(operator_b.user)
    services.propose(
        actor=a, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=250_000
    )
    services.propose(
        actor=b, job_id=requested_job.id, operator_id=operator_b.id, amount_kes=245_000
    )
    thread_a = NegotiationThread.objects.get(job=requested_job, operator=operator_a)
    thread_b = NegotiationThread.objects.get(job=requested_job, operator=operator_b)

    services.accept(actor=a, thread_id=thread_a.id)
    services.accept(actor=owner_actor, thread_id=thread_a.id)

    thread_a.refresh_from_db()
    thread_b.refresh_from_db()
    assert thread_a.status == ThreadStatus.CLOSED
    assert thread_b.status == ThreadStatus.SUPERSEDED
    # thread B's entries are now all non-ACTIVE by derivation (no row was updated)
    b_view = services.view_thread(actor=b, thread_id=thread_b.id)
    assert _by_status(b_view["entries"], EntryStatus.ACTIVE) == []


def test_negotiation_entries_are_immutable_at_the_database(
    requested_job: Any, operator_a: Any, _actor: Any
) -> None:
    from django.db import DatabaseError, connection, transaction

    op = _actor(operator_a.user)
    services.propose(
        actor=op, job_id=requested_job.id, operator_id=operator_a.id, amount_kes=230_000
    )
    entry = NegotiationEntry.objects.filter(job=requested_job).first()

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE negotiation_entry SET amount_kes = 1 WHERE id = %s", [str(entry.id)]
                )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("DELETE FROM negotiation_entry WHERE id = %s", [str(entry.id)])
