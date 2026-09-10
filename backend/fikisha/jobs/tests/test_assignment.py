"""Assignment (``CONFIRMED -> ASSIGNED``) — eligibility against the specific
assigned driver + vehicle (plan §9, Founder Increment-3 conditions)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.assignment import assign_job
from fikisha.jobs.constants import AssignedBy, JobStatus
from fikisha.jobs.errors import (
    DriverNotEligible,
    GuardFailed,
    NotAuthorisedToAssign,
    VehicleNotEligible,
)
from fikisha.jobs.models import Assignment, JobEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def operator_actor() -> Callable[[Any], Any]:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user


# ─── solo operator ─────────────────────────────────────────────────
def test_operator_self_assigns_happy_path(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    operator_actor: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    view = assign_job(
        actor=operator_actor(eligible_driver.user),
        job_id=job.id,
        driver_profile_id=eligible_driver.id,
        vehicle_id=eligible_vehicle.id,
    )
    assert view["status"] == JobStatus.ASSIGNED
    assignment = Assignment.objects.get(job=job)
    assert assignment.assigned_driver_profile_id == eligible_driver.id
    assert assignment.vehicle_id == eligible_vehicle.id
    assert assignment.assigned_by == AssignedBy.SELF
    assert assignment.driver_trust_level == "L1"
    assert JobEvent.objects.filter(job=job, is_custody=True, type="OPERATOR_ASSIGNED").exists()


def test_a_stranger_cannot_assign(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    make_user: Any,
    operator_actor: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    with pytest.raises(NotAuthorisedToAssign):
        assign_job(
            actor=operator_actor(make_user("+254799111000")),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=eligible_vehicle.id,
        )
    job.refresh_from_db()
    assert job.status == JobStatus.CONFIRMED


def test_requester_may_not_be_the_driver(
    db: Any,
    make_confirmed_job: Callable,
    make_vehicle: Callable,
    verify_subject: Callable,
    verified_business: Any,
    operator_actor: Callable,
) -> None:
    # the business owner (job requester) IS the operator -> requester == provider
    owner = verified_business.owner_user
    from fikisha.operators.models import OperatorProfile, OperatorStatus

    prof = OperatorProfile.objects.create(
        user=owner, full_name="Owner Driver", status=OperatorStatus.ACTIVE
    )
    verify_subject(prof, "IDENTITY", "LICENCE", "GOOD_CONDUCT")
    vehicle = make_vehicle(owner_operator=prof, registration="KDA 900Z")
    job = make_confirmed_job(operator=prof)
    with pytest.raises(GuardFailed):  # RequesterIsNotProvider
        assign_job(
            actor=operator_actor(owner),
            job_id=job.id,
            driver_profile_id=prof.id,
            vehicle_id=vehicle.id,
        )


# ─── vehicle eligibility ──────────────────────────────────────────
def test_vehicle_must_be_controlled_by_the_confirmed_party(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    make_verified_operator: Callable,
    make_vehicle: Callable,
    operator_actor: Callable,
) -> None:
    other = make_verified_operator("+254733200099", "Other Op")
    someone_elses_vehicle = make_vehicle(owner_operator=other, registration="KDA 111X")
    job = make_confirmed_job(operator=eligible_driver)
    with pytest.raises(VehicleNotEligible):
        assign_job(
            actor=operator_actor(eligible_driver.user),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=someone_elses_vehicle.id,
        )


def test_inactive_vehicle_rejected(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    make_vehicle: Callable,
    operator_actor: Callable,
) -> None:
    from fikisha.vehicles.models import VehicleStatus

    v = make_vehicle(
        owner_operator=eligible_driver, registration="KDA 222Y", status=VehicleStatus.UNDER_REPAIR
    )
    job = make_confirmed_job(operator=eligible_driver)
    with pytest.raises(VehicleNotEligible):
        assign_job(
            actor=operator_actor(eligible_driver.user),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=v.id,
        )


def test_vehicle_capacity_below_requirement_rejected(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    make_vehicle: Callable,
    operator_actor: Callable,
) -> None:
    small = make_vehicle(
        owner_operator=eligible_driver, registration="KDA 333Z", capacity_value=100
    )
    job = make_confirmed_job(operator=eligible_driver, min_payload_kg=1000)
    with pytest.raises(VehicleNotEligible):
        assign_job(
            actor=operator_actor(eligible_driver.user),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=small.id,
        )


def test_heavy_vehicle_needs_heavy_class_compliance(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    make_vehicle: Callable,
    operator_actor: Callable,
) -> None:
    heavy_unverified = make_vehicle(
        owner_operator=eligible_driver, registration="KDB 444H", heavy=True, verified=False
    )
    # give it VEHICLE + ASSOCIATION but NOT HEAVY_CLASS_COMPLIANCE
    from fikisha.verification.models import State, VerificationRecord

    for d in ("VEHICLE", "ASSOCIATION"):
        VerificationRecord.objects.create(
            subject_type="VEHICLE", subject_vehicle=heavy_unverified, domain=d, state=State.VERIFIED
        )
    job = make_confirmed_job(operator=eligible_driver)
    with pytest.raises(VehicleNotEligible):
        assign_job(
            actor=operator_actor(eligible_driver.user),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=heavy_unverified.id,
        )


# ─── driver verification ──────────────────────────────────────────
def test_driver_missing_good_conduct_rejected(
    make_confirmed_job: Callable,
    make_verified_operator: Callable,
    make_vehicle: Callable,
    verify_subject: Callable,
    operator_actor: Callable,
) -> None:
    driver = make_verified_operator("+254733200055", "Half Verified", verified=False)
    verify_subject(driver, "IDENTITY", "LICENCE")  # no GOOD_CONDUCT
    vehicle = make_vehicle(owner_operator=driver, registration="KDA 555V")
    job = make_confirmed_job(operator=driver)
    with pytest.raises(DriverNotEligible):
        assign_job(
            actor=operator_actor(driver.user),
            job_id=job.id,
            driver_profile_id=driver.id,
            vehicle_id=vehicle.id,
        )


def test_group_membership_does_not_substitute_for_driver_verification(
    db: Any,
    make_confirmed_job: Callable,
    make_verified_operator: Callable,
    make_vehicle: Callable,
    make_user: Any,
    operator_actor: Callable,
) -> None:
    from fikisha.groups.models import (
        AssignmentMode,
        GroupMemberRole,
        GroupMembership,
        GroupMembershipStatus,
    )
    from fikisha.groups.services import create_group

    manager = make_verified_operator("+254744300001", "Mgr")
    group = create_group(
        actor=operator_actor(manager.user),
        name="Yard",
        type="YARD_OWNER",
        assignment_mode=AssignmentMode.MANAGER_ASSIGNS,
    )
    unverified_driver = make_verified_operator("+254744300002", "Unverified", verified=False)
    GroupMembership.objects.create(
        group=group,
        operator=unverified_driver,
        role=GroupMemberRole.DRIVER,
        status=GroupMembershipStatus.ACTIVE,
    )
    gv = make_vehicle(owner_group=group, owner_operator=None, registration="KDA 700G")
    job = make_confirmed_job(group=group)
    with pytest.raises(DriverNotEligible):  # member, but not verified
        assign_job(
            actor=operator_actor(manager.user),
            job_id=job.id,
            driver_profile_id=unverified_driver.id,
            vehicle_id=gv.id,
        )
