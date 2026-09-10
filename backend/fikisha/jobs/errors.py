"""Typed Job-domain errors (mapped to RFC-9457 problem+json by the common handler)."""

from __future__ import annotations

from rest_framework import status

from fikisha.common.exceptions import ConflictError, DomainError


class TransitionNotAllowed(DomainError):
    default_code = "transition_not_allowed"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "That job status transition is not allowed."


class NotAuthorisedToInitiate(DomainError):
    default_code = "not_authorised_to_initiate"
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You may not initiate this transition."


class StaleJob(DomainError):
    default_code = "stale_job"
    status_code = status.HTTP_412_PRECONDITION_FAILED
    default_detail = "The job has changed since you loaded it; refetch and retry."


class JobNoLongerAvailable(ConflictError):
    default_code = "job_no_longer_available"
    default_detail = "This job is no longer available."


class GuardFailed(DomainError):
    """Base for a precondition guard failure; subclasses set ``code``."""

    default_code = "guard_failed"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class PickupConfirmationRequired(GuardFailed):
    default_code = "pickup_confirmation_required"
    default_detail = "A verified pickup confirmation is required for this job's value band."


class DeliveryProofIncomplete(GuardFailed):
    default_code = "delivery_proof_incomplete"
    default_detail = "The delivery proof does not meet this job's value-band requirement."


class DriverNotEligible(GuardFailed):
    default_code = "driver_not_eligible"


class VehicleNotEligible(GuardFailed):
    default_code = "vehicle_not_eligible"


class HighValueApprovalRequired(GuardFailed):
    default_code = "high_value_approval_required"


class NotAHighValueJob(DomainError):
    default_code = "not_a_high_value_job"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "This job is not in a high-value band; no approval applies."


class HighValueAlreadyDecided(ConflictError):
    default_code = "high_value_already_decided"
    default_detail = "A high-value decision has already been recorded for this job."


class NotAuthorisedToAssign(DomainError):
    default_code = "not_authorised_to_assign"
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You may not assign a driver and vehicle to this job."


class NotImplementedInThisIncrement(DomainError):
    """Raised by transition paths whose initiating service is not built yet
    (Phase 2D increment 1 covers the lifecycle engine + pure-jobs transitions;
    negotiation / assignment / proof / dispute services are later increments)."""

    default_code = "not_implemented_yet"
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_detail = "This operation is not available in the current build increment."
