"""Commission statements services (Commission & Statements plan S-1,
ADR-2D-42).

- ``run_statements``: bill one Mon-Sun period (plan §3.3-3.4). Called weekly
  by Celery beat and on demand by a Platform Admin. Idempotent per payee and
  period.
- ``record_payment`` / ``reverse_payment``: a Platform Admin records an M-Pesa
  payment against a statement, or reverses a mistaken one (D-4, D-5). Both
  need a fresh step-up.
- Reads: a payee's own statements, one statement in detail, one job's
  earnings, the admin list with totals.

Commission data comes only through ``jobs.commission``'s billing reads
(module boundary rule). Nothing here moves money: Fikisha records what a
payee owes for its own commission and what they reported paying.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db import connection, transaction
from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, DomainError
from fikisha.groups import authz as groups_authz
from fikisha.groups import services as groups_services
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.identity.authz.step_up import require_step_up
from fikisha.jobs import commission as jobs_commission
from fikisha.jobs.selectors import current_config_version
from fikisha.operators import authz as operators_authz
from fikisha.operators import services as operators_services
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config
from fikisha.statements.models import (
    CommissionStatement,
    LineKind,
    PayeeKind,
    SettlementKind,
    SettlementMethod,
    StatementLine,
    StatementSeen,
    StatementSettlement,
)

#: Read every statement (Platform Admin via "*"; Operations Officer, D-4).
PERM_READ_ALL = "statements.read.all"
#: Run a period by hand (Platform Admin).
PERM_RUN = "statements.run"
#: Record or reverse a payment (Platform Admin, with step-up; D-4, D-5).
PERM_SETTLE = "statements.settle"

REASON_MIN_LENGTH = 10
DEFAULT_OVERDUE_DAYS = 14
#: Serialises concurrent runs (the weekly beat task and a manual run).
_RUN_LOCK_KEY = 74_210_015


class InvalidPeriod(DomainError):
    default_code = "invalid_statement_period"


class InvalidSettlement(DomainError):
    default_code = "invalid_settlement"


class SettlementExceedsDue(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "settlement_exceeds_due"
    default_detail = "That is more than this statement still owes."


class DuplicatePaymentRef(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "duplicate_payment_ref"
    default_detail = "A payment with this reference is already recorded."


class SettlementNotReversible(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "settlement_not_reversible"
    default_detail = "Only a payment that hasn't been reversed can be reversed."


def _require(actor: Any, permission: str) -> None:
    if not actor_has_permission(actor, permission):
        raise AuthorizationError(f"missing permission {permission!r}")


def _user(actor: Any) -> Any:
    user = getattr(actor, "user", None)
    return user if getattr(user, "pk", None) else None


# ─── Periods (Kenya time, Monday to Sunday) ──────────────────────────────
def period_bounds(period_start: date) -> tuple[date, date, datetime]:
    """``(start, end, as_of)``: ``as_of`` is the instant the period ends
    (Monday 00:00 EAT after ``end``); billing is decided as of then."""
    if period_start.weekday() != 0:
        raise InvalidPeriod("A statement period starts on a Monday.")
    period_end = period_start + timedelta(days=6)
    as_of = timezone.make_aware(datetime.combine(period_end + timedelta(days=1), time.min))
    return period_start, period_end, as_of


def last_completed_period_start(now: datetime | None = None) -> date:
    today = timezone.localdate(now or timezone.now())
    this_monday = today - timedelta(days=today.weekday())
    return this_monday - timedelta(days=7)


def reference_for(statement_id: Any) -> str:
    """``ST-`` and the last 6 of the id, like the 6-character job reference."""
    return "ST-" + str(statement_id).replace("-", "")[-6:].upper()


# ─── The run (plan §3.3-3.4) ─────────────────────────────────────────────
def run_statements(*, period_start: date, actor: Any) -> dict[str, Any]:
    """Bill every payee with commission ready by the end of ``period_start``'s
    week. A payee who already has a statement for this period is skipped; what
    they have waiting rolls to the next period. ``actor`` is a Platform Admin
    (manual run) or the system actor (the weekly schedule)."""
    is_system = _user(actor) is None
    if not is_system:
        _require(actor, PERM_RUN)
    start, end, as_of = period_bounds(period_start)
    if as_of > timezone.now():
        raise InvalidPeriod("That week hasn't finished yet.")

    created: list[str] = []
    skipped = 0
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", [_RUN_LOCK_KEY])

        billed_records = StatementLine.objects.filter(kind=LineKind.COMMISSION).values(
            "commission_record_id"
        )
        billed_adjustments = StatementLine.objects.filter(kind=LineKind.ADJUSTMENT).values(
            "adjustment_id"
        )
        records = jobs_commission.billable_commission(
            as_of=as_of, exclude_record_ids=billed_records
        )
        new_record_ids = [r["record_id"] for r in records]
        adjustments = jobs_commission.unbilled_adjustments(
            record_ids=list(billed_records.values_list("commission_record_id", flat=True))
            + new_record_ids,
            exclude_adjustment_ids=billed_adjustments,
            created_before=as_of,
        )

        by_payee: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: {"records": [], "adjustments": []}
        )
        for r in records:
            by_payee[(r["payee_kind"], r["payee_id"])]["records"].append(r)
        for a in adjustments:
            by_payee[(a["payee_kind"], a["payee_id"])]["adjustments"].append(a)

        existing = set(
            CommissionStatement.objects.filter(period_start=start).values_list(
                "payee_kind", "payee_id"
            )
        )
        config_version = current_config_version()
        for (payee_kind, payee_id), items in sorted(by_payee.items()):
            if (payee_kind, _uuid(payee_id)) in existing:
                skipped += 1
                continue
            statement = _write_statement(
                payee_kind=payee_kind,
                payee_id=payee_id,
                start=start,
                end=end,
                items=items,
                actor=actor,
                config_version=config_version,
            )
            created.append(str(statement.id))
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "statements_created": len(created),
        "statement_ids": created,
        "payees_skipped_existing": skipped,
    }


def _uuid(value: Any) -> Any:
    import uuid

    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _write_statement(
    *,
    payee_kind: str,
    payee_id: str,
    start: date,
    end: date,
    items: dict[str, list[dict[str, Any]]],
    actor: Any,
    config_version: Any,
) -> CommissionStatement:
    gross = sum(r["commission_kes"] for r in items["records"])
    adjustments = sum(a["amount_kes"] for a in items["adjustments"])
    statement = CommissionStatement(
        payee_kind=payee_kind,
        payee_id=payee_id,
        period_start=start,
        period_end=end,
        gross_commission_kes=gross,
        adjustments_kes=adjustments,
        net_due_kes=gross + adjustments,
        generated_by=_user(actor),
        config_version=config_version,
    )
    statement.reference = reference_for(statement.id)
    statement.save()
    StatementLine.objects.bulk_create(
        [
            StatementLine(
                statement=statement,
                kind=LineKind.COMMISSION,
                commission_record_id=r["record_id"],
                job_id=r["job_id"],
                job_reference=r["job_reference"],
                agreed_price_kes=r["agreed_price_kes"],
                amount_kes=r["commission_kes"],
            )
            for r in items["records"]
        ]
        + [
            StatementLine(
                statement=statement,
                kind=LineKind.ADJUSTMENT,
                adjustment_id=a["adjustment_id"],
                job_id=a["job_id"],
                job_reference=a["job_reference"],
                amount_kes=a["amount_kes"],
            )
            for a in items["adjustments"]
        ]
    )
    audit.record(
        actor=actor,
        action="statement.generated",
        entity_type="commission_statement",
        entity_id=statement.id,
        after={
            "payee_kind": payee_kind,
            "payee_id": str(payee_id),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "reference": statement.reference,
            "lines": len(items["records"]) + len(items["adjustments"]),
            "gross_commission_kes": gross,
            "adjustments_kes": adjustments,
            "net_due_kes": gross + adjustments,
        },
        source_channel="SCHEDULER" if _user(actor) is None else "ADMIN_UI",
    )
    emit(
        event_type="StatementGenerated",
        aggregate_type="commission_statement",
        aggregate_id=str(statement.id),
        # Identifiers only; a notifier (D-6, not wired) reads the rest.
        payload={"payee_kind": payee_kind, "payee_id": str(payee_id)},
    )
    return statement


# ─── Settlements (D-4, D-5) ──────────────────────────────────────────────
def _settled_kes(statement_id: Any) -> int:
    return StatementSettlement.objects.filter(statement_id=statement_id).aggregate(
        total=Coalesce(Sum("amount_kes"), 0)
    )["total"]


def record_payment(
    *,
    actor: Any,
    statement_id: Any,
    amount_kes: int,
    payment_ref: str,
    paid_on: date,
    method: str = SettlementMethod.MPESA_PAYBILL,
    note: str = "",
) -> dict[str, Any]:
    """Record that the payee paid (part of) a statement. Permission, input,
    step-up, then one transaction: lock the statement, refuse more than is
    still owed or a reference already used, write the row, audit."""
    _require(actor, PERM_SETTLE)
    if not isinstance(amount_kes, int) or isinstance(amount_kes, bool) or amount_kes <= 0:
        raise InvalidSettlement("The amount must be a positive whole number (KES minor units).")
    payment_ref = (payment_ref or "").strip().upper()
    if not payment_ref:
        raise InvalidSettlement("Enter the M-Pesa (or bank) reference.")
    if method not in SettlementMethod.values:
        raise InvalidSettlement("Unknown payment method.")
    if paid_on > timezone.localdate():
        raise InvalidSettlement("The payment date can't be in the future.")

    require_step_up(actor)

    with transaction.atomic():
        statement = _locked_statement(statement_id)
        reversed_ids = StatementSettlement.objects.filter(kind=SettlementKind.REVERSAL).values(
            "reverses_id"
        )
        if (
            StatementSettlement.objects.filter(kind=SettlementKind.PAYMENT, payment_ref=payment_ref)
            .exclude(id__in=reversed_ids)
            .exists()
        ):
            raise DuplicatePaymentRef()
        outstanding = statement.net_due_kes - _settled_kes(statement.id)
        if amount_kes > outstanding:
            raise SettlementExceedsDue(
                f"That is more than this statement still owes (KES {outstanding / 100:,.2f})."
            )
        row = StatementSettlement.objects.create(
            statement=statement,
            kind=SettlementKind.PAYMENT,
            amount_kes=amount_kes,
            method=method,
            payment_ref=payment_ref,
            paid_on=paid_on,
            note=(note or "").strip(),
            recorded_by=_user(actor),
        )
        audit.record(
            actor=actor,
            action="statement.payment_recorded",
            entity_type="commission_statement",
            entity_id=statement.id,
            after={
                "settlement_id": str(row.id),
                "amount_kes": amount_kes,
                "method": method,
                "payment_ref": payment_ref,
                "paid_on": paid_on.isoformat(),
            },
            source_channel="ADMIN_UI",
        )
        emit(
            event_type="StatementSettlementRecorded",
            aggregate_type="commission_statement",
            aggregate_id=str(statement.id),
            payload={"settlement_id": str(row.id)},
        )
    return statement_detail(statement)


def reverse_payment(
    *, actor: Any, statement_id: Any, settlement_id: Any, reason: str
) -> dict[str, Any]:
    """Reverse a payment recorded by mistake (D-5). The original stays; a
    ``REVERSAL`` row cancels it."""
    _require(actor, PERM_SETTLE)
    reason = (reason or "").strip()
    if len(reason) < REASON_MIN_LENGTH:
        raise InvalidSettlement(f"Give a reason of at least {REASON_MIN_LENGTH} characters.")

    require_step_up(actor)

    with transaction.atomic():
        statement = _locked_statement(statement_id)
        original = StatementSettlement.objects.filter(id=settlement_id, statement=statement).first()
        if original is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No such payment on this statement.")
        if (
            original.kind != SettlementKind.PAYMENT
            or StatementSettlement.objects.filter(reverses=original).exists()
        ):
            raise SettlementNotReversible()
        row = StatementSettlement.objects.create(
            statement=statement,
            kind=SettlementKind.REVERSAL,
            amount_kes=-original.amount_kes,
            method=original.method,
            payment_ref=original.payment_ref,
            paid_on=original.paid_on,
            note=reason,
            reverses=original,
            recorded_by=_user(actor),
        )
        audit.record(
            actor=actor,
            action="statement.payment_reversed",
            entity_type="commission_statement",
            entity_id=statement.id,
            before={"settlement_id": str(original.id), "amount_kes": original.amount_kes},
            after={"reversal_id": str(row.id), "reason": reason},
            source_channel="ADMIN_UI",
        )
        emit(
            event_type="StatementSettlementReversed",
            aggregate_type="commission_statement",
            aggregate_id=str(statement.id),
            payload={"settlement_id": str(original.id), "reversal_id": str(row.id)},
        )
    return statement_detail(statement)


def _locked_statement(statement_id: Any) -> CommissionStatement:
    statement = CommissionStatement.objects.select_for_update().filter(id=statement_id).first()
    if statement is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("No such statement.")
    return statement


# ─── Who may see what (plan §3.5) ────────────────────────────────────────
def is_payee(actor: Any, payee_kind: str, payee_id: Any) -> bool:
    """A solo operator for their own statements; a group's OWNER/MANAGER for
    the group's. A group DRIVER member is not a payee (FR-O-8)."""
    if payee_kind == PayeeKind.OPERATOR:
        return operators_authz.owns_profile(actor, {"operator_id": str(payee_id)})
    if payee_kind == PayeeKind.GROUP:
        return groups_authz.can_manage(actor, {"group_id": str(payee_id)})
    return False


