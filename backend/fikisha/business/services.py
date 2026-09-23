"""Business domain services (Phase 1 domain-architecture §3.2).

All state changes go through here (not through views), each inside a
``transaction.atomic`` with an audit row written in the same transaction.
Cross-organisation access is *not* checked here — the API layer runs the
authorization engine first; these functions assume an authorised caller and
enforce only the domain invariants.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.business.models import (
    BusinessAccount,
    BusinessLocation,
    BusinessMembership,
    BusinessRole,
    BusinessStanding,
    LocationType,
    MembershipStatus,
)
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.identity.models import User
from fikisha.identity.phone import normalize_phone
from fikisha.outbox.services import emit

MEMBER_ADDED_EVENT = "business.member.added"

_EDITABLE_FIELDS = ("trading_name", "category", "contact_name", "contact_phone", "contact_email")


def businesses_for(user: User) -> QuerySet[BusinessAccount]:
    """List a user's businesses, each annotated with ``my_role`` (the
    requesting user's own active role on that business) so
    ``BusinessSerializer`` — a per-object ``SerializerMethodField`` — can
    render it correctly across a list, not just the single-object
    create/detail views (see ADR: list `my_role` regression, phase-2d-
    decisions.md)."""
    my_active_role = BusinessMembership.objects.filter(
        business_id=OuterRef("pk"), user=user, status=MembershipStatus.ACTIVE
    ).values("role")[:1]
    return (
        BusinessAccount.objects.filter(
            memberships__user=user, memberships__status=MembershipStatus.ACTIVE
        )
        .annotate(my_role=Subquery(my_active_role))
        .distinct()
        .order_by("-created_at")
    )


def display_name_for(business_id: Any) -> str | None:
    """The business's trading name — for another module (e.g. the Ops job
    monitor) to label a job's business without reaching into this module's
    model fields directly (module boundary rule, mirrors
    ``operators.services.display_name_for``)."""
    return (
        BusinessAccount.objects.filter(id=business_id)
        .values_list("trading_name", flat=True)
        .first()
    )


def display_names_for(business_ids: Any) -> dict[str, str]:
    """Bulk form of :func:`display_name_for` — one query for a list page."""
    return {
        str(pk): name
        for pk, name in BusinessAccount.objects.filter(id__in=list(business_ids)).values_list(
            "id", "trading_name"
        )
    }


def contact_for(business_id: Any) -> dict[str, str] | None:
    """The business's own registered contact (name + phone). Callers are
    responsible for authorising and auditing the reveal — this is a plain
    read (Design Phase 6 Increment 8, Ops "contact parties")."""
    row = (
        BusinessAccount.objects.filter(id=business_id)
        .values_list("trading_name", "contact_name", "contact_phone")
        .first()
    )
    if row is None:
        return None
    trading_name, contact_name, contact_phone = row
    return {"name": contact_name or trading_name, "phone": contact_phone}


def membership_for(user: User, business_id: Any) -> BusinessMembership | None:
    return BusinessMembership.objects.filter(
        business_id=business_id, user=user, status=MembershipStatus.ACTIVE
    ).first()


def _audit_actor(actor: Any) -> Any:
    return getattr(actor, "user", actor)


@transaction.atomic
def create_business(
    *,
    actor: Any,
    trading_name: str,
    category: str = "",
    contact_name: str = "",
    contact_phone: str = "",
    contact_email: str = "",
) -> BusinessAccount:
    user = _audit_actor(actor)
    business = BusinessAccount.objects.create(
        owner_user=user,
        trading_name=trading_name.strip(),
        category=category.strip(),
        contact_name=contact_name.strip(),
        contact_phone=contact_phone.strip(),
        contact_email=contact_email.strip(),
    )
    membership = BusinessMembership.objects.create(
        business=business, user=user, role=BusinessRole.OWNER, status=MembershipStatus.ACTIVE
    )
    audit.record(
        actor=actor,
        action="business.created",
        entity_type="business_account",
        entity_id=business.id,
        after={"trading_name": business.trading_name},
    )
    audit.record(
        actor=actor,
        action="business.member.added",
        entity_type="business_membership",
        entity_id=membership.id,
        after={"business_id": str(business.id), "user_id": str(user.id), "role": membership.role},
    )
    return business


@transaction.atomic
def update_business(
    *, actor: Any, business: BusinessAccount, patch: dict[str, Any], is_platform_admin: bool = False
) -> BusinessAccount:
    business = BusinessAccount.objects.select_for_update().get(pk=business.pk)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}

    for field in _EDITABLE_FIELDS:
        if field in patch and patch[field] is not None:
            new_value = str(patch[field]).strip()
            if new_value != getattr(business, field):
                before[field] = getattr(business, field)
                after[field] = new_value
                setattr(business, field, new_value)

    if "standing" in patch and patch["standing"] is not None:
        if not is_platform_admin:
            raise AuthorizationError(
                "Only a platform administrator can change a business's standing.",
                code="authz.forbidden",
            )
        new_standing = str(patch["standing"])
        if new_standing not in BusinessStanding.values:
            raise DomainError(f"Unknown standing {new_standing!r}.", code="validation_error")
        if new_standing != business.standing:
            before["standing"] = business.standing
            after["standing"] = new_standing
            business.standing = new_standing

    if not after:
        return business

    business.save(update_fields=[*after.keys(), "updated_at"])
    audit.record(
        actor=actor,
        action="business.updated",
        entity_type="business_account",
        entity_id=business.id,
        before=before,
        after=after,
    )
    return business


def _active_owner_count(business_id: Any, *, exclude_membership_id: Any = None) -> int:
    qs = BusinessMembership.objects.filter(
        business_id=business_id, role=BusinessRole.OWNER, status=MembershipStatus.ACTIVE
    )
    if exclude_membership_id is not None:
        qs = qs.exclude(pk=exclude_membership_id)
    return qs.count()


@transaction.atomic
def add_member(
    *, actor: Any, business: BusinessAccount, phone: str, role: str
) -> BusinessMembership:
    if role not in BusinessRole.values:
        raise DomainError(f"Unknown role {role!r}.", code="validation_error")
    normalized = normalize_phone(phone)
    user, _created = User.objects.get_or_create_by_phone(normalized)

    membership, created = BusinessMembership.objects.select_for_update().get_or_create(
        business=business,
        user=user,
        defaults={
            "role": role,
            "status": MembershipStatus.ACTIVE,
            "invited_by": _audit_actor(actor),
        },
    )
    if not created:
        if membership.status == MembershipStatus.ACTIVE:
            raise ConflictError("That user is already a member of this business.", code="conflict")
        membership.status = MembershipStatus.ACTIVE
        membership.role = role
        membership.invited_by = _audit_actor(actor)
        membership.save(update_fields=["status", "role", "invited_by", "updated_at"])

    audit.record(
        actor=actor,
        action="business.member.added",
        entity_type="business_membership",
        entity_id=membership.id,
        after={"business_id": str(business.id), "user_id": str(user.id), "role": role},
    )
    emit(
        event_type=MEMBER_ADDED_EVENT,
        aggregate_type="business_membership",
        aggregate_id=str(membership.id),
        payload={
            "business_id": str(business.id),
            "user_id": str(user.id),
            "role": role,
            "added_by": str(getattr(_audit_actor(actor), "id", "")),
        },
    )
    return membership


@transaction.atomic
def update_membership(
    *,
    actor: Any,
    business: BusinessAccount,
    membership: BusinessMembership,
    role: str | None = None,
    status: str | None = None,
) -> BusinessMembership:
    membership = BusinessMembership.objects.select_for_update().get(pk=membership.pk)
    if membership.business_id != business.id:
        raise DomainError("Membership does not belong to this business.", code="not_found")

    before = {"role": membership.role, "status": membership.status}
    would_lose_owner = (
        membership.role == BusinessRole.OWNER
        and membership.status == MembershipStatus.ACTIVE
        and (
            (role is not None and role != BusinessRole.OWNER)
            or (status is not None and status != MembershipStatus.ACTIVE)
        )
    )
    if (
        would_lose_owner
        and _active_owner_count(business.id, exclude_membership_id=membership.id) == 0
    ):
        raise ConflictError("A business must keep at least one active owner.", code="last_owner")

    if role is not None:
        if role not in BusinessRole.values:
            raise DomainError(f"Unknown role {role!r}.", code="validation_error")
        membership.role = role
    if status is not None:
        if status not in MembershipStatus.values:
            raise DomainError(f"Unknown status {status!r}.", code="validation_error")
        membership.status = status

    membership.save(update_fields=["role", "status", "updated_at"])
    audit.record(
        actor=actor,
        action="business.member.updated",
        entity_type="business_membership",
        entity_id=membership.id,
        before=before,
        after={"role": membership.role, "status": membership.status},
    )
    return membership


@transaction.atomic
def remove_member(*, actor: Any, business: BusinessAccount, membership: BusinessMembership) -> None:
    membership = BusinessMembership.objects.select_for_update().get(pk=membership.pk)
    if membership.business_id != business.id:
        raise DomainError("Membership does not belong to this business.", code="not_found")
    if (
        membership.role == BusinessRole.OWNER
        and membership.status == MembershipStatus.ACTIVE
        and _active_owner_count(business.id, exclude_membership_id=membership.id) == 0
    ):
        raise ConflictError("A business must keep at least one active owner.", code="last_owner")

    before = {"role": membership.role, "status": membership.status}
    membership.status = MembershipStatus.REMOVED
    membership.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="business.member.removed",
        entity_type="business_membership",
        entity_id=membership.id,
        before=before,
        after={"status": membership.status},
    )


# ─── Locations ────────────────────────────────────────────────────────
_LOCATION_FIELDS = (
    "label",
    "address_text",
    "lat",
    "lng",
    "contact_name",
    "contact_phone",
    "hours",
    "access_notes",
)


def locations_for(business: BusinessAccount) -> QuerySet[BusinessLocation]:
    return business.locations.filter(deactivated_at__isnull=True).order_by("type", "label")


def _demote_existing_main(business: BusinessAccount, *, keep_id: Any = None) -> None:
    qs = BusinessLocation.objects.filter(
        business=business, type=LocationType.MAIN, deactivated_at__isnull=True
    )
    if keep_id is not None:
        qs = qs.exclude(pk=keep_id)
    qs.update(type=LocationType.BRANCH, updated_at=timezone.now())


@transaction.atomic
def create_location(
    *, actor: Any, business: BusinessAccount, data: dict[str, Any]
) -> BusinessLocation:
    location_type = str(data.get("type", ""))
    if location_type not in LocationType.values:
        raise DomainError(f"Unknown location type {location_type!r}.", code="validation_error")
    if location_type == LocationType.MAIN:
        _demote_existing_main(business)

    location = BusinessLocation.objects.create(
        business=business,
        type=location_type,
        label=str(data.get("label", "")).strip(),
        address_text=str(data.get("address_text", "")).strip(),
        lat=data.get("lat"),
        lng=data.get("lng"),
        zone_id=data.get("zone_id"),
        contact_name=str(data.get("contact_name", "")).strip(),
        contact_phone=str(data.get("contact_phone", "")).strip(),
        hours=data.get("hours") or {},
        access_notes=str(data.get("access_notes", "")).strip(),
    )
    audit.record(
        actor=actor,
        action="business.location.added",
        entity_type="business_location",
        entity_id=location.id,
        after={"business_id": str(business.id), "type": location.type, "label": location.label},
    )
    return location


@transaction.atomic
def update_location(
    *, actor: Any, business: BusinessAccount, location: BusinessLocation, data: dict[str, Any]
) -> BusinessLocation:
    location = BusinessLocation.objects.select_for_update().get(pk=location.pk)
    if location.business_id != business.id or location.deactivated_at is not None:
        raise DomainError("Location not found for this business.", code="not_found")

    before: dict[str, Any] = {}
    changed: list[str] = []
    for field in _LOCATION_FIELDS:
        if field in data and data[field] is not None:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            if value != getattr(location, field):
                before[field] = getattr(location, field)
                setattr(location, field, value)
                changed.append(field)

    new_type = data.get("type")
    if new_type is not None and new_type != location.type:
        if new_type not in LocationType.values:
            raise DomainError(f"Unknown location type {new_type!r}.", code="validation_error")
        if new_type == LocationType.MAIN:
            _demote_existing_main(business, keep_id=location.id)
        before["type"] = location.type
        location.type = new_type
        changed.append("type")

    if not changed:
        return location

    location.save(update_fields=[*changed, "updated_at"])
    audit.record(
        actor=actor,
        action="business.location.updated",
        entity_type="business_location",
        entity_id=location.id,
        before=before,
        after={f: getattr(location, f) for f in changed},
    )
    return location


@transaction.atomic
def deactivate_location(
    *, actor: Any, business: BusinessAccount, location: BusinessLocation
) -> None:
    location = BusinessLocation.objects.select_for_update().get(pk=location.pk)
    if location.business_id != business.id:
        raise DomainError("Location not found for this business.", code="not_found")
    if location.deactivated_at is not None:
        return
    location.deactivated_at = timezone.now()
    location.save(update_fields=["deactivated_at", "updated_at"])
    audit.record(
        actor=actor,
        action="business.location.deactivated",
        entity_type="business_location",
        entity_id=location.id,
        after={"deactivated_at": location.deactivated_at.isoformat()},
    )
