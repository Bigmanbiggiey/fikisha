"""Custody + proof service (plan §10, chain-of-custody.md, D-CUS-2 / D-TRU-5).

Thin wrappers that resolve what the caller supplies (geo reading, OTP code,
business confirmation, attested fallback), verify it, and call
``JobLifecycleService.transition`` — the sole writer of ``job.status`` — which
runs the band-matrix guards and writes the append-only custody ``job_event``
rows + ``ProofOf*`` in one transaction.

OTP verification runs in **its own** committed transaction before the transition
so a failed attempt's ``attempts`` increment survives (brute-force cap) even
though the call then raises. The transition manages its own transaction.

Increment 4 covers the driver-side and business-side paths. The recipient-side
delivery confirmation via the scoped access link is plan §19 Step 7.
"""

from __future__ import annotations

from typing import Any

from fikisha.business import authz as business_authz
from fikisha.business.models import BusinessRole
from fikisha.jobs import otp as otp_service
from fikisha.jobs.constants import JobStatus, ValueBand
from fikisha.jobs.errors import GuardFailed, PickupConfirmationRequired
from fikisha.jobs.selectors import get_job
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition

_BUSINESS_CONFIRMERS: set[str] = {BusinessRole.OWNER, BusinessRole.DISPATCHER}
_HIGH_OR_ELEVATED = {ValueBand.ELEVATED, ValueBand.HIGH, ValueBand.VERY_HIGH}


class _BusinessRef:
    def __init__(self, business_id: Any) -> None:
        self.business_id = str(business_id)


def _geo(geo: dict[str, Any] | None) -> dict[str, Any] | None:
    if not geo:
        return None
    return {"lat": geo.get("lat"), "lng": geo.get("lng"), "accuracy_m": geo.get("accuracy_m")}


def _actor_is_business_party(actor: Any, job: Any) -> bool:
    return business_authz.has_role(actor, _BusinessRef(job.business_id), _BUSINESS_CONFIRMERS)


def _advance(
    *, actor: Any, job_id: Any, to: str, data: dict[str, Any], idempotency_key: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one transition; return ``(view, ctx.data)`` so a caller can read back
    a dev-exposed OTP code the apply fn stashed in the context."""
    ctx = TransitionContext(data=data)
    view = job_transition(
        job_id=job_id, to=to, actor=actor, context=ctx, idempotency_key=idempotency_key
    )
    return view, ctx.data


# ─── arrivals + transit (custody geo capture, OTP issuance) ──────────
def arrive_at_pickup(
    *, actor: Any, job_id: Any, geo: dict[str, Any] | None = None, idempotency_key: str = ""
) -> dict[str, Any]:
    view, data = _advance(
        actor=actor,
        job_id=job_id,
        to=JobStatus.AT_PICKUP,
        data={"initiator_tokens": [], "geo": _geo(geo)},
        idempotency_key=idempotency_key,
    )
    return {**view, "pickup_otp": data.get("_dev_otp_PICKUP_HANDOVER")}


def start_transit(*, actor: Any, job_id: Any, idempotency_key: str = "") -> dict[str, Any]:
    view, _ = _advance(
        actor=actor,
        job_id=job_id,
        to=JobStatus.IN_TRANSIT,
        data={"initiator_tokens": []},
        idempotency_key=idempotency_key,
    )
    return view


def arrive_at_destination(
    *, actor: Any, job_id: Any, geo: dict[str, Any] | None = None, idempotency_key: str = ""
) -> dict[str, Any]:
    view, data = _advance(
        actor=actor,
        job_id=job_id,
        to=JobStatus.AT_DESTINATION,
        data={"initiator_tokens": [], "geo": _geo(geo)},
        idempotency_key=idempotency_key,
    )
    return {
        **view,
        "recipient_otp": data.get("_dev_otp_RECIPIENT_VERIFY"),
        "recipient_link_token": data.get("_dev_recipient_link_token"),
    }


# ─── pickup proof (AT_PICKUP -> PICKED_UP) ──────────────────────────
def confirm_pickup_with_otp(
    *,
    actor: Any,
    job_id: Any,
    code: str,
    condition_note: str = "",
    photo_evidence_ids: list[Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    job = get_job(job_id)
    # validate now (own txn — a wrong code's attempt count sticks); consume only
    # when the transition commits
    cid = otp_service.verify_otp(
        job=job, purpose="PICKUP_HANDOVER", code=code, actor=actor, consume=False
    )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.PICKED_UP,
        data={
            "initiator_tokens": [],
            "pickup_method": "OTP",
            "_otp_challenge_id": cid,
            "_otp_purpose": "PICKUP_HANDOVER",
            "condition_note": condition_note,
            "photo_evidence_ids": photo_evidence_ids or [],
        },
        idempotency_key=idempotency_key,
    )
    return view


def confirm_pickup_by_business(
    *,
    actor: Any,
    job_id: Any,
    condition_note: str = "",
    photo_evidence_ids: list[Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Server-confirmed in-app pickup confirmation by the business owner/
    dispatcher — same authoritative transition and proof model as the OTP path
    (Founder Increment-4 condition 6)."""
    job = get_job(job_id)
    if not _actor_is_business_party(actor, job):
        raise GuardFailed(
            "In-app pickup confirmation must come from the business owner or dispatcher.",
            code="not_a_business_party",
        )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.PICKED_UP,
        data={
            "initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"],
            "pickup_method": "BUSINESS_CONFIRM",
            "actor_is_business_party": True,
            "condition_note": condition_note,
            "photo_evidence_ids": photo_evidence_ids or [],
        },
        idempotency_key=idempotency_key,
    )
    return view