def can_read_statement(actor: Any, statement: CommissionStatement) -> bool:
    return actor_has_permission(actor, PERM_READ_ALL) or is_payee(
        actor, statement.payee_kind, statement.payee_id
    )


def statements_for(actor: Any) -> QuerySet[CommissionStatement]:
    """The actor's own statements as a payee, newest first."""
    user = _user(actor)
    if user is None:
        return CommissionStatement.objects.none()
    q = Q(pk__in=[])
    profile = operators_services.profile_for(user)
    if profile is not None:
        q |= Q(payee_kind=PayeeKind.OPERATOR, payee_id=profile.id)
    managed = [
        g.id
        for g in groups_services.groups_for(user)
        if groups_authz.can_manage(actor, {"group_id": str(g.id)})
    ]
    if managed:
        q |= Q(payee_kind=PayeeKind.GROUP, payee_id__in=managed)
    return CommissionStatement.objects.filter(q).order_by("-period_start", "-created_at")


def admin_queryset(
    *,
    period_start: date | None = None,
    payee_kind: str | None = None,
    payee_id: Any = None,
) -> QuerySet[CommissionStatement]:
    qs = CommissionStatement.objects.all()
    if period_start is not None:
        qs = qs.filter(period_start=period_start)
    if payee_kind:
        qs = qs.filter(payee_kind=payee_kind)
    if payee_id:
        qs = qs.filter(payee_id=payee_id)
    return qs


