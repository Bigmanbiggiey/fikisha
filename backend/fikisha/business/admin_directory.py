"""Platform Admin directory reads and the admin standing change for business
accounts (Design Phase 6 Increment 9, ADR-2D-38). The public surface
``fikisha.admin_console`` uses; it never imports these models itself.

Plain reads and one plain write. Authorisation, step-up, the reason, the
``admin_intervention`` row and the audit entry all belong to the caller,
inside the caller's transaction.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework.exceptions import NotFound

from fikisha.business.models import BusinessAccount, BusinessStanding, MembershipStatus

STANDINGS = tuple(BusinessStanding.values)


def queryset(*, q: str = "", standing: str = "") -> QuerySet[BusinessAccount]:
    qs = BusinessAccount.objects.select_related("owner_user").annotate(
        active_members=Count("memberships", filter=Q(memberships__status=MembershipStatus.ACTIVE))
    )
    if q:
        qs = qs.filter(Q(trading_name__icontains=q) | Q(contact_name__icontains=q))
    if standing:
        qs = qs.filter(standing=standing)
    return qs


def row(business: BusinessAccount) -> dict[str, Any]:
    return {
        "id": str(business.id),
        "kind": "BUSINESS",
        "name": business.trading_name,
        "category": business.category,
        "state": business.standing,
        "verification_status": business.verification_status,
        "phone": business.contact_phone or business.owner_user.phone,
        "member_count": getattr(business, "active_members", None),
        "created_at": business.created_at.isoformat(),
    }


def detail(business_id: Any) -> dict[str, Any]:
    business = queryset().filter(id=business_id).first()
    if business is None:
        raise NotFound("No such business.")
    members = [
        {
            "user_id": str(m.user_id),
            "name": m.user.display_name or "",
            "role": m.role,
            "status": m.status,
            "user_status": m.user.status,
        }
        for m in business.memberships.select_related("user").order_by("created_at")
    ]
    return {
        **row(business),
        "contact_name": business.contact_name,
        "owner_user_id": str(business.owner_user_id),
        "owner_user_status": business.owner_user.status,
        "members": members,
    }


def contact(business_id: Any) -> dict[str, str] | None:
    business = BusinessAccount.objects.select_related("owner_user").filter(id=business_id).first()
    if business is None:
        return None
    return {
        "name": business.contact_name or business.trading_name,
        "phone": business.contact_phone or business.owner_user.phone,
    }


def set_state(business_id: Any, standing: str) -> tuple[str, str]:
    """Set the standing; returns ``(before, after)``. Call inside a
    transaction (the row is locked)."""
    business = BusinessAccount.objects.select_for_update().filter(id=business_id).first()
    if business is None:
        raise NotFound("No such business.")
    before = business.standing
    business.standing = standing
    business.save(update_fields=["standing", "updated_at"])
    return before, standing
