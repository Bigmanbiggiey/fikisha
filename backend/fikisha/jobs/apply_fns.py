"""Transition side-effect functions (job-state-machine.md §3 "Side effects").

Each ``apply`` fn is ``fn(job, actor, ctx) -> None`` and runs **inside** the
lifecycle transaction, after the guards pass and before ``job.status`` is
written. It creates the rows the transition implies (``Agreement`` /
``Assignment`` / ``ProofOf*`` / ``CancellationRecord`` / ``FailureRecord`` …)
and may set domain fields on ``job`` (e.g. ``value_band`` at publish). It must
**not** write ``job.status``, ``job.version``, the ``*_at`` lifecycle stamps,
the ``job_event`` rows, the audit row, or the outbox rows — the service owns
those (§2.1 steps 8-12).

Custody side effects (Increment 4): ``arrive_pickup`` / ``arrive_destination``
issue the pickup / recipient OTP; ``confirm_pickup`` / ``confirm_delivery`` write
the ``ProofOf*`` row **and** the method-specific custody ``job_event``
(``PICKUP_OTP_CONFIRMED`` / ``PICKUP_BUSINESS_CONFIRMED`` /
``PICKUP_OPERATOR_ATTESTED`` / ``RECIPIENT_VERIFIED``) — the one place the method
is known (ADR-2D-15).

Dispute side effects (Step 8, plan §19): ``freeze`` / ``freeze_post_completion``
/ ``resolve_failed`` / ``resolve_cancelled`` are ``noop`` here **by design**,
not a stub. The Job-lifecycle module boundary rule (sibling apps depend
inward on ``jobs``, never the reverse) means this module must not import or
write ``fikisha.incidents`` models. ``fikisha.incidents.services`` owns
creating the ``Dispute`` row (stamping ``pre_dispute_status`` from the
still-pre-write, row-locked ``job.status`` it reads itself, ADR-2D-07) and
marking a resolved ``Dispute`` — both **before** calling
``JobLifecycleService.transition()`` inside the *same* outer
``transaction.atomic()`` (a nested atomic block is a savepoint on the same
locked row, so both reads see the identical, consistent job state). The DISPUTED
status write itself — plus the ``job_event`` / audit / outbox rows the engine
already produces — is the entire job-side effect of a freeze or of a
non-completing resolution; there is nothing left for these four apply fns to
do. ``resolve_completed`` (``DISPUTED → COMPLETED``) is the one resolution
route with a real job-side effect — see "Completion + commission" below.

Completion + commission (Step 9, plan §19): ``complete`` calls
``fikisha.jobs.commission.create_commission_record_locked`` — a same-app
domain-surface module (mirrors ``jobs.otp`` / ``jobs.recipient``; no
cross-app boundary question at all, since commission is Job-lifecycle
financial data, not a separate bounded workflow the way Incidents is). This
keeps commission creation *literally* inside the transition's own
transaction rather than wrapping it from outside (ADR-2D-22's pattern,
adapted): if it fails, the whole ``DELIVERED → COMPLETED`` (or
``DISPUTED → COMPLETED``) transition — including the status write — rolls
back with it. ``resolve_completed`` is a plain alias of ``complete``: both
routes to ``COMPLETED`` need the identical, idempotent "ensure a
CommissionRecord exists" side effect (ADR-2D-23).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db.models import Max

from fikisha.jobs import commission as commission_service
from fikisha.jobs import eligibility
from fikisha.jobs.constants import (
    HIGH_VALUE_BANDS,
    Attestation,
    CancellationReason,
    ConfirmationMethod,
    JobEventCategory,
    JobEventType,
    JobStatus,
    OperatorParty,
    ProofCapturedBy,
    ProofKind,
    TrustLevel,
    ValueBand,
    compute_penalty_class,
)
from fikisha.jobs.errors import GuardFailed, OtpNotIssued
from fikisha.jobs.models import (
    Agreement,
    Assignment,
    CancellationRecord,
    FailureRecord,
    JobEvent,
    ProofOfDelivery,
    ProofOfPickup,
)
from fikisha.jobs.selectors import current_config_version

ApplyFn = Callable[[Any, Any, dict[str, Any]], None]


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def _actor_role(actor: Any) -> str:
    return str(getattr(actor, "audit_role", "") or "")


def _resolve_party(ctx: dict[str, Any]) -> tuple[str, Any, Any]:
    """``(operator_party, operator_id, group_id)`` with exactly one id set —
    matches the ``ck_*_one_party`` DB constraint. The Negotiation / Assignment
    services (plan §19 Steps 4-5) always supply these."""
    party = ctx.get("operator_party") or OperatorParty.OPERATOR
    operator_id = ctx.get("operator_id") if party == OperatorParty.OPERATOR else None
    group_id = ctx.get("group_id") if party == OperatorParty.GROUP else None
    if operator_id is None and group_id is None:
        raise GuardFailed(
            "The operator (or group) party must be identified for this transition.",
            code="operator_party_required",
        )
    return party, operator_id, group_id


# ── no-op transitions (the job_event the service writes is the whole record) ──
def noop(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    return None


start_transit = noop


def _append_event(
    job: Any,
    *,
    event_type: str,
    actor: Any,
    category: str = JobEventCategory.CUSTODY,
    is_custody: bool = True,
    confirmation_method: str | None = None,
    evidence_ids: list[Any] | None = None,
    source_meta: dict[str, Any] | None = None,
    note: str = "",
) -> None:
    """Write one ``job_event`` inside the transition txn (append-only). The
    service's ``_write_events`` continues the ``seq`` after it."""
    seq = (JobEvent.objects.filter(job=job).aggregate(m=Max("seq"))["m"] or 0) + 1
    user = getattr(actor, "user", actor)
    JobEvent.objects.create(
        job=job,
        seq=seq,
        category=category,
        type=event_type,
        is_custody=is_custody,
        actor_user=user if getattr(user, "pk", None) else None,
        actor_role=str(getattr(actor, "audit_role", "") or ""),
        confirmation_method=confirmation_method,
        evidence_ids=[str(e) for e in (evidence_ids or []) if e],
        source_meta=source_meta or {},
        note=note,
        config_version_id=job.config_version_id,
    )


