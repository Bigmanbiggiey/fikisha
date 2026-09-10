"""The single authoritative allowed-transition table (job-state-machine.md §3).

This is **data**. ``JobLifecycleService.transition()`` is the only consumer that
writes ``job.status``; a Postgres trigger seeded from ``ALLOWED_TRANSITIONS`` is
the backstop. Parametrised tests run the full ``JobStatus x JobStatus``
cross-product against this table.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fikisha.jobs.constants import JobEventType, JobStatus

S = JobStatus


@dataclass(frozen=True)
class Rule:
    #: initiator role tokens accepted for this transition (see guards.actor_allowed)
    initiators: tuple[str, ...]
    #: guard names (resolved in jobs.guards.GUARDS) run in order, before any write
    guards: tuple[str, ...] = ()
    #: name of the side-effect function in jobs.apply_fns.APPLY (default: no-op)
    apply: str = "noop"
    #: outbox event types emitted (async) on success
    events: tuple[str, ...] = ()
    #: whether the STATUS_TRANSITION job_event also implies a custody link
    is_custody: bool = False
    #: the job_event.type recorded for the transition itself
    event_type: str = JobEventType.NOTE
    #: extra job_event.type rows written in the same transaction (custody steps)
    extra_events: tuple[str, ...] = field(default_factory=tuple)


# Initiator tokens (matched in jobs.guards.actor_allowed against the Actor):
#   BUSINESS_OWNER_OR_DISPATCHER · BUSINESS_PARTY · OPERATOR_PARTY · GROUP_MANAGER
#   · ASSIGNED_DRIVER · RECIPIENT · SCHEDULER · ADMIN · PLATFORM_ADMIN · ANY_PARTICIPANT

ALLOWED_TRANSITIONS: dict[tuple[str, str], Rule] = {
    # ── 3.1 pre-custody ────────────────────────────────────────────────
    (S.DRAFT, S.REQUESTED): Rule(
        initiators=("BUSINESS_OWNER_OR_DISPATCHER", "ADMIN"),
        guards=("RequiredFieldsComplete", "BusinessVerifiedWithLocation", "CargoNotProhibited"),
        apply="publish",
        events=("JobRequested",),
        event_type=JobEventType.JOB_PUBLISHED,
    ),
    (S.DRAFT, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    (S.REQUESTED, S.NEGOTIATING): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "ADMIN"),
        guards=("OperatorEligibleForJob",),
        apply="noop",
        events=("JobNegotiating",),
        event_type=JobEventType.NOTE,
    ),
    (S.REQUESTED, S.CONFIRMED): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "ADMIN"),
        guards=("NoRacingConfirm", "MutualAcceptanceExists", "OperatorEligibleForJob"),
        apply="confirm",
        events=("JobConfirmed",),
        event_type=JobEventType.PRICE_AGREED,
    ),
    (S.REQUESTED, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    (S.REQUESTED, S.FAILED): Rule(
        initiators=("SCHEDULER", "ADMIN"),
        guards=("RequestExpired",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.NEGOTIATING, S.NEGOTIATING): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "ADMIN"),
        apply="noop",
        events=("OfferPlaced",),
        event_type=JobEventType.OFFER_REF,
    ),
    (S.NEGOTIATING, S.CONFIRMED): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "ADMIN"),
        guards=("NoRacingConfirm", "MutualAcceptanceExists", "OperatorEligibleForJob"),
        apply="confirm",
        events=("JobConfirmed",),
        event_type=JobEventType.PRICE_AGREED,
    ),
    (S.NEGOTIATING, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    (S.NEGOTIATING, S.FAILED): Rule(
        initiators=("SCHEDULER", "ADMIN", "ANY_PARTICIPANT"),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.CONFIRMED, S.ASSIGNED): Rule(
        initiators=("OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        guards=(
            "RequesterIsNotProvider",
            "VehicleEligible",
            "DriverVerificationCurrent",
            "DriverTrustCeilingCoversValue",
            "HighValueApproved",
        ),
        apply="assign",
        events=("JobAssigned",),
        is_custody=True,
        event_type=JobEventType.OPERATOR_ASSIGNED,
        extra_events=(JobEventType.DRIVER_CONFIRMED, JobEventType.VEHICLE_CONFIRMED),
    ),
    (S.CONFIRMED, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    # ── 3.2 custody ───────────────────────────────────────────────────
    (S.ASSIGNED, S.AT_PICKUP): Rule(
        initiators=("ASSIGNED_DRIVER",),
        apply="arrive_pickup",
        events=("ArrivedAtPickup", "otp.pickup.requested"),
        is_custody=True,
        event_type=JobEventType.ARRIVED_AT_PICKUP,
        extra_events=(JobEventType.PICKUP_OTP_ISSUED,),
    ),
    (S.ASSIGNED, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    (S.ASSIGNED, S.FAILED): Rule(
        initiators=("ADMIN",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.ASSIGNED, S.DISPUTED): Rule(
        initiators=("ANY_PARTICIPANT", "ADMIN"),
        guards=("BlockingIncidentExists",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.AT_PICKUP, S.PICKED_UP): Rule(
        initiators=("ASSIGNED_DRIVER", "BUSINESS_OWNER_OR_DISPATCHER"),
        guards=("PickupProofValidForBand",),
        apply="confirm_pickup",
        events=("JobPickedUp",),
        is_custody=True,
        event_type=JobEventType.GOODS_RECEIVED,
    ),
    (S.AT_PICKUP, S.CANCELLED): Rule(
        initiators=("BUSINESS_PARTY", "OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        apply="cancel",
        events=("JobCancelled",),
        event_type=JobEventType.CANCELLED,
    ),
    (S.AT_PICKUP, S.FAILED): Rule(
        initiators=("ASSIGNED_DRIVER", "ADMIN"),
        guards=("FailureReasonProvided",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.AT_PICKUP, S.DISPUTED): Rule(
        initiators=("ANY_PARTICIPANT", "ADMIN"),
        guards=("BlockingIncidentExists",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.PICKED_UP, S.IN_TRANSIT): Rule(
        initiators=("ASSIGNED_DRIVER",),
        apply="start_transit",
        events=("JobInTransit",),
        is_custody=True,
        event_type=JobEventType.IN_TRANSIT,
    ),
    (S.PICKED_UP, S.DISPUTED): Rule(
        initiators=("ANY_PARTICIPANT", "ADMIN"),
        guards=("BlockingIncidentExists",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.PICKED_UP, S.FAILED): Rule(
        initiators=("ADMIN",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.IN_TRANSIT, S.AT_DESTINATION): Rule(
        initiators=("ASSIGNED_DRIVER",),
        apply="arrive_destination",
        events=("JobAtDestination", "otp.recipient.requested"),
        is_custody=True,
        event_type=JobEventType.ARRIVED_AT_DESTINATION,
        extra_events=(JobEventType.RECIPIENT_OTP_ISSUED,),
    ),
    (S.IN_TRANSIT, S.DISPUTED): Rule(
        initiators=("ANY_PARTICIPANT", "ADMIN"),
        guards=("BlockingIncidentExists",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.IN_TRANSIT, S.FAILED): Rule(
        initiators=("ADMIN",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    (S.AT_DESTINATION, S.DELIVERED): Rule(
        initiators=("ASSIGNED_DRIVER", "RECIPIENT"),
        guards=("DeliveryProofValidForBand",),
        apply="confirm_delivery",
        events=("JobDelivered",),
        is_custody=True,
        event_type=JobEventType.DELIVERY_CONFIRMED,
        extra_events=(JobEventType.RECIPIENT_VERIFIED,),
    ),
    (S.AT_DESTINATION, S.DISPUTED): Rule(
        initiators=("ANY_PARTICIPANT", "RECIPIENT", "ADMIN"),
        guards=("BlockingIncidentExists",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.AT_DESTINATION, S.FAILED): Rule(
        initiators=("ADMIN",),
        apply="fail",
        events=("JobFailed",),
        event_type=JobEventType.FAILED,
    ),
    # ── 3.3 completion & post-completion ──────────────────────────────
    (S.DELIVERED, S.COMPLETED): Rule(
        initiators=("BUSINESS_PARTY", "RECIPIENT", "SCHEDULER", "ADMIN"),
        guards=("NoOpenBlockingDispute",),
        apply="complete",
        events=("JobCompleted",),
        is_custody=True,
        event_type=JobEventType.COMPLETED,
    ),
    (S.DELIVERED, S.DISPUTED): Rule(
        initiators=("BUSINESS_PARTY", "RECIPIENT", "OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        guards=("WithinDeliveryAcceptanceWindow",),
        apply="freeze",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    (S.COMPLETED, S.DISPUTED): Rule(
        initiators=("BUSINESS_PARTY", "RECIPIENT", "OPERATOR_PARTY", "GROUP_MANAGER", "ADMIN"),
        guards=("WithinPostCompletionWindow",),
        apply="freeze_post_completion",
        events=("JobDisputed",),
        event_type=JobEventType.DISPUTED,
    ),
    # ── 3.4 dispute resolution (RESUME is NOT implemented — ADR-2D-07) ──
    (S.DISPUTED, S.COMPLETED): Rule(
        initiators=("ADMIN", "PLATFORM_ADMIN"),
        guards=("ResolutionRecorded", "AdminBandAuthorised"),
        apply="resolve_completed",
        events=("DisputeResolved", "JobCompleted"),
        event_type=JobEventType.DISPUTE_RESOLVED,
    ),
    (S.DISPUTED, S.FAILED): Rule(
        initiators=("ADMIN", "PLATFORM_ADMIN"),
        guards=("ResolutionRecorded", "AdminBandAuthorised"),
        apply="resolve_failed",
        events=("DisputeResolved", "JobFailed"),
        event_type=JobEventType.DISPUTE_RESOLVED,
    ),
    (S.DISPUTED, S.CANCELLED): Rule(
        initiators=("ADMIN", "PLATFORM_ADMIN"),
        guards=("ResolutionRecorded", "AdminBandAuthorised"),
        apply="resolve_cancelled",
        events=("DisputeResolved", "JobCancelled"),
        event_type=JobEventType.DISPUTE_RESOLVED,
    ),
}


def is_allowed(from_status: str, to_status: str) -> bool:
    return (from_status, to_status) in ALLOWED_TRANSITIONS


def rule_for(from_status: str, to_status: str) -> Rule | None:
    return ALLOWED_TRANSITIONS.get((from_status, to_status))


#: for the 0002 migration seed + the DB trigger.
ALLOWED_PAIRS: tuple[tuple[str, str], ...] = tuple(ALLOWED_TRANSITIONS.keys())

_ = Callable  # referenced for type-checkers
