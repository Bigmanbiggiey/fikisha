"""Platform Admin directory reads and the admin standing change for operator
groups (Design Phase 6 Increment 9, ADR-2D-38). The public surface
``fikisha.admin_console`` uses; it never imports these models itself.

Plain reads and one plain write. Authorisation, step-up, the reason, the
``admin_intervention`` row and the audit entry all belong to the caller,
inside the caller's transaction.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework.exceptions import NotFound

from fikisha.groups.models import GroupMembershipStatus, GroupStanding, OperatorGroup

STANDINGS = tuple(GroupStanding.values)


def queryset(*, q: str = "", standing: str = "") -> QuerySet[OperatorGroup]:
    qs = OperatorGroup.objects.select_related("primary_contact").annotate(
        active_members=Count(
            "memberships", filter=Q(memberships__status=GroupMembershipStatus.ACTIVE)
        )
    )
    if q:
        qs = qs.filter(name__icontains=q)
    if standing:
        qs = qs.filter(standing=standing)
    return qs


def row(group: OperatorGroup) -> dict[str, Any]:
    return {
        "id": str(group.id),
        "kind": "GROUP",
        "name": group.name,
        "group_type": group.type,
        "state": group.standing,
        "verification_status": group.verification_status,
        "assignment_mode": group.assignment_mode,
        "phone": group.primary_contact.phone,
        "member_count": getattr(group, "active_members", None),
        "created_at": group.created_at.isoformat(),
    }


def detail(group_id: Any) -> dict[str, Any]:
    group = queryset().filter(id=group_id).first()
    if group is None:
        raise NotFound("No such group.")
    members = [
        {
            "operator_id": str(m.operator_id),
            "name": m.operator.display_name or m.operator.full_name,
            "role": m.role,
            "status": m.status,
        }
        for m in group.memberships.select_related("operator").order_by("created_at")
    ]
    return {**row(group), "members": members}


def contact(group_id: Any) -> dict[str, str] | None:
    group = queryset().filter(id=group_id).first()
    if group is None:
        return None
    contact_user = group.primary_contact
    return {"name": contact_user.display_name or group.name, "phone": contact_user.phone}


def set_state(group_id: Any, standing: str) -> tuple[str, str]:
    """Set the standing; returns ``(before, after)``. Call inside a
    transaction (the row is locked)."""
    group = OperatorGroup.objects.select_for_update().filter(id=group_id).first()
    if group is None:
        raise NotFound("No such group.")
    before = group.standing
    group.standing = standing
    group.save(update_fields=["standing", "updated_at"])
    return before, standing