_OTP_ISSUED_EVENT = {
    "PICKUP_HANDOVER": JobEventType.PICKUP_OTP_ISSUED,
    "RECIPIENT_VERIFY": JobEventType.RECIPIENT_OTP_ISSUED,
}


def _issue_step_otp(job: Any, actor: Any, ctx: dict[str, Any], *, purpose: str, phone: str) -> None:
    """Best-effort OTP issuance on arrival. A missing contact phone does **not**
    block the arrival transition — the driver can still use in-app business
    confirmation (or, STANDARD only, the attested fallback). The
    ``*_OTP_ISSUED`` timeline event is written only when a code was actually
    issued."""
    from fikisha.jobs import otp as otp_service

    try:
        issued = otp_service.issue_otp(job=job, purpose=purpose, phone=phone or "", actor=actor)
    except OtpNotIssued:
        return
    ctx[f"_dev_otp_{purpose}"] = issued.dev_code
    _append_event(
        job,
        event_type=_OTP_ISSUED_EVENT[purpose],
        actor=actor,
        category=JobEventCategory.SYSTEM,
        is_custody=False,
        source_meta={"challenge_id": issued.challenge_id, "sent_to_phone": issued.sent_to_phone},
    )


def arrive_pickup(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    phone = getattr(job.pickup_location, "contact_phone", "") if job.pickup_location_id else ""
    _issue_step_otp(job, actor, ctx, purpose="PICKUP_HANDOVER", phone=phone)


def arrive_destination(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    _issue_step_otp(job, actor, ctx, purpose="RECIPIENT_VERIFY", phone=job.recipient_phone or "")
    # the recipient access link — job row is already FOR-UPDATE-locked by the
    # transition, so the amended revoke-then-replace runs in this same txn
    # (plan §19 Step 7, ADR-2D-18). Boundary only: no delivery of the link here.
    from django.conf import settings

    from fikisha.jobs import recipient as recipient_service

    _link, raw_token = recipient_service.issue_or_refresh_link_locked(job=job, actor=actor)
    if settings.AUTH_CONFIG.get("OTP_DEV_EXPOSE"):
        ctx["_dev_recipient_link_token"] = raw_token


# ── publish ──────────────────────────────────────────────────────────
def publish(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Compute + freeze the value band, required trust level and high-value flag;
    pin the config version. ``published_at`` is stamped by the service."""
    band = eligibility.band_for_declared_value(job.declared_value_kes)
    job.value_band = band
    job.required_trust_level = eligibility.band_min_trust_level(band) or TrustLevel.L1
    job.is_high_value = band in HIGH_VALUE_BANDS
    if job.config_version_id is None:
        job.config_version = current_config_version()


# ── cancel / fail (terminal-reason rows) ─────────────────────────────
def cancel(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    reason_code = ctx.get("reason_code") or CancellationReason.OTHER
    CancellationRecord.objects.create(
        job=job,
        cancelled_by_role=_actor_role(actor),
        cancelled_by_user=_actor_user(actor),
        at_status=job.status,
        reason_code=reason_code,
        reason_text=(ctx.get("reason_text") or "").strip(),
        penalty_class=compute_penalty_class(job.status),
    )


def fail(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    reason = (ctx.get("reason_text") or "").strip()
    if not reason:
        # REQUESTED→FAILED via the scheduler carries a canonical reason.
        reason = "EXPIRED_NO_OFFER" if job.status == JobStatus.REQUESTED else "UNSPECIFIED"
    FailureRecord.objects.create(
        job=job,
        at_status=job.status,
        reason_text=reason,
        recorded_by_admin=_actor_user(actor),
    )


# ── confirm (freeze the agreed price) ───────────────────────────────
def confirm(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Create the (append-only) ``Agreement`` and point the job at it.
    ``confirmed_at`` is stamped by the service. The Negotiation Service (plan
    §19 Step 4) supplies the accepted price + accepting entries in ``ctx``."""
    party, operator_id, group_id = _resolve_party(ctx)
    agreement = Agreement.objects.create(
        job=job,
        operator_party=party,
        operator_id=operator_id,
        group_id=group_id,
        agreed_price_kes=int(ctx["agreed_price_kes"]),
        accepting_entry_ids=list(ctx.get("accepting_entry_ids") or []),
        terms_note=(ctx.get("terms_note") or "").strip(),
    )
    job.agreement = agreement
    # The frozen agreed price becomes the job's price of record.
    job.proposed_price_kes = agreement.agreed_price_kes


# ── assign (driver + vehicle) ──────────────────────────────────────
def assign(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    driver = ctx["driver_profile"]
    vehicle = ctx["vehicle"]
    party, operator_id, group_id = _resolve_party(ctx)
    assignment = Assignment.objects.create(
        job=job,
        operator_party=party,
        operator_id=operator_id,
        group_id=group_id,
        assigned_driver_profile=driver,
        vehicle=vehicle,
        assigned_by=ctx.get("assigned_by") or "SELF",
        assigned_by_user=_actor_user(actor),
        reassigned_from_id=ctx.get("reassigned_from_id"),
        admin_override_reason=(ctx.get("admin_override_reason") or "").strip(),
        driver_trust_level=eligibility.interim_driver_trust_level(driver) or TrustLevel.L1,
        config_version=current_config_version(),
    )
    job.assignment = assignment


# ── custody proofs (chain-of-custody.md §2 / §4, D-CUS-2 / D-TRU-5) ──
_PICKUP_METHOD_EVENT = {
    "OTP": (JobEventType.PICKUP_OTP_CONFIRMED, ConfirmationMethod.OTP),
    "BUSINESS_CONFIRM": (JobEventType.PICKUP_BUSINESS_CONFIRMED, ConfirmationMethod.IN_APP),
    "ATTESTED": (JobEventType.PICKUP_OPERATOR_ATTESTED, ConfirmationMethod.PHOTO),
}


def confirm_pickup(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfPickup`` + the method-specific custody event. The
    operator-attested STANDARD-band fallback records
    ``attestation = OPERATOR_ATTESTED_UNVERIFIED`` and **caps the job at
    STANDARD** (the guard has already refused it for any higher band).
    ``picked_up_at`` is stamped by the service."""
    method = str(ctx.get("pickup_method") or "")
    attested = method == "ATTESTED"
    event_type, conf_method = _PICKUP_METHOD_EVENT.get(
        method, (JobEventType.GOODS_RECEIVED, ConfirmationMethod.NONE)
    )
    photo_ids = list(ctx.get("photo_evidence_ids") or [])
    if attested and ctx.get("fallback_photo_id"):
        photo_ids = [ctx["fallback_photo_id"], *photo_ids]

    ProofOfPickup.objects.create(
        job=job,
        kind=ProofKind.PICKUP,
        party_name=(ctx.get("pickup_contact_name") or "").strip(),
        methods=[conf_method] if conf_method != ConfirmationMethod.NONE else [],
        otp_verified=method == "OTP",
        signature_evidence_id=ctx.get("signature_evidence_id"),
        photo_evidence_ids=photo_ids,
        captured_by=ctx.get("captured_by")
        or (
            ProofCapturedBy.BUSINESS_CONTACT
            if method == "BUSINESS_CONFIRM"
            else ProofCapturedBy.OPERATOR
        ),
        condition_note=(ctx.get("condition_note") or "").strip(),
        attestation=Attestation.OPERATOR_ATTESTED_UNVERIFIED if attested else Attestation.VERIFIED,
    )
    _append_event(
        job,
        event_type=event_type,
        actor=actor,
        confirmation_method=conf_method,
        evidence_ids=photo_ids,
        note=(ctx.get("condition_note") or "").strip(),
    )
    if ctx.get("_otp_challenge_id"):
        from fikisha.jobs import otp as otp_service

        otp_service.consume_otp(purpose=ctx["_otp_purpose"], challenge_id=ctx["_otp_challenge_id"])
    if attested:
        job.value_band = ValueBand.STANDARD


def confirm_delivery(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfDelivery`` + the ``RECIPIENT_VERIFIED`` custody event.
    ``delivered_at`` is stamped by the service."""
    otp_ok = bool(ctx.get("otp_verified"))
    photos = list(ctx.get("photo_evidence_ids") or [])
    sig = ctx.get("signature_evidence_id")
    methods: list[str] = []
    if otp_ok:
        methods.append(ConfirmationMethod.OTP)
    if sig:
        methods.append(ConfirmationMethod.SIGNATURE)
    if photos:
        methods.append(ConfirmationMethod.PHOTO)
    conf_method = methods[0] if methods else ConfirmationMethod.NONE

    ProofOfDelivery.objects.create(
        job=job,
        kind=ProofKind.DELIVERY,
        party_name=(ctx.get("party_name") or "").strip(),
        methods=methods,
        otp_verified=otp_ok,
        signature_evidence_id=sig,
        photo_evidence_ids=photos,
        captured_by=ctx.get("captured_by") or ProofCapturedBy.OPERATOR,
        condition_note=(ctx.get("condition_note") or "").strip(),
    )
    _append_event(
        job,
        event_type=JobEventType.RECIPIENT_VERIFIED,
        actor=actor,
        confirmation_method=conf_method,
        evidence_ids=[*([sig] if sig else []), *photos],
        note=(ctx.get("condition_note") or "").strip(),
    )
    if ctx.get("_otp_challenge_id"):
        from fikisha.jobs import otp as otp_service

        otp_service.consume_otp(purpose=ctx["_otp_purpose"], challenge_id=ctx["_otp_challenge_id"])


# ── complete (Step 9 — commission) ───────────────────────────────────
# As of Step 9, every transition in ALLOWED_TRANSITIONS has a real apply fn
# (``noop`` counts as real — an intentional no-op, not "not built yet"); the
# ``_deferred(...)`` placeholder-stub helper that Increments 1-8 used for
# ``freeze`` / ``resolve_*`` / ``complete`` is retired (Steps 10-15 add no new
# Job transitions). ``NotImplementedInThisIncrement`` itself stays in
# ``jobs.errors`` — harmless, and removing an exception class is more
# disruptive than the dead code it would save.
def complete(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """``DELIVERED -> COMPLETED`` *and* ``DISPUTED -> COMPLETED``
    (``resolve_completed`` is a literal alias — see below) share this body:
    ensure exactly one ``CommissionRecord`` exists for this job, computed
    from its frozen ``Agreement`` under the row lock this apply fn already
    runs inside (job-state-machine.md §2.1 — apply fns run *before* the
    status write, in the same transaction the engine commits or rolls back
    as one unit; a failure here aborts the whole transition, so ``job.status``
    never reaches ``COMPLETED`` with a missing commission record). Idempotent:
    a job that reaches ``COMPLETED`` a second time (a post-completion dispute
    resolved back to ``COMPLETED``, Step 8 ADR-2D-20) already has its record
    from the first pass and gets no second one (plan §19 Step 9 brief §18-19)."""
    commission_service.create_commission_record_locked(job=job, actor=actor)


# Dispute freeze / resolution: the job-side effect is exactly the status write
# the engine already performs — see the module docstring. ``fikisha.incidents
# .services`` creates/updates the ``Dispute`` row itself, before/around this
# call, in the same transaction.
freeze = noop
freeze_post_completion = noop
resolve_completed = complete
resolve_failed = noop
resolve_cancelled = noop


APPLY: dict[str, ApplyFn] = {
    "noop": noop,
    "publish": publish,
    "cancel": cancel,
    "fail": fail,
    "confirm": confirm,
    "assign": assign,
    "arrive_pickup": arrive_pickup,
    "confirm_pickup": confirm_pickup,
    "start_transit": start_transit,
    "arrive_destination": arrive_destination,
    "confirm_delivery": confirm_delivery,
    "freeze": freeze,
    "freeze_post_completion": freeze_post_completion,
    "complete": complete,
    "resolve_completed": resolve_completed,
    "resolve_failed": resolve_failed,
    "resolve_cancelled": resolve_cancelled,
}