def admin_totals(qs: QuerySet[CommissionStatement]) -> dict[str, int]:
    """Invoiced vs settled over the whole filtered set (pilot-strategy §4.7)."""
    invoiced = qs.aggregate(total=Coalesce(Sum("net_due_kes"), 0))["total"]
    settled = StatementSettlement.objects.filter(statement__in=qs).aggregate(
        total=Coalesce(Sum("amount_kes"), 0)
    )["total"]
    return {
        "statements": qs.count(),
        "invoiced_kes": invoiced,
        "settled_kes": settled,
        "outstanding_kes": invoiced - settled,
    }


# ─── Seen markers (S-2, D-6) ─────────────────────────────────────────────
def mark_seen(*, actor: Any, statement: CommissionStatement) -> None:
    """Record that the payee opened this statement. Staff opening it changes
    nothing: the marker is the payee's own."""
    user = _user(actor)
    if user is None or not is_payee(actor, statement.payee_kind, statement.payee_id):
        return
    StatementSeen.objects.get_or_create(user=user, statement=statement)


def seen_statement_ids(*, actor: Any, statement_ids: list[Any]) -> set[str]:
    user = _user(actor)
    if user is None or not statement_ids:
        return set()
    return {
        str(s)
        for s in StatementSeen.objects.filter(
            user=user, statement_id__in=statement_ids
        ).values_list("statement_id", flat=True)
    }


