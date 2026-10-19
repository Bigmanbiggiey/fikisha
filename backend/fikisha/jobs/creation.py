"""Job creation + business-initiated cancellation (plan §19 Step 10).

Increments 1-9 built the lifecycle engine, guards, and every transition
**after** `DRAFT` — but no domain function ever created the `DRAFT` row
itself (every test built one directly via `Job.objects.create(...)`,
mirroring what a from-scratch fixture needs, not a real entry point). The
Step 10 API needs a real one. `DRAFT` is not reached via
`JobLifecycleService.transition()` (there is no `(_, DRAFT)` row in
`ALLOWED_TRANSITIONS` — a job is *born* there), so this is a plain create,
not a lifecycle transition; `submit_job` immediately hands off to the
authoritative `transition(REQUESTED)` for the real first transition.

The pickup may be one of the business's saved locations
(`pickup_location.business_location_id` → `source_kind=BUSINESS_LOCATION`,
copied at creation so a later edit does not rewrite the job; assessment
2026-10-19 part 2) or an ad-hoc address (`source_kind=AD_HOC`). The
destination is always ad-hoc.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.http import Http404

from fikisha.audit import services as audit
from fikisha.common.exceptions import DomainError
from fikisha.jobs import cargo_categories, job_authz
from fikisha.jobs.constants import GeoState, JobStatus, LocationSourceKind, LocationType
from fikisha.jobs.dto import job_view
from fikisha.jobs.errors import GuardFailed, NotAuthorisedToAssign
from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
from fikisha.jobs.selectors import get_job
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.outbox.services import emit


class NotAuthorisedToCreateJob(NotAuthorisedToAssign):
    default_code = "not_authorised_to_create_job"
    default_detail = "You may not create a job for this business."


class BusinessSuspended(GuardFailed):
    """A suspended business may not create new work (Increment 9 D-2,
    ADR-2D-38). Same code the ``DRAFT -> REQUESTED`` guard uses."""

    default_code = "business_suspended"
    default_detail = "The business is suspended."


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


class DestinationRequired(DomainError):
    default_code = "destination_required"
    default_detail = "Pin the destination on the map or name it."


class UnknownBusinessLocation(DomainError):
    default_code = "unknown_business_location"
    default_detail = "That saved location is not an active location of this business."


def _geo_state(lat: Any, lng: Any) -> str:
    """A location with both coordinates was pinned on the map (maps M-3)."""
    return GeoState.CAPTURED if lat is not None and lng is not None else GeoState.NOT_CAPTURED


def _make_saved_location(*, type_: str, business_id: Any, data: dict[str, Any]) -> JobLocation:
    """Snapshot a saved business location (``source_kind=BUSINESS_LOCATION``).
    The request may still override the contact for this one job."""
    from fikisha.business import services as business_services

    snap = business_services.active_location_snapshot(business_id, data["business_location_id"])
    if snap is None:
        raise UnknownBusinessLocation()
    return JobLocation.objects.create(
        type=type_,
        source_kind=LocationSourceKind.BUSINESS_LOCATION,
        source_location_id=snap["id"],
        address_text=snap["address_text"],
        lat=snap["lat"],
        lng=snap["lng"],
        geo_state=_geo_state(snap["lat"], snap["lng"]),
        zone_id=snap["zone_id"],
        contact_name=(data.get("contact_name") or "").strip() or snap["contact_name"],
        contact_phone=(data.get("contact_phone") or "").strip() or snap["contact_phone"],
        notes=(data.get("notes") or "").strip() or snap["notes"],
    )


def _make_location(*, type_: str, data: dict[str, Any]) -> JobLocation:
    return JobLocation.objects.create(
        type=type_,
        source_kind=LocationSourceKind.AD_HOC,
        address_text=(data.get("address_text") or "").strip(),
        lat=data.get("lat"),
        lng=data.get("lng"),
        geo_state=_geo_state(data.get("lat"), data.get("lng")),
        contact_name=(data.get("contact_name") or "").strip(),
        contact_phone=(data.get("contact_phone") or "").strip(),
        notes=(data.get("notes") or "").strip(),
    )


@transaction.atomic
def create_draft(*, actor: Any, business_id: Any, data: dict[str, Any]) -> Job:
    """Create a `DRAFT` job for `business_id`. `actor` must be an owner or
    dispatcher of that business — the same relationship `RequiredFieldsComplete`
    / the `DRAFT -> REQUESTED` initiator check will demand again at submit
    time; this is the create-time half of the same server-side check."""
    from fikisha.business import authz as business_authz
    from fikisha.business.models import BusinessAccount, BusinessRole, BusinessStanding

    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist as exc:
        raise Http404("No such business.") from exc
    is_business_party = business_authz.has_role(
        actor, business, {BusinessRole.OWNER, BusinessRole.DISPATCHER}
    )
    if not is_business_party and not job_authz.is_admin(actor):
        raise NotAuthorisedToCreateJob()
    if business.standing == BusinessStanding.SUSPENDED:
        raise BusinessSuspended()

    description = (data["cargo"].get("description") or "").strip()
    category_code, category_auto = cargo_categories.resolve(
        category_code=data["cargo"].get("category_code") or "", description=description
    )
    cargo = CargoDetails.objects.create(
        description=description,
        category_code=category_code,
        category_auto=category_auto,
        est_weight_kg=data["cargo"].get("est_weight_kg"),
        dims_l_cm=data["cargo"].get("dims_l_cm"),
        dims_w_cm=data["cargo"].get("dims_w_cm"),
        dims_h_cm=data["cargo"].get("dims_h_cm"),
        declared_value_kes=data["cargo"]["declared_value_kes"],
        handling_flags=list(data["cargo"].get("handling_flags") or []),
    )
    pickup_data = data["pickup_location"]
    pickup = (
        _make_saved_location(type_=LocationType.PICKUP, business_id=business.id, data=pickup_data)
        if pickup_data.get("business_location_id")
        else _make_location(type_=LocationType.PICKUP, data=pickup_data)
    )
    dest_data = data["destination_location"]
    # A pin or a name: the sender chooses (assessment 2026-10-20 L-2).
    has_pin = dest_data.get("lat") is not None and dest_data.get("lng") is not None
    if not has_pin and not (dest_data.get("address_text") or "").strip():
        raise DestinationRequired()
    destination = _make_location(type_=LocationType.DESTINATION, data=dest_data)
    vehicle_requirement = VehicleRequirement.objects.create(
        required_vehicle_class_codes=list(
            data.get("vehicle_requirement", {}).get("required_vehicle_class_codes") or []
        ),
        min_payload_kg=data.get("vehicle_requirement", {}).get("min_payload_kg") or 0,
        min_volume_m3=data.get("vehicle_requirement", {}).get("min_volume_m3"),
        required_features=list(data.get("vehicle_requirement", {}).get("required_features") or []),
        notes=(data.get("vehicle_requirement", {}).get("notes") or "").strip(),
    )

    job = Job.objects.create(
        business=business,
        created_by=_actor_user(actor),
        status=JobStatus.DRAFT,
        pickup_location=pickup,
        destination_location=destination,
        recipient_name=(data.get("recipient_name") or "").strip(),
        recipient_phone=(data.get("recipient_phone") or "").strip(),
        cargo=cargo,
        vehicle_requirement=vehicle_requirement,
        delivery_requirements=(data.get("delivery_requirements") or "").strip(),
        delivery_flags=list(data.get("delivery_flags") or []),
        proposed_price_kes=data.get("proposed_price_kes"),
        declared_value_kes=cargo.declared_value_kes,
        # The category sets it (D-JOB-5's latent-risk categories, F-6); a
        # client may still flag other cargo as latent-risk explicitly.
        latent_risk_cargo=bool(data.get("latent_risk_cargo", False))
        or cargo_categories.is_latent_risk(category_code),
    )
    audit.record(
        actor=actor,
        action="job.created",
        entity_type="job",
        entity_id=job.id,
        after={"business_id": str(business.id), "status": job.status},
    )
    emit(
        event_type="JobCreated",
        aggregate_type="job",
        aggregate_id=str(job.id),
        payload={"job_id": str(job.id), "business_id": str(business.id)},
    )
    return job


def submit_job(*, actor: Any, job_id: Any, idempotency_key: str = "") -> dict[str, Any]:
    """`DRAFT -> REQUESTED` through the authoritative transition — this
    function resolves the initiator token server-side and calls
    `JobLifecycleService.transition()`; it implements nothing itself.

    ``get_job`` (unlocked) is enough here: this read only resolves which
    initiator token the actor holds, never the write itself — `transition()`
    re-fetches and re-locks the row under its own `select_for_update()`
    immediately after, which is the actual authoritative check."""
    job = get_job(job_id)
    token = "BUSINESS_OWNER_OR_DISPATCHER" if job_authz.business_is_party(actor, job) else None
    return job_transition(
        job_id=job.id,
        to=JobStatus.REQUESTED,
        actor=actor,
        context=TransitionContext(data={"initiator_tokens": [token] if token else []}),
        idempotency_key=idempotency_key,
    )


def cancel_job(
    *,
    actor: Any,
    job_id: Any,
    reason_code: str,
    reason_text: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Business- or admin-initiated cancellation, through the authoritative
    transition — server-resolves which initiator token the actor actually
    holds; the transition's own initiator check remains the real guard.

    ``get_job`` (unlocked): same rationale as ``submit_job`` — this read only
    resolves the initiator token; `transition()` re-locks the row itself."""
    job = get_job(job_id)
    token = "BUSINESS_PARTY" if job_authz.business_is_party(actor, job) else None
    return job_transition(
        job_id=job.id,
        to=JobStatus.CANCELLED,
        actor=actor,
        context=TransitionContext(
            data={
                "initiator_tokens": [token] if token else [],
                "reason_code": reason_code,
                "reason_text": reason_text,
            }
        ),
        idempotency_key=idempotency_key,
    )


