"""Commission domain surface (Phase 2D Step 9, plan §19, CLAUDE.md §4
"Payments / revenue"). Fikisha never holds the transport fare, operates no
wallet/escrow, and this module moves no money — it records the platform's own
commission entitlement for a completed Job, and (append-only) any authorized
correction to it.

``create_commission_record_locked`` is called **only** from
``jobs.apply_fns.complete`` — inside ``JobLifecycleService.transition()``'s
own transaction, with the Job row already locked (``SELECT ... FOR UPDATE``).
That is the entire atomicity story: if this raises, the whole transition
(including the ``job.status`` write) rolls back with it; nothing here takes
its own lock or opens its own transaction.

``create_adjustment`` is called by ``fikisha.incidents.services.resolve_
dispute()`` — the *only* authorized caller (an explicit, admin-reviewed
Resolution; never automatic). ``jobs`` never imports ``fikisha.incidents``
(ADR-2D-01/22); the caller supplies its own dispute/resolution ids for
forensic cross-reference as plain UUIDs, not FKs. Unlike
``create_commission_record_locked`` (which relies entirely on the caller
already holding the Job row lock inside the transition's own transaction),
``create_adjustment`` opens its own ``@transaction.atomic`` and takes its own
``select_for_update()`` on the commission record — it is not only ever called
from inside another atomic block.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction

from fikisha.audit import services as audit
from fikisha.jobs.constants import CommissionAdjustmentKind
from fikisha.jobs.errors import (
    CommissionAdjustmentReasonRequired,
    CommissionAgreementMissing,
    CommissionConfigInvalid,
    InvalidCommissionAdjustmentAmount,
    NotAuthorisedForCommissionAdjustment,
)
from fikisha.jobs.models import CommissionAdjustment, CommissionRecord, Job
from fikisha.jobs.selectors import current_config_version
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config

#: The only commission model actually implemented (defaults.py's
#: ``_ALLOWED_COMMISSION_MODELS`` also lists ``BANDED_TAPER`` / ``RAMPED`` as
#: *syntactically* valid config values for a future phase — Step 9 brief §2
#: explicitly forbids introducing a taper/ramp now, so this module refuses to
#: silently miscalculate against either).
_IMPLEMENTED_MODEL = "FLAT_WITH_MIN_CAP"


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def _is_platform_admin(actor: Any) -> bool:
    role = str(getattr(actor, "audit_role", "") or "")
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    return role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in roles


def can_adjust_commission(actor: Any) -> bool:
    """Platform-Admin-only (Step 9 brief §12: "Operations Officer must not
    gain adjustment authority merely because they can review incidents [or
    resolve disputes]" — no ``role_permissions`` entry grants any other role
    this, so the check is a direct Platform-Admin test, exactly like the
    job-lifecycle engine's own ``AdminBandAuthorised`` guard for
    above-Standard binding resolution, D-ADM-1)."""
    return _is_platform_admin(actor)


def calculate_commission_kes(
    agreed_price_kes: int, *, rate: float | Decimal, min_fee_kes: int, cap_kes: int
) -> int:
    """``commission = max(min_fee, min(price * rate, cap))`` — deterministic,
    integer-in/integer-out. ``rate`` is converted via ``Decimal(str(rate))``
    (never ``Decimal(rate)`` on a float — that reproduces the binary float's
    rounding error) so the *approved* rate (0.10) is exact; the product is
    rounded to the nearest whole KES minor unit, half up (Step 9 brief §6:
    "exact integer arithmetic", "avoid floating point")."""
    if not isinstance(agreed_price_kes, int) or isinstance(agreed_price_kes, bool):
        raise TypeError("agreed_price_kes must be an int (KES minor units)")
    if agreed_price_kes < 0:
        raise ValueError("agreed_price_kes must not be negative")
    raw = (Decimal(agreed_price_kes) * Decimal(str(rate))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return max(int(min_fee_kes), min(int(raw), int(cap_kes)))


def _resolve_commission_config() -> dict[str, Any]:
    commission = config.get("commission", {}) or {}
    if commission.get("model") != _IMPLEMENTED_MODEL:
        raise CommissionConfigInvalid(
            f"commission.model={commission.get('model')!r} is not implemented "
            f"(only {_IMPLEMENTED_MODEL!r} is)."
        )
    return commission


def create_commission_record_locked(*, job: Job, actor: Any) -> CommissionRecord:
    """Idempotent: returns the existing record if the job already has one — a
    job can reach ``COMPLETED`` more than once (an original completion, then
    later a post-completion dispute resolved back to ``COMPLETED``); never
    creates a second row (the ``OneToOneField`` on ``job`` is the DB-level
    backstop, ``UNIQUE(job_id)``). Must be called with the Job row already
    locked (``SELECT ... FOR UPDATE``) — true for every caller, since this
    only ever runs from inside the lifecycle transition's own apply fn."""
    existing = CommissionRecord.objects.filter(job=job).first()
    if existing is not None:
        return existing

    agreement = job.agreement
    if agreement is None:  # pragma: no cover - guarded by the state machine
        raise CommissionAgreementMissing()

    commission_cfg = _resolve_commission_config()
    rate = commission_cfg["rate"]
    min_fee_kes = int(commission_cfg["min_fee_kes"])
    cap_kes = int(commission_cfg["cap_kes"])
    agreed_price_kes = int(agreement.agreed_price_kes)
    commission_kes = calculate_commission_kes(
        agreed_price_kes, rate=rate, min_fee_kes=min_fee_kes, cap_kes=cap_kes
    )
    version = current_config_version()

    record = CommissionRecord.objects.create(
        job=job,
        agreement=agreement,
        agreed_price_kes=agreed_price_kes,
        rate=Decimal(str(rate)),
        min_fee_kes=min_fee_kes,
        cap_kes=cap_kes,
        commission_kes=commission_kes,
        config_version=version,
    )
    audit.record(
        actor=actor,
        action="commission.recorded",
        entity_type="commission_record",
        entity_id=record.id,
        after={
            "job_id": str(job.id),
            "agreed_price_kes": agreed_price_kes,
            "rate": str(record.rate),
            "min_fee_kes": min_fee_kes,
            "cap_kes": cap_kes,
            "commission_kes": commission_kes,
            "config_version": version.version if version else None,
        },
    )
    emit(
        event_type="CommissionRecorded",
        aggregate_type="commission_record",
        aggregate_id=str(record.id),
        # Identifiers only — the commission amount is commercially sensitive
        # (Step 9 brief §23) and stays behind the DB's own access control; a
        # future statement/notification consumer looks it up, never receives
        # it broadcast through the event stream. The full calculation detail
        # is in the audit entry above, which already has stricter access.
        payload={"job_id": str(job.id)},
    )
    return record


