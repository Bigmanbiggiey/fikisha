"""Vehicle domain services. Every mutation is atomic with its audit row.
Authorization is run by the API layer first.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.groups.models import OperatorGroup
from fikisha.operators.models import OperatorProfile
from fikisha.platform_config.models import VehicleClass
from fikisha.vehicles.models import (
    OPERATOR_STATUSES,
    Vehicle,
    VehicleOwnership,
    VehicleStatus,
    normalize_registration,
)

_EDITABLE = (
    "sub_descriptor",
    "make",
    "model",
    "year",
    "capacity_value",
    "capacity_unit",
    "volume_m3",
    "tare_kg",
    "feature_tags",
    "ownership",
    "speed_limiter_fitted",
    "telematics_installed",
)


def _audit_actor(actor: Any) -> Any:
    return getattr(actor, "user", actor)


def vehicles_for_operator(profile: OperatorProfile) -> QuerySet[Vehicle]:
    return (
        Vehicle.objects.filter(owner_operator=profile, deactivated_at__isnull=True)
        .select_related("vehicle_class")
        .order_by("-created_at")
    )


def vehicles_for_group(group: OperatorGroup) -> QuerySet[Vehicle]:
    return (
        Vehicle.objects.filter(owner_group=group, deactivated_at__isnull=True)
        .select_related("vehicle_class")
        .order_by("-created_at")
    )


@transaction.atomic
def register_vehicle(
    *,
    actor: Any,
    owner_operator: OperatorProfile | None = None,
    owner_group: OperatorGroup | None = None,
    vehicle_class_code: str,
    registration: str,
    capacity_value: Any,
    capacity_unit: str = "KG",
    **fields: Any,
) -> Vehicle:
    if bool(owner_operator) == bool(owner_group):
        raise DomainError(
            "A vehicle must be controlled by exactly one operator or one group.",
            code="validation_error",
        )
    try:
        klass = VehicleClass.objects.get(code=vehicle_class_code, active=True)
    except VehicleClass.DoesNotExist as exc:
        raise DomainError(
            f"Unknown vehicle class {vehicle_class_code!r}.", code="validation_error"
        ) from exc

    norm = normalize_registration(registration)
    if not norm:
        raise DomainError("A registration number is required.", code="validation_error")
    if Vehicle.objects.filter(registration_normalized=norm, deactivated_at__isnull=True).exists():
        raise ConflictError(
            "An active vehicle with that registration already exists.", code="conflict"
        )

    clean: dict[str, Any] = {k: v for k, v in fields.items() if k in _EDITABLE and v is not None}
    if clean.get("ownership") and clean["ownership"] not in VehicleOwnership.values:
        raise DomainError("Unknown ownership value.", code="validation_error")

    vehicle = Vehicle.objects.create(
        owner_operator=owner_operator,
        owner_group=owner_group,
        vehicle_class=klass,
        registration=registration.strip(),
        capacity_value=capacity_value,
        capacity_unit=capacity_unit,
        **clean,
    )
    audit.record(
        actor=actor,
        action="vehicle.registered",
        entity_type="vehicle",
        entity_id=vehicle.id,
        after={
            "registration": vehicle.registration,
            "class": klass.code,
            "controller": vehicle.controller_kind,
        },
    )
    return vehicle


@transaction.atomic
def update_vehicle(*, actor: Any, vehicle: Vehicle, patch: dict[str, Any]) -> Vehicle:
    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
    if vehicle.deactivated_at is not None:
        raise DomainError("This vehicle has been deactivated.", code="not_found")

    before: dict[str, Any] = {}
    changed: list[str] = []
    for field in _EDITABLE:
        if field in patch and patch[field] is not None:
            value = patch[field]
            if value != getattr(vehicle, field):
                before[field] = getattr(vehicle, field)
                setattr(vehicle, field, value)
                changed.append(field)

    if patch.get("vehicle_class_code"):
        try:
            klass = VehicleClass.objects.get(code=patch["vehicle_class_code"], active=True)
        except VehicleClass.DoesNotExist as exc:
            raise DomainError("Unknown vehicle class.", code="validation_error") from exc
        if klass.id != vehicle.vehicle_class_id:
            before["vehicle_class"] = vehicle.vehicle_class.code
            vehicle.vehicle_class = klass
            changed.append("vehicle_class")

    if patch.get("registration"):
        norm = normalize_registration(patch["registration"])
        if norm != vehicle.registration_normalized:
            if (
                Vehicle.objects.filter(registration_normalized=norm, deactivated_at__isnull=True)
                .exclude(pk=vehicle.pk)
                .exists()
            ):
                raise ConflictError(
                    "An active vehicle with that registration already exists.", code="conflict"
                )
            before["registration"] = vehicle.registration
            vehicle.registration = patch["registration"].strip()
            changed.append("registration")

    if not changed:
        return vehicle

    vehicle.save()
    audit.record(
        actor=actor,
        action="vehicle.updated",
        entity_type="vehicle",
        entity_id=vehicle.id,
        before=before,
        after={f: str(getattr(vehicle, f)) for f in changed},
    )
    return vehicle


@transaction.atomic
def set_status(
    *, actor: Any, vehicle: Vehicle, status: str, reason: str = "", is_platform_admin: bool = False
) -> Vehicle:
    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
    if status not in VehicleStatus.values:
        raise DomainError(f"Unknown status {status!r}.", code="validation_error")
    if status == VehicleStatus.SUSPENDED and not is_platform_admin:
        raise AuthorizationError(
            "Only a platform administrator can suspend a vehicle.", code="authz.forbidden"
        )
    if (
        vehicle.status == VehicleStatus.SUSPENDED
        and status != VehicleStatus.SUSPENDED
        and not is_platform_admin
    ):
        raise AuthorizationError(
            "Only a platform administrator can lift a suspension.", code="authz.forbidden"
        )
    if (
        status in OPERATOR_STATUSES
        and vehicle.status == VehicleStatus.SUSPENDED
        and not is_platform_admin
    ):
        raise AuthorizationError("Vehicle is suspended.", code="authz.forbidden")

    if status == vehicle.status:
        return vehicle
    before = {"status": vehicle.status}
    vehicle.status = status
    vehicle.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="vehicle.status_changed",
        entity_type="vehicle",
        entity_id=vehicle.id,
        before=before,
        after={"status": status, "reason": reason},
    )
    return vehicle


@transaction.atomic
def deactivate_vehicle(*, actor: Any, vehicle: Vehicle, reason: str = "") -> None:
    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
    if vehicle.deactivated_at is not None:
        return
    vehicle.deactivated_at = timezone.now()
    vehicle.status = VehicleStatus.INACTIVE
    vehicle.save(update_fields=["deactivated_at", "status", "updated_at"])
    audit.record(
        actor=actor,
        action="vehicle.deactivated",
        entity_type="vehicle",
        entity_id=vehicle.id,
        after={"deactivated_at": vehicle.deactivated_at.isoformat(), "reason": reason},
    )


def controlled_by_query(profile_ids: list[Any], group_ids: list[Any]) -> Q:
    return Q(owner_operator_id__in=profile_ids) | Q(owner_group_id__in=group_ids)
