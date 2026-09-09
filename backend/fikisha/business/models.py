"""Business data model (Phase 1 database-design §4.2, functional-requirements FR-A / FR-B).

Kept intentionally small — this is not accounting / ERP / CRM / fleet software.
No verification workflow lives here (that is a later phase); ``verification_status``
is an inert field so the shape exists for the future.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import TimestampedModel


class BusinessStanding(models.TextChoices):
    GOOD = "GOOD", "Good"
    RESTRICTED = "RESTRICTED", "Restricted"
    SUSPENDED = "SUSPENDED", "Suspended"


class BusinessVerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified"
    VERIFIED = "VERIFIED", "Verified"


class BusinessRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    DISPATCHER = "DISPATCHER", "Dispatcher"
    VIEWER = "VIEWER", "Viewer"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    REMOVED = "REMOVED", "Removed"


class LocationType(models.TextChoices):
    MAIN = "MAIN", "Main"
    BRANCH = "BRANCH", "Branch"
    WAREHOUSE = "WAREHOUSE", "Warehouse"
    STORE = "STORE", "Store"
    PICKUP_POINT = "PICKUP_POINT", "Pickup point"


class BusinessAccount(TimestampedModel):
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_businesses",
    )
    trading_name = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True, default="")
    contact_name = models.CharField(max_length=120, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    standing = models.CharField(
        max_length=16, choices=BusinessStanding.choices, default=BusinessStanding.GOOD
    )
    verification_status = models.CharField(
        max_length=16,
        choices=BusinessVerificationStatus.choices,
        default=BusinessVerificationStatus.UNVERIFIED,
    )

    class Meta:
        db_table = "business_account"
        indexes = [
            models.Index(fields=["owner_user"]),
            models.Index(fields=["standing"]),
        ]

    def __str__(self) -> str:
        return f"{self.trading_name} ({self.id})"

    @property
    def is_operational(self) -> bool:
        return self.standing != BusinessStanding.SUSPENDED


class BusinessMembership(TimestampedModel):
    business = models.ForeignKey(
        BusinessAccount, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_memberships"
    )
    role = models.CharField(max_length=16, choices=BusinessRole.choices)
    status = models.CharField(
        max_length=16, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "business_membership"
        constraints = [
            models.UniqueConstraint(fields=["business", "user"], name="uniq_business_member"),
        ]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.business_id} ({self.role}/{self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == MembershipStatus.ACTIVE


class BusinessLocation(TimestampedModel):
    business = models.ForeignKey(
        BusinessAccount, on_delete=models.CASCADE, related_name="locations"
    )
    label = models.CharField(max_length=120)
    type = models.CharField(max_length=16, choices=LocationType.choices)
    address_text = models.TextField(blank=True, default="")
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
    contact_name = models.CharField(max_length=120, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    hours = models.JSONField(default=dict, blank=True)
    access_notes = models.TextField(blank=True, default="")
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "business_location"
        constraints = [
            models.UniqueConstraint(
                fields=["business"],
                condition=models.Q(type="MAIN", deactivated_at__isnull=True),
                name="uniq_main_location_per_business",
            ),
        ]
        indexes = [
            models.Index(
                fields=["business"],
                condition=models.Q(deactivated_at__isnull=True),
                name="ix_active_business_location",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.type})"

    @property
    def is_active(self) -> bool:
        return self.deactivated_at is None
