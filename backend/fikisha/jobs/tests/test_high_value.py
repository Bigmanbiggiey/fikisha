"""High-value approval gate + its interaction with assignment
(trust-architecture.md §1, D-TRU-5, Founder Increment-3 condition 6:
assignment must not create a path around high-value approval or verification)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.assignment import assign_job
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import (
    HighValueAlreadyDecided,
    HighValueApprovalRequired,
    NotAHighValueJob,
    NotAuthorisedToAssign,
)
from fikisha.jobs.high_value import decide_high_value
from fikisha.jobs.models import HighValueApproval

pytestmark = pytest.mark.django_db

HIGH = 30_000_000  # KES 300,000 -> HIGH band
VERY_HIGH = 150_000_000  # -> VERY_HIGH band


@pytest.fixture
def actor_of() -> Callable[[Any], Any]:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user


# ─── decide_high_value ────────────────────────────────────────────
def test_decide_rejects_a_non_high_value_job(
    make_confirmed_job: Callable, eligible_driver: Any, admin_actor: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)  # STANDARD
    with pytest.raises(NotAHighValueJob):
        decide_high_value(actor=admin_actor, job_id=job.id, decision="APPROVED", rationale="x")


def test_ops_officer_may_approve_high_but_not_very_high(
    make_confirmed_job: Callable, eligible_driver: Any, ops_officer: Any, actor_of: Callable
) -> None:
    ops = actor_of(ops_officer)
    high_job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    out = decide_high_value(
        actor=ops, job_id=high_job.id, decision="APPROVED", rationale="cover ok"
    )
    assert out["decision"] == "APPROVED"
    assert out["decided_by_is_platform_admin"] is False

    vh_job = make_confirmed_job(operator=eligible_driver, declared_value_kes=VERY_HIGH)
    with pytest.raises(NotAuthorisedToAssign):
        decide_high_value(actor=ops, job_id=vh_job.id, decision="APPROVED", rationale="no")


def test_one_decision_per_job(
    make_confirmed_job: Callable, eligible_driver: Any, admin_actor: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    decide_high_value(actor=admin_actor, job_id=job.id, decision="APPROVED", rationale="a")
    with pytest.raises(HighValueAlreadyDecided):
        decide_high_value(actor=admin_actor, job_id=job.id, decision="REJECTED", rationale="b")


# ─── assignment interaction ───────────────────────────────────────
def test_high_value_job_cannot_be_assigned_without_approval(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    admin_actor: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    with pytest.raises(HighValueApprovalRequired):
        assign_job(
            actor=admin_actor,
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=eligible_vehicle.id,
            admin_override_reason="trusted driver",  # relaxes trust ceiling, NOT high-value
        )
    job.refresh_from_db()
    assert job.status == JobStatus.CONFIRMED


def test_high_value_job_assigns_after_ops_officer_approval_plus_override(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    ops_officer: Any,
    admin_actor: Any,
    actor_of: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    decide_high_value(
        actor=actor_of(ops_officer), job_id=job.id, decision="APPROVED", rationale="ok"
    )
    view = assign_job(
        actor=admin_actor,
        job_id=job.id,
        driver_profile_id=eligible_driver.id,
        vehicle_id=eligible_vehicle.id,
        admin_override_reason="interim trust ceiling override (L1 driver, HIGH band)",
    )
    assert view["status"] == JobStatus.ASSIGNED


def test_very_high_needs_platform_admin_approval_even_with_ops_officer_approval(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    ops_officer: Any,
    platform_admin: Any,
    admin_actor: Any,
    actor_of: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=VERY_HIGH)
    # ops officer cannot even record a VERY_HIGH decision
    with pytest.raises(NotAuthorisedToAssign):
        decide_high_value(
            actor=actor_of(ops_officer), job_id=job.id, decision="APPROVED", rationale="x"
        )
    # a platform-admin approval unblocks it
    decide_high_value(
        actor=actor_of(platform_admin), job_id=job.id, decision="APPROVED", rationale="board ok"
    )
    approval = HighValueApproval.objects.get(job=job)
    assert approval.decided_by_is_platform_admin is True
    view = assign_job(
        actor=admin_actor,
        job_id=job.id,
        driver_profile_id=eligible_driver.id,
        vehicle_id=eligible_vehicle.id,
        admin_override_reason="platform-admin cleared",
    )
    assert view["status"] == JobStatus.ASSIGNED


def test_rejected_high_value_decision_still_blocks_assignment(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    admin_actor: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    decide_high_value(actor=admin_actor, job_id=job.id, decision="REJECTED", rationale="no cover")
    with pytest.raises(HighValueApprovalRequired):
        assign_job(
            actor=admin_actor,
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=eligible_vehicle.id,
            admin_override_reason="x",
        )
