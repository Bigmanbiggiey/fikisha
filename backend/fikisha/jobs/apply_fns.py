"""Transition side-effect functions (job-state-machine.md §3 "Side effects").

Each ``apply`` fn is ``fn(job, actor, ctx) -> None`` and runs **inside** the
lifecycle transaction, after the guards pass and before ``job.status`` is
written. It creates the rows the transition implies (``Agreement`` /
``Assignment`` / ``ProofOf*`` / ``CancellationRecord`` / ``FailureRecord`` …)
and may set domain fields on ``job`` (e.g. ``value_band`` at publish). It must
**not** write ``job.status``, ``job.version``, the ``*_at`` lifecycle stamps,
the ``job_event`` rows, the audit row, or the outbox rows — the service owns
those (§2.1 steps 8-12).

Increment 1 (this file) implements the transitions whose side-effect rows live
in the ``jobs`` app itself. ``freeze`` / ``complete`` / ``resolve_*`` need the
``incidents`` and ``commission`` apps (plan §19 Steps 8-9) and raise
``NotImplementedInThisIncrement`` until those land — the transition table, the
guards, and the DB backstop for them are already complete and tested.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fikisha.jobs import eligibility
from fikisha.jobs.constants import (
    HIGH_VALUE_BANDS,
    Attestation,
    CancellationReason,
    JobStatus,
    OperatorParty,
    ProofCapturedBy,
    ProofKind,
    TrustLevel,
    ValueBand,
    compute_penalty_class,
)
from fikisha.jobs.errors import GuardFailed, NotImplementedInThisIncrement
from fikisha.jobs.models import (
    Agreement,
    Assignment,
    CancellationRecord,
    FailureRecord,
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


# ── no-op transitions (custody arrival / transit start — the job_event the
#    service writes is the whole record; no extra rows) ─────────────────
def noop(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    return None


arrive_pickup = noop
start_transit = noop
arrive_destination = noop


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


# ── custody proofs ────────────────────────────────────────────────
def confirm_pickup(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfPickup``. The operator-attested Standard-band fallback caps
    the job at STANDARD (D-CUS-2); the guard has already refused it for any
    higher band. ``picked_up_at`` is stamped by the service."""
    method = ctx.get("pickup_method")
    attested = method == "ATTESTED"
    methods = {
        "OTP": ["OTP"],
        "BUSINESS_CONFIRM": ["IN_APP"],
        "ATTESTED": ["PHOTO"],
    }.get(method or "", [])
    ProofOfPickup.objects.create(
        job=job,
        kind=ProofKind.PICKUP,
        party_name=(ctx.get("pickup_contact_name") or "").strip(),
        methods=methods,
        otp_verified=method == "OTP",
        signature_evidence_id=ctx.get("signature_evidence_id"),
        photo_evidence_ids=list(ctx.get("photo_evidence_ids") or []),
        captured_by=ctx.get("captured_by")
        or (
            ProofCapturedBy.BUSINESS_CONTACT
            if method == "BUSINESS_CONFIRM"
            else ProofCapturedBy.OPERATOR
        ),
        condition_note=(ctx.get("condition_note") or "").strip(),
        attestation=Attestation.OPERATOR_ATTESTED_UNVERIFIED if attested else Attestation.VERIFIED,
    )
    if attested:
        job.value_band = ValueBand.STANDARD


def confirm_delivery(job: Any, actor: Any, ctx: dict[str, Any]) -> None:
    """Write ``ProofOfDelivery``. ``delivered_at`` is stamped by the service."""
    methods: list[str] = []
    if ctx.get("otp_verified"):
        methods.append("OTP")
    if ctx.get("signature_evidence_id"):
        methods.append("SIGNATURE")
    if ctx.get("photo_evidence_ids"):
        methods.append("PHOTO")
    ProofOfDelivery.objects.create(
        job=job,
        kind=ProofKind.DELIVERY,
        party_name=(ctx.get("party_name") or "").strip(),
        methods=methods,
        otp_verified=bool(ctx.get("otp_verified")),
        signature_evidence_id=ctx.get("signature_evidence_id"),
        photo_evidence_ids=list(ctx.get("photo_evidence_ids") or []),
        captured_by=ctx.get("captured_by") or ProofCapturedBy.OPERATOR,
        condition_note=(ctx.get("condition_note") or "").strip(),
    )


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
