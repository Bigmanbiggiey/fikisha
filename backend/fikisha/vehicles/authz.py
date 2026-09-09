"""Authorization helpers for the Vehicles module.

Control of a vehicle follows the Phase 2B actor graph:
  * an individual operator controls vehicles whose ``owner_operator`` is their
    own ``OperatorProfile``;
  * a group ``OWNER`` / ``MANAGER`` controls the group's vehicles (reusing
    ``groups.authz``); a group ``DRIVER`` does not.
"""

from __future__ import annotations

from typing import Any

from fikisha.groups.authz import can_manage as group_can_manage
from fikisha.groups.authz import is_member as group_is_member
from fikisha.operators.models import OperatorProfile
from fikisha.vehicles.models import Vehicle


def _actor_profile_id(actor: Any) -> Any | None:
    user_id = getattr(getattr(actor, "user", None), "id", None)
    if user_id is None:
        return None
    return OperatorProfile.objects.filter(user_id=user_id).values_list("id", flat=True).first()


def can_view(actor: Any, vehicle: Vehicle) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    if vehicle.owner_operator_id is not None:
        return str(vehicle.owner_operator_id) == str(_actor_profile_id(actor))
    return group_is_member(actor, {"group_id": vehicle.owner_group_id})


def can_manage(actor: Any, vehicle: Vehicle) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    if vehicle.owner_operator_id is not None:
        return str(vehicle.owner_operator_id) == str(_actor_profile_id(actor))
    return group_can_manage(actor, {"group_id": vehicle.owner_group_id})
