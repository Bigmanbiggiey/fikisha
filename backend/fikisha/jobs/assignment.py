"""Assignment service (``CONFIRMED -> ASSIGNED``) — plan §9, job-state-machine.md §3.2.

Resolves the caller's authority to assign server-side, then calls
``JobLifecycleService.transition(job, ASSIGNED, …)`` — the single authoritative
writer — which runs the eligibility guards (``DriverAssignmentAllowed``,
``VehicleEligible``, ``DriverVerificationCurrent``,
``DriverTrustCeilingCoversValue``, ``HighValueApproved``,
``RequesterIsNotProvider``) against the **specific driver and vehicle** and
creates the ``Assignment`` row.

Who may assign:
* **solo-operator job** — only that operator, driving their own job with their
  own vehicle (``assigned_by = SELF``);
* **group job, MANAGER_ASSIGNS** — a group OWNER / MANAGER names an active-member
  driver + a group vehicle (``assigned_by = GROUP_MANAGER``);
* **group job, DRIVER_ACCEPTS** — an active-member driver self-assigns
  (``assigned_by = SELF``), or a manager assigns as above;
* **Platform Admin / Operations Officer** — either case (``assigned_by = ADMIN``),
  ``admin_override_reason`` optional (it relaxes only the trust-ceiling guard).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import Http404

from fikisha.groups import authz as groups_authz
from fikisha.groups.models import AssignmentMode, GroupMembership, GroupMembershipStatus
from fikisha.jobs.constants import AssignedBy, JobStatus, OperatorParty
from fikisha.jobs.errors import JobNoLongerAvailable, NotAuthorisedToAssign
from fikisha.jobs.selectors import job_for_update
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.operators import authz as operators_authz
from fikisha.operators.models import OperatorProfile
from fikisha.vehicles.models import Vehicle


def _is_admin(actor: Any) -> bool:
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    return bool(roles & {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"}) or bool(
        getattr(actor, "is_admin", False)
    )


def _resolve_authority(actor: Any, job: Any, driver: OperatorProfile) -> tuple[str, str]:
    """``(initiator_token, assigned_by)`` — or raise ``NotAuthorisedToAssign``."""
    if _is_admin(actor):
        return "ADMIN", AssignedBy.ADMIN

    agreement = job.agreement
    if agreement is None:  # pragma: no cover - guarded upstream
        raise NotAuthorisedToAssign("The job has no confirmed agreement.")

    if agreement.operator_party == OperatorParty.OPERATOR:
        if operators_authz.owns_profile(actor, {"operator_id": str(agreement.operator_id)}):
            return "OPERATOR_PARTY", AssignedBy.SELF
        raise NotAuthorisedToAssign("Only the confirmed operator may assign this job.")

    # group job
    if groups_authz.can_manage(actor, {"group_id": str(agreement.group_id)}):
        return "GROUP_MANAGER", AssignedBy.GROUP_MANAGER

    from fikisha.groups.models import OperatorGroup

    group = OperatorGroup.objects.filter(id=agreement.group_id).first()
    actor_user_id = getattr(getattr(actor, "user", None), "id", None)
    is_self = actor_user_id is not None and str(driver.user_id) == str(actor_user_id)
    is_active_member = GroupMembership.objects.filter(
        group_id=agreement.group_id,
        operator_id=driver.id,
        status=GroupMembershipStatus.ACTIVE,
    ).exists()
    if (
        group is not None
        and group.assignment_mode == AssignmentMode.DRIVER_ACCEPTS
        and is_self
        and is_active_member
    ):
        return "OPERATOR_PARTY", AssignedBy.SELF

    raise NotAuthorisedToAssign(
        "This group assigns work through its manager; a driver cannot self-assign."
    )


@transaction.atomic
def assign_job(
    *,
    actor: Any,
    job_id: Any,
    driver_profile_id: Any,
    vehicle_id: Any,
    admin_override_reason: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    job = job_for_update(job_id)
    if job.status != JobStatus.CONFIRMED:
        raise JobNoLongerAvailable("Only a confirmed job can be assigned.")
    agreement = job.agreement
    if agreement is None:  # a CONFIRMED job always has one — defensive
        raise JobNoLongerAvailable("The confirmed job has no agreement.")

    try:
        driver = OperatorProfile.objects.get(id=driver_profile_id)
    except OperatorProfile.DoesNotExist as exc:
        raise Http404("No such operator profile.") from exc
    try:
        vehicle = Vehicle.objects.select_related("vehicle_class").get(id=vehicle_id)
    except Vehicle.DoesNotExist as exc:
        raise Http404("No such vehicle.") from exc

    token, assigned_by = _resolve_authority(actor, job, driver)

    ctx = TransitionContext(
        data={
            "initiator_tokens": [token],
            "operator_party": agreement.operator_party,
            "operator_id": str(agreement.operator_id) if agreement.operator_id else None,
            "group_id": str(agreement.group_id) if agreement.group_id else None,
            "driver_profile": driver,
            "vehicle": vehicle,
            "assigned_by": assigned_by,
            "admin_override_reason": admin_override_reason if _is_admin(actor) else "",
        }
    )
    return job_transition(
        job_id=job.id,
        to=JobStatus.ASSIGNED,
        actor=actor,
        context=ctx,
        idempotency_key=idempotency_key,
    )
