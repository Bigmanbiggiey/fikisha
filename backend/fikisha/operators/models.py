"""Operator + operating-location data model (Phase 1 database-design §4.3,
functional-requirements FR-A-5 / FR-O-2, operator-model §1 / §3).

Deliberately NOT here in Phase 2B: vehicles, verification records, trust level,
service areas, availability, payout details. Those belong to later phases and to
other modules.

``OperatingBase`` is a first-class place (a stage / base / yard). It is not
"owned" — an operator or a group declares a *presence* at it through
``BaseMembership``. A base can also be created directly by an operator, so a
physical operating location does not require formal membership of a shared stage
(operator-model §3, Phase 2B brief §20).
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from fikisha.common.models import TimestampedModel


class OperatorStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    RESTRICTED = "RESTRICTED", "Restricted"
    SUSPENDED = "SUSPENDED", "Suspended"
    OFFBOARDED = "OFFBOARDED", "Offboarded"


class BaseType(models.TextChoices):
    STAGE = "STAGE", "Stage"
    BASE = "BASE", "Base"
    YARD = "YARD", "Yard"
    WAITING_AREA = "WAITING_AREA", "Waiting area"


class BaseMembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class OperatorProfile(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="operator_profile"
    )
    full_name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=120, blank=True, default="")
    phones = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
        help_text="Additional contact numbers; the login phone lives on User.",
    )
    status = models.CharField(
        max_length=16, choices=OperatorStatus.choices, default=OperatorStatus.PENDING
    )

    class Meta:
        db_table = "operator_profile"
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.id})"

    @property
    def is_operational(self) -> bool:
        return self.status not in {OperatorStatus.SUSPENDED, OperatorStatus.OFFBOARDED}


class OperatingBase(TimestampedModel):
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=BaseType.choices)
    # Plain lat/lng (no PostGIS in 2B — see docs/phase-2/phase-2b-decisions.md).
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    zone = models.ForeignKey(
        "platform_config.Zone",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    landmark = models.CharField(max_length=200, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "operating_base"
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["zone"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


class BaseMembership(TimestampedModel):
    """An operator OR a group declares operating presence at a base.

    Exactly one of ``operator`` / ``group`` is set (two nullable typed FKs rather
    than a raw polymorphic column — Phase 1 database-design §4.3).
    """

    base = models.ForeignKey(OperatingBase, on_delete=models.CASCADE, related_name="memberships")
    operator = models.ForeignKey(
        OperatorProfile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="base_memberships",
    )
    group = models.ForeignKey(
        "groups.OperatorGroup",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="base_memberships",
    )
    role = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Free text (e.g. owner / member): a claim of presence, not formal ownership.",
    )
    status = models.CharField(
        max_length=16, choices=BaseMembershipStatus.choices, default=BaseMembershipStatus.ACTIVE
    )

    class Meta:
        db_table = "base_membership"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(operator__isnull=False, group__isnull=True)
                    | models.Q(operator__isnull=True, group__isnull=False)
                ),
                name="base_membership_exactly_one_party",
            ),
            models.UniqueConstraint(
                fields=["base", "operator"],
                condition=models.Q(operator__isnull=False),
                name="uniq_base_operator",
            ),
            models.UniqueConstraint(
                fields=["base", "group"],
                condition=models.Q(group__isnull=False),
                name="uniq_base_group",
            ),
        ]
        indexes = [models.Index(fields=["base", "status"])]

    def __str__(self) -> str:
        party = self.operator_id or self.group_id
        return f"{party} @ base {self.base_id} ({self.status})"
