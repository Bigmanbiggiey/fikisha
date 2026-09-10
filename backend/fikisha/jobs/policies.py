"""Job-domain authorization policies (registered on app ``ready()``).

These are the **coarse** gate — "may this actor touch jobs at all". The
fine-grained *who may initiate this specific transition* check is the
initiator-token match inside :func:`fikisha.jobs.service.transition`, driven by
the authoritative table in :mod:`fikisha.jobs.transitions`.

Full per-resource policies (business owns the job, operator is on the agreement,
recipient link scope, admin band authority) land with the API layer in plan §19
Step 10; nothing here grants access to another org's data.
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
def _job_read(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed_or_system(actor)


@policy("job.create")
def _job_create(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("job.transition")
def _job_transition(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate only — the allowed-initiator match happens in the service."""
    return _authed_or_system(actor)
