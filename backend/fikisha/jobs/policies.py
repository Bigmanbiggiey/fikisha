"""Job-domain authorization policies (registered on app ``ready()``).

The write-side actions here are still a **coarse** gate — "may this actor
touch jobs at all". The fine-grained *who may initiate this specific
transition* check is the initiator-token match inside
:func:`fikisha.jobs.service.transition`, driven by the authoritative table in
:mod:`fikisha.jobs.transitions` — that remains the real guard for every write.

``job.read`` (Step 10, plan §19) is the one **object-level** policy here: a
list view passes no resource (``get_authz_resource()`` returns ``None``
without a ``resolve_target``) and falls back to the coarse authenticated
check — the view itself scopes the queryset
(:func:`fikisha.jobs.job_authz.jobs_visible_to`); a detail view resolves the
actual ``Job`` first, and this policy then runs
:func:`fikisha.jobs.job_authz.is_job_party` against it — the real
cross-business / cross-operator isolation boundary (brief §20).
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy


def _is_system(actor: Any) -> bool:
    return str(getattr(actor, "audit_role", "") or "") == "SYSTEM"


def _authed_or_system(actor: Any) -> Decision:
    if getattr(actor, "is_authenticated", False) or _is_system(actor):
        return ALLOW
    return deny("authz.unauthenticated")


@policy("job.read")
def _job_read(actor: Any, _action: str, resource: Any) -> Decision:
    if resource is None:
        return _authed_or_system(actor)
    if not getattr(actor, "is_authenticated", False) and not _is_system(actor):
        return deny("authz.unauthenticated")
    from fikisha.jobs import job_authz

    if job_authz.is_job_party(actor, resource):
        return ALLOW
    return deny("authz.forbidden", "You are not a party to this job.")


@policy("job.create")
def _job_create(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("job.transition")
def _job_transition(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate only — the allowed-initiator match happens in the service."""
    return _authed_or_system(actor)


@policy("job.assign")
def _job_assign(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate — the operator/group-manager/driver-self/admin resolution and
    the eligibility guards run in :mod:`fikisha.jobs.assignment` / the service."""
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("job.proof.pickup")
def _job_proof_pickup(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate — the driver-vs-business-party resolution and the band matrix
    run in :mod:`fikisha.jobs.custody` / the guards."""
    return _authed_or_system(actor)


@policy("job.proof.delivery")
def _job_proof_delivery(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed_or_system(actor)


@policy("commission.read")
def _commission_read(actor: Any, _action: str, _resource: Any) -> Decision:
    """Platform-Admin-only (Step 10 brief §17/§23 — commission is commercially
    sensitive; nothing in the approved requirements names another party with a
    right to read it, so this stays conservative rather than inventing a
    broader disclosure)."""
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    from fikisha.jobs import job_authz

    return ALLOW if job_authz.is_platform_admin(actor) else deny("authz.forbidden")


@policy("highvalue.approve")
def _highvalue_approve(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate — HIGH vs VERY_HIGH admin-tier resolution is in
    :func:`fikisha.jobs.high_value.decide_high_value`."""
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    if roles & {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"} or getattr(actor, "is_admin", False):
        return ALLOW
    return deny("authz.forbidden", "A high-value decision requires an admin role.")
