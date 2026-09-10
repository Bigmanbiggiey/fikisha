"""Job-domain enums and the authoritative transition set.

Phase 2D. The 14 ``JobStatus`` values are taken **verbatim** from
``docs/phase-0/job-lifecycle.md`` / ``docs/phase-1/job-state-machine.md §1``
(D-JOB-3) — no additions, renames, or reordering.
"""

from __future__ import annotations

from django.db import models


class JobStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    REQUESTED = "REQUESTED", "Requested"
    NEGOTIATING = "NEGOTIATING", "Negotiating"
    CONFIRMED = "CONFIRMED", "Confirmed"
    ASSIGNED = "ASSIGNED", "Assigned"
    AT_PICKUP = "AT_PICKUP", "At pickup"
    PICKED_UP = "PICKED_UP", "Picked up"
    IN_TRANSIT = "IN_TRANSIT", "In transit"
    AT_DESTINATION = "AT_DESTINATION", "At destination"
    DELIVERED = "DELIVERED", "Delivered"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    DISPUTED = "DISPUTED", "Disputed"


#: Lifecycle-terminal states (no outbound transition except via DISPUTED entry).
TERMINAL_STATES: frozenset[str] = frozenset(
    {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED}
)

#: Goods are in operator custody in these states.
CUSTODY_STATES: frozenset[str] = frozenset(
    {JobStatus.PICKED_UP, JobStatus.IN_TRANSIT, JobStatus.AT_DESTINATION}
)

#: A DISPUTED job may be RESUMEd (later, founder-gated) only from one of these.
RESUMABLE_PRE_DISPUTE_STATES: frozenset[str] = frozenset(
    {
        JobStatus.ASSIGNED,
        JobStatus.AT_PICKUP,
        JobStatus.PICKED_UP,
        JobStatus.IN_TRANSIT,
        JobStatus.AT_DESTINATION,
        JobStatus.DELIVERED,
    }
)


class ValueBand(models.TextChoices):
    STANDARD = "STANDARD", "Standard"
    ELEVATED = "ELEVATED", "Elevated"
    HIGH = "HIGH", "High"
    VERY_HIGH = "VERY_HIGH", "Very high"


HIGH_VALUE_BANDS: frozenset[str] = frozenset({ValueBand.HIGH, ValueBand.VERY_HIGH})


class TrustLevel(models.TextChoices):
    """Interim trust levels (ADR-2D-05 Option b). The full Trust engine is a
    later phase; in 2D a driver's level is derived conservatively from
    verification facts and gates assignment via the configured value bands."""

    L1 = "L1", "L1 · verified"
    L2 = "L2", "L2 · established"
    L3 = "L3", "L3 · trusted"


class JobEventCategory(models.TextChoices):
    STATUS_TRANSITION = "STATUS_TRANSITION", "Status transition"
    CUSTODY = "CUSTODY", "Custody"
    SYSTEM = "SYSTEM", "System"
    ADMIN_ACTION = "ADMIN_ACTION", "Admin action"


class JobEventType(models.TextChoices):
    JOB_CREATED = "JOB_CREATED", "Job created"
    JOB_PUBLISHED = "JOB_PUBLISHED", "Job published"
    OFFER_REF = "OFFER_REF", "Offer referenced"
    PRICE_AGREED = "PRICE_AGREED", "Price agreed"
    OPERATOR_ASSIGNED = "OPERATOR_ASSIGNED", "Operator assigned"
    DRIVER_CONFIRMED = "DRIVER_CONFIRMED", "Driver confirmed"
    VEHICLE_CONFIRMED = "VEHICLE_CONFIRMED", "Vehicle confirmed"
    ARRIVED_AT_PICKUP = "ARRIVED_AT_PICKUP", "Arrived at pickup"
    PICKUP_OTP_ISSUED = "PICKUP_OTP_ISSUED", "Pickup OTP issued"
    PICKUP_OTP_CONFIRMED = "PICKUP_OTP_CONFIRMED", "Pickup OTP confirmed"
    PICKUP_BUSINESS_CONFIRMED = "PICKUP_BUSINESS_CONFIRMED", "Pickup confirmed by sender"
    PICKUP_OPERATOR_ATTESTED = "PICKUP_OPERATOR_ATTESTED", "Pickup operator-attested (unverified)"
    GOODS_RECEIVED = "GOODS_RECEIVED", "Goods received"
    IN_TRANSIT = "IN_TRANSIT", "In transit"
    ARRIVED_AT_DESTINATION = "ARRIVED_AT_DESTINATION", "Arrived at destination"
    RECIPIENT_OTP_ISSUED = "RECIPIENT_OTP_ISSUED", "Recipient OTP issued"
    RECIPIENT_VERIFIED = "RECIPIENT_VERIFIED", "Recipient verified"
    DELIVERY_CONFIRMED = "DELIVERY_CONFIRMED", "Delivery confirmed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    DISPUTED = "DISPUTED", "Disputed"
    DISPUTE_RESOLVED = "DISPUTE_RESOLVED", "Dispute resolved"
    RESUMED = "RESUMED", "Resumed"
    ADMIN_FORCED_TRANSITION = "ADMIN_FORCED_TRANSITION", "Admin forced transition"
    ADMIN_REASSIGNED = "ADMIN_REASSIGNED", "Admin reassigned"
    NOTE = "NOTE", "Note"


