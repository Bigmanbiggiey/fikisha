"""Server-side resolution of the caller's relationship to a negotiation.

Never trusts a client-supplied role or id. Uses the sibling modules' public
``authz`` surfaces (``business.authz`` / ``operators.authz`` / ``groups.authz``)
so the "sealed thread" property is one policy rule, not isolation infra (ADR-006).
"""

from __future__ import annotations

from typing import Any

from fikisha.business import authz as business_authz
from fikisha.business.models import BusinessRole
from fikisha.groups import authz as groups_authz
from fikisha.negotiation.constants import EntryActorRole
from fikisha.negotiation.models import NegotiationThread
from fikisha.operators import authz as operators_authz

_BUSINESS_NEGOTIATORS: set[str] = {BusinessRole.OWNER, BusinessRole.DISPATCHER}


class _BusinessRef:
    """Adapts a Job to the ``business.authz`` resource shape."""

    def __init__(self, business_id: Any) -> None:
        self.business_id = str(business_id)


def is_admin(actor: Any) -> bool:
    role = str(getattr(actor, "audit_role", "") or "")
    return role in {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"} or bool(
        getattr(actor, "is_admin", False)
    )


def business_can_negotiate(actor: Any, job: Any) -> bool:
    return business_authz.has_role(actor, _BusinessRef(job.business_id), _BUSINESS_NEGOTIATORS)


def operator_owns_thread(actor: Any, thread: NegotiationThread) -> bool:
    if thread.operator_id is not None:
        return operators_authz.owns_profile(actor, {"operator_id": str(thread.operator_id)})
    if thread.group_id is not None:
        return groups_authz.can_manage(actor, {"group_id": str(thread.group_id)})
    return False


def operator_may_open(actor: Any, *, operator_id: Any = None, group_id: Any = None) -> bool:
    if operator_id is not None:
        return operators_authz.owns_profile(actor, {"operator_id": str(operator_id)})
    if group_id is not None:
        return groups_authz.can_manage(actor, {"group_id": str(group_id)})
    return False


def actor_side_for_thread(actor: Any, job: Any, thread: NegotiationThread) -> str | None:
    """``BUSINESS`` / ``OPERATOR`` / ``ADMIN`` — or ``None`` if not a party."""
    if business_can_negotiate(actor, job):
        return EntryActorRole.BUSINESS
    if operator_owns_thread(actor, thread):
        return EntryActorRole.OPERATOR
    if is_admin(actor):
        return EntryActorRole.ADMIN
    return None


def can_read_thread(actor: Any, job: Any, thread: NegotiationThread) -> bool:
    return actor_side_for_thread(actor, job, thread) is not None
