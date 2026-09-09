"""Operator group data model (Phase 1 database-design §4.3, operator-model §1.1).

Minimal by design. ``standing`` is a plain admin lever here; the append-only
``group_standing_change`` history and ``payout`` details belong to later
(trust / commission) phases. ``verification_status`` is an inert field for the
future.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import TimestampedModel


class GroupType(models.TextChoices):
    YARD_OWNER = "YARD_OWNER", "Yard owner"
    FLEET = "FLEET", "Fleet"
    SACCO = "SACCO", "SACCO"
    PARTNERSHIP = "PARTNERSHIP", "Partnership"


class GroupStanding(models.TextChoices):
    GOOD = "GOOD", "Good"
    RESTRICTED = "RESTRICTED", "Restricted"
    SUSPENDED = "SUSPENDED", "Suspended"


class AssignmentMode(models.TextChoices):
    MANAGER_ASSIGNS = "MANAGER_ASSIGNS", "Manager assigns"
    DRIVER_ACCEPTS = "DRIVER_ACCEPTS", "Driver accepts"


class GroupVerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified"
    VERIFIED = "VERIFIED", "Verified"


class GroupMemberRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    MANAGER = "MANAGER", "Manager"
    DRIVER = "DRIVER", "Driver"


class GroupMembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class OperatorGroup(TimestampedModel):
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=GroupType.choices)
    primary_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="primary_contact_groups",
    )
    standing = models.CharField(
        max_length=16, choices=GroupStanding.choices, default=GroupStanding.GOOD
    )
    assignment_mode = models.CharField(
        max_length=20, choices=AssignmentMode.choices, default=AssignmentMode.MANAGER_ASSIGNS
    )
    verification_status = models.CharField(
        max_length=16,
        choices=GroupVerificationStatus.choices,
        default=GroupVerificationStatus.UNVERIFIED,
    )

    class Meta:
        db_table = "operator_group"
        indexes = [models.Index(fields=["standing"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"

    @property
    def is_operational(self) -> bool:
        return self.standing != GroupStanding.SUSPENDED


class GroupMembership(TimestampedModel):
    group = models.ForeignKey(OperatorGroup, on_delete=models.CASCADE, related_name="memberships")
    operator = models.ForeignKey(
        "operators.OperatorProfile", on_delete=models.CASCADE, related_name="group_memberships"
    )
    role = models.CharField(max_length=16, choices=GroupMemberRole.choices)
    status = models.CharField(
        max_length=16,
        choices=GroupMembershipStatus.choices,
        default=GroupMembershipStatus.ACTIVE,
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    since = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "group_membership"
        constraints = [
            models.UniqueConstraint(fields=["group", "operator"], name="uniq_group_member"),
            models.UniqueConstraint(
                fields=["operator"],
                condition=models.Q(status="ACTIVE"),
                name="uniq_active_group_per_operator",
            ),
        ]
        indexes = [models.Index(fields=["group", "role", "status"])]

    def __str__(self) -> str:
        return f"{self.operator_id} @ {self.group_id} ({self.role}/{self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == GroupMembershipStatus.ACTIVE
