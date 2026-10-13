"""Platform Admin directory reads and the admin status change for operator
profiles (Design Phase 6 Increment 9, ADR-2D-38). The public surface
``fikisha.admin_console`` uses; it never imports these models itself.

Plain reads and one plain write. Authorisation, step-up, the reason, the
``admin_intervention`` row and the audit entry all belong to the caller,
inside the caller's transaction.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from rest_framework.exceptions import NotFound

from fikisha.operators.models import OperatorProfile, OperatorStatus

STATUSES = tuple(OperatorStatus.values)


def queryset(*, q: str = "", status: str = "") -> QuerySet[OperatorProfile]:
    qs = OperatorProfile.objects.select_related("user")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(display_name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return qs


def row(profile: OperatorProfile) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "kind": "OPERATOR",
        "name": profile.display_name or profile.full_name,
        "full_name": profile.full_name,
        "state": profile.status,
        "phone": profile.user.phone,
        "created_at": profile.created_at.isoformat(),
    }


def detail(operator_id: Any) -> dict[str, Any]:
    profile = queryset().filter(id=operator_id).first()
    if profile is None:
        raise NotFound("No such operator.")
    return {
        **row(profile),
        "user_id": str(profile.user_id),
        "user_status": profile.user.status,
    }


def contact(operator_id: Any) -> dict[str, str] | None:
    profile = queryset().filter(id=operator_id).first()
    if profile is None:
        return None
    return {"name": profile.display_name or profile.full_name, "phone": profile.user.phone}


def set_state(operator_id: Any, status: str) -> tuple[str, str]:
    """Set the status; returns ``(before, after)``. Call inside a
    transaction (the row is locked)."""
    profile = OperatorProfile.objects.select_for_update().filter(id=operator_id).first()
    if profile is None:
        raise NotFound("No such operator.")
    before = profile.status
    profile.status = status
    profile.save(update_fields=["status", "updated_at"])
    return before, status
