"""Organisation-level authorization helpers for the Operator Groups module."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fikisha.groups.models import GroupMemberRole, GroupMembership, GroupMembershipStatus
from fikisha.operators.models import OperatorProfile


def _group_id(resource: Any) -> str | None:
    if resource is None:
        return None
    for attr in ("group_id", "id"):
        value = getattr(resource, attr, None)
        if value is not None:
            return str(value)
    if isinstance(resource, dict):
        value = resource.get("group_id") or resource.get("id")
        return str(value) if value is not None else None
    if isinstance(resource, str | UUID):
        return str(resource)
    return None


def active_membership(actor: Any, resource: Any) -> GroupMembership | None:
    if not getattr(actor, "is_authenticated", False):
        return None
    group_id = _group_id(resource)
    user_id = getattr(actor.user, "id", None)
    if group_id is None or user_id is None:
        return None
    profile_id = (
        OperatorProfile.objects.filter(user_id=user_id).values_list("id", flat=True).first()
    )
    if profile_id is None:
        return None
    return (
        GroupMembership.objects.filter(  # type: ignore[misc]  # dynamic FK-id lookups
            group_id=group_id,
            operator_id=profile_id,
            status=GroupMembershipStatus.ACTIVE,
        )
        .select_related("group")
        .first()
    )


def has_role(actor: Any, resource: Any, roles: set[str]) -> bool:
    membership = active_membership(actor, resource)
    return membership is not None and membership.role in roles


def is_member(actor: Any, resource: Any) -> bool:
    return active_membership(actor, resource) is not None


def can_manage(actor: Any, resource: Any) -> bool:
    return has_role(actor, resource, {GroupMemberRole.OWNER, GroupMemberRole.MANAGER})
