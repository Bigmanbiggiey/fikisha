"""Lifecycle guards (job-state-machine.md §4).

Each guard is ``fn(job, actor, ctx) -> None`` and **raises** a typed error on
failure (never returns a bool). Guards run in order, before any write; a raise
rolls the whole transition transaction back with no side effects.

``ctx`` is a plain dict carried on ``TransitionContext.data`` — the initiating
service (negotiation / assignment / proof / dispute — later increments) fills in
the fields a guard needs; the engine itself is fully exercisable now by passing
those fields directly.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.utils import timezone

from fikisha.jobs import eligibility
from fikisha.jobs.constants import HIGH_VALUE_BANDS, ValueBand
from fikisha.jobs.errors import (
    DeliveryProofIncomplete,
    DriverNotEligible,
    GuardFailed,
    HighValueApprovalRequired,
    JobNoLongerAvailable,
    PickupConfirmationRequired,
    VehicleNotEligible,
)

Guard = Callable[[Any, Any, dict[str, Any]], None]


def _fail(code: str, detail: str) -> None:
    raise GuardFailed(detail, code=code)


# ── publish ──────────────────────────────────────────────────────────
def required_fields_complete(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    missing = [
        name
        for name, val in {
            "pickup_location": job.pickup_location_id,
            "destination_location": job.destination_location_id,
            "cargo": job.cargo_id,
            "vehicle_requirement": job.vehicle_requirement_id,
        }.items()
        if not val
    ]
    if job.declared_value_kes is None or job.declared_value_kes <= 0:
        missing.append("declared_value_kes")
    if missing:
        _fail("required_fields_incomplete", f"Missing required fields: {', '.join(missing)}.")


def business_verified_with_location(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    from fikisha.business.models import BusinessLocation, BusinessVerificationStatus

    biz = job.business
    if biz.verification_status != BusinessVerificationStatus.VERIFIED:
        _fail("business_not_verified", "The business is not verified.")
    if not BusinessLocation.objects.filter(business=biz, deactivated_at__isnull=True).exists():
        _fail("business_no_active_location", "The business has no active location.")


def cargo_not_prohibited(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    flags = set((job.cargo.handling_flags if job.cargo_id else []) or [])
    if "HAZARDOUS" in flags:
        _fail("cargo_prohibited", "Hazardous cargo is not accepted in the MVP.")


# ── negotiate / confirm ──────────────────────────────────────────────
def operator_eligible_for_job(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Operator-side eligibility at negotiate/confirm time. The concrete operator
    identity comes from the negotiation service via ``ctx``; when absent (pure
    engine test) the guard is a no-op — full eligibility is re-checked at
    ``CONFIRMED → ASSIGNED`` against the *assigned driver*."""
    op = ctx.get("operator_profile")
    if op is None:
        return
    from fikisha.operators.models import OperatorStatus

    if getattr(op, "status", None) in {OperatorStatus.SUSPENDED, OperatorStatus.RESTRICTED}:
        raise DriverNotEligible("Operator is suspended or restricted.")


