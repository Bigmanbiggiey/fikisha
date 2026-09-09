"""Business authorization policies (Phase 1 authentication-authorization.md §3/§4).

Default deny. Platform admins pass via their ``"*"`` permission
(``actor_has_permission``); everyone else must have the right **active
membership role** for the specific business named in the resource.

An ``OPERATIONS_OFFICER`` may *read* organisations (FR-ADM-1) but not mutate them.
"""

from __future__ import annotations

from typing import Any

from fikisha.business import authz
from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("business.list")
def _list(actor: Any, _action: str, _resource: Any) -> Decision:
    # The view scopes the queryset to the caller's own memberships.
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("business.create")
def _create(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("business.read")
def _read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.read"):
        return ALLOW
    return ALLOW if authz.is_member(actor, resource) else deny("authz.forbidden")


@policy("business.update")
def _update(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.update"):
        return ALLOW
    return ALLOW if authz.is_owner(actor, resource) else deny("authz.forbidden")


@policy("business.member.list")
def _member_list(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.read"):
        return ALLOW
    return ALLOW if authz.is_member(actor, resource) else deny("authz.forbidden")


@policy("business.member.manage")
def _member_manage(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.member.manage"):
        return ALLOW
    return ALLOW if authz.is_owner(actor, resource) else deny("authz.forbidden")


@policy("business.location.read")
def _location_read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.read"):
        return ALLOW
    return ALLOW if authz.is_member(actor, resource) else deny("authz.forbidden")


@policy("business.location.manage")
def _location_manage(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "business.location.manage"):
        return ALLOW
    return ALLOW if authz.can_manage_locations(actor, resource) else deny("authz.forbidden")
