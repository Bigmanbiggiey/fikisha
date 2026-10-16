"""Weekly commission statements (Commission & Statements plan S-1,
ADR-2D-42; `commission-ledger.md` §3.3-3.4, `database-design.md` §4.11).

Three append-only tables, each guarded at model, queryset and Postgres-trigger
level like ``commission_record``:

- ``commission_statement``: one per payee (a solo operator or a group) per
  week, with frozen totals.
- ``statement_line``: one per billed commission record or adjustment. The
  unique keys on ``commission_record`` and ``adjustment`` are what "billed"
  means, so nothing is billed twice and ``commission_record`` needs no status.
- ``statement_settlement``: a payment an admin recorded, or a reversal of
  one. Paid / part-paid / unpaid is derived from these rows, never stored.

Fikisha holds no fare and no balance: these rows record what a payee owes
Fikisha for its own commission and what they reported paying to its paybill.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel


class PayeeKind(models.TextChoices):
    OPERATOR = "OPERATOR", "Operator"
    GROUP = "GROUP", "Operator group"


class LineKind(models.TextChoices):
    COMMISSION = "COMMISSION", "Commission"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class SettlementKind(models.TextChoices):
    PAYMENT = "PAYMENT", "Payment"
    REVERSAL = "REVERSAL", "Reversal"


class SettlementMethod(models.TextChoices):
    MPESA_PAYBILL = "MPESA_PAYBILL", "M-Pesa paybill"
    BANK = "BANK", "Bank"
    OTHER = "OTHER", "Other"


class CommissionStatement(AppendOnlyModel):
    payee_kind = models.CharField(max_length=10, choices=PayeeKind.choices)
    payee_id = models.UUIDField()
    #: Kenya dates, Monday to Sunday inclusive.
    period_start = models.DateField()
    period_end = models.DateField()
    gross_commission_kes = models.BigIntegerField()
    #: Zero or negative (adjustments only ever reduce commission).
    adjustments_kes = models.BigIntegerField()
    net_due_kes = models.BigIntegerField()
    #: Shown to the payee and used as the paybill account number (D-3).
    reference = models.CharField(max_length=12, db_index=True)
    #: Null when the weekly schedule generated it.
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    config_version = models.ForeignKey(
        "platform_config.PlatformConfigVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "commission_statement"
        constraints = [
            models.UniqueConstraint(
                fields=["payee_kind", "payee_id", "period_start"],
                name="uq_statement_payee_period",
            ),
            models.CheckConstraint(
                condition=Q(gross_commission_kes__gte=0), name="ck_statement_gross_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(adjustments_kes__lte=0), name="ck_statement_adjustments_non_positive"
            ),
            models.CheckConstraint(
                condition=Q(
                    net_due_kes=models.F("gross_commission_kes") + models.F("adjustments_kes")
                ),
                name="ck_statement_net_is_gross_plus_adjustments",
            ),
            models.CheckConstraint(
                condition=Q(period_end__gt=models.F("period_start")),
                name="ck_statement_period_order",
            ),
        ]
        indexes = [models.Index(fields=["payee_kind", "payee_id", "-period_start"])]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"statement {self.reference} {self.period_start}"


class StatementLine(AppendOnlyModel):
    statement = models.ForeignKey(
        CommissionStatement, on_delete=models.PROTECT, related_name="lines"
    )
    kind = models.CharField(max_length=10, choices=LineKind.choices)
    commission_record = models.OneToOneField(
        "jobs.CommissionRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    adjustment = models.OneToOneField(
        "jobs.CommissionAdjustment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="+")
    #: Frozen at billing time so the statement reads the same forever.
    job_reference = models.CharField(max_length=8)
    agreed_price_kes = models.BigIntegerField(null=True, blank=True)
    amount_kes = models.BigIntegerField()

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "statement_line"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        kind="COMMISSION",
                        commission_record__isnull=False,
                        adjustment__isnull=True,
                        amount_kes__gte=0,
                    )
                    | Q(
                        kind="ADJUSTMENT",
                        commission_record__isnull=True,
                        adjustment__isnull=False,
                        amount_kes__lt=0,
                    )
                ),
                name="ck_statement_line_shape",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.kind} {self.amount_kes} on {self.statement_id}"


class StatementSettlement(AppendOnlyModel):
    statement = models.ForeignKey(
        CommissionStatement, on_delete=models.PROTECT, related_name="settlements"
    )
    kind = models.CharField(max_length=10, choices=SettlementKind.choices)
    #: Positive for a payment; the negative of the original for a reversal.
    amount_kes = models.BigIntegerField()
    method = models.CharField(max_length=14, choices=SettlementMethod.choices)
    payment_ref = models.CharField(max_length=64)
    paid_on = models.DateField()
    #: A payment's optional note, or a reversal's required reason.
    note = models.TextField(blank=True, default="")
    reverses = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversed_by"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "statement_settlement"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="PAYMENT", amount_kes__gt=0, reverses__isnull=True)
                    | Q(kind="REVERSAL", amount_kes__lt=0, reverses__isnull=False)
                ),
                name="ck_statement_settlement_shape",
            ),
        ]
        indexes = [models.Index(fields=["payment_ref"])]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.kind} {self.amount_kes} on {self.statement_id}"


class StatementSeen(TimestampedModel):
    """ "This payee has opened this statement" (S-2, D-6: the unread marker on
    the Statements list and the Home "New statement" card). One row per
    person and statement, written the first time they open it. Not audited:
    it records what someone looked at, not a change to the ledger (like
    ``inbox_read_marker``, ADR-2D-37)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    statement = models.ForeignKey(
        CommissionStatement, on_delete=models.CASCADE, related_name="seen_by"
    )

    class Meta:
        db_table = "statement_seen"
        constraints = [
            models.UniqueConstraint(fields=["user", "statement"], name="uq_statement_seen_user"),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.user_id} saw {self.statement_id}"
