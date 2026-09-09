"""Authorization helpers for the Verification module.

Two kinds of caller:
  * the **subject owner** — the operator whose profile / whose vehicle / whose
    operating base the record is about — may read it and submit evidence;
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
    return False


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
    return False
