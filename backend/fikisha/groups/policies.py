"""Operator Group authorization policies.

Default deny. Only an operator (a user with an ``OperatorProfile``) may form a
group. Reading a group needs an active membership (any role); managing the group
or its membership needs OWNER/MANAGER. Platform admins pass via ``"*"``; an
``OPERATIONS_OFFICER`` may read groups (FR-ADM-1) but not mutate them.
"""

from __future__ import annotations

from typing import Any

from fikisha.groups import authz
from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.operators.authz import has_profile


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("group.list")
def _list(actor: Any, _action: str, _resource: Any) -> Decision:
    # The view scopes the queryset to groups the caller is an active member of.
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("group.create")
def _create(actor: Any, _action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return (
        ALLOW
        if has_profile(actor)
        else deny("authz.forbidden", "an operator profile is required to create a group")
    )


@policy("group.read")
def _read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "group.read"):
        return ALLOW
    return ALLOW if authz.is_member(actor, resource) else deny("authz.forbidden")


@policy("group.update")
def _update(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "group.update"):
        return ALLOW
    return ALLOW if authz.can_manage(actor, resource) else deny("authz.forbidden")


@policy("group.member.list")
def _member_list(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "group.read"):
        return ALLOW
    return ALLOW if authz.is_member(actor, resource) else deny("authz.forbidden")


@policy("group.member.manage")
def _member_manage(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "group.member.manage"):
        return ALLOW
    return ALLOW if authz.can_manage(actor, resource) else deny("authz.forbidden")
