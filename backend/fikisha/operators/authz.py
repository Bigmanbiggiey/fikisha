"""Organisation-level authorization helpers for the Operators module."""

from __future__ import annotations

from typing import Any

from fikisha.operators.models import OperatingBase, OperatorProfile


def owns_profile(actor: Any, resource: Any) -> bool:
    """True when ``resource`` is (or names) an OperatorProfile owned by the actor."""
    if not getattr(actor, "is_authenticated", False):
        return False
    actor_user_id = str(getattr(actor.user, "id", ""))
    if isinstance(resource, OperatorProfile):
        return str(resource.user_id) == actor_user_id
    user_id = getattr(resource, "user_id", None)
    if user_id is not None:
        return str(user_id) == actor_user_id
    profile_id = getattr(resource, "id", None) or (
        resource.get("operator_id") if isinstance(resource, dict) else None
    )
    if profile_id is None:
        return False
    return OperatorProfile.objects.filter(id=profile_id, user_id=actor_user_id).exists()


def has_profile(actor: Any) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    user_id = getattr(actor.user, "id", None)
    return user_id is not None and OperatorProfile.objects.filter(user_id=user_id).exists()


def created_base(actor: Any, resource: Any) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    actor_user_id = str(getattr(actor.user, "id", ""))
    if isinstance(resource, OperatingBase):
        return str(resource.created_by_id) == actor_user_id
    created_by = getattr(resource, "created_by_id", None)
    return created_by is not None and str(created_by) == actor_user_id
