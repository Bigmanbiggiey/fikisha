"""Commission statements authorization policies (registered on app
``ready()``; plan §3.5).

- ``statements.read.own``: any signed-in person may list their own statements;
  what they see is decided by ``services.statements_for`` (their operator
  profile and the groups they manage), never by a client-supplied id.
- ``statements.read.one``: object-level; the statement's payee, or staff with
  ``statements.read.all``.
- ``statements.read.all`` / ``statements.run`` / ``statements.settle``:
  config-driven permissions. The Platform Admin holds ``"*"``; the Operations
  Officer holds ``statements.read.all`` only (D-4). Recording or reversing a
  payment also needs a fresh step-up, checked in the service.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


@policy("statements.read.own")
def _read_own(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("statements.read.one")
def _read_one(actor: Any, _action: str, resource: Any) -> Decision:
    from fikisha.statements.services import can_read_statement

    if not _authed(actor):
        return deny("authz.unauthenticated")
    if resource is None:
        return deny("authz.forbidden")
    return ALLOW if can_read_statement(actor, resource) else deny("authz.not_payee")


@policy("statements.job_earnings")
def _job_earnings(actor: Any, _action: str, _resource: Any) -> Decision:
    # Coarse gate; ``services.job_earnings`` answers 404 to anyone who is
    # neither the job's payee nor staff.
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


def _by_permission(actor: Any, action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return ALLOW if actor_has_permission(actor, action) else deny("authz.missing_permission")


for _permission in ("statements.read.all", "statements.run", "statements.settle"):
    policy(_permission)(_by_permission)
