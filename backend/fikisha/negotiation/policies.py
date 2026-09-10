"""Negotiation authorization policies (registered on app ``ready()``).

Coarse gate only — "may this actor use negotiation at all". The authoritative
resource-aware check ("is this actor the business owner/dispatcher for this job,
or the operator/group that owns this thread, or an admin") runs in
:mod:`fikisha.negotiation.services` via :mod:`fikisha.negotiation.authz`, which
resolves the relationship server-side and never trusts a client-supplied role
or id. The "sealed thread" read scoping (ADR-006) lives there too.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.negotiation import authz


def _authed(actor: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("negotiation.read")
def _read(actor: Any, _action: str, resource: Any) -> Decision:
    decision = _authed(actor)
    if not decision.allowed or resource is None:
        return decision
    job = getattr(resource, "job", None) or getattr(resource, "job_obj", None)
    thread = resource if hasattr(resource, "operator_party") else None
    if job is not None and thread is not None and not authz.can_read_thread(actor, job, thread):
        return deny("authz.forbidden", "You are not a party to this negotiation.")
    return ALLOW


@policy("negotiation.propose")
def _propose(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("negotiation.counter")
def _counter(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("negotiation.accept")
def _accept(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("negotiation.decline")
def _decline(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)
