"""Vehicle authorization policies. Default deny."""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.vehicles import authz
from fikisha.vehicles.models import Vehicle


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("vehicle.list")
def _list(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("vehicle.create")
def _create(actor: Any, _action: str, _resource: Any) -> Decision:
    # The view checks that the caller controls the named operator/group.
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("vehicle.read")
def _read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "vehicle.read"):
        return ALLOW
    if isinstance(resource, Vehicle) and authz.can_view(actor, resource):
        return ALLOW
    return deny("authz.forbidden")


@policy("vehicle.manage")
def _manage(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "vehicle.manage"):
        return ALLOW
    if isinstance(resource, Vehicle) and authz.can_manage(actor, resource):
        return ALLOW
    return deny("authz.forbidden")
