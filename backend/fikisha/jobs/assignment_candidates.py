"""Read-only assignment-candidate preview (plan §9.2) — Design Phase 6
Increment 4.

**Individual-operator-only this increment** (Founder scope decision,
2026-09-21): the driver pool is exactly the confirmed solo operator; a Group
Manager's "assign one of my group's drivers" flow is deferred to a later
increment (``supports_group_assignment: False`` on a group-agreement job).

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
    from fikisha.jobs.models import HighValueApproval

    approval = HighValueApproval.objects.filter(job=job).first()
    if approval is None or approval.decision != HighValueDecision.APPROVED:
        return "This job requires Fikisha's high-value review before it can be assigned."
    if job.value_band == ValueBand.VERY_HIGH and not approval.decided_by_is_platform_admin:
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
        if not (
            job_authz.is_admin(actor)
            or (agreement.group_id is not None and job_authz.operator_is_party(actor, job))
        ):
            raise NotAuthorisedToAssign("You are not a party to this job's confirmed group.")
        return {
            "job_id": str(job.id),
            "value_band": job.value_band,
            "supports_group_assignment": False,
            "blocked": None,
            "drivers": [],
            "vehicles": [],
        }

    if not (
        job_authz.is_admin(actor)
        or operators_authz.owns_profile(actor, {"operator_id": str(agreement.operator_id)})
    ):
        raise NotAuthorisedToAssign("Only the confirmed operator may assign this job.")

    driver = agreement.operator
    verification_reasons = guards._driver_verification_reasons(driver)
    level, trust_reasons = guards._driver_trust_reasons(driver, job)
    driver_reasons = verification_reasons + trust_reasons

    vehicle_rows: list[dict[str, Any]] = []
    for vehicle in vehicles_for_operator(driver):
        reasons = guards._vehicle_reasons(vehicle, job, operator_id=agreement.operator_id)
        vehicle_rows.append(
            {
                "id": str(vehicle.id),
                "registration": vehicle.registration,
                "vehicle_class": getattr(vehicle.vehicle_class, "code", None),
                "capacity_value": str(vehicle.capacity_value),
                "capacity_unit": vehicle.capacity_unit,
                "status": vehicle.status,
                "eligible": not reasons,
                "reasons": reasons,
            }
        )

    return {
        "job_id": str(job.id),
        "value_band": job.value_band,
        "supports_group_assignment": False,
        "blocked": _high_value_blocked(job),
        "drivers": [
            {
                "id": str(driver.id),
                "name": driver.display_name,
                "trust_level": level,
                "eligible": not driver_reasons,
                "reasons": driver_reasons,
            }
        ],
        "vehicles": vehicle_rows,
    }
