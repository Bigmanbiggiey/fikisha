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
``fikisha.jobs.commission.create_commission_records_locked`` — a same-app
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

from django.db import transaction
from django.db.models import Max

from fikisha.common.logging_setup import get_logger
from fikisha.jobs import commission as commission_service
from fikisha.jobs import eligibility
from fikisha.jobs.constants import (
    HIGH_VALUE_BANDS,
    Attestation,
    CancellationReason,
    CancellingSide,
    ConfirmationMethod,
    JobEventCategory,
    JobEventType,
    JobStatus,
    OperatorParty,
    PenaltyClass,
    ProofCapturedBy,
    ProofKind,
    TrustLevel,
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

log = get_logger("fikisha.jobs.apply")

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
def _freeze_value_band(job: Any) -> None:
    """Compute + freeze the value band, required trust level and high-value
    flag; pin the config version. Shared by ``publish`` and by ``cancel``
    when a job is cancelled directly from ``DRAFT`` (see ``cancel``'s
    docstring) — both are "a job leaves DRAFT" moments, and
    ``ck_job_band_set_once_published`` requires every non-DRAFT row to carry
    a real band, not a fabricated one computed after the fact."""
    band = eligibility.band_for_declared_value(job.declared_value_kes)
    job.value_band = band
    job.required_trust_level = eligibility.band_min_trust_level(band) or TrustLevel.L1
    job.is_high_value = band in HIGH_VALUE_BANDS
    if job.config_version_id is None:
        job.config_version = current_config_version()


def publish(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """``published_at`` is stamped by the service."""
    _freeze_value_band(job)


# ── cancel / fail (terminal-reason rows) ─────────────────────────────
def cancel(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """A job cancelled directly from ``DRAFT`` (the ``(DRAFT, CANCELLED)`` row)
    never went through ``publish`` — ``value_band`` freezes here instead, using
    the identical computation, so ``ck_job_band_set_once_published`` holds for
    every row that has ever left ``DRAFT``, cancelled-before-publish included
    (a real gap: no test exercised this path before Step 10's API tests did —
    self-caught during that verification, matching the Increment 3/4
    precedent of fixing what a later increment's testing surfaces)."""
    if job.status == JobStatus.DRAFT:
        _freeze_value_band(job)
    reason_code = ctx.get("reason_code") or CancellationReason.OTHER
    tokens = {str(t) for t in (ctx.get("initiator_tokens") or [])}
    side = CancellingSide.BUSINESS if "BUSINESS_PARTY" in tokens else CancellingSide.STAFF
    record = CancellationRecord.objects.create(
        job=job,
        cancelled_by_role=_actor_role(actor),
        cancelled_by_user=_actor_user(actor),
        at_status=job.status,
        reason_code=reason_code,
        reason_text=(ctx.get("reason_text") or "").strip(),
        penalty_class=compute_penalty_class(job.status),
        cancelling_side=side,
        business_id=job.business_id,
    )
    if side == CancellingSide.BUSINESS and record.penalty_class != PenaltyClass.NONE:
        from fikisha.jobs import cancellation_flags

        cancellation_flags.check_business(job.business_id)


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
        # each side's commission rate, fixed now (commission split D-4)
        **commission_service.pinned_rates(),
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
        driver_trust_level=eligibility.driver_trust_level(driver) or TrustLevel.L1,
        config_version=current_config_version(),
    )
    job.assignment = assignment


# ── custody proofs (chain-of-custody.md §2, founder assessment 2026-10-20) ──
_METHOD_ORDER = (
    ConfirmationMethod.OTP,
    ConfirmationMethod.IN_APP,
    ConfirmationMethod.SIGNATURE,
    ConfirmationMethod.PHOTO,
)


def _ordered(present: set[str]) -> list[str]:
    return [str(m) for m in _METHOD_ORDER if str(m) in present]


def _recorded_evidence(job: Any, stage: str) -> list[Any]:
    ids: list[Any] = []
    from fikisha.jobs import confirmations

    for row in confirmations.counted(job, stage).values_list("evidence_ids", flat=True):
        ids.extend(row or [])
    return ids


def confirm_pickup(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfPickup`` with every method present (the band guard has
    checked them against ``custody_proof_rules``) and the custody event. The
    driver captures it; the sender's own in-app confirmation is part of it.
    ``picked_up_at`` is stamped by the service."""
    from fikisha.jobs.guards import custody_methods_present

    methods = _ordered(custody_methods_present(job, "PICKUP", ctx))
    photo_ids = list(ctx.get("photo_evidence_ids") or [])
    if ConfirmationMethod.OTP in methods:
        event_type = JobEventType.PICKUP_OTP_CONFIRMED
    elif ConfirmationMethod.IN_APP in methods:
        event_type = JobEventType.PICKUP_BUSINESS_CONFIRMED
    else:
        event_type = JobEventType.GOODS_RECEIVED
    conf_method = methods[0] if methods else ConfirmationMethod.NONE
    sig = ctx.get("signature_evidence_id")

    ProofOfPickup.objects.create(
        job=job,
        kind=ProofKind.PICKUP,
        party_name=(ctx.get("pickup_contact_name") or "").strip(),
        methods=methods,
        otp_verified=ConfirmationMethod.OTP in methods,
        signature_evidence_id=sig,
        photo_evidence_ids=photo_ids,
        captured_by=ctx.get("captured_by") or ProofCapturedBy.OPERATOR,
        condition_note=(ctx.get("condition_note") or "").strip(),
        attestation=Attestation.VERIFIED,
    )
    _append_event(
        job,
        event_type=event_type,
        actor=actor,
        confirmation_method=conf_method,
        evidence_ids=[*([sig] if sig else []), *photo_ids],
        note=(ctx.get("condition_note") or "").strip(),
    )
    if ctx.get("_otp_challenge_id"):
        from fikisha.jobs import otp as otp_service

        otp_service.consume_otp(purpose=ctx["_otp_purpose"], challenge_id=ctx["_otp_challenge_id"])


def confirm_delivery(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfDelivery`` + the ``RECIPIENT_VERIFIED`` custody event,
    counting a code or signature the recipient gave through their link.
    ``delivered_at`` is stamped by the service."""
    from fikisha.jobs.guards import custody_methods_present

    methods = _ordered(custody_methods_present(job, "DELIVERY", ctx))
    photos = list(ctx.get("photo_evidence_ids") or [])
    sig = ctx.get("signature_evidence_id")
    linked = _recorded_evidence(job, "DELIVERY")
    if not sig and linked:
        sig = linked[0]
    conf_method = methods[0] if methods else ConfirmationMethod.NONE

    ProofOfDelivery.objects.create(
        job=job,
        kind=ProofKind.DELIVERY,
        party_name=(ctx.get("party_name") or "").strip(),
        methods=methods,
        otp_verified=ConfirmationMethod.OTP in methods,
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
    ensure the job's ``CommissionRecord``s (one per paying side, ADR-2D-55)
    exist, computed from its frozen ``Agreement`` and the rates fixed on it,
    under the row lock this apply fn already runs inside
    (job-state-machine.md §2.1 — apply fns run *before* the status write, in
    the same transaction the engine commits or rolls back as one unit; a
    failure here aborts the whole transition, so ``job.status`` never
    reaches ``COMPLETED`` with a missing commission record). Idempotent: a
    job that reaches ``COMPLETED`` a second time (a post-completion dispute
    resolved back to ``COMPLETED``, Step 8 ADR-2D-20) already has its records
    from the first pass and gets none new (plan §19 Step 9 brief §18-19)."""
    commission_service.create_commission_records_locked(job=job, actor=actor)
    driver_id = getattr(job.assignment, "assigned_driver_profile_id", None)
    if driver_id is not None:
        transaction.on_commit(lambda: _propose_tier(driver_id))


def _propose_tier(driver_id: Any) -> None:
    """After a completion commits: propose the driver's next tier if it just
    became due (operator tiers, ADR-2D-52). Proposes only; a failure here is
    logged and never undoes the completion."""
    from fikisha.trust import services as trust

    try:
        trust.evaluate_operator_id(driver_id)
    except Exception:
        log.exception("trust.evaluate_after_completion_failed", operator_id=str(driver_id))


# Dispute freeze / resolution: the job-side effect is exactly the status write
# the engine already performs — see the module docstring. ``fikisha.incidents
# .services`` creates/updates the ``Dispute`` row itself, before/around this
# call, in the same transaction.
freeze = noop
freeze_post_completion = noop
resolve_completed = complete
resolve_failed = noop
resolve_cancelled = noop


def resume(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """``DISPUTED -> pre-dispute state`` (trust-and-disputes plan B1, B2):
    the pending step gets fresh codes. At pickup a new pickup code; at the
    destination a new recipient code and the recipient link revoked and
    reissued with the same actions. Earlier confirmations stop counting
    (``jobs.confirmations``). No commission (none exists before COMPLETED)."""
    target = ctx.get("routed_job_status")
    if target == JobStatus.AT_PICKUP:
        arrive_pickup(job, actor, ctx)
    elif target == JobStatus.AT_DESTINATION:
        arrive_destination(job, actor, ctx)


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
    "resume": resume,
}
