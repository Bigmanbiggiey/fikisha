"""Authorization helpers for the Verification module.

Two kinds of caller:
  * the **subject owner** — the operator whose profile / whose vehicle / whose
    operating base the record is about, the OWNER of a business, or an OWNER /
    MANAGER of an operator group — may read it and submit evidence;
  * a **reviewer** — a user holding the ``verification.decide`` permission
    (pilot: Operations Officer or Platform Admin) — may read any record and act
    on it. A business user is neither.
"""

from __future__ import annotations

from typing import Any

from fikisha.groups.authz import is_member as group_is_member
from fikisha.operators.models import OperatingBase, OperatorProfile
from fikisha.vehicles.models import Vehicle
from fikisha.verification.models import VerificationRecord


def _actor_profile_id(actor: Any) -> Any | None:
    user_id = getattr(getattr(actor, "user", None), "id", None)
    if user_id is None:
        return None
    return OperatorProfile.objects.filter(user_id=user_id).values_list("id", flat=True).first()


def owns_subject(actor: Any, record: VerificationRecord) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    profile_id = _actor_profile_id(actor)
    actor_user_id = str(getattr(actor.user, "id", ""))

    if record.subject_operator_id is not None:
        return str(record.subject_operator_id) == str(profile_id)
    if record.subject_vehicle_id is not None:
        vehicle = Vehicle.objects.filter(pk=record.subject_vehicle_id).first()
        if vehicle is None:
            return False
        if vehicle.owner_operator_id is not None:
            return str(vehicle.owner_operator_id) == str(profile_id)
        return group_is_member(actor, {"group_id": vehicle.owner_group_id})
    if record.subject_base_id is not None:
        base = OperatingBase.objects.filter(pk=record.subject_base_id).first()
        return base is not None and str(base.created_by_id) == actor_user_id
    if record.subject_business_id is not None:
        return _owns_business(actor, record.subject_business_id)
    if record.subject_group_id is not None:
        return _manages_group(actor, record.subject_group_id)
    return False


def _owns_business(actor: Any, business_id: Any) -> bool:
    from fikisha.business import authz as business_authz

    return business_authz.is_owner(actor, {"business_id": business_id})


def _manages_group(actor: Any, group_id: Any) -> bool:
    from fikisha.groups import authz as group_authz
    from fikisha.groups.models import GroupMemberRole

    return group_authz.has_role(
        actor, {"group_id": group_id}, {GroupMemberRole.OWNER, GroupMemberRole.MANAGER}
    )


def can_submit_for(actor: Any, subject: Any) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    profile_id = _actor_profile_id(actor)
    actor_user_id = str(getattr(actor.user, "id", ""))

    if isinstance(subject, OperatorProfile):
        return str(subject.id) == str(profile_id)
    if isinstance(subject, Vehicle):
        if subject.owner_operator_id is not None:
            return str(subject.owner_operator_id) == str(profile_id)
        return group_is_member(actor, {"group_id": subject.owner_group_id})
    if isinstance(subject, OperatingBase):
        return str(subject.created_by_id) == actor_user_id
    from fikisha.business.models import BusinessAccount
    from fikisha.groups.models import OperatorGroup

    if isinstance(subject, BusinessAccount):
        return _owns_business(actor, subject.id)
    if isinstance(subject, OperatorGroup):
        return _manages_group(actor, subject.id)
    return False
