"""Server-side resolution of the caller's relationship to a Job's incidents and
disputes (mirrors :mod:`fikisha.negotiation.authz` / :mod:`fikisha.jobs.assignment`
— never trusts a client-supplied role or id; uses the sibling modules' own
``authz`` surfaces so cross-job/cross-business/cross-operator isolation is one
policy rule, not isolation infra reinvented here).
"""

from __future__ import annotations

from typing import Any

from fikisha.business import authz as business_authz
from fikisha.business.models import BusinessRole
from fikisha.groups import authz as groups_authz
from fikisha.incidents.constants import PartyKind
from fikisha.operators import authz as operators_authz

_BUSINESS_PARTY_ROLES: set[str] = {BusinessRole.OWNER, BusinessRole.DISPATCHER}


class _BusinessRef:
    """Adapts a Job to the ``business.authz`` resource shape."""

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


def actor_has_permission(actor: Any, permission: str) -> bool:
    """Config-driven fine-grained check against ``platform_config.role_permissions``
    (already approved config — e.g. ``OPERATIONS_OFFICER`` carries
    ``incident.intake`` / ``incident.amicable.facilitate``, ADR-2A pattern).
    A Platform Admin's ``"*"`` entry always matches."""
    from fikisha.platform_config import services as cfg

    perms_map = cfg.get("role_permissions", {}) or {}
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    audit_role = str(getattr(actor, "audit_role", "") or "")
    if audit_role:
        roles.add(audit_role)
    for role in roles:
        perms = perms_map.get(role) or []
        if "*" in perms or permission in perms:
            return True
    return False


def business_is_party(actor: Any, job: Any) -> bool:
    return business_authz.has_role(actor, _BusinessRef(job.business_id), _BUSINESS_PARTY_ROLES)


def operator_is_party(actor: Any, job: Any) -> bool:
    """True if ``actor`` controls the job's confirmed operator or group
    (``job.agreement``), or is the specific assigned driver (``job.assignment``)
    — either is legitimately "the operator side" for incident purposes."""
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
    return False


def is_group_party(actor: Any, job: Any) -> bool:
    agreement = getattr(job, "agreement", None)
    return bool(
        agreement is not None
        and agreement.group_id is not None
        and groups_authz.can_manage(actor, {"group_id": str(agreement.group_id)})
    )


def party_kind_for_job(actor: Any, job: Any) -> str | None:
    """``PartyKind.{ADMIN,BUSINESS,GROUP,OPERATOR}`` — or ``None`` if the actor
    is not a party to this job at all (a ``RECIPIENT`` never reaches this
    function; it acts through its own scoped ``RecipientPrincipal`` path)."""
    if is_admin(actor):
        return PartyKind.ADMIN
    if business_is_party(actor, job):
        return PartyKind.BUSINESS
    if is_group_party(actor, job):
        return PartyKind.GROUP
    if operator_is_party(actor, job):
        return PartyKind.OPERATOR
    return None


def is_job_party(actor: Any, job: Any) -> bool:
    """Coarse "may this actor see/act on this job's incidents at all" check —
    the authorisation boundary preventing cross-job / cross-business /
    cross-operator access (Step 8 brief §17)."""
    return party_kind_for_job(actor, job) is not None


def initiator_token_for_job(actor: Any, job: Any) -> str | None:
    """The **Job-lifecycle** initiator token (``jobs.service`` vocabulary —
    distinct from :class:`PartyKind`) this actor holds for this job, if any.
    ``ADMIN`` / ``PLATFORM_ADMIN`` / ``ASSIGNED_DRIVER`` are derived
    automatically by the engine and never need to be asserted here."""
    if is_admin(actor):
        return "ADMIN"
    if business_is_party(actor, job):
        return "BUSINESS_PARTY"
    if is_group_party(actor, job):
        return "GROUP_MANAGER"
    agreement = getattr(job, "agreement", None)
    if (
        agreement is not None
        and agreement.operator_id is not None
        and operators_authz.owns_profile(actor, {"operator_id": str(agreement.operator_id)})
    ):
        return "OPERATOR_PARTY"
    return None
