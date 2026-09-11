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


class OtpNotIssued(DomainError):
    default_code = "otp_not_issued"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "No OTP has been issued for this step."


class OtpInvalid(DomainError):
    default_code = "otp_invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Incorrect or unknown code."


class OtpExpired(DomainError):
    default_code = "otp_expired"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "This code has expired; request a new one."


class OtpLocked(DomainError):
    default_code = "otp_too_many_attempts"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many attempts. Request a new code."


class RecipientLinkNotFound(DomainError):
    """The token does not resolve to any link. ``404``, not ``403`` — deliberately
    indistinguishable from "never existed" so nothing about token validity is
    revealed (recipient-access.md §5)."""

    default_code = "recipient_link_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Not found."


class RecipientLinkInactive(DomainError):
    """The token resolves, but the link is expired or revoked. ``410`` — the
    resource existed but is gone; still no further detail."""

    default_code = "recipient_link_inactive"
    status_code = status.HTTP_410_GONE
    default_detail = "This link is no longer active."


class RecipientActionNotAllowed(DomainError):
    default_code = "recipient_action_not_allowed"
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This action is not available on this link."


class CommissionAgreementMissing(GuardFailed):
    """Defensive — a job that legitimately reaches ``COMPLETED`` always has a
    frozen ``Agreement`` (CONFIRMED requires one); this guards against a
    silent ``AttributeError`` if that invariant is ever violated."""

    default_code = "commission_agreement_missing"
    default_detail = "The job has no confirmed agreement to base commission on."


class CommissionConfigInvalid(DomainError):
    """``platform_config.commission.model`` names a model that is syntactically
    valid (``defaults.py``'s ``_ALLOWED_COMMISSION_MODELS``) but not actually
    implemented — only ``FLAT_WITH_MIN_CAP`` is (Step 9 brief §2/§6)."""

    default_code = "commission_config_invalid"
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_detail = "The configured commission model is not implemented."


class NotAuthorisedForCommissionAdjustment(DomainError):
    default_code = "not_authorised_for_commission_adjustment"
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Commission adjustments require Platform Administrator authority."


class CommissionAdjustmentReasonRequired(DomainError):
    default_code = "commission_adjustment_reason_required"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "A reason is required to adjust commission."


class InvalidCommissionAdjustmentAmount(DomainError):
    default_code = "invalid_commission_adjustment_amount"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "That commission adjustment amount is not valid."


class CommissionRecordNotFound(DomainError):
    default_code = "commission_record_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "No commission record exists for that job."


class NotImplementedInThisIncrement(DomainError):
    """Raised by transition paths whose initiating service is not built yet
    (Phase 2D increment 1 covers the lifecycle engine + pure-jobs transitions;
    negotiation / assignment / proof / dispute services are later increments)."""

    default_code = "not_implemented_yet"
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_detail = "This operation is not available in the current build increment."