def no_racing_confirm(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    from fikisha.jobs.constants import JobStatus

    if job.status not in {JobStatus.REQUESTED, JobStatus.NEGOTIATING}:
        raise JobNoLongerAvailable()


def mutual_acceptance_exists(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """A mutual ACCEPT in one thread. Verified by the NegotiationService (later
    increment); here the engine accepts a pre-validated
    ``ctx['agreed_price_kes']`` + ``ctx['accepting_entry_ids']`` +
    ``ctx['operator_party']``."""
    if not ctx.get("agreed_price_kes") or not ctx.get("operator_party"):
        _fail(
            "no_mutual_acceptance",
            "A mutual price acceptance in one negotiation thread is required.",
        )


# ── assign ───────────────────────────────────────────────────────────
def requester_is_not_provider(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    driver = ctx.get("driver_profile")
    if driver is not None and getattr(driver, "user_id", None) == job.created_by_id:
        _fail("requester_is_provider", "The requester may not be the assigned driver.")


def vehicle_eligible(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    vehicle = ctx.get("vehicle")
    if vehicle is None:
        raise VehicleNotEligible("No vehicle supplied for assignment.")
    if not vehicle.is_active:
        raise VehicleNotEligible("Vehicle is not active.")
    req = job.vehicle_requirement
    if req and req.required_vehicle_class_codes:
        code = getattr(vehicle.vehicle_class, "code", None)
        if code not in req.required_vehicle_class_codes:
            raise VehicleNotEligible("Vehicle class does not match the requirement.")
    if getattr(vehicle.vehicle_class, "heavy", False):
        from fikisha.verification.models import Domain
        from fikisha.verification.services import subject_meets

        if not subject_meets(vehicle, [Domain.HEAVY_CLASS_COMPLIANCE, Domain.VEHICLE]):
            raise VehicleNotEligible("Heavy-class compliance is not verified for this vehicle.")


def driver_verification_current(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    driver = ctx.get("driver_profile")
    if driver is None:
        raise DriverNotEligible("No driver supplied for assignment.")
    from fikisha.verification.models import Domain
    from fikisha.verification.services import subject_meets

    if not subject_meets(driver, [Domain.IDENTITY, Domain.LICENCE, Domain.GOOD_CONDUCT]):
        raise DriverNotEligible(
            "Driver identity, licence, and good-conduct verification must be current."
        )


def driver_trust_ceiling_covers_value(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    driver = ctx.get("driver_profile")
    if driver is None:
        raise DriverNotEligible("No driver supplied for assignment.")
    level = eligibility.interim_driver_trust_level(driver)
    band = job.value_band or ValueBand.STANDARD
    if eligibility.level_covers_band(level, band):
        return
    if (ctx.get("admin_override_reason") or "").strip():
        return
    raise DriverNotEligible(
        f"The driver's trust level ({level or 'none'}) does not cover this job's "
        f"{band} value band, and no admin override reason was recorded."
    )


def high_value_approved(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    if job.value_band not in HIGH_VALUE_BANDS:
        return
    from fikisha.jobs.constants import HighValueDecision
    from fikisha.jobs.models import HighValueApproval

    approval = HighValueApproval.objects.filter(job=job).first()
    if approval is None or approval.decision != HighValueDecision.APPROVED:
        raise HighValueApprovalRequired("This high-value job requires an approved review.")
    if job.value_band == ValueBand.VERY_HIGH and not approval.decided_by_is_platform_admin:
        raise HighValueApprovalRequired("Very-high-value jobs require Platform Admin approval.")


# ── custody / proof ──────────────────────────────────────────────────
def pickup_proof_valid_for_band(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Encoded exactly from chain-of-custody.md §4 / D-CUS-2 / design-phase-2 §39.

    STANDARD: pickup-contact OTP  OR  in-app business confirmation  OR
              (OTP undeliverable) operator-attested fallback = goods photo +
              pickup-contact name  → recorded OPERATOR_ATTESTED_UNVERIFIED,
              job capped at STANDARD.
    ELEVATED / HIGH / VERY_HIGH: OTP  OR  in-app business confirmation.
              **No** operator-attested fallback. Missing → pickup_confirmation_required.
    """
    method = ctx.get("pickup_method")  # OTP | BUSINESS_CONFIRM | ATTESTED
    band = job.value_band or ValueBand.STANDARD
    if method == "OTP":
        from fikisha.jobs.models import PickupOtpChallenge

        challenge = PickupOtpChallenge.objects.filter(job=job).order_by("-created_at").first()
        if challenge is None or challenge.consumed_at is None:
            raise PickupConfirmationRequired("The pickup OTP has not been verified.")
        return
    if method == "BUSINESS_CONFIRM":
        return
    if method == "ATTESTED":
        if band != ValueBand.STANDARD:
            raise PickupConfirmationRequired(
                "This value band requires a verified pickup (OTP or in-app "
                "business confirmation) — the operator-attested fallback is not allowed."
            )
        if not ctx.get("fallback_photo_id") or not (ctx.get("pickup_contact_name") or "").strip():
            raise PickupConfirmationRequired(
                "The operator-attested fallback needs a goods photo and the "
                "pickup-contact's name."
            )
        return
    raise PickupConfirmationRequired("No pickup confirmation was supplied.")


def delivery_proof_valid_for_band(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Encoded from chain-of-custody.md §3 / D-TRU-5 / design-phase-2 §44.

    STANDARD: recipient name + at least one of {recipient OTP, signature, photo}.
    ELEVATED / HIGH / VERY_HIGH: recipient name + recipient OTP **and** ≥ 1 photo.
    """
    band = job.value_band or ValueBand.STANDARD
    name = (ctx.get("party_name") or "").strip()
    otp_ok = bool(ctx.get("otp_verified"))
    has_sig = bool(ctx.get("signature_evidence_id"))
    photos = ctx.get("photo_evidence_ids") or []
    if not name:
        raise DeliveryProofIncomplete("The recipient's name is required.")
    if band in HIGH_VALUE_BANDS or band == ValueBand.ELEVATED:
        if not (otp_ok and photos):
            raise DeliveryProofIncomplete(
                "This value band requires a verified recipient OTP and a photo POD."
            )
        return
    if not (otp_ok or has_sig or photos):
        raise DeliveryProofIncomplete("Provide the recipient OTP, a signature, or a photo POD.")


def failure_reason_provided(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    if not (ctx.get("reason_text") or "").strip():
        _fail("failure_reason_required", "A failure reason is required.")


# ── dispute ──────────────────────────────────────────────────────────
def blocking_incident_exists(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """An OPEN/UNDER_REVIEW progression-blocking incident. Verified by the
    IncidentService (later increment); the engine accepts
    ``ctx['blocking_incident_id']``."""
    if not ctx.get("blocking_incident_id"):
        _fail("no_blocking_incident", "A progression-blocking incident is required to dispute.")


def resolution_recorded(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    if not ctx.get("resolution_id") or not ctx.get("routed_job_status"):
        _fail("no_resolution", "A recorded dispute Resolution is required.")


def admin_band_authorised(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Binding resolution above the STANDARD band requires a Platform Admin
    (D-ADM-1)."""
    band = job.value_band or ValueBand.STANDARD
    if band == ValueBand.STANDARD:
        return
    roles = set(getattr(actor, "roles", []) or [])
    if "PLATFORM_ADMIN" not in roles:
        raise GuardFailed(
            "Binding dispute resolution above the Standard band requires a Platform Administrator.",
            code="platform_admin_required",
        )


def no_open_blocking_dispute(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    try:
        from fikisha.incidents.models import (  # type: ignore[import-not-found]
            Dispute,
            DisputeStatus,
        )
    except ImportError:
        return  # the incidents app (plan §19 Step 8) is not installed yet → no disputes
    if Dispute.objects.filter(job=job).exclude(status=DisputeStatus.RESOLVED).exists():
        raise JobNoLongerAvailable()


def request_expired(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Scheduler-only: the request-expiry timer elapsed with no acceptable offer.
    The sweep passes ``ctx['expiry_reached']``; here it is a no-op for admin
    force-fail with an explicit reason."""
    if ctx.get("expiry_reached"):
        return
    if (ctx.get("reason_text") or "").strip():
        return
    _fail("request_not_expired", "The request has not expired.")


def _within_window(job: Any, anchor_field: str, hours: float) -> bool:
    anchor = getattr(job, anchor_field, None)
    if anchor is None:
        return False
    return timezone.now() <= anchor + timedelta(hours=hours)


def within_delivery_acceptance_window(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """job-state-machine §3.3 / D-JOB-5: 24h Standard/Elevated, 48h High/Very-high."""
    from fikisha.platform_config import services as cfg

    windows = cfg.get("timeouts.delivery_acceptance", {}) or {}
    hrs = windows.get("high_hours", 48) if job.is_high_value else windows.get("standard_hours", 24)
    if not _within_window(job, "delivered_at", hrs):
        _fail("acceptance_window_closed", "The delivery-acceptance window has closed.")


def within_post_completion_window(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """job-state-machine §3.3 / D-JOB-5: 72h all bands; 7 days for High/Very-high
    **or** ``latent_risk_cargo``."""
    from fikisha.platform_config import services as cfg

    window = cfg.get("timeouts.post_completion_window", {}) or {}
    if job.is_high_value or job.latent_risk_cargo:
        hrs = float(window.get("high_and_latent_days", 7)) * 24.0
    else:
        hrs = float(window.get("default_hours", 72))
    if not _within_window(job, "completed_at", hrs):
        _fail("post_completion_window_closed", "The post-completion dispute window has closed.")


GUARDS: dict[str, Guard] = {
    "RequiredFieldsComplete": required_fields_complete,
    "BusinessVerifiedWithLocation": business_verified_with_location,
    "CargoNotProhibited": cargo_not_prohibited,
    "OperatorEligibleForJob": operator_eligible_for_job,
    "NoRacingConfirm": no_racing_confirm,
    "MutualAcceptanceExists": mutual_acceptance_exists,
    "RequesterIsNotProvider": requester_is_not_provider,
    "VehicleEligible": vehicle_eligible,
    "DriverVerificationCurrent": driver_verification_current,
    "DriverTrustCeilingCoversValue": driver_trust_ceiling_covers_value,
    "HighValueApproved": high_value_approved,
    "PickupProofValidForBand": pickup_proof_valid_for_band,
    "DeliveryProofValidForBand": delivery_proof_valid_for_band,
    "FailureReasonProvided": failure_reason_provided,
    "BlockingIncidentExists": blocking_incident_exists,
    "ResolutionRecorded": resolution_recorded,
    "AdminBandAuthorised": admin_band_authorised,
    "NoOpenBlockingDispute": no_open_blocking_dispute,
    "RequestExpired": request_expired,
    "WithinDeliveryAcceptanceWindow": within_delivery_acceptance_window,
    "WithinPostCompletionWindow": within_post_completion_window,
}
