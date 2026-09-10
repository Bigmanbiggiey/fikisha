"""Sealed-thread read scoping + party authorization (ADR-006, FR-N-3, NFR-PRIV-6)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.negotiation import services
from fikisha.negotiation.errors import NotANegotiationParty
from fikisha.negotiation.models import NegotiationThread

pytestmark = pytest.mark.django_db


def _thread_for(job: Any, operator: Any, actor_factory: Any) -> Any:
    services.propose(
        actor=actor_factory(operator.user),
        job_id=job.id,
        operator_id=operator.id,
        amount_kes=240_000,
    )
    return NegotiationThread.objects.get(job=job, operator=operator)


def test_operator_cannot_read_a_rival_operators_thread(
    requested_job: Any, operator_a: Any, operator_b: Any, _actor: Any
) -> None:
    thread_a = _thread_for(requested_job, operator_a, _actor)
    b = _actor(operator_b.user)

    with pytest.raises(NotANegotiationParty):
        services.view_thread(actor=b, thread_id=thread_a.id)

    # and the list endpoint never leaks a rival thread's existence
    assert services.list_threads(actor=b, job_id=requested_job.id) == []


def test_business_sees_every_thread_on_its_job(
    requested_job: Any, operator_a: Any, operator_b: Any, owner_actor: Any, _actor: Any
) -> None:
    _thread_for(requested_job, operator_a, _actor)
    _thread_for(requested_job, operator_b, _actor)
    threads = services.list_threads(actor=owner_actor, job_id=requested_job.id)
    assert len(threads) == 2


def test_operator_sees_only_its_own_thread(
    requested_job: Any, operator_a: Any, operator_b: Any, _actor: Any
) -> None:
    _thread_for(requested_job, operator_a, _actor)
    _thread_for(requested_job, operator_b, _actor)
    a_threads = services.list_threads(actor=_actor(operator_a.user), job_id=requested_job.id)
    assert len(a_threads) == 1
    assert a_threads[0]["operator_id"] == str(operator_a.id)


def test_business_viewer_cannot_negotiate(
    requested_job: Any, operator_a: Any, make_user: Any, _actor: Any
) -> None:
    from fikisha.business.models import BusinessMembership, BusinessRole, MembershipStatus

    viewer = make_user("+254721000009")
    BusinessMembership.objects.create(
        business=requested_job.business,
        user=viewer,
        role=BusinessRole.VIEWER,
        status=MembershipStatus.ACTIVE,
    )
    thread = _thread_for(requested_job, operator_a, _actor)
    with pytest.raises(NotANegotiationParty):
        services.counter(actor=_actor(viewer), thread_id=thread.id, amount_kes=200_000)


def test_stranger_is_not_a_party(
    requested_job: Any, operator_a: Any, other_user: Any, _actor: Any
) -> None:
    thread = _thread_for(requested_job, operator_a, _actor)
    with pytest.raises(NotANegotiationParty):
        services.view_thread(actor=_actor(other_user), thread_id=thread.id)
    with pytest.raises(NotANegotiationParty):
        services.counter(actor=_actor(other_user), thread_id=thread.id, amount_kes=1)


def test_operator_from_another_thread_cannot_act_on_this_one(
    requested_job: Any, operator_a: Any, operator_b: Any, _actor: Any
) -> None:
    thread_a = _thread_for(requested_job, operator_a, _actor)
    _thread_for(requested_job, operator_b, _actor)
    with pytest.raises(NotANegotiationParty):
        services.counter(actor=_actor(operator_b.user), thread_id=thread_a.id, amount_kes=1_000)
