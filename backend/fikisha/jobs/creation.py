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

Only ad-hoc pickup/destination locations are supported here (`source_kind
=AD_HOC`) — reusing a saved `BusinessLocation` (`source_kind=BUSINESS_
LOCATION`) is deliberately deferred; nothing in the approved schema is
missing for it, there simply isn't yet a caller that needs it. See the
Step 10 Founder Gate report's Known limitations.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import Http404

from fikisha.audit import services as audit
from fikisha.jobs import job_authz
from fikisha.jobs.constants import JobStatus, LocationSourceKind, LocationType
from fikisha.jobs.dto import job_view
from fikisha.jobs.errors import NotAuthorisedToAssign
from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
from fikisha.jobs.selectors import job_for_update
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.outbox.services import emit


class NotAuthorisedToCreateJob(NotAuthorisedToAssign):
    default_code = "not_authorised_to_create_job"
    default_detail = "You may not create a job for this business."


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def _make_location(*, type_: str, data: dict[str, Any]) -> JobLocation:
    return JobLocation.objects.create(
        type=type_,
        source_kind=LocationSourceKind.AD_HOC,
        address_text=(data.get("address_text") or "").strip(),
        lat=data.get("lat"),
        lng=data.get("lng"),
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
    from fikisha.business.models import BusinessAccount, BusinessRole

    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist as exc:
        raise Http404("No such business.") from exc
    is_business_party = business_authz.has_role(
        actor, business, {BusinessRole.OWNER, BusinessRole.DISPATCHER}
    )
    if not is_business_party and not job_authz.is_admin(actor):
        raise NotAuthorisedToCreateJob()

    cargo = CargoDetails.objects.create(
        description=(data["cargo"].get("description") or "").strip(),
        category_code=(data["cargo"].get("category_code") or "").strip(),
        est_weight_kg=data["cargo"].get("est_weight_kg"),
        dims_l_cm=data["cargo"].get("dims_l_cm"),
        dims_w_cm=data["cargo"].get("dims_w_cm"),
        dims_h_cm=data["cargo"].get("dims_h_cm"),
        declared_value_kes=data["cargo"]["declared_value_kes"],
        handling_flags=list(data["cargo"].get("handling_flags") or []),
    )
    pickup = _make_location(type_=LocationType.PICKUP, data=data["pickup_location"])
    destination = _make_location(type_=LocationType.DESTINATION, data=data["destination_location"])
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
        latent_risk_cargo=bool(data.get("latent_risk_cargo", False)),
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
    `JobLifecycleService.transition()`; it implements nothing itself."""
    job = job_for_update(job_id)
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
    holds; the transition's own initiator check remains the real guard."""
    job = job_for_update(job_id)
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


def job_detail(job: Job) -> dict[str, Any]:
    """Read projection for the API — `job_view()` plus the lightweight,
    already-frozen related-object summaries a caller needs (never
    recomputed business logic — every field here is a stored value)."""
    view = job_view(job)
    view["pickup_location"] = _location_view(job.pickup_location)
    view["destination_location"] = _location_view(job.destination_location)
    view["recipient_name"] = job.recipient_name
    view["recipient_phone"] = job.recipient_phone
    view["cargo"] = _cargo_view(job.cargo)
    agreement = job.agreement
    assignment = job.assignment
    view["agreed_price_kes"] = agreement.agreed_price_kes if agreement is not None else None
    view["assigned_driver_id"] = (
        str(assignment.assigned_driver_profile_id) if assignment is not None else None
    )
    view["assigned_vehicle_id"] = str(assignment.vehicle_id) if assignment is not None else None
    return view


def _location_view(location: JobLocation | None) -> dict[str, Any] | None:
    if location is None:
        return None
    return {
        "id": str(location.id),
        "type": location.type,
        "address_text": location.address_text,
        "lat": location.lat,
        "lng": location.lng,
        "contact_name": location.contact_name,
        "contact_phone": location.contact_phone,
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