def confirm_pickup_attested(
    *,
    actor: Any,
    job_id: Any,
    fallback_photo_id: Any,
    pickup_contact_name: str,
    condition_note: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """STANDARD-band-only operator-attested fallback for an undeliverable OTP:
    goods photo + pickup-contact name -> attestation OPERATOR_ATTESTED_UNVERIFIED,
    the job is capped at STANDARD (D-CUS-2). Refused for ELEVATED+."""
    job = get_job(job_id)
    if (job.value_band or ValueBand.STANDARD) in _HIGH_OR_ELEVATED:
        raise PickupConfirmationRequired(
            "This value band requires a verified pickup (OTP or in-app business "
            "confirmation); the operator-attested fallback is not allowed."
        )
    if not fallback_photo_id or not (pickup_contact_name or "").strip():
        raise PickupConfirmationRequired(
            "The attested fallback needs a goods photo and the pickup-contact's name."
        )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.PICKED_UP,
        data={
            "initiator_tokens": [],
            "pickup_method": "ATTESTED",
            "fallback_photo_id": fallback_photo_id,
            "pickup_contact_name": pickup_contact_name.strip(),
            "condition_note": condition_note,
        },
        idempotency_key=idempotency_key,
    )
    return view


# ─── delivery proof (AT_DESTINATION -> DELIVERED) ───────────────────
def confirm_delivery(
    *,
    actor: Any,
    job_id: Any,
    party_name: str,
    code: str | None = None,
    signature_evidence_id: Any = None,
    photo_evidence_ids: list[Any] | None = None,
    condition_note: str = "",
    geo: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Driver-side proof of delivery. STANDARD: name + >=1 of {OTP, SIGNATURE,
    PHOTO}. ELEVATED/HIGH/VERY_HIGH: name + recipient OTP **and** >=1 photo
    (D-TRU-5). The recipient-via-link path is plan §19 Step 7."""
    job = get_job(job_id)
    cid = None
    if code:
        cid = otp_service.verify_otp(
            job=job, purpose="RECIPIENT_VERIFY", code=code, actor=actor, consume=False
        )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.DELIVERED,
        data={
            "initiator_tokens": [],
            "party_name": party_name,
            "otp_verified": cid is not None,
            "_otp_challenge_id": cid,
            "_otp_purpose": "RECIPIENT_VERIFY",
            "signature_evidence_id": signature_evidence_id,
            "photo_evidence_ids": photo_evidence_ids or [],
            "condition_note": condition_note,
            "geo": _geo(geo),
        },
        idempotency_key=idempotency_key,
    )
    return view


# ─── pickup failure (AT_PICKUP -> FAILED) ───────────────────────────
def fail_at_pickup(
    *, actor: Any, job_id: Any, reason_text: str, idempotency_key: str = ""
) -> dict[str, Any]:
    view, _ = _advance(
        actor=actor,
        job_id=job_id,
        to=JobStatus.FAILED,
        data={"initiator_tokens": [], "reason_text": reason_text},
        idempotency_key=idempotency_key,
    )
    return view
