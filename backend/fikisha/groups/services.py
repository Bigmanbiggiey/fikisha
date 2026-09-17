"""Operator Group domain services (Phase 1 domain-architecture §3.4).

State changes go through here, each atomic with its audit row. Authorization is
run by the API layer before these are called.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import OuterRef, QuerySet, Subquery

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.groups.models import (
    AssignmentMode,
    GroupMemberRole,
    GroupMembership,
    GroupMembershipStatus,
    GroupStanding,
    GroupType,
    OperatorGroup,
)
from fikisha.identity.models import User
from fikisha.operators.models import OperatorProfile

MEMBER_ADDED_EVENT = "group.member.added"

_EDITABLE_FIELDS = ("name", "assignment_mode")


def _audit_actor(actor: Any) -> Any:
    return getattr(actor, "user", actor)


def display_name_for(group_id: Any) -> str | None:
    """The group's public name — for another module (e.g. negotiation) to
    label a counterparty without reaching through the FK into this module's
    model fields directly (module boundary rule)."""
    return OperatorGroup.objects.filter(id=group_id).values_list("name", flat=True).first()


def groups_for(user: User) -> QuerySet[OperatorGroup]:
    """List a user's groups, each annotated with ``my_role`` (the requesting
    user's own active role on that group) so ``GroupSerializer`` — a
    per-object ``SerializerMethodField`` — can render it correctly across a
    list, not just the single-object create/detail views (see ADR-2B-11 /
    businesses_for's identical annotation)."""
    my_active_role = GroupMembership.objects.filter(
        group_id=OuterRef("pk"), operator__user=user, status=GroupMembershipStatus.ACTIVE
    ).values("role")[:1]
    return (
        OperatorGroup.objects.filter(
            memberships__operator__user=user,
            memberships__status=GroupMembershipStatus.ACTIVE,
        )
        .annotate(my_role=Subquery(my_active_role))
        .distinct()
        .order_by("-created_at")
    )


@transaction.atomic
def create_group(
    *,
    actor: Any,
    name: str,
    type: str,
    assignment_mode: str = AssignmentMode.MANAGER_ASSIGNS,
) -> OperatorGroup:
    if type not in GroupType.values:
        raise DomainError(f"Unknown group type {type!r}.", code="validation_error")
    if assignment_mode not in AssignmentMode.values:
        raise DomainError(f"Unknown assignment mode {assignment_mode!r}.", code="validation_error")
    user = _audit_actor(actor)
    owner_profile = OperatorProfile.objects.filter(user=user).first()
    if owner_profile is None:
        raise DomainError(
            "An operator profile is required to create a group.", code="operator_profile_required"
        )
    if GroupMembership.objects.filter(
        operator=owner_profile, status=GroupMembershipStatus.ACTIVE
    ).exists():
        raise ConflictError(
            "This operator is already an active member of a group.", code="already_in_group"
        )

    group = OperatorGroup.objects.create(
        name=name.strip(), type=type, primary_contact=user, assignment_mode=assignment_mode
    )
    membership = GroupMembership.objects.create(
        group=group,
        operator=owner_profile,
        role=GroupMemberRole.OWNER,
        status=GroupMembershipStatus.ACTIVE,
        added_by=user,
    )
    audit.record(
        actor=actor,
        action="group.created",
        entity_type="operator_group",
        entity_id=group.id,
        after={"name": group.name, "type": group.type},
    )
    audit.record(
        actor=actor,
        action="group.member.added",
        entity_type="group_membership",
        entity_id=membership.id,
        after={"group_id": str(group.id), "operator_id": str(owner_profile.id), "role": "OWNER"},
    )
    return group


@transaction.atomic
def update_group(
    *,
    actor: Any,
    group: OperatorGroup,
    patch: dict[str, Any],
    is_platform_admin: bool = False,
) -> OperatorGroup:
    group = OperatorGroup.objects.select_for_update().get(pk=group.pk)
    before: dict[str, Any] = {}
    changed: list[str] = []

    if "name" in patch and patch["name"] is not None:
        value = str(patch["name"]).strip()
        if value != group.name:
            before["name"] = group.name
            group.name = value
            changed.append("name")
    if "assignment_mode" in patch and patch["assignment_mode"] is not None:
        value = str(patch["assignment_mode"])
        if value not in AssignmentMode.values:
            raise DomainError(f"Unknown assignment mode {value!r}.", code="validation_error")
        if value != group.assignment_mode:
            before["assignment_mode"] = group.assignment_mode
            group.assignment_mode = value
            changed.append("assignment_mode")
    if "standing" in patch and patch["standing"] is not None:
        if not is_platform_admin:
            raise AuthorizationError(
                "Only a platform administrator can change a group's standing.",
                code="authz.forbidden",
            )
        value = str(patch["standing"])
        if value not in GroupStanding.values:
            raise DomainError(f"Unknown standing {value!r}.", code="validation_error")
        if value != group.standing:
            before["standing"] = group.standing
            group.standing = value
            changed.append("standing")

    if not changed:
        return group
    group.save(update_fields=[*changed, "updated_at"])
    audit.record(
        actor=actor,
        action="group.updated",
        entity_type="operator_group",
        entity_id=group.id,
        before=before,
        after={f: getattr(group, f) for f in changed},
    )
    return group


def _active_owner_count(group_id: Any, *, exclude_membership_id: Any = None) -> int:
    qs = GroupMembership.objects.filter(
        group_id=group_id, role=GroupMemberRole.OWNER, status=GroupMembershipStatus.ACTIVE
    )
    if exclude_membership_id is not None:
        qs = qs.exclude(pk=exclude_membership_id)
    return qs.count()


@transaction.atomic
def add_member(
    *, actor: Any, group: OperatorGroup, operator: OperatorProfile, role: str
) -> GroupMembership:
    if role not in GroupMemberRole.values:
        raise DomainError(f"Unknown role {role!r}.", code="validation_error")

    membership = (
        GroupMembership.objects.select_for_update().filter(group=group, operator=operator).first()
    )
    if membership is not None and membership.status == GroupMembershipStatus.ACTIVE:
        raise ConflictError("That operator is already a member of this group.", code="conflict")
    if (
        GroupMembership.objects.filter(operator=operator, status=GroupMembershipStatus.ACTIVE)
        .exclude(group=group)
        .exists()
    ):
        raise ConflictError(
            "That operator is already an active member of another group.", code="already_in_group"
        )

    if membership is None:
        membership = GroupMembership.objects.create(
            group=group,
            operator=operator,
            role=role,
            status=GroupMembershipStatus.ACTIVE,
            added_by=_audit_actor(actor),
        )
    else:
        membership.role = role
        membership.status = GroupMembershipStatus.ACTIVE
        membership.added_by = _audit_actor(actor)
        membership.save(update_fields=["role", "status", "added_by", "updated_at"])

    audit.record(
        actor=actor,
        action="group.member.added",
        entity_type="group_membership",
        entity_id=membership.id,
        after={"group_id": str(group.id), "operator_id": str(operator.id), "role": role},
    )
    from fikisha.outbox.services import emit

    emit(
        event_type=MEMBER_ADDED_EVENT,
        aggregate_type="group_membership",
        aggregate_id=str(membership.id),
        payload={
            "group_id": str(group.id),
            "operator_id": str(operator.id),
            "role": role,
            "added_by": str(getattr(_audit_actor(actor), "id", "")),
        },
    )
    return membership


@transaction.atomic
def update_member(
    *,
    actor: Any,
    group: OperatorGroup,
    membership: GroupMembership,
    role: str | None = None,
    status: str | None = None,
) -> GroupMembership:
    membership = GroupMembership.objects.select_for_update().get(pk=membership.pk)
    if membership.group_id != group.id:
        raise DomainError("Membership does not belong to this group.", code="not_found")

    before = {"role": membership.role, "status": membership.status}
    would_lose_owner = (
        membership.role == GroupMemberRole.OWNER
        and membership.status == GroupMembershipStatus.ACTIVE
        and (
            (role is not None and role != GroupMemberRole.OWNER)
            or (status is not None and status != GroupMembershipStatus.ACTIVE)
        )
    )
    if would_lose_owner and _active_owner_count(group.id, exclude_membership_id=membership.id) == 0:
        raise ConflictError("A group must keep at least one active owner.", code="last_owner")

    if role is not None:
        if role not in GroupMemberRole.values:
            raise DomainError(f"Unknown role {role!r}.", code="validation_error")
        membership.role = role
    if status is not None:
        if status not in GroupMembershipStatus.values:
            raise DomainError(f"Unknown status {status!r}.", code="validation_error")
        if status == GroupMembershipStatus.ACTIVE and membership.status != status:
            clash = (
                GroupMembership.objects.filter(
                    operator=membership.operator, status=GroupMembershipStatus.ACTIVE
                )
                .exclude(pk=membership.pk)
                .exists()
            )
            if clash:
                raise ConflictError(
                    "That operator is already active in another group.", code="already_in_group"
                )
        membership.status = status

    membership.save(update_fields=["role", "status", "updated_at"])
    audit.record(
        actor=actor,
        action="group.member.updated",
        entity_type="group_membership",
        entity_id=membership.id,
        before=before,
        after={"role": membership.role, "status": membership.status},
    )
    return membership


@transaction.atomic
def remove_member(*, actor: Any, group: OperatorGroup, membership: GroupMembership) -> None:
    membership = GroupMembership.objects.select_for_update().get(pk=membership.pk)
    if membership.group_id != group.id:
        raise DomainError("Membership does not belong to this group.", code="not_found")
    if (
        membership.role == GroupMemberRole.OWNER
        and membership.status == GroupMembershipStatus.ACTIVE
        and _active_owner_count(group.id, exclude_membership_id=membership.id) == 0
    ):
        raise ConflictError("A group must keep at least one active owner.", code="last_owner")

    before = {"role": membership.role, "status": membership.status}
    membership.status = GroupMembershipStatus.INACTIVE
    membership.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="group.member.removed",
        entity_type="group_membership",
        entity_id=membership.id,
        before=before,
        after={"status": membership.status},
    )
