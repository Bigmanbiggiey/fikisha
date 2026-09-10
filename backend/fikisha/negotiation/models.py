"""Negotiation data model (database-design.md §4.8, negotiation-architecture.md §2).

- ``NegotiationThread`` — one per ``(job, operator | group)``. Mutable ``status``
  (ACTIVE → SUPERSEDED / CLOSED). Sealed: read scoping (not isolation infra) keeps
  operators from seeing each other's threads (ADR-006).
- ``NegotiationEntry`` — **append-only**, immutable. `PROPOSE / COUNTER / ACCEPT /
  REJECT`. Never updated or deleted; a correction is a new entry (FR-N-2). Its
  ACTIVE/SUPERSEDED/EXPIRED status is **derived** (`selectors.effective_entry_status`,
  ADR-2D-11), not stored.

Money is KES minor units (BigInteger). There is no ``Agreement`` here — the Job
Lifecycle Service creates it inside the confirming transaction.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel
from fikisha.jobs.constants import OperatorParty
from fikisha.negotiation.constants import EntryActorRole, EntryType, ThreadStatus


class NegotiationThread(TimestampedModel):
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.PROTECT, related_name="negotiation_threads"
    )
    operator_party = models.CharField(max_length=12, choices=OperatorParty.choices)
    operator = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    group = models.ForeignKey(
        "groups.OperatorGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    status = models.CharField(
        max_length=12, choices=ThreadStatus.choices, default=ThreadStatus.ACTIVE
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "negotiation_thread"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(operator__isnull=False, group__isnull=True)
                    | models.Q(operator__isnull=True, group__isnull=False)
                ),
                name="ck_negotiation_thread_one_party",
            ),
            models.UniqueConstraint(
                fields=["job", "operator"],
                condition=models.Q(operator__isnull=False),
                name="uq_negotiation_thread_operator",
            ),
            models.UniqueConstraint(
                fields=["job", "group"],
                condition=models.Q(group__isnull=False),
                name="uq_negotiation_thread_group",
            ),
        ]
        indexes = [models.Index(fields=["job", "status"], name="ix_negotiation_thread_job")]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"Thread {self.pk} on job {self.job_id} [{self.status}]"

    @property
    def counterparty_id(self) -> object:
        return self.operator_id or self.group_id


class NegotiationEntry(AppendOnlyModel):
    """Append-only. See ADR-2D-11 — no ``status`` column; effective status is
    computed in :mod:`fikisha.negotiation.selectors`."""

    thread = models.ForeignKey(NegotiationThread, on_delete=models.PROTECT, related_name="entries")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.PROTECT, related_name="negotiation_entries"
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_role = models.CharField(max_length=12, choices=EntryActorRole.choices)
    type = models.CharField(max_length=12, choices=EntryType.choices)
    amount_kes = models.BigIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KES")
    note = models.TextField(blank=True, default="")
    in_response_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "negotiation_entry"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(type="REJECT") | models.Q(amount_kes__isnull=False)),
                name="ck_negotiation_entry_amount_required",
            ),
            models.CheckConstraint(
                condition=(models.Q(amount_kes__isnull=True) | models.Q(amount_kes__gt=0)),
                name="ck_negotiation_entry_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["thread", "created_at"], name="ix_negotiation_entry_thread"),
            models.Index(fields=["job"], name="ix_negotiation_entry_job"),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.actor_role} {self.type} {self.amount_kes or ''} (thread {self.thread_id})"
