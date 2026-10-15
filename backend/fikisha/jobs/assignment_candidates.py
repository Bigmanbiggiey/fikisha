"""Read-only assignment-candidate preview (plan §9.2) — Design Phase 6
Increment 4.

A solo operator's pool is themselves and their own vehicles. A group job's
pool is the group's active members and the group's vehicles, for its manager
(or staff); in a ``DRIVER_ACCEPTS`` group a member sees only themselves
(founder decision 2026-10-14, item 19; it was deferred on 2026-09-21).

Reuses the exact reason-producing predicates the ``CONFIRMED -> ASSIGNED``
transition's guards enforce (``jobs.guards._driver_verification_reasons``,
``_driver_trust_reasons``, ``_vehicle_reasons``) so this preview can never
drift from what the server will actually accept when ``assign_job()`` is
called — the UI mirrors server-side authorization, it does not duplicate the
rule (CLAUDE.md §4 "Trust, verification, value bands").
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs import guards, job_authz
from fikisha.jobs.constants import (
    HIGH_VALUE_BANDS,
    HighValueDecision,
    JobStatus,
    OperatorParty,
    ValueBand,
)
from fikisha.jobs.errors import JobNoLongerAvailable, NotAuthorisedToAssign
from fikisha.jobs.selectors import get_job
from fikisha.operators import authz as operators_authz
from fikisha.vehicles.services import vehicles_for_operator


def _high_value_blocked(job: Any) -> str | None:
    if job.value_band not in HIGH_VALUE_BANDS:
        return None
    from fikisha.jobs.high_value import effective_decision

    decision, by_platform_admin = effective_decision(job)
    if decision != HighValueDecision.APPROVED:
        return "This job requires Fikisha's high-value review before it can be assigned."
    if job.value_band == ValueBand.VERY_HIGH and not by_platform_admin:
        return "Very-high-value jobs require Platform Admin approval before assignment."
    return None


def candidates(*, actor: Any, job_id: Any) -> dict[str, Any]:
    job = get_job(job_id)
    if job.status != JobStatus.CONFIRMED:
        raise JobNoLongerAvailable("Only a confirmed job can be assigned.")
    agreement = job.agreement
    if agreement is None:  # pragma: no cover - a CONFIRMED job always has one
        raise JobNoLongerAvailable("The confirmed job has no agreement.")

    if agreement.operator_party != OperatorParty.OPERATOR:
        return _group_candidates(actor, job, agreement)

    if not (
        job_authz.is_admin(actor)
        or operators_authz.owns_profile(actor, {"operator_id": str(agreement.operator_id)})
    ):
        raise NotAuthorisedToAssign("Only the confirmed operator may assign this job.")

    driver = agreement.operator
    if driver is None:  # pragma: no cover - an OPERATOR-party agreement always has one
        raise JobNoLongerAvailable("The confirmed job has no operator.")
    return {
        "job_id": str(job.id),
        "value_band": job.value_band,
        "supports_group_assignment": False,
        "blocked": _high_value_blocked(job),
        "drivers": [_driver_row(driver, job)],
        "vehicles": [
            _vehicle_row(v, job, operator_id=agreement.operator_id)
            for v in vehicles_for_operator(driver)
        ],
    }


def _driver_row(driver: Any, job: Any, *, role: str | None = None) -> dict[str, Any]:
    verification_reasons = guards._driver_verification_reasons(driver)
    level, trust_reasons = guards._driver_trust_reasons(driver, job)
    reasons = verification_reasons + trust_reasons
    row = {
        "id": str(driver.id),
        "name": driver.display_name or driver.full_name,
        "trust_level": level,
        "eligible": not reasons,
        "reasons": reasons,
    }
    if role is not None:
        row["group_role"] = role
    return row


def _vehicle_row(vehicle: Any, job: Any, **owner: Any) -> dict[str, Any]:
    reasons = guards._vehicle_reasons(vehicle, job, **owner)
    return {
        "id": str(vehicle.id),
        "registration": vehicle.registration,
        "vehicle_class": getattr(vehicle.vehicle_class, "code", None),
        "capacity_value": str(vehicle.capacity_value),
        "capacity_unit": vehicle.capacity_unit,
        "status": vehicle.status,
        "eligible": not reasons,
        "reasons": reasons,
    }


def _group_candidates(actor: Any, job: Any, agreement: Any) -> dict[str, Any]:
    """Group jobs (founder decision 2026-10-14, item 19). A Group Manager
    (or staff) picks any **active member** of the group and one of the
    **group's** vehicles, the same pool ``driver_assignment_allowed`` and
    ``vehicle_eligible`` accept. In a ``DRIVER_ACCEPTS`` group an active
    member may take the job themselves: the pool is just them. Eligibility
    reasons come from the same guard predicates as the assignment itself."""
    from fikisha.groups import authz as groups_authz
    from fikisha.groups.models import (
        AssignmentMode,
        GroupMembership,
        GroupMembershipStatus,
        GroupStanding,
        OperatorGroup,
    )
    from fikisha.vehicles.services import vehicles_for_group

    group = OperatorGroup.objects.filter(id=agreement.group_id).first()
    if group is None:  # pragma: no cover - a group agreement always has one
        raise JobNoLongerAvailable("The confirmed group no longer exists.")
    members = GroupMembership.objects.filter(
        group=group, status=GroupMembershipStatus.ACTIVE
    ).select_related("operator")

    manages = job_authz.is_admin(actor) or groups_authz.can_manage(
        actor, {"group_id": str(group.id)}
    )
    if manages:
        pool = list(members.order_by("operator__full_name"))
    else:
        user_id = getattr(getattr(actor, "user", None), "id", None)
        own = [m for m in members if str(m.operator.user_id) == str(user_id)]
        if not own or group.assignment_mode != AssignmentMode.DRIVER_ACCEPTS:
            raise NotAuthorisedToAssign(
                "This group assigns work through its manager; a driver cannot self-assign."
            )
        pool = own

    drivers = [_driver_row(m.operator, job, role=m.role) for m in pool]
    if group.standing == GroupStanding.SUSPENDED:
        # driver_assignment_allowed refuses every member of a suspended group
        for row in drivers:
            row["reasons"].append("The confirmed group is suspended and cannot be assigned work.")
            row["eligible"] = False

    return {
        "job_id": str(job.id),
        "value_band": job.value_band,
        "supports_group_assignment": True,
        "assignment_mode": group.assignment_mode,
        "blocked": _high_value_blocked(job),
        "drivers": drivers,
        "vehicles": [_vehicle_row(v, job, group_id=group.id) for v in vehicles_for_group(group)],
    }
