"""Vehicle services — mutation paths not covered by the API happy-path tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.identity.authz.actors import actor_from_user
from fikisha.operators import services as op_services
from fikisha.vehicles import services
from fikisha.vehicles.models import VehicleStatus

pytestmark = pytest.mark.django_db


def _actor(u: Any) -> Any:
    return actor_from_user(u)


@pytest.fixture
def vehicle(user: Any) -> Any:
    prof = op_services.create_profile(actor=_actor(user), full_name="Op")
    return services.register_vehicle(
        actor=_actor(user),
        owner_operator=prof,
        vehicle_class_code="PICKUP",
        registration="KAA 1A",
        capacity_value=Decimal("500"),
    )


def test_update_fields_and_class_and_registration(user: Any, vehicle: Any) -> None:
    updated = services.update_vehicle(
        actor=_actor(user),
        vehicle=vehicle,
        patch={"make": "Toyota", "year": 2019, "vehicle_class_code": "CANTER"},
    )
    assert updated.make == "Toyota"
    assert updated.year == 2019
    assert updated.vehicle_class.code == "CANTER"

    again = services.update_vehicle(
        actor=_actor(user), vehicle=vehicle, patch={"registration": "kbb-2b"}
    )
    assert again.registration_normalized == "KBB2B"


def test_update_noop_returns_same(user: Any, vehicle: Any) -> None:
    same = services.update_vehicle(actor=_actor(user), vehicle=vehicle, patch={})
    assert same.pk == vehicle.pk


def test_update_registration_conflict(user: Any, vehicle: Any) -> None:
    prof = vehicle.owner_operator
    services.register_vehicle(
        actor=_actor(user),
        owner_operator=prof,
        vehicle_class_code="PICKUP",
        registration="KZZ 9Z",
        capacity_value=1,
    )
    with pytest.raises(ConflictError):
        services.update_vehicle(
            actor=_actor(user), vehicle=vehicle, patch={"registration": "KZZ 9Z"}
        )


def test_update_bad_class(user: Any, vehicle: Any) -> None:
    with pytest.raises(DomainError):
        services.update_vehicle(
            actor=_actor(user), vehicle=vehicle, patch={"vehicle_class_code": "HOVERCRAFT"}
        )


def test_status_transitions_and_suspend_rules(user: Any, platform_admin: Any, vehicle: Any) -> None:
    services.set_status(actor=_actor(user), vehicle=vehicle, status=VehicleStatus.ACTIVE)
    # non-admin cannot suspend
    with pytest.raises(AuthorizationError):
        services.set_status(actor=_actor(user), vehicle=vehicle, status=VehicleStatus.SUSPENDED)
    # admin suspends
    services.set_status(
        actor=_actor(platform_admin),
        vehicle=vehicle,
        status=VehicleStatus.SUSPENDED,
        is_platform_admin=True,
    )
    vehicle.refresh_from_db()
    assert vehicle.status == VehicleStatus.SUSPENDED
    # non-admin cannot move it off SUSPENDED
    with pytest.raises(AuthorizationError):
        services.set_status(actor=_actor(user), vehicle=vehicle, status=VehicleStatus.ACTIVE)
    # admin lifts it
    services.set_status(
        actor=_actor(platform_admin),
        vehicle=vehicle,
        status=VehicleStatus.INACTIVE,
        is_platform_admin=True,
    )
    vehicle.refresh_from_db()
    assert vehicle.status == VehicleStatus.INACTIVE


def test_status_noop_and_bad_status(user: Any, vehicle: Any) -> None:
    same = services.set_status(actor=_actor(user), vehicle=vehicle, status=vehicle.status)
    assert same.status == vehicle.status
    with pytest.raises(DomainError):
        services.set_status(actor=_actor(user), vehicle=vehicle, status="FLYING")


def test_deactivate_is_idempotent(user: Any, vehicle: Any) -> None:
    services.deactivate_vehicle(actor=_actor(user), vehicle=vehicle, reason="sold")
    services.deactivate_vehicle(actor=_actor(user), vehicle=vehicle)  # no error
    vehicle.refresh_from_db()
    assert vehicle.deactivated_at is not None
    with pytest.raises(DomainError):
        services.update_vehicle(actor=_actor(user), vehicle=vehicle, patch={"make": "X"})