#: JobEventType values that also represent a custody link (chain_of_custody view).
CUSTODY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        JobEventType.OPERATOR_ASSIGNED,
        JobEventType.DRIVER_CONFIRMED,
        JobEventType.VEHICLE_CONFIRMED,
        JobEventType.ARRIVED_AT_PICKUP,
        JobEventType.PICKUP_OTP_CONFIRMED,
        JobEventType.PICKUP_BUSINESS_CONFIRMED,
        JobEventType.PICKUP_OPERATOR_ATTESTED,
        JobEventType.GOODS_RECEIVED,
        JobEventType.IN_TRANSIT,
        JobEventType.ARRIVED_AT_DESTINATION,
        JobEventType.RECIPIENT_VERIFIED,
        JobEventType.DELIVERY_CONFIRMED,
        JobEventType.COMPLETED,
    }
)


class ConfirmationMethod(models.TextChoices):
    OTP = "OTP", "OTP"
    SIGNATURE = "SIGNATURE", "Signature"
    PHOTO = "PHOTO", "Photo"
    IN_APP = "IN_APP", "In-app confirmation"
    NONE = "NONE", "None"


class GeoState(models.TextChoices):
    CAPTURED = "CAPTURED", "Captured"
    NOT_CAPTURED = "NOT_CAPTURED", "Not captured"
    COARSENED = "COARSENED", "Coarsened"


class Attestation(models.TextChoices):
    VERIFIED = "VERIFIED", "Verified"
    OPERATOR_ATTESTED_UNVERIFIED = "OPERATOR_ATTESTED_UNVERIFIED", "Operator-attested (unverified)"


class PenaltyClass(models.TextChoices):
    NONE = "NONE", "None"
    LATE_CANCELLATION = "LATE_CANCELLATION", "Late cancellation"
    WASTED_TRIP = "WASTED_TRIP", "Wasted trip"


class CancellationReason(models.TextChoices):
    BUSINESS_CHANGED_MIND = "BUSINESS_CHANGED_MIND", "No longer needed"
    OPERATOR_UNAVAILABLE = "OPERATOR_UNAVAILABLE", "Operator unavailable"
    NO_ACCEPTABLE_OFFER = "NO_ACCEPTABLE_OFFER", "No acceptable offer"
    PRICE_DISAGREEMENT = "PRICE_DISAGREEMENT", "Could not agree a price"
    ADMIN_ACTION = "ADMIN_ACTION", "Administrative action"
    OTHER = "OTHER", "Other"


def compute_penalty_class(at_status: str) -> str:
    """D-DIS-3 / job-state-machine §3: before ASSIGNED → NONE; ASSIGNED→AT_PICKUP
    → LATE_CANCELLATION; at/after AT_PICKUP → WASTED_TRIP."""
    if at_status in {
        JobStatus.DRAFT,
        JobStatus.REQUESTED,
        JobStatus.NEGOTIATING,
        JobStatus.CONFIRMED,
    }:
        return PenaltyClass.NONE
    if at_status == JobStatus.ASSIGNED:
        return PenaltyClass.LATE_CANCELLATION
    return PenaltyClass.WASTED_TRIP


class LocationType(models.TextChoices):
    PICKUP = "PICKUP", "Pickup"
    DESTINATION = "DESTINATION", "Destination"


class LocationSourceKind(models.TextChoices):
    BUSINESS_LOCATION = "BUSINESS_LOCATION", "From a business location"
    AD_HOC = "AD_HOC", "Ad-hoc"


class OperatorParty(models.TextChoices):
    OPERATOR = "OPERATOR", "Individual operator"
    GROUP = "GROUP", "Operator group"


class AssignedBy(models.TextChoices):
    SELF = "SELF", "Operator (self)"
    GROUP_MANAGER = "GROUP_MANAGER", "Group manager"
    ADMIN = "ADMIN", "Administrator"


class ProofKind(models.TextChoices):
    PICKUP = "PICKUP", "Pickup"
    DELIVERY = "DELIVERY", "Delivery"


class ProofCapturedBy(models.TextChoices):
    OPERATOR = "OPERATOR", "Operator / driver"
    BUSINESS_CONTACT = "BUSINESS_CONTACT", "Business contact"
    RECIPIENT = "RECIPIENT", "Recipient"
    ADMIN = "ADMIN", "Administrator"


class OtpPurpose(models.TextChoices):
    PICKUP_HANDOVER = "PICKUP_HANDOVER", "Pickup handover"
    RECIPIENT_VERIFY = "RECIPIENT_VERIFY", "Recipient verification"


class HighValueDecision(models.TextChoices):
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
