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

from django.db import transaction

from fikisha.audit import services as audit
from fikisha.business import authz as business_authz
from fikisha.business.models import BusinessRole
from fikisha.common.exceptions import DomainError
from fikisha.jobs import otp as otp_service
from fikisha.jobs.constants import JobStatus, ValueBand
from fikisha.jobs.errors import GuardFailed
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


# ─── two-party custody (founder assessment 2026-10-20 L-5, LD-4/LD-5) ──
# The driver's call completes pickup and delivery; the other party takes part
# by giving the code, signing on the driver's phone, or confirming on their
# own device (the sender in the app, the recipient through the link), which
# is recorded first as a ``CustodyConfirmation``. ``custody_rules`` says which
# methods each value band needs.


def _recorded_methods(job: Any, stage: str) -> set[str]:
    from fikisha.jobs.models import CustodyConfirmation

    return set(
        CustodyConfirmation.objects.filter(job=job, stage=stage).values_list("method", flat=True)
    )


class SenderConfirmationNotAllowed(GuardFailed):
    default_code = "sender_confirmation_not_allowed"
    default_detail = "The sender can confirm pickup only once the driver is assigned or at pickup."


@transaction.atomic
def sender_confirm_pickup(*, actor: Any, job_id: Any, party_name: str = "") -> dict[str, Any]:
    """The sender (business owner/dispatcher) confirms the handover in their
    own app. Recorded once; it counts as ``IN_APP`` when the driver completes
    pickup."""
    from fikisha.jobs.constants import ProofCapturedBy
    from fikisha.jobs.dto import job_view
    from fikisha.jobs.models import CustodyConfirmation
    from fikisha.jobs.selectors import job_for_update

    job = job_for_update(job_id)  # a double tap records once
    if not _actor_is_business_party(actor, job):
        raise GuardFailed(
            "In-app pickup confirmation must come from the business owner or dispatcher.",
            code="not_a_business_party",
        )
    if job.status not in {JobStatus.ASSIGNED, JobStatus.AT_PICKUP}:
        raise SenderConfirmationNotAllowed()
    if not CustodyConfirmation.objects.filter(job=job, stage="PICKUP", method="IN_APP").exists():
        user = getattr(actor, "user", None)
        CustodyConfirmation.objects.create(
            job=job,
            stage="PICKUP",
            method="IN_APP",
            captured_by=ProofCapturedBy.BUSINESS_CONTACT,
            actor=user if getattr(user, "pk", None) else None,
            party_name=(party_name or "").strip(),
        )
        audit.record(
            actor=actor,
            action="job.custody.sender_confirmed",
            entity_type="job",
            entity_id=job.id,
            after={"method": "IN_APP"},
        )
    return job_view(job)


def confirm_pickup(
    *,
    actor: Any,
    job_id: Any,
    code: str | None = None,
    signature_evidence_id: Any = None,
    photo_evidence_ids: list[Any] | None = None,
    party_name: str = "",
    condition_note: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """The driver completes pickup (``AT_PICKUP -> PICKED_UP``) with whatever
    the sender gave (code, signature) and the driver's photos; the sender's
    in-app confirmation counts if recorded. The band guard refuses it, naming
    what is missing, until the rule is met."""
    job = get_job(job_id)
    cid = None
    if code:
        # validated now (own txn: a wrong code's attempt count sticks),
        # consumed only when the transition commits
        cid = otp_service.verify_otp(
            job=job, purpose="PICKUP_HANDOVER", code=code, actor=actor, consume=False
        )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.PICKED_UP,
        data={
            "initiator_tokens": [],
            "_otp_challenge_id": cid,
            "_otp_purpose": "PICKUP_HANDOVER",
            "signature_evidence_id": signature_evidence_id,
            "photo_evidence_ids": photo_evidence_ids or [],
            "pickup_contact_name": (party_name or "").strip(),
            "condition_note": condition_note,
        },
        idempotency_key=idempotency_key,
    )
    return view


def confirm_pickup_with_otp(
    *,
    actor: Any,
    job_id: Any,
    code: str,
    condition_note: str = "",
    photo_evidence_ids: list[Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """The driver completes pickup with the sender's code (and any photos):
    ``confirm_pickup`` with a code."""
    return confirm_pickup(
        actor=actor,
        job_id=job_id,
        code=code,
        photo_evidence_ids=photo_evidence_ids,
        condition_note=condition_note,
        idempotency_key=idempotency_key,
    )


class PickupFallbackRetired(DomainError):
    status_code = 410
    default_code = "pickup_fallback_retired"
    default_detail = (
        "The operator-only pickup was retired: the sender must confirm too "
        "(code, signature or in-app)."
    )


def confirm_pickup_attested(**_: Any) -> dict[str, Any]:
    """Retired (LD-4): one party can no longer confirm a pickup alone."""
    raise PickupFallbackRetired()


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
    """The driver completes delivery with the recipient's name and whatever the
    band needs (code or signature, and the driver's photo for ELEVATED+). A
    code or signature the recipient already gave through their link counts."""
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


# ─── close-off (DELIVERED -> COMPLETED) ─────────────────────────────
class NotABusinessParty(GuardFailed):
    default_code = "not_a_business_party"
    default_detail = "Only the business owner or dispatcher can close this job."


@transaction.atomic
def sender_close_job(
    *,
    actor: Any,
    job_id: Any,
    method: str,
    mpesa_reference: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """The sender confirms the goods arrived and records paying the operator;
    the job completes (founder 2026-10-20, PD-3 / PD-4). Fikisha does not take
    or move the money: the record is the sender's statement, kept
    append-only. A failed transition (e.g. an open dispute) rolls the record
    back with it."""
    from fikisha.jobs.models import JobPaymentRecord
    from fikisha.jobs.selectors import job_for_update

    job = job_for_update(job_id)
    if not _actor_is_business_party(actor, job):
        raise NotABusinessParty()
    if job.status != JobStatus.DELIVERED:
        raise GuardFailed("Only a delivered job can be closed.", code="not_delivered")
    user: Any = actor.user  # a signed-in business party (checked above)
    if not JobPaymentRecord.objects.filter(job=job).exists():
        record = JobPaymentRecord.objects.create(
            job=job,
            method=method,
            mpesa_reference=(mpesa_reference or "").strip().upper(),
            recorded_by=user,
        )
        audit.record(
            actor=actor,
            action="job.payment.recorded_by_sender",
            entity_type="job",
            entity_id=job.id,
            after={"method": record.method, "mpesa_reference": record.mpesa_reference},
        )
    view, _ = _advance(
        actor=actor,
        job_id=job.id,
        to=JobStatus.COMPLETED,
        data={"initiator_tokens": ["BUSINESS_PARTY"]},
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
