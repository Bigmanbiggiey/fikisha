"""Commission domain surface (Phase 2D Step 9, plan §19, CLAUDE.md §4
"Payments / revenue"). Fikisha never holds the transport fare, operates no
wallet/escrow, and this module moves no money — it records the platform's own
commission entitlement for a completed Job, and (append-only) any authorized
correction to it.

Commission split (ADR-2D-55, founder decision 2026-10-22): the business and
the operator each owe their own rate of the agreed price (5% and 5% by
default), with no minimum or cap. Each side is a separate
``CommissionRecord`` (``party``), rounded on its own (D-2). The rates are
fixed on the ``Agreement`` when the price is agreed (D-4).

``create_commission_records_locked`` is called **only** from
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
``create_commission_records_locked`` (which relies entirely on the caller
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
from fikisha.jobs.constants import CommissionAdjustmentKind, CommissionParty
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

#: The only commission model implemented (ADR-2D-55). The calculator
#: refuses any other value rather than silently miscalculating.
_IMPLEMENTED_MODEL = "SPLIT_FLAT"

#: Config key for each side's rate.
_RATE_KEYS = {
    CommissionParty.BUSINESS: "business_rate",
    CommissionParty.OPERATOR: "operator_rate",
}


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


def calculate_fee_kes(agreed_price_kes: int, *, rate: float | Decimal) -> int:
    """One side's fee: ``price * rate``, rounded to the nearest whole KES
    minor unit, half up (D-2: each side on its own). Integer in, integer
    out. ``rate`` goes through ``Decimal(str(rate))`` (never ``Decimal(rate)``
    on a float, which would carry the binary float's error) so 0.05 is
    exact."""
    if not isinstance(agreed_price_kes, int) or isinstance(agreed_price_kes, bool):
        raise TypeError("agreed_price_kes must be an int (KES minor units)")
    if agreed_price_kes < 0:
        raise ValueError("agreed_price_kes must not be negative")
    raw = (Decimal(agreed_price_kes) * Decimal(str(rate))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(raw)


def live_rates() -> dict[str, Decimal]:
    """Each side's rate from the live config. Raises
    ``CommissionConfigInvalid`` for any model other than the split."""
    commission = config.get("commission", {}) or {}
    if commission.get("model") != _IMPLEMENTED_MODEL:
        raise CommissionConfigInvalid(
            f"commission.model={commission.get('model')!r} is not implemented "
            f"(only {_IMPLEMENTED_MODEL!r} is)."
        )
    rates: dict[str, Decimal] = {}
    for party, key in _RATE_KEYS.items():
        value = commission.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
            raise CommissionConfigInvalid(f"commission.{key}={value!r} is not a rate.")
        rates[party] = Decimal(str(value)).quantize(Decimal("0.0001"))
    return rates


def pinned_rates() -> dict[str, Any]:
    """The rates to fix on a new ``Agreement`` (D-4), with the config version
    they came from. Called from the ``confirm`` apply fn."""
    rates = live_rates()
    return {
        "business_rate": rates[CommissionParty.BUSINESS],
        "operator_rate": rates[CommissionParty.OPERATOR],
        "rates_config_version": current_config_version(),
    }


def rates_for(agreement: Any) -> dict[str, Decimal]:
    """The rates an agreement charges: the ones fixed on it, or, for an
    agreement made before the split (no rates fixed), the live ones."""
    if agreement.business_rate is not None and agreement.operator_rate is not None:
        return {
            CommissionParty.BUSINESS: agreement.business_rate,
            CommissionParty.OPERATOR: agreement.operator_rate,
        }
    return live_rates()


def fee_view(agreed_price_kes: int, party: str, rate: Decimal) -> dict[str, Any]:
    """What one side sees about its fee on a price: the rate, the fee, and
    what that means for them (the business pays price + fee; the operator
    keeps price - fee). Computed here, never in the browser."""
    fee = calculate_fee_kes(int(agreed_price_kes), rate=rate)
    view: dict[str, Any] = {"party": party, "rate": str(rate), "fee_kes": fee}
    if party == CommissionParty.BUSINESS:
        view["total_cost_kes"] = int(agreed_price_kes) + fee
    else:
        view["operator_keeps_kes"] = int(agreed_price_kes) - fee
    return view


def quote(agreed_price_kes: int, party: str) -> dict[str, Any]:
    """One side's fee on a price at the live rates (while negotiating, before
    any rate is fixed)."""
    return fee_view(agreed_price_kes, party, live_rates()[party])


def fees_for_job(job: Job, parties: Any) -> list[dict[str, Any]]:
    """The fee views for ``parties`` on a job's agreed price. Once the job has
    commission records, what was actually recorded (after any dispute
    adjustment): a job completed before the split shows its operator-only
    10% and no business fee. Before that, the rates fixed on the agreement
    (or, for an agreement made before the split, the live ones)."""
    agreement = job.agreement
    records = {
        r.party: r for r in CommissionRecord.objects.filter(job=job).prefetch_related("adjustments")
    }
    if records:
        views = []
        for party in parties:
            record = records.get(party)
            if record is None:
                continue
            view = fee_view(record.agreed_price_kes, party, record.rate)
            effective = effective_commission_kes(record)
            view["fee_kes"] = effective
            if party == CommissionParty.BUSINESS:
                view["total_cost_kes"] = record.agreed_price_kes + effective
            else:
                view["operator_keeps_kes"] = record.agreed_price_kes - effective
            views.append(view)
        return views
    if agreement is None:
        return []
    rates = rates_for(agreement)
    return [fee_view(agreement.agreed_price_kes, party, rates[party]) for party in parties]


def create_commission_records_locked(*, job: Job, actor: Any) -> list[CommissionRecord]:
    """One record per side with a rate above zero, computed from the job's
    frozen ``Agreement`` and its fixed rates. Commission is fixed once, the
    first time the job completes: a job can reach ``COMPLETED`` again (a
    post-completion dispute resolved back to ``COMPLETED``) and then gets
    nothing new (``UNIQUE(job_id, party)`` is the DB backstop). Must be
    called with the Job row already locked (``SELECT ... FOR UPDATE``) —
    true for every caller, since this only ever runs from inside the
    lifecycle transition's own apply fn."""
    existing = list(CommissionRecord.objects.filter(job=job).order_by("party"))
    if existing:
        return existing

    agreement = job.agreement
    if agreement is None:  # pragma: no cover - guarded by the state machine
        raise CommissionAgreementMissing()

    rates = rates_for(agreement)
    agreed_price_kes = int(agreement.agreed_price_kes)
    version = current_config_version()
    records: list[CommissionRecord] = []
    for party in (CommissionParty.BUSINESS, CommissionParty.OPERATOR):
        rate = rates[party]
        if rate <= 0:
            continue
        commission_kes = calculate_fee_kes(agreed_price_kes, rate=rate)
        record = CommissionRecord.objects.create(
            job=job,
            party=party,
            agreement=agreement,
            agreed_price_kes=agreed_price_kes,
            rate=rate,
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
                "party": party,
                "agreed_price_kes": agreed_price_kes,
                "rate": str(record.rate),
                "commission_kes": commission_kes,
                "config_version": version.version if version else None,
            },
        )
        emit(
            event_type="CommissionRecorded",
            aggregate_type="commission_record",
            aggregate_id=str(record.id),
            # Identifiers only — the commission amount is commercially
            # sensitive (Step 9 brief §23) and stays behind the DB's own
            # access control; a later statement/notification consumer looks
            # it up. The full calculation is in the audit entry above.
            payload={"job_id": str(job.id), "party": party},
        )
        records.append(record)
    return records