def job_detail(job: Job, viewer: Any = None) -> dict[str, Any]:
    """Read projection for the API — `job_view()` plus the lightweight,
    already-frozen related-object summaries a caller needs (never
    recomputed business logic — every field here is a stored value).

    Pass the ``viewer`` (the actor reading it): contact phone numbers are
    blanked per ``job_authz.hidden_contacts`` (an operator not assigned the
    job sees none; the assigned side sees the recipient's only from pickup
    and none once the job is closed: ADR-2D-36, assessment 2026-10-20), and
    ``contacts_hidden`` / ``hidden_contacts`` say so. Without a viewer (the
    business's own create response) nothing is hidden."""
    # Exact map pins: the business, staff and the assigned side; anyone else
    # (an operator still looking or negotiating) sees the ~1 km area (MD-2).
    coarsen = viewer is not None and not job_authz.may_see_contact_phones(viewer, job)
    # Contact phones also depend on the job's stage (assessment 2026-10-20
    # item 4): the recipient's only from pickup, none once the job is closed.
    hidden: dict[str, str | None] = (
        job_authz.hidden_contacts(viewer, job)
        if viewer is not None
        else {"pickup": None, "recipient": None}
    )
    hide_pickup = hidden["pickup"] is not None
    hide_recipient = hidden["recipient"] is not None
    view = job_view(job)
    view["pickup_location"] = _location_view(
        job.pickup_location, hide_phone=hide_pickup, coarsen=coarsen
    )
    view["destination_location"] = _location_view(
        job.destination_location, hide_phone=hide_recipient, coarsen=coarsen
    )
    view["recipient_name"] = job.recipient_name
    view["recipient_phone"] = "" if hide_recipient else job.recipient_phone
    view["contacts_hidden"] = hide_pickup or hide_recipient
    view["hidden_contacts"] = hidden
    # What pickup and delivery need for this job's band, and what the other
    # party has already confirmed on their own device (assessment 2026-10-20
    # L-5), so the driver's screen can show both.
    from fikisha.jobs import custody_rules
    from fikisha.jobs.models import CustodyConfirmation

    view["custody_requirements"] = custody_rules.requirements_view(job)
    recorded = set(CustodyConfirmation.objects.filter(job=job).values_list("stage", "method"))
    view["custody_confirmations"] = {
        "sender_in_app": ("PICKUP", "IN_APP") in recorded,
        "recipient_code": ("DELIVERY", "OTP") in recorded,
        "recipient_signature": ("DELIVERY", "SIGNATURE") in recorded,
    }
    if viewer is not None and job.is_high_value and job_authz.is_admin(viewer):
        # staff only: the effective high-value decision, so the console can
        # offer a Platform Admin the reversal of a rejection
        from fikisha.jobs.high_value import effective_decision

        decision, _ = effective_decision(job)
        view["high_value_decision"] = decision
    view["cargo"] = _cargo_view(job.cargo)
    agreement = job.agreement
    assignment = job.assignment
    view["agreed_price_kes"] = agreement.agreed_price_kes if agreement is not None else None
    view["assigned_driver_id"] = (
        str(assignment.assigned_driver_profile_id) if assignment is not None else None
    )
    view["assigned_vehicle_id"] = str(assignment.vehicle_id) if assignment is not None else None
    return view


#: Two decimal places of latitude/longitude is about 1.1 km at the equator:
#: enough to judge distance, not enough to find a house (maps MD-2).
_COARSE = Decimal("0.01")


def _location_view(
    location: JobLocation | None, *, hide_phone: bool = False, coarsen: bool = False
) -> dict[str, Any] | None:
    if location is None:
        return None
    lat, lng, geo_state = location.lat, location.lng, location.geo_state
    if coarsen and lat is not None and lng is not None:
        lat = lat.quantize(_COARSE, rounding=ROUND_HALF_UP)
        lng = lng.quantize(_COARSE, rounding=ROUND_HALF_UP)
        geo_state = GeoState.COARSENED
    return {
        "id": str(location.id),
        "type": location.type,
        "address_text": location.address_text,
        "lat": lat,
        "lng": lng,
        "geo_state": geo_state,
        "contact_name": location.contact_name,
        "contact_phone": "" if hide_phone else location.contact_phone,
    }


def _cargo_view(cargo: CargoDetails | None) -> dict[str, Any] | None:
    if cargo is None:
        return None
    return {
        "id": str(cargo.id),
        "description": cargo.description,
        "declared_value_kes": cargo.declared_value_kes,
        "handling_flags": cargo.handling_flags,
    }
