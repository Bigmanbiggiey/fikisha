"""Operator tier authorization (operator-tiers plan TD-1, TD-6).

- ``trust.read``: the operator themselves, or staff who can read operators
  (Operations Officer, Platform Admin). A group manager sees their drivers'
  tiers on the driver-pool screen (assignment candidates), not here.
- ``trust.queue.read``: staff who can read operators.
- ``trust.change.apply``: config permission held by the Platform Admin
  (``"*"``) only; the service also requires a fresh step-up.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.operators import authz as operators_authz


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("trust.read")
def _trust_read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if actor_has_permission(actor, "operator.read"):
        return ALLOW
    return ALLOW if operators_authz.owns_profile(actor, resource) else deny("authz.forbidden")


@policy("trust.queue.read")
def _trust_queue(actor: Any, _action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return (
        ALLOW if actor_has_permission(actor, "operator.read") else deny("authz.missing_permission")
    )


@policy("trust.change.apply")
def _trust_apply(actor: Any, action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return ALLOW if actor_has_permission(actor, action) else deny("authz.missing_permission")