def get_commission_records(job: Job) -> dict[str, CommissionRecord]:
    """The job's records by party; empty if the job has never completed (e.g.
    a dispute opened and resolved to ``FAILED``/``CANCELLED`` before any
    ``COMPLETED`` pass created them). Callers
    (``incidents.services.resolve_dispute()``) treat a treatment other than
    ``APPLY`` on a side with no record as "nothing to adjust", not an
    error."""
    return {r.party: r for r in CommissionRecord.objects.filter(job=job)}


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
            "party": locked.party,
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


# ─── Billing reads for the statement run (Commission & Statements S-1) ──────
# ``fikisha.statements`` never imports these models (module boundary rule); it
# asks here for plain rows. Who is billed: the business for a ``BUSINESS``
# record (ADR-2D-55); for an ``OPERATOR`` record the confirmed operator on a
# solo job, the group on a group job (FR-O-8).


def _payee_of(record: CommissionRecord) -> tuple[str, str]:
    if record.party == CommissionParty.BUSINESS:
        return "BUSINESS", str(record.job.business_id)
    agreement = record.agreement
    if agreement.operator_id is not None:
        return "OPERATOR", str(agreement.operator_id)
    return "GROUP", str(agreement.group_id)


def billable_commission(*, as_of: Any, exclude_record_ids: Any) -> list[dict[str, Any]]:
    """Commission records ready to bill as of ``as_of`` (plan §3.3, D-2): the
    job is ``COMPLETED`` (so not ``DISPUTED``) and its post-completion
    dispute window closed on or before ``as_of``. ``exclude_record_ids`` (an
    iterable or a values queryset) are records already on a statement."""
    from datetime import timedelta

    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.guards import post_completion_window_hours
    from fikisha.jobs.ops import job_reference

    window = config.get("timeouts.post_completion_window", {}) or {}
    shortest = min(
        float(window.get("default_hours", 72)), float(window.get("high_and_latent_days", 7)) * 24
    )
    qs = (
        CommissionRecord.objects.select_related("job", "agreement")
        .filter(
            job__status=JobStatus.COMPLETED,
            job__completed_at__isnull=False,
            job__completed_at__lte=as_of - timedelta(hours=shortest),
        )
        .exclude(id__in=exclude_record_ids)
        .order_by("job__completed_at", "id")
    )
    rows = []
    for record in qs:
        job = record.job
        closes_at = job.completed_at + timedelta(hours=post_completion_window_hours(job))
        if closes_at > as_of:
            continue
        payee_kind, payee_id = _payee_of(record)
        rows.append(
            {
                "record_id": str(record.id),
                "party": record.party,
                "job_id": str(job.id),
                "job_reference": job_reference(job.id),
                "payee_kind": payee_kind,
                "payee_id": payee_id,
                "agreed_price_kes": record.agreed_price_kes,
                "commission_kes": record.commission_kes,
            }
        )
    return rows


