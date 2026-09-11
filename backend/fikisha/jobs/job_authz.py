"""Server-side resolution of the caller's relationship to a Job, for the API
layer's **object-level** read/action authorization (plan §19 Step 10).

Mirrors :mod:`fikisha.incidents.authz` / :mod:`fikisha.negotiation.authz`
exactly (never trusts a client-supplied role or id; uses the sibling
modules' own ``authz`` surfaces) — duplicated here rather than imported,
because the module-boundary rule (ADR-2D-01) runs the other way: `incidents`
and `negotiation` may depend on `jobs`, `jobs` must never depend on them.
This is the coarse-plus-object-level check the `@policy` functions in
`jobs.policies` were always meant to be completed by (see that module's
docstring) — the fine-grained *who may initiate this specific transition*
check still lives in the transition engine itself and is not duplicated
here.
"""

from __future__ import annotations

from typing import Any

from fikisha.business import authz as business_authz
from fikisha.business.models import BusinessRole
from fikisha.groups import authz as groups_authz
from fikisha.operators import authz as operators_authz

_BUSINESS_PARTY_ROLES: set[str] = {BusinessRole.OWNER, BusinessRole.DISPATCHER}


class _BusinessRef:
    def __init__(self, business_id: Any) -> None:
        self.business_id = str(business_id)


def is_admin(actor: Any) -> bool:
    role = str(getattr(actor, "audit_role", "") or "")
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    return (
        role in {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"}
        or bool(roles & {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"})
        or bool(getattr(actor, "is_admin", False))
    )


def is_platform_admin(actor: Any) -> bool:
    role = str(getattr(actor, "audit_role", "") or "")
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    return role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in roles


def business_is_party(actor: Any, job: Any) -> bool:
    return business_authz.has_role(actor, _BusinessRef(job.business_id), _BUSINESS_PARTY_ROLES)


def operator_is_party(actor: Any, job: Any) -> bool:
    """True if ``actor`` controls the job's confirmed operator/group
    (``job.agreement``), is the specific assigned driver (``job.assignment``),
    or is a party to any negotiation thread on the job (pre-confirmation —
    an operator who has only *proposed*, not yet been confirmed, still
    legitimately needs to read the job they are negotiating over)."""
    agreement = getattr(job, "agreement", None)
    if agreement is not None:
        if agreement.operator_id is not None and operators_authz.owns_profile(
            actor, {"operator_id": str(agreement.operator_id)}
        ):
            return True
        if agreement.group_id is not None and groups_authz.can_manage(
            actor, {"group_id": str(agreement.group_id)}
        ):
            return True
    assignment = getattr(job, "assignment", None)
    if assignment is not None:
        driver = assignment.assigned_driver_profile
        user = getattr(actor, "user", None)
        if (
            driver is not None
            and user is not None
            and getattr(driver, "user_id", None) == getattr(user, "id", None)
        ):
            return True
    from fikisha.negotiation.models import NegotiationThread

    for thread in NegotiationThread.objects.filter(job=job).only("id", "operator_id", "group_id"):
        if thread.operator_id is not None and operators_authz.owns_profile(
            actor, {"operator_id": str(thread.operator_id)}
        ):
            return True
        if thread.group_id is not None and groups_authz.can_manage(
            actor, {"group_id": str(thread.group_id)}
        ):
            return True
    return False


def is_job_party(actor: Any, job: Any) -> bool:
    """Coarse "may this actor see/act on this job at all" boundary —
    prevents cross-business / cross-operator access (Step 10 brief §20)."""
    return is_admin(actor) or business_is_party(actor, job) or operator_is_party(actor, job)


def jobs_visible_to(actor: Any) -> Any:
    """A queryset of ``Job`` rows this actor may list — its own business's
    jobs, or jobs it is negotiating/assigned on. Platform Admin / Operations
    Officer see everything (``job.monitor.view`` is already an approved Ops
    Officer permission — ``platform_config.role_permissions``)."""
    from django.db.models import Q

    from fikisha.jobs.models import Job

    if is_admin(actor):
        return Job.objects.all()

    user = getattr(actor, "user", None)
    user_id = getattr(user, "id", None)
    if user_id is None:
        return Job.objects.none()

    from fikisha.business.models import BusinessMembership, MembershipStatus
    from fikisha.groups.models import GroupMembership, GroupMembershipStatus
    from fikisha.negotiation.models import NegotiationThread
    from fikisha.operators.models import OperatorProfile

    business_ids = BusinessMembership.objects.filter(
        user_id=user_id, status=MembershipStatus.ACTIVE
    ).values_list("business_id", flat=True)
    operator_ids = list(
        OperatorProfile.objects.filter(user_id=user_id).values_list("id", flat=True)
    )
    group_ids = GroupMembership.objects.filter(
        operator_id__in=operator_ids, status=GroupMembershipStatus.ACTIVE
    ).values_list("group_id", flat=True)
    thread_job_ids = NegotiationThread.objects.filter(
        Q(operator_id__in=operator_ids) | Q(group_id__in=group_ids)
    ).values_list("job_id", flat=True)

    return Job.objects.filter(
        Q(business_id__in=business_ids)
        | Q(id__in=thread_job_ids)
        | Q(assignment__assigned_driver_profile__in=operator_ids)
    ).distinct()
