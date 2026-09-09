"""Operator + operating-location authorization policies.

Default deny. A user manages their own operator profile; an operating base is a
low-sensitivity physical place (any authenticated user may read/list it), but
editing one is limited to its creator or a platform admin. Associating a party
with a base is checked by the caller against the party's own authorization
(own operator profile, or group manage rights).
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.operators import authz


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("operator.create")
def _operator_create(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("operator.read.me")
def _operator_read_me(actor: Any, _action: str, _resource: Any) -> Decision:
    # Always the caller's own profile — the handler 404s when there is none.
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("operator.read")
def _operator_read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "operator.read"):
        return ALLOW
    return ALLOW if authz.owns_profile(actor, resource) else deny("authz.forbidden")


@policy("operator.update")
def _operator_update(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "operator.update"):
        return ALLOW
    return ALLOW if authz.owns_profile(actor, resource) else deny("authz.forbidden")


@policy("operating_location.read")
def _base_read(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("operating_location.create")
def _base_create(actor: Any, _action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "operating_location.create"):
        return ALLOW
    # A base is declared by an operator (or an admin).
    return (
        ALLOW
        if authz.has_profile(actor)
        else deny("authz.forbidden", "an operator profile is required to add an operating location")
    )


@policy("operating_location.manage")
def _base_manage(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "operating_location.manage"):
        return ALLOW
    return ALLOW if authz.created_base(actor, resource) else deny("authz.forbidden")