def unseen_count(actor: Any) -> int:
    user = _user(actor)
    if user is None:
        return 0
    return statements_for(actor).exclude(seen_by__user=user).count()


# ─── Read projections ────────────────────────────────────────────────────
def _payee_name(payee_kind: str, payee_id: Any) -> str | None:
    if payee_kind == PayeeKind.OPERATOR:
        return operators_services.display_name_for(payee_id)
    return groups_services.display_name_for(payee_id)


def _overdue_days() -> int:
    value = config.get("statements.overdue_days", DEFAULT_OVERDUE_DAYS)
    return value if isinstance(value, int) and value > 0 else DEFAULT_OVERDUE_DAYS


def payment_details() -> dict[str, Any]:
    """Where to pay (D-3). ``paybill_number`` stays null until the founder
    sets ``statements.paybill_number``; the UI then shows "payment details to
    follow"."""
    number = config.get("statements.paybill_number")
    return {"paybill_number": str(number) if number else None}


def statement_summary(
    statement: CommissionStatement, *, settled_kes: int | None = None
) -> dict[str, Any]:
    settled = _settled_kes(statement.id) if settled_kes is None else settled_kes
    outstanding = statement.net_due_kes - settled
    if outstanding <= 0:
        state = "PAID"
    elif settled > 0:
        state = "PART_PAID"
    else:
        state = "UNPAID"
    overdue = state != "PAID" and timezone.now() - statement.created_at > timedelta(
        days=_overdue_days()
    )
    return {
        "id": str(statement.id),
        "reference": statement.reference,
        "payee": {
            "kind": statement.payee_kind,
            "id": str(statement.payee_id),
            "name": _payee_name(statement.payee_kind, statement.payee_id),
        },
        "period_start": statement.period_start.isoformat(),
        "period_end": statement.period_end.isoformat(),
        "gross_commission_kes": statement.gross_commission_kes,
        "adjustments_kes": statement.adjustments_kes,
        "net_due_kes": statement.net_due_kes,
        "settled_kes": settled,
        "outstanding_kes": max(outstanding, 0),
        "state": state,
        "overdue": overdue,
        "generated_at": statement.created_at.isoformat(),
    }


