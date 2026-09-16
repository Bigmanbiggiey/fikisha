"""Group-side negotiation: a group MANAGER/OWNER negotiates on the group's
thread; confirmation records the group as the operator party."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.jobs.constants import JobStatus, OperatorParty
from fikisha.negotiation import services
from fikisha.negotiation.errors import NotANegotiationParty
from fikisha.negotiation.models import NegotiationThread

pytestmark = pytest.mark.django_db


@pytest.fixture
def group_with_manager(db: Any, make_operator: Any, _actor: Any) -> Any:
    from fikisha.groups.services import create_group

    manager_profile = make_operator("+254740000001", "G. Manager")
    group = create_group(
        actor=_actor(manager_profile.user), name="Kitengela Yard", type="YARD_OWNER"
    )
    return group, manager_profile


def test_group_manager_negotiates_and_confirms(
    requested_job: Any, group_with_manager: Any, owner_actor: Any, _actor: Any
) -> None:
    group, manager = group_with_manager
    mgr = _actor(manager.user)

    view = services.propose(
        actor=mgr, job_id=requested_job.id, group_id=group.id, amount_kes=240_000
    )
    assert view["operator_display_name"] == "Kitengela Yard"
    thread = NegotiationThread.objects.get(job=requested_job, group=group)
    assert thread.operator_party == OperatorParty.GROUP

    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.NEGOTIATING

    services.accept(actor=owner_actor, thread_id=thread.id)  # business accepts the group's 240k
    out = services.accept(actor=mgr, thread_id=thread.id)  # group manager finalises
    assert out["confirmed"] is True

    requested_job.refresh_from_db()
    assert requested_job.status == JobStatus.CONFIRMED
    assert requested_job.agreement.operator_party == OperatorParty.GROUP
    assert requested_job.agreement.group_id == group.id
    assert requested_job.agreement.operator_id is None


def test_operator_cannot_act_on_a_group_thread(
    requested_job: Any, group_with_manager: Any, operator_a: Any, _actor: Any
) -> None:
    group, _manager = group_with_manager
    services.propose(
        actor=_actor(group_with_manager[1].user),
        job_id=requested_job.id,
        group_id=group.id,
        amount_kes=240_000,
    )
    thread = NegotiationThread.objects.get(job=requested_job, group=group)
    with pytest.raises(NotANegotiationParty):
        services.counter(actor=_actor(operator_a.user), thread_id=thread.id, amount_kes=1_000)


def test_admin_may_read_any_thread(
    requested_job: Any, operator_a: Any, platform_admin: Any, _actor: Any
) -> None:
    services.propose(
        actor=_actor(operator_a.user),
        job_id=requested_job.id,
        operator_id=operator_a.id,
        amount_kes=240_000,
    )
    thread = NegotiationThread.objects.get(job=requested_job, operator=operator_a)
    view = services.view_thread(actor=_actor(platform_admin), thread_id=thread.id)
    assert view["thread_id"] == str(thread.id)
    assert len(services.list_threads(actor=_actor(platform_admin), job_id=requested_job.id)) == 1
