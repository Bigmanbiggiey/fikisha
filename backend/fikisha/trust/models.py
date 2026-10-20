"""Operator tier data model (trust-architecture.md §2).

``trust_level_state`` is the current tier, one row per operator, written
only by ``fikisha.trust.services``. No row means L1 (the tier every
verified operator had under the interim rule), so nobody's access changed
when tiers shipped.

``trust_level_change`` is append-only (service + model + Postgres trigger).
A proposal stays ``PROPOSED`` forever; its decision is a later row whose
``decides`` points at it (one decision per proposal, enforced by a unique
constraint).

Deviation from database-design §4.5: no stored ``value_ceiling_kes``; the
ceiling is read from ``value_bands`` config for the tier, so a band change
applies at once (historical rows keep their ``config_version``).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel
from fikisha.trust.constants import ChangeStatus, ChangeTrigger, ProposedBy, Tier


class TrustLevelState(TimestampedModel):
    operator = models.OneToOneField(
        "operators.OperatorProfile", on_delete=models.PROTECT, related_name="trust_state"
    )
    level = models.CharField(max_length=12, choices=Tier.choices, default=Tier.L1)
    since = models.DateTimeField(null=True, blank=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    config_version = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "trust_level_state"


class TrustLevelChange(AppendOnlyModel):
    operator = models.ForeignKey(
        "operators.OperatorProfile", on_delete=models.PROTECT, related_name="trust_changes"
    )
    from_level = models.CharField(max_length=12, choices=Tier.choices)
    to_level = models.CharField(max_length=12, choices=Tier.choices)
    trigger = models.CharField(max_length=20, choices=ChangeTrigger.choices)
    status = models.CharField(max_length=10, choices=ChangeStatus.choices)
    reason = models.TextField(blank=True, default="")
    proposed_by = models.CharField(max_length=8, choices=ProposedBy.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    decides = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="decisions"
    )
    criteria_snapshot = models.JSONField(default=dict, blank=True)
    evidence_job_ids = models.JSONField(default=list, blank=True)
    evidence_incident_ids = models.JSONField(default=list, blank=True)
    config_version = models.IntegerField(null=True, blank=True)
    #: What a demotion proposal rests on (trust-and-disputes plan A6): the
    #: finding id (INCIDENT) or a hash of the counted rating ids
    #: (RATING_DROP). The same evidence is never proposed twice.
    evidence_key = models.CharField(max_length=64, blank=True, default="")

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "trust_level_change"
        indexes = [
            models.Index(fields=["operator", "-created_at"], name="ix_trust_change_operator")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["decides"],
                condition=models.Q(decides__isnull=False),
                name="uniq_trust_change_one_decision",
            ),
            models.UniqueConstraint(
                fields=["operator", "trigger", "evidence_key"],
                condition=models.Q(trigger="RATING_DROP", status="PROPOSED"),
                name="uq_trust_rating_drop_evidence",
            ),
            models.UniqueConstraint(
                fields=["evidence_key"],
                condition=models.Q(trigger="INCIDENT", status="PROPOSED"),
                name="uq_trust_incident_evidence",
            ),
        ]
