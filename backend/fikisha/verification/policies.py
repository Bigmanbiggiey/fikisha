"""Verification authorization policies. Default deny.

An operator/business user can never review verification (they lack the
``verification.decide`` permission); the service layer additionally rejects a
reviewer who is the submitter (brief §17).
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.verification import authz
from fikisha.verification.models import VerificationRecord


def _authed(actor: Any) -> bool:
    return bool(getattr(actor, "is_authenticated", False))


def _is_reviewer(actor: Any) -> bool:
    return actor_has_permission(actor, "verification.decide")


@policy("verification.record.list")
def _list(actor: Any, _action: str, _resource: Any) -> Decision:
    # The view scopes results to the caller's own subjects (or the queue view).
    return ALLOW if _authed(actor) else deny("authz.unauthenticated")


@policy("verification.record.read")
def _read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if _is_reviewer(actor) or actor_has_permission(actor, "verification.queue.view"):
        return ALLOW
    if isinstance(resource, VerificationRecord) and authz.owns_subject(actor, resource):
        return ALLOW
    return deny("authz.forbidden")


@policy("verification.submit")
def _submit(actor: Any, _action: str, _resource: Any) -> Decision:
    # The view checks the caller owns the concrete subject before calling the
    # service; an admin may also submit on someone's behalf (audited).
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return ALLOW


@policy("verification.queue")
def _queue(actor: Any, _action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return (
        ALLOW
        if actor_has_permission(actor, "verification.queue.view") or _is_reviewer(actor)
        else deny("authz.forbidden")
    )


@policy("verification.decide")
def _decide(actor: Any, _action: str, _resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    return ALLOW if _is_reviewer(actor) else deny("authz.forbidden")


@policy("verification.evidence.read")
def _evidence_read(actor: Any, _action: str, resource: Any) -> Decision:
    if not _authed(actor):
        return deny("authz.unauthenticated")
    if _is_reviewer(actor):
        return ALLOW
    if isinstance(resource, VerificationRecord) and authz.owns_subject(actor, resource):
        return ALLOW
    return deny("authz.forbidden")
