"""Group assignment: MANAGER_ASSIGNS vs DRIVER_ACCEPTS, membership, standing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.assignment import assign_job
from fikisha.jobs.constants import AssignedBy, JobStatus
from fikisha.jobs.errors import DriverNotEligible, NotAuthorisedToAssign
from fikisha.jobs.models import Assignment

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor_of() -> Callable[[Any], Any]:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user


@pytest.fixture
def group_setup(
    db: Any, make_verified_operator: Callable, make_vehicle: Callable, actor_of: Callable
) -> Callable[..., Any]:
    from fikisha.groups.models import (
        AssignmentMode,
        GroupMemberRole,
        GroupMembership,
        GroupMembershipStatus,
        GroupStanding,
    )
    from fikisha.groups.services import create_group

    def _make(
        *, mode: str = AssignmentMode.MANAGER_ASSIGNS, standing: str = GroupStanding.GOOD
    ) -> Any:
        manager = make_verified_operator("+254745000001", "Manager")
        group = create_group(
            actor=actor_of(manager.user),
            name="Kitengela Yard",
            type="YARD_OWNER",
            assignment_mode=mode,
        )
        if standing != GroupStanding.GOOD:
            group.standing = standing
            group.save(update_fields=["standing"])
        member = make_verified_operator("+254745000002", "Member Driver")
        GroupMembership.objects.create(
            group=group,
            operator=member,
            role=GroupMemberRole.DRIVER,
            status=GroupMembershipStatus.ACTIVE,
        )
        vehicle = make_vehicle(owner_group=group, owner_operator=None, registration="KDA 800G")
        return {"group": group, "manager": manager, "member": member, "vehicle": vehicle}

    return _make


def test_manager_assigns_a_member_driver(
    group_setup: Callable, make_confirmed_job: Callable, actor_of: Callable
) -> None:
    s = group_setup()
    job = make_confirmed_job(group=s["group"])
    view = assign_job(
        actor=actor_of(s["manager"].user),
        job_id=job.id,
        driver_profile_id=s["member"].id,
        vehicle_id=s["vehicle"].id,
    )
    assert view["status"] == JobStatus.ASSIGNED
    a = Assignment.objects.get(job=job)
    assert a.group_id == s["group"].id
    assert a.assigned_driver_profile_id == s["member"].id
    assert a.assigned_by == AssignedBy.GROUP_MANAGER


def test_manager_assigns_mode_blocks_driver_self_assign(
    group_setup: Callable, make_confirmed_job: Callable, actor_of: Callable
) -> None:
    s = group_setup()  # MANAGER_ASSIGNS
    job = make_confirmed_job(group=s["group"])
    with pytest.raises(NotAuthorisedToAssign):
        assign_job(
            actor=actor_of(s["member"].user),
            job_id=job.id,
            driver_profile_id=s["member"].id,
            vehicle_id=s["vehicle"].id,
        )


def test_driver_accepts_mode_allows_self_assign(
    group_setup: Callable, make_confirmed_job: Callable, actor_of: Callable
) -> None:
    from fikisha.groups.models import AssignmentMode

    s = group_setup(mode=AssignmentMode.DRIVER_ACCEPTS)
    job = make_confirmed_job(group=s["group"])
    view = assign_job(
        actor=actor_of(s["member"].user),
        job_id=job.id,
        driver_profile_id=s["member"].id,
        vehicle_id=s["vehicle"].id,
    )
    assert view["status"] == JobStatus.ASSIGNED
    assert Assignment.objects.get(job=job).assigned_by == AssignedBy.SELF


def test_non_member_driver_rejected(
    group_setup: Callable,
    make_confirmed_job: Callable,
    make_verified_operator: Callable,
    actor_of: Callable,
) -> None:
    s = group_setup()
    outsider = make_verified_operator("+254745000099", "Outsider")
    job = make_confirmed_job(group=s["group"])
    with pytest.raises(DriverNotEligible):
        assign_job(
            actor=actor_of(s["manager"].user),
            job_id=job.id,
            driver_profile_id=outsider.id,
            vehicle_id=s["vehicle"].id,
        )


def test_a_driver_role_member_cannot_assign_a_fellow_member(
    group_setup: Callable,
    make_verified_operator: Callable,
    make_confirmed_job: Callable,
    make_vehicle: Callable,
    actor_of: Callable,
) -> None:
    """Regression for the Phase 2D final-verification report's N-3 coverage
    gap: no test proved a DRIVER-role member cannot exercise manager
    authority over the group's assignment, as distinct from self-assign
    being blocked by mode (already covered above). ``DRIVER_ACCEPTS`` is
    used here specifically so the mode-gate can't be the reason this fails —
    isolating `groups.authz.can_manage()` (membership in {OWNER, MANAGER})
    as the actual thing under test: a DRIVER trying to assign *someone else*
    always falls through to the "cannot self-assign for another" branch."""
    from fikisha.groups.models import (
        AssignmentMode,
        GroupMemberRole,
        GroupMembership,
        GroupMembershipStatus,
    )

    s = group_setup(mode=AssignmentMode.DRIVER_ACCEPTS)
    other_driver = make_verified_operator("+254745000003", "Second Driver")
    GroupMembership.objects.create(
        group=s["group"],
        operator=other_driver,
        role=GroupMemberRole.DRIVER,
        status=GroupMembershipStatus.ACTIVE,
    )
    other_vehicle = make_vehicle(
        owner_group=s["group"], owner_operator=None, registration="KDA 801G"
    )
    job = make_confirmed_job(group=s["group"])
    with pytest.raises(NotAuthorisedToAssign):
        assign_job(
            actor=actor_of(s["member"].user),  # the first DRIVER, not a manager
            job_id=job.id,
            driver_profile_id=other_driver.id,  # assigning a fellow member, not self
            vehicle_id=other_vehicle.id,
        )


def test_suspended_group_cannot_be_assigned(
    group_setup: Callable, make_confirmed_job: Callable, actor_of: Callable
) -> None:
    from fikisha.groups.models import GroupStanding

    # Suspended after the agreement: a group that is already suspended can't
    # reach one (OperatorEligibleForJob refuses it, Increment 9 ADR-2D-38).
    s = group_setup()
    job = make_confirmed_job(group=s["group"])
    s["group"].standing = GroupStanding.SUSPENDED
    s["group"].save(update_fields=["standing"])
    with pytest.raises(DriverNotEligible):
        assign_job(
            actor=actor_of(s["manager"].user),
            job_id=job.id,
            driver_profile_id=s["member"].id,
            vehicle_id=s["vehicle"].id,
        )


# ─── Group Manager assigns from the driver pool (founder decision 2026-10-14) ──
def _candidates(client: Any, job: Any) -> Any:
    return client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")


def test_manager_sees_the_group_pool_and_assigns_from_it(
    group_setup: Callable,
    make_confirmed_job: Callable,
    make_vehicle: Callable,
    client_for: Callable,
) -> None:
    s = group_setup()
    # a member's own vehicle is not the group's, so it isn't offered
    make_vehicle(owner_operator=s["member"], registration="KDA 900P")
    job = make_confirmed_job(group=s["group"])
    client = client_for(s["manager"].user)

    r = _candidates(client, job)
    assert r.status_code == 200, r.content
    assert r.data["supports_group_assignment"] is True
    assert r.data["assignment_mode"] == "MANAGER_ASSIGNS"
    drivers = {d["id"]: d for d in r.data["drivers"]}
    assert set(drivers) == {str(s["manager"].id), str(s["member"].id)}
    assert drivers[str(s["member"].id)]["group_role"] == "DRIVER"
    assert drivers[str(s["member"].id)]["eligible"] is True
    assert [v["registration"] for v in r.data["vehicles"]] == ["KDA 800G"]
    assert r.data["vehicles"][0]["eligible"] is True

    r = client.post(
        f"/api/v1/jobs/{job.id}/assign",
        {"driver_profile_id": str(s["member"].id), "vehicle_id": str(s["vehicle"].id)},
        format="json",
        HTTP_IDEMPOTENCY_KEY="group-assign-1",
    )
    assert r.status_code == 200, r.content
    job.refresh_from_db()
    assert job.status == JobStatus.ASSIGNED
    assert str(job.assignment.assigned_driver_profile_id) == str(s["member"].id)


def test_a_member_cannot_see_the_pool_when_the_manager_assigns(
    group_setup: Callable, make_confirmed_job: Callable, client_for: Callable
) -> None:
    s = group_setup()
    job = make_confirmed_job(group=s["group"])
    r = _candidates(client_for(s["member"].user), job)
    assert r.status_code in (403, 422), r.content


def test_in_driver_accepts_mode_a_member_sees_only_themselves(
    group_setup: Callable, make_confirmed_job: Callable, client_for: Callable
) -> None:
    from fikisha.groups.models import AssignmentMode

    s = group_setup(mode=AssignmentMode.DRIVER_ACCEPTS)
    job = make_confirmed_job(group=s["group"])
    r = _candidates(client_for(s["member"].user), job)
    assert r.status_code == 200, r.content
    assert [d["id"] for d in r.data["drivers"]] == [str(s["member"].id)]
    assert r.data["assignment_mode"] == "DRIVER_ACCEPTS"


def test_an_outsider_cannot_see_a_group_pool(
    group_setup: Callable,
    make_confirmed_job: Callable,
    make_verified_operator: Callable,
    client_for: Callable,
) -> None:
    s = group_setup()
    job = make_confirmed_job(group=s["group"])
    outsider = make_verified_operator("+254745000099", "Outsider")
    r = _candidates(client_for(outsider.user), job)
    assert r.status_code in (403, 404, 422), r.content
    assert "drivers" not in (r.data or {})


def test_a_suspended_groups_pool_is_shown_but_not_eligible(
    group_setup: Callable, make_confirmed_job: Callable, client_for: Callable
) -> None:
    from fikisha.groups.models import GroupStanding

    s = group_setup()
    job = make_confirmed_job(group=s["group"])
    s["group"].standing = GroupStanding.SUSPENDED
    s["group"].save(update_fields=["standing"])
    r = _candidates(client_for(s["manager"].user), job)
    assert r.status_code == 200, r.content
    assert r.data["drivers"]
    assert all(not d["eligible"] for d in r.data["drivers"])
    assert all(any("suspended" in reason for reason in d["reasons"]) for d in r.data["drivers"])
