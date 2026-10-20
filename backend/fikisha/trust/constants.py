"""Operator tier enums (trust-architecture.md §1-§2, operator-tiers plan)."""

from __future__ import annotations

from django.db import models


class Tier(models.TextChoices):
    #: Computed, never stored: the verification floor is not met.
    L0 = "L0", "Pending"
    L1 = "L1", "Verified"
    L2 = "L2", "Established"
    L3 = "L3", "Trusted"
    #: Admin-imposed demotion: STANDARD jobs only (TD-4).
    RESTRICTED = "RESTRICTED", "Restricted"


STORED_TIERS = (Tier.L1, Tier.L2, Tier.L3, Tier.RESTRICTED)
#: The tier above each tier that can progress (Restricted can't; L3 is the top).
NEXT_TIER = {Tier.L0: Tier.L1, Tier.L1: Tier.L2, Tier.L2: Tier.L3}
#: For band coverage: Restricted covers what L1 covers (STANDARD).
TIER_ORDER = {Tier.L0: 0, Tier.RESTRICTED: 1, Tier.L1: 1, Tier.L2: 2, Tier.L3: 3}


class ChangeStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    APPLIED = "APPLIED", "Applied"
    REJECTED = "REJECTED", "Rejected"


class ChangeTrigger(models.TextChoices):
    AUTO_PROPOSED = "AUTO_PROPOSED", "Proposed by Fikisha"
    ADMIN_CONFIRMED = "ADMIN_CONFIRMED", "Proposal confirmed"
    ADMIN_REJECTED = "ADMIN_REJECTED", "Proposal rejected"
    #: A Platform Admin's direct promote / demote (TD-1, shown as "manual").
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE", "Manual change"
    #: Proposed to Restricted after a serious at-fault finding naming the
    #: driver (TE-5); a Platform Admin confirms (FR-T-4).
    INCIDENT = "INCIDENT", "Proposed after a fault finding"
    #: Proposed one tier down after the rating average fell (TE-6).
    RATING_DROP = "RATING_DROP", "Proposed after a rating drop"
    #: A Platform Admin lifts a restriction, back to L1 only (TD-4).
    REMEDIATION_EXIT = "REMEDIATION_EXIT", "Restriction lifted"


#: Proposals that move an operator down; while one is open no promotion is
#: proposed.
DEMOTION_TRIGGERS = (ChangeTrigger.INCIDENT, ChangeTrigger.RATING_DROP)

#: One tier down (TE-6).
LOWER_TIER = {"L3": "L2", "L2": "L1", "L1": "RESTRICTED"}


class ProposedBy(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    ADMIN = "ADMIN", "Admin"


class CriterionStatus(models.TextChoices):
    MET = "MET", "Met"
    NOT_MET = "NOT_MET", "Not met"
    #: Not recordable yet (or not switched on): shown, never blocking (TD-3).
    NOT_MEASURED = "NOT_MEASURED", "Not yet measured"
    #: measurable, but too little data yet (e.g. fewer than 3 counted
    #: ratings); blocks a proposal like NOT_MET (TE-11)
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Not enough data yet"
