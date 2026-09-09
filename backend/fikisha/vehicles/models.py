"""Vehicle data model (Phase 1 database-design §4.3, operator-model §2).

A vehicle is controlled by **exactly one** party — an individual operator OR an
operator group (a DB CHECK enforces it). Ownership/control is fixed at
registration in 2C; changing it means deactivate + re-register (see
docs/phase-2/phase-2c-summary.md — known limitations).
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.db import models

from fikisha.common.models import TimestampedModel


class VehicleOwnership(models.TextChoices):
    OWNED = "OWNED", "Owned"
    AUTHORISED_DRIVER = "AUTHORISED_DRIVER", "Authorised driver"


class VehicleStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    UNDER_REPAIR = "UNDER_REPAIR", "Under repair"
    SUSPENDED = "SUSPENDED", "Suspended"  # admin-only (extends Phase 1's set — ADR-2C-02)


class CapacityUnit(models.TextChoices):
    KG = "KG", "Kilograms"
    TONNES = "TONNES", "Tonnes"


# Operator-settable statuses; SUSPENDED is administrative only.
OPERATOR_STATUSES = {VehicleStatus.ACTIVE, VehicleStatus.INACTIVE, VehicleStatus.UNDER_REPAIR}


def normalize_registration(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


class Vehicle(TimestampedModel):
    owner_operator = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    owner_group = models.ForeignKey(
        "groups.OperatorGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    vehicle_class = models.ForeignKey(
        "platform_config.VehicleClass", on_delete=models.PROTECT, related_name="+"
    )
    sub_descriptor = models.CharField(max_length=80, blank=True, default="")
    registration = models.CharField(max_length=32)
    registration_normalized = models.CharField(max_length=32, editable=False, db_index=True)
    make = models.CharField(max_length=60, blank=True, default="")
    model = models.CharField(max_length=60, blank=True, default="")
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    capacity_value = models.DecimalField(max_digits=10, decimal_places=2)
    capacity_unit = models.CharField(
        max_length=8, choices=CapacityUnit.choices, default=CapacityUnit.KG
    )
    volume_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tare_kg = models.PositiveIntegerField(null=True, blank=True)
    feature_tags = ArrayField(models.CharField(max_length=40), blank=True, default=list)
    ownership = models.CharField(
        max_length=20, choices=VehicleOwnership.choices, default=VehicleOwnership.OWNED
    )
    # Operator-declared claims. The *verified* facts live in the
    # HEAVY_CLASS_COMPLIANCE verification domain, not in these booleans.
    speed_limiter_fitted = models.BooleanField(null=True, blank=True)
    telematics_installed = models.BooleanField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=VehicleStatus.choices, default=VehicleStatus.INACTIVE
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vehicle"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(owner_operator__isnull=False, owner_group__isnull=True)
                    | models.Q(owner_operator__isnull=True, owner_group__isnull=False)
                ),
                name="vehicle_exactly_one_controller",
            ),
            models.UniqueConstraint(
                fields=["registration_normalized"],
                condition=models.Q(deactivated_at__isnull=True),
                name="uniq_active_vehicle_registration",
            ),
        ]
        indexes = [
            models.Index(fields=["owner_operator", "status"]),
            models.Index(fields=["owner_group", "status"]),
            models.Index(fields=["vehicle_class"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.registration_normalized = normalize_registration(self.registration)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.registration} ({self.vehicle_class_id})"

    @property
    def controller_kind(self) -> str:
        return "GROUP" if self.owner_group_id else "OPERATOR"

    @property
    def is_active(self) -> bool:
        return self.status == VehicleStatus.ACTIVE and self.deactivated_at is None
