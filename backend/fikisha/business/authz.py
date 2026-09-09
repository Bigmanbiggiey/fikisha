"""Organisation-level authorization helpers for the Business module.

These resolve the caller's relationship to a specific business **server-side**
(never trusting a client-supplied role or id). The registered policies in
``policies.py`` use them.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fikisha.business.models import BusinessMembership, BusinessRole, MembershipStatus


def _business_id(resource: Any) -> str | None:
    """Extract a business id from an authz resource (a model instance or a mapping)."""
    if resource is None:
        return None
    for attr in ("business_id", "id"):
        value = getattr(resource, attr, None)
        if value is not None:
            return str(value)
    if isinstance(resource, dict):
        value = resource.get("business_id") or resource.get("id")
        return str(value) if value is not None else None
    if isinstance(resource, str | UUID):
        return str(resource)
    return None


def active_membership(actor: Any, resource: Any) -> BusinessMembership | None:
    if not getattr(actor, "is_authenticated", False):
        return None
    business_id = _business_id(resource)
    user_id = getattr(actor.user, "id", None)
    if business_id is None or user_id is None:
        return None
    return (
        BusinessMembership.objects.filter(  # type: ignore[misc]  # dynamic FK-id lookups
            business_id=business_id,
            user_id=user_id,
            status=MembershipStatus.ACTIVE,
        )
        .select_related("business")
        .first()
    )


def has_role(actor: Any, resource: Any, roles: set[str]) -> bool:
    membership = active_membership(actor, resource)
    return membership is not None and membership.role in roles


def is_member(actor: Any, resource: Any) -> bool:
    return active_membership(actor, resource) is not None


def is_owner(actor: Any, resource: Any) -> bool:
    return has_role(actor, resource, {BusinessRole.OWNER})


def can_manage_locations(actor: Any, resource: Any) -> bool:
    return has_role(actor, resource, {BusinessRole.OWNER, BusinessRole.DISPATCHER})
