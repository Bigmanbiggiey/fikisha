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
is known (ADR-2D-15). ``freeze`` / ``complete`` / ``resolve_*`` still raise
``NotImplementedInThisIncrement`` (plan §19 Steps 8-9).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db.models import Max

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
from fikisha.jobs.errors import GuardFailed, NotImplementedInThisIncrement, OtpNotIssued
from fikisha.jobs.models import (
    Agreement,
    Assignment,
    CancellationRecord,
    FailureRecord,
    JobEvent,
    ProofOfDelivery,
    ProofOfPickup,
)

ApplyFn = Callable[[Any, Any, dict[str, Any]], None]


def _current_config_version() -> Any:
    from fikisha.platform_config.models import PlatformConfig

    cfg = PlatformConfig.objects.select_related("current_version").filter(pk=1).first()
    return cfg.current_version if cfg and cfg.current_version_id else None


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


# ── publish ──────────────────────────────────────────────────────────
def publish(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Compute + freeze the value band, required trust level and high-value flag;
    pin the config version. ``published_at`` is stamped by the service."""
    band = eligibility.band_for_declared_value(job.declared_value_kes)
    job.value_band = band
    job.required_trust_level = eligibility.band_min_trust_level(band) or TrustLevel.L1
    job.is_high_value = band in HIGH_VALUE_BANDS
    if job.config_version_id is None:
        job.config_version = _current_config_version()


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
        config_version=_current_config_version(),
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


# ── deferred to later increments ────────────────────────────────────
def _deferred(what: str) -> ApplyFn:
    def _fn(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
        raise NotImplementedInThisIncrement(
            f"The {what} transition path is delivered in a later Phase 2D increment "
            f"(plan §19); the lifecycle engine, guards and DB backstop for it are complete."
        )

    return _fn


freeze = _deferred("dispute (freeze)")
freeze_post_completion = _deferred("post-completion dispute (freeze)")
complete = _deferred("completion + commission")
resolve_completed = _deferred("dispute resolution → COMPLETED")
resolve_failed = _deferred("dispute resolution → FAILED")
resolve_cancelled = _deferred("dispute resolution → CANCELLED")


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
