"""Fixtures for the commission statements tests (Commission & Statements S-1).
Re-exports the jobs fixtures (see admin_console/tests/conftest.py), freezes
the clock to a fixed week, and builds completed solo and group jobs through
the real custody flow."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from freezegun import freeze_time

from fikisha.jobs.tests.conftest import (  # noqa: F401 - re-exported fixtures
    actor_for,
    admin_actor,
    business_actor,
    complete_job,
    delivered_job,
    do_transition,
    draft_job,
    driver_actor,
    eligible_driver,
    eligible_vehicle,
    make_assigned_job,
    make_confirmed_job,
    make_vehicle,
    make_verified_operator,
    verified_business,
    verify_subject,
)

#: Wednesday 2026-10-14 10:00 EAT. Last finished week: Mon 5 to Sun 11 Oct,
#: which ends at Mon 12 Oct 00:00 EAT.
NOW = "2026-10-14T07:00:00+00:00"
LAST_WEEK = date(2026, 10, 5)
WEEK_BEFORE = date(2026, 9, 28)


@pytest.fixture(autouse=True)
def frozen() -> Iterator[Any]:
    with freeze_time(NOW, tick=True) as clock:
        yield clock


@pytest.fixture(autouse=True)
def operator_side_only(request: Any) -> None:
    """Most tests here check the billing mechanics on the operator side, so
    the business rate is 0 and each job makes one record. A test that asks
    for ``both_sides`` keeps the real split (ADR-2D-55). Set before any job
    is agreed, since the rates are fixed on the agreement."""
    if "both_sides" in request.fixturenames:
        return
    from fikisha.platform_config import services as config

    config.apply_change(
        patch={"commission": {"business_rate": 0}},
        changed_by=None,
        rationale="test: operator side only",
    )


@pytest.fixture
def both_sides() -> None:
    """Ask for this to keep the 5% + 5% split (see ``operator_side_only``)."""


@pytest.fixture
def stepped_up_admin(admin_actor: Any) -> Any:  # noqa: F811
    return dataclasses.replace(admin_actor, is_step_up_fresh=True)


def age_completion(job: Any, *, before: date, days: float = 4) -> None:
    """Move ``completed_at`` to ``days`` before the end of the week starting
    ``before``, so its dispute window has (or hasn't) closed by then. Test
    setup only; ``Job`` timestamps are not append-only."""
    from fikisha.jobs.models import Job
    from fikisha.statements.services import period_bounds

    _, _, as_of = period_bounds(before)
    Job.objects.filter(id=job.id).update(completed_at=as_of - timedelta(days=days))


@pytest.fixture
def completed_solo_job(delivered_job: Callable, complete_job: Callable) -> Callable[..., Any]:  # noqa: F811
    """A COMPLETED job for ``eligible_driver`` whose window closed before the
    end of ``LAST_WEEK`` (pass ``days`` < 3 for one still inside it)."""

    def _make(*, before: date = LAST_WEEK, days: float = 4) -> Any:
        job = delivered_job()
        complete_job(job)
        age_completion(job, before=before, days=days)
        job.refresh_from_db()
        return job

    return _make


@pytest.fixture
def group_setup(
    make_verified_operator: Callable,  # noqa: F811
    make_vehicle: Callable,  # noqa: F811
    actor_for: Callable,  # noqa: F811
) -> dict[str, Any]:
    from fikisha.groups.models import GroupMemberRole, GroupMembership, GroupMembershipStatus
    from fikisha.groups.services import create_group

    manager = make_verified_operator("+254745100001", "Grace Manager")
    group = create_group(actor=actor_for(manager.user), name="Isinya Yard", type="YARD_OWNER")
    member = make_verified_operator("+254745100002", "Brian Driver")
    GroupMembership.objects.create(
        group=group,
        operator=member,
        role=GroupMemberRole.DRIVER,
        status=GroupMembershipStatus.ACTIVE,
    )
    vehicle = make_vehicle(owner_group=group, owner_operator=None, registration="KDB 700G")
    return {"group": group, "manager": manager, "member": member, "vehicle": vehicle}


@pytest.fixture
def completed_group_job(
    group_setup: dict[str, Any],
    make_confirmed_job: Callable,  # noqa: F811
    actor_for: Callable,  # noqa: F811
    complete_job: Callable,  # noqa: F811
) -> Callable[..., Any]:
    from fikisha.jobs import custody
    from fikisha.jobs.assignment import assign_job

    def _make(*, before: date = LAST_WEEK, days: float = 4) -> Any:
        s = group_setup
        job = make_confirmed_job(group=s["group"])
        # the pickup / delivery codes go to these contacts (as make_assigned_job)
        job.pickup_location.contact_phone = "+254700900101"
        job.pickup_location.save(update_fields=["contact_phone"])
        job.recipient_phone = "+254700900102"
        job.save(update_fields=["recipient_phone"])
        assign_job(
            actor=actor_for(s["manager"].user),
            job_id=job.id,
            driver_profile_id=s["member"].id,
            vehicle_id=s["vehicle"].id,
        )
        driver = actor_for(s["member"].user)
        custody.arrive_at_pickup(actor=driver, job_id=job.id)
        custody.confirm_pickup(
            actor=driver, job_id=job.id, code="000000", photo_evidence_ids=["ev-goods"]
        )
        custody.start_transit(actor=driver, job_id=job.id)
        custody.arrive_at_destination(actor=driver, job_id=job.id)
        custody.confirm_delivery(
            actor=driver,
            job_id=job.id,
            party_name="R. Recipient",
            code="000000",
            photo_evidence_ids=["ev-1"],
        )
        job.refresh_from_db()
        complete_job(job)
        age_completion(job, before=before, days=days)
        job.refresh_from_db()
        return job

    return _make
