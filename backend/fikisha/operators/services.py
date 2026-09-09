"""Operator + operating-location domain services (Phase 1 domain-architecture §3.3).

State changes go through here, each atomic with its audit row. Authorization is
run by the API layer before these are called.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import QuerySet

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.identity.models import User
from fikisha.operators.models import (
    BaseMembership,
    BaseMembershipStatus,
    BaseType,
    OperatingBase,
    OperatorProfile,
    OperatorStatus,
)

_PROFILE_FIELDS = ("full_name", "display_name", "phones")


def _audit_actor(actor: Any) -> Any:
    return getattr(actor, "user", actor)


def profile_for(user: User) -> OperatorProfile | None:
    return OperatorProfile.objects.filter(user=user).first()


@transaction.atomic
def create_profile(
    *, actor: Any, full_name: str, display_name: str = "", phones: list[str] | None = None
) -> OperatorProfile:
    user = _audit_actor(actor)
    if OperatorProfile.objects.filter(user=user).exists():
        raise ConflictError("This user already has an operator profile.", code="conflict")
    profile = OperatorProfile.objects.create(
        user=user,
        full_name=full_name.strip(),
        display_name=display_name.strip(),
        phones=[p.strip() for p in (phones or []) if p.strip()],
    )
    audit.record(
        actor=actor,
        action="operator.created",
        entity_type="operator_profile",
        entity_id=profile.id,
        after={"full_name": profile.full_name},
    )
    return profile


@transaction.atomic
def update_profile(
    *,
    actor: Any,
    profile: OperatorProfile,
    patch: dict[str, Any],
    is_platform_admin: bool = False,
) -> OperatorProfile:
    profile = OperatorProfile.objects.select_for_update().get(pk=profile.pk)
    before: dict[str, Any] = {}
    changed: list[str] = []

    for field in _PROFILE_FIELDS:
        if field in patch and patch[field] is not None:
            value = patch[field]
            if field == "phones":
                value = [str(p).strip() for p in value if str(p).strip()]
            else:
                value = str(value).strip()
            if value != getattr(profile, field):
                before[field] = getattr(profile, field)
                setattr(profile, field, value)
                changed.append(field)

    if "status" in patch and patch["status"] is not None:
        if not is_platform_admin:
            raise AuthorizationError(
                "Only a platform administrator can change an operator's status.",
                code="authz.forbidden",
            )
        new_status = str(patch["status"])
        if new_status not in OperatorStatus.values:
            raise DomainError(f"Unknown status {new_status!r}.", code="validation_error")
        if new_status != profile.status:
            before["status"] = profile.status
            profile.status = new_status
            changed.append("status")

    if not changed:
        return profile

    profile.save(update_fields=[*changed, "updated_at"])
    audit.record(
        actor=actor,
        action="operator.updated",
        entity_type="operator_profile",
        entity_id=profile.id,
        before=before,
        after={f: getattr(profile, f) for f in changed},
    )
    return profile


# ─── Operating locations (stage / base / yard) ───────────────────────
def bases(*, base_type: str | None = None, zone_id: Any = None) -> QuerySet[OperatingBase]:
    qs = OperatingBase.objects.select_related("zone").order_by("name")
    if base_type:
        qs = qs.filter(type=base_type)
    if zone_id:
        qs = qs.filter(zone_id=zone_id)
    return qs


@transaction.atomic
def create_base(*, actor: Any, data: dict[str, Any]) -> OperatingBase:
    base_type = str(data.get("type", ""))
    if base_type not in BaseType.values:
        raise DomainError(
            f"Unknown operating-location type {base_type!r}.", code="validation_error"
        )
    base = OperatingBase.objects.create(
        name=str(data.get("name", "")).strip(),
        type=base_type,
        lat=data.get("lat"),
        lng=data.get("lng"),
        zone_id=data.get("zone_id"),
        landmark=str(data.get("landmark", "")).strip(),
        created_by=_audit_actor(actor),
    )
    audit.record(
        actor=actor,
        action="operating_location.created",
        entity_type="operating_base",
        entity_id=base.id,
        after={"name": base.name, "type": base.type},
    )
    return base


@transaction.atomic
def update_base(*, actor: Any, base: OperatingBase, data: dict[str, Any]) -> OperatingBase:
    base = OperatingBase.objects.select_for_update().get(pk=base.pk)
    before: dict[str, Any] = {}
    changed: list[str] = []
    for field in ("name", "lat", "lng", "landmark", "zone_id"):
        key = field
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, str):
                value = value.strip()
            if value != getattr(base, field):
                before[field] = getattr(base, field)
                setattr(base, field, value)
                changed.append(field)
    new_type = data.get("type")
    if new_type is not None and new_type != base.type:
        if new_type not in BaseType.values:
            raise DomainError(f"Unknown type {new_type!r}.", code="validation_error")
        before["type"] = base.type
        base.type = new_type
        changed.append("type")

    if not changed:
        return base
    base.save(update_fields=[*changed, "updated_at"])
    audit.record(
        actor=actor,
        action="operating_location.updated",
        entity_type="operating_base",
        entity_id=base.id,
        before=before,
        after={f: getattr(base, f) for f in changed},
    )
    return base


@transaction.atomic
def associate_operator(
    *, actor: Any, base: OperatingBase, operator: OperatorProfile, role: str = ""
) -> BaseMembership:
    membership, created = BaseMembership.objects.select_for_update().get_or_create(
        base=base,
        operator=operator,
        defaults={"role": role.strip(), "status": BaseMembershipStatus.ACTIVE},
    )
    if not created and membership.status == BaseMembershipStatus.INACTIVE:
        membership.status = BaseMembershipStatus.ACTIVE
        membership.role = role.strip() or membership.role
        membership.save(update_fields=["status", "role", "updated_at"])
    elif not created:
        raise ConflictError("This operator already operates from that location.", code="conflict")

    audit.record(
        actor=actor,
        action="operating_location.operator_associated",
        entity_type="base_membership",
        entity_id=membership.id,
        after={"base_id": str(base.id), "operator_id": str(operator.id)},
    )
    return membership


@transaction.atomic
def associate_group(
    *, actor: Any, base: OperatingBase, group: Any, role: str = ""
) -> BaseMembership:
    membership, created = BaseMembership.objects.select_for_update().get_or_create(
        base=base,
        group=group,
        defaults={"role": role.strip(), "status": BaseMembershipStatus.ACTIVE},
    )
    if not created and membership.status == BaseMembershipStatus.INACTIVE:
        membership.status = BaseMembershipStatus.ACTIVE
        membership.save(update_fields=["status", "updated_at"])
    elif not created:
        raise ConflictError("This group already operates from that location.", code="conflict")
    audit.record(
        actor=actor,
        action="operating_location.group_associated",
        entity_type="base_membership",
        entity_id=membership.id,
        after={"base_id": str(base.id), "group_id": str(group.id)},
    )
    return membership


@transaction.atomic
def end_association(*, actor: Any, membership: BaseMembership) -> None:
    membership = BaseMembership.objects.select_for_update().get(pk=membership.pk)
    if membership.status == BaseMembershipStatus.INACTIVE:
        return
    membership.status = BaseMembershipStatus.INACTIVE
    membership.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="operating_location.association_ended",
        entity_type="base_membership",
        entity_id=membership.id,
        after={"status": membership.status},
    )