def unbilled_adjustments(
    *, record_ids: Any, exclude_adjustment_ids: Any, created_before: Any
) -> list[dict[str, Any]]:
    """Adjustments to bill: their record is billed (``record_ids``), they are
    not on a statement yet, and they existed by ``created_before``. An
    adjustment whose record was never billed (for example a job that ended
    ``FAILED`` after a dispute) is never billed either."""
    from fikisha.jobs.ops import job_reference

    qs = (
        CommissionAdjustment.objects.select_related(
            "commission_record__agreement", "commission_record__job"
        )
        .filter(commission_record_id__in=record_ids, created_at__lt=created_before)
        .exclude(id__in=exclude_adjustment_ids)
        .order_by("created_at", "id")
    )
    rows = []
    for adj in qs:
        record = adj.commission_record
        payee_kind, payee_id = _payee_of(record)
        rows.append(
            {
                "adjustment_id": str(adj.id),
                "record_id": str(record.id),
                "job_id": str(record.job_id),
                "job_reference": job_reference(record.job_id),
                "payee_kind": payee_kind,
                "payee_id": payee_id,
                "kind": adj.kind,
                "amount_kes": adj.amount_kes,
            }
        )
    return rows


def commission_for_job(job_id: Any) -> list[dict[str, Any]]:
    """Each side's commission on one job, for "Earnings for this job" /
    "Cost for this job" (P3 §7.4): agreed price, commission, adjustments,
    and what it means for that side. Empty if the job has no commission
    record. Authorization is the caller's (``statements``), per side."""
    records = (
        CommissionRecord.objects.select_related("agreement", "job")
        .prefetch_related("adjustments")
        .filter(job_id=job_id)
        .order_by("party")
    )
    rows = []
    for record in records:
        payee_kind, payee_id = _payee_of(record)
        adjustments_kes = sum(a.amount_kes for a in record.adjustments.all())
        effective = record.commission_kes + adjustments_kes
        row = {
            "job_id": str(record.job_id),
            "record_id": str(record.id),
            "party": record.party,
            "payee_kind": payee_kind,
            "payee_id": payee_id,
            "agreed_price_kes": record.agreed_price_kes,
            "rate": str(record.rate),
            "commission_kes": record.commission_kes,
            "adjustments_kes": adjustments_kes,
            "effective_commission_kes": effective,
        }
        if record.party == CommissionParty.BUSINESS:
            row["total_cost_kes"] = record.agreed_price_kes + effective
        else:
            row["net_to_operator_kes"] = record.agreed_price_kes - effective
        rows.append(row)
    return rows
