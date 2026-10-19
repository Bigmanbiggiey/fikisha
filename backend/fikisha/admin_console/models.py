"""Platform Admin console state (Design Phase 6 Increment 9, ADR-2D-38).

``AdminIntervention`` is the account-level half of Phase 1's
``admin_intervention`` table (`database-design.md` §4.16): one append-only
row per suspend / reinstate / offboard, naming the admin, the reason and the
account's state before and after. Job-level interventions (cancel, notes,
contact reveal, high-value decisions) already have their own records
(``job_event``, ``high_value_approval``) and are not duplicated here.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet


class AccountType(models.TextChoices):
    USER = "USER", "User account"
    OPERATOR = "OPERATOR", "Operator profile"
    BUSINESS = "BUSINESS", "Business account"
    GROUP = "GROUP", "Operator group"


class InterventionAction(models.TextChoices):
    SUSPEND = "SUSPEND", "Suspend"
    REINSTATE = "REINSTATE", "Reinstate"
    OFFBOARD = "OFFBOARD", "Offboard"
    #: A reviewer approves a new operator: PENDING → ACTIVE (assessment
    #: 2026-10-19 D-2). Not part of ``intervene()``; see ``approve_operator``.
    APPROVE = "APPROVE", "Approve"


class AdminIntervention(AppendOnlyModel):
    account_type = models.CharField(max_length=12, choices=AccountType.choices)
    account_id = models.UUIDField()
    action = models.CharField(max_length=12, choices=InterventionAction.choices)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    reason = models.TextField()
    #: Recorded only (D-2): nothing reinstates automatically; a Platform Admin
    #: reinstates by hand.
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    before_state = models.CharField(max_length=16)
    after_state = models.CharField(max_length=16)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "admin_intervention"
        indexes = [models.Index(fields=["account_type", "account_id", "created_at"])]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.action} {self.account_type} {self.account_id}"