def get_commission_record(job: Job) -> CommissionRecord | None:
    """``None`` if the job has never completed (e.g. a dispute opened and
    resolved to ``FAILED``/``CANCELLED`` before any ``COMPLETED`` pass ever
    created one) — callers (``incidents.services.resolve_dispute()``) treat a
    ``commission_treatment`` other than ``APPLY`` on such a job as
    "nothing to adjust", not an error."""
    return CommissionRecord.objects.filter(job=job).first()


def effective_commission_kes(commission_record: CommissionRecord) -> int:
    """``original + adjustments`` (Step 9 brief §10) — the historical rows
    stay immutable; this is a read-time projection, never stored."""
    total = sum(commission_record.adjustments.values_list("amount_kes", flat=True))
    return commission_record.commission_kes + total


@transaction.atomic
def create_adjustment(
    *,
    commission_record: CommissionRecord,
    actor: Any,
    kind: str,
    amount_kes: int,
    reason: str,
    source_dispute_id: Any = None,
    source_resolution_id: Any = None,
) -> CommissionAdjustment:
    """Create an append-only correction against ``commission_record``. Opens
    its own transaction (a nested call from an already-atomic caller — e.g.
    ``incidents.services.resolve_dispute()`` — is just a savepoint, the normal
    Django pattern used throughout this codebase) so this function is safe to
    call on its own, not only from inside another atomic block. Never
    mutates the original row. ``amount_kes`` must be negative (a reduction or
    a full waiver — never an increase, never an automatic rule: Step 9 brief
    §10/§13). Re-locks the commission record (defence in depth against a
    concurrent adjustment, on top of whatever lock the caller already holds —
    in practice always the Job row lock ``resolve_dispute()`` takes, since a
    job's ``Dispute`` uniqueness constraint already serialises this to one
    caller at a time, ADR-2D-20)."""
    if not can_adjust_commission(actor):
        raise NotAuthorisedForCommissionAdjustment()
    reason = (reason or "").strip()
    if not reason:
        raise CommissionAdjustmentReasonRequired()
    if kind not in CommissionAdjustmentKind.values:
        raise InvalidCommissionAdjustmentAmount(f"{kind!r} is not a recognised adjustment kind.")
    if not isinstance(amount_kes, int) or isinstance(amount_kes, bool) or amount_kes >= 0:
        raise InvalidCommissionAdjustmentAmount(
            "A commission adjustment amount must be a negative integer (KES minor units)."
        )

    locked = CommissionRecord.objects.select_for_update().get(pk=commission_record.pk)
    if effective_commission_kes(locked) + amount_kes < 0:
        raise InvalidCommissionAdjustmentAmount(
            "This adjustment would reduce the effective commission below zero."
        )

    adjustment = CommissionAdjustment.objects.create(
        commission_record=locked,
        kind=kind,
        amount_kes=amount_kes,
        reason=reason,
        authorized_by=_actor_user(actor),
        authorized_by_is_platform_admin=_is_platform_admin(actor),
        source_dispute_id=source_dispute_id,
        source_resolution_id=source_resolution_id,
        config_version=current_config_version(),
    )
    audit.record(
        actor=actor,
        action="commission.adjusted",
        entity_type="commission_adjustment",
        entity_id=adjustment.id,
        after={
            "commission_record_id": str(locked.id),
            "job_id": str(locked.job_id),
            "kind": kind,
            "amount_kes": amount_kes,
            "reason": reason,
            "source_dispute_id": str(source_dispute_id) if source_dispute_id else None,
            "source_resolution_id": str(source_resolution_id) if source_resolution_id else None,
        },
    )
    emit(
        event_type="CommissionAdjusted",
        aggregate_type="commission_adjustment",
        aggregate_id=str(adjustment.id),
        # Identifiers only — see the note in create_commission_record_locked.
        payload={"job_id": str(locked.job_id), "commission_record_id": str(locked.id)},
    )
    return adjustment