def statement_detail(statement: CommissionStatement) -> dict[str, Any]:
    lines = list(statement.lines.order_by("kind", "created_at", "id"))
    settlements = list(statement.settlements.order_by("created_at", "id"))
    reversed_ids = {str(s.reverses_id) for s in settlements if s.reverses_id}
    data = statement_summary(statement, settled_kes=sum(s.amount_kes for s in settlements))
    data["lines"] = [
        {
            "id": str(line.id),
            "kind": line.kind,
            "job_id": str(line.job_id),
            "job_reference": line.job_reference,
            "agreed_price_kes": line.agreed_price_kes,
            "amount_kes": line.amount_kes,
        }
        for line in lines
    ]
    data["settlements"] = [
        {
            "id": str(s.id),
            "kind": s.kind,
            "amount_kes": s.amount_kes,
            "method": s.method,
            "payment_ref": s.payment_ref,
            "paid_on": s.paid_on.isoformat(),
            "note": s.note,
            "reverses": str(s.reverses_id) if s.reverses_id else None,
            "reversed": str(s.id) in reversed_ids,
            "recorded_at": s.created_at.isoformat(),
        }
        for s in settlements
    ]
    data["payment"] = {**payment_details(), "account_reference": statement.reference}
    return data


def job_earnings(*, actor: Any, job_id: Any) -> dict[str, Any]:
    """ "Earnings for this Job" (P3 §7.4) for the job's payee or staff with
    ``statements.read.all``. Anyone else gets 404, so a job's existence and
    commission don't leak."""
    from rest_framework.exceptions import NotFound

    row = jobs_commission.commission_for_job(job_id)
    if row is None or not (
        actor_has_permission(actor, PERM_READ_ALL)
        or is_payee(actor, row["payee_kind"], row["payee_id"])
    ):
        raise NotFound("No earnings for this job.")
    line = (
        StatementLine.objects.select_related("statement")
        .filter(commission_record_id=row["record_id"])
        .first()
    )
    row["statement"] = (
        {"id": str(line.statement_id), "reference": line.statement.reference} if line else None
    )
    row.pop("record_id")
    return row


# ─── Reconciliation (commission-ledger.md §7) ────────────────────────────
def reconcile() -> list[dict[str, Any]]:
    """Every statement must satisfy ``net_due == Σ COMMISSION + Σ ADJUSTMENT``,
    totals must match their lines, and ``settled ≤ max(net_due, 0)``. Returns
    the mismatches (empty when all is well)."""
    problems: list[dict[str, Any]] = []
    sums: dict[Any, dict[str, int]] = defaultdict(lambda: {"COMMISSION": 0, "ADJUSTMENT": 0})
    for row in StatementLine.objects.values("statement_id", "kind").annotate(
        total=Sum("amount_kes")
    ):
        sums[row["statement_id"]][row["kind"]] = row["total"]
    settled = {
        row["statement_id"]: row["total"]
        for row in StatementSettlement.objects.values("statement_id").annotate(
            total=Sum("amount_kes")
        )
    }
    for st in CommissionStatement.objects.all().iterator():
        s = sums[st.id]
        paid = settled.get(st.id, 0)
        if (
            st.gross_commission_kes != s["COMMISSION"]
            or st.adjustments_kes != s["ADJUSTMENT"]
            or st.net_due_kes != s["COMMISSION"] + s["ADJUSTMENT"]
            or paid > max(st.net_due_kes, 0)
            or paid < 0
        ):
            problems.append(
                {
                    "statement_id": str(st.id),
                    "net_due_kes": st.net_due_kes,
                    "lines_commission_kes": s["COMMISSION"],
                    "lines_adjustment_kes": s["ADJUSTMENT"],
                    "settled_kes": paid,
                }
            )
    return problems
