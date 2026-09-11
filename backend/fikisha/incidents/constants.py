"""Incidents & Disputes enums (dispute-and-liability.md, FR-D-1..D-10,
database-design.md §4.10). The 11-value incident taxonomy is verbatim from
FR-D-1 / dispute-and-liability.md §2 — do not add categories casually.

Incident status and Dispute status are deliberately **small, explicit**
workflows, not the 14-state Job lifecycle re-used (plan §19 Step 8 brief §8/9).
"""

from __future__ import annotations

from django.db import models


class IncidentType(models.TextChoices):
    DAMAGE = "DAMAGE", "Damage"
    LOSS = "LOSS", "Loss"
    MISSING_GOODS = "MISSING_GOODS", "Missing goods (partial shortage)"
    WRONG_RECIPIENT = "WRONG_RECIPIENT", "Wrong recipient"
    WRONG_PICKUP = "WRONG_PICKUP", "Wrong pickup"
    MISCONDUCT = "MISCONDUCT", "Misconduct"
    BREAKDOWN = "BREAKDOWN", "Breakdown"
    ACCIDENT = "ACCIDENT", "Accident"
    DELAY = "DELAY", "Delay"
    CANCELLATION = "CANCELLATION", "Cancellation"
    OTHER = "OTHER", "Other"


class IncidentSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


#: dispute-and-liability.md §2: "administrator-set, with defaults by type" — no
#: exact per-type table is specified anywhere in the approved docs, so this is
#: a single neutral fallback, not an invented severity policy. An admin can
#: always change it (``set_severity``).
DEFAULT_SEVERITY = IncidentSeverity.MEDIUM


class IncidentStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    AMICABLE_PENDING = "AMICABLE_PENDING", "Amicable resolution pending"
    RESOLVED = "RESOLVED", "Resolved"
    ESCALATED = "ESCALATED", "Escalated"


class ReportedByKind(models.TextChoices):
    USER = "USER", "Platform user"
    RECIPIENT_LINK = "RECIPIENT_LINK", "Recipient (scoped link)"
    ADMIN = "ADMIN", "Administrator"


class PartyKind(models.TextChoices):
    BUSINESS = "BUSINESS", "Business"
    OPERATOR = "OPERATOR", "Operator"
    GROUP = "GROUP", "Operator group"
    RECIPIENT = "RECIPIENT", "Recipient"
    ADMIN = "ADMIN", "Administrator"


#: Mirrors IncidentStatus — a Dispute goes through the same shape of workflow
#: (open -> under review / amicable pending -> resolved), independently of
#: Job.status, which only ever reads DISPUTED for the whole freeze window.
class DisputeStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    AMICABLE_PENDING = "AMICABLE_PENDING", "Amicable resolution pending"
    RESOLVED = "RESOLVED", "Resolved"
    ESCALATED = "ESCALATED", "Escalated"


#: What actually happened, not who was at fault — the platform makes no
#: automated liability determination (dispute-and-liability.md §1, §7).
class ResolutionOutcome(models.TextChoices):
    AMICABLE_AGREEMENT = "AMICABLE_AGREEMENT", "Amicable agreement"
    ADMIN_DETERMINATION = "ADMIN_DETERMINATION", "Administrative determination"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class CommissionTreatment(models.TextChoices):
    APPLY = "APPLY", "Apply as normal"
    REDUCE = "REDUCE", "Reduce"
    WAIVE = "WAIVE", "Waive"


#: Recorded intents only (FR-D-6) — Step 8 does not execute any of these; there
#: is no rating/trust/suspension engine to execute them against (ADR-2D-21).
class ResolutionAction(models.TextChoices):
    NONE = "NONE", "No further action"
    RATING_IMPACT = "RATING_IMPACT", "Rating impact (recorded only)"
    TRUST_CHANGE = "TRUST_CHANGE", "Trust-level change (recorded only)"
    SUSPENSION = "SUSPENSION", "Suspension (recorded only)"


#: DISPUTED -> RESUME (RESUME_PRIOR) is explicitly OPEN / not implemented
#: (E-1, ADR-2D-07) — a resolution may only route to one of these. A **tuple**,
#: not a set/frozenset: a set's iteration order is randomised per-process
#: (``PYTHONHASHSEED``), and this constant is rendered into a DB
#: ``CheckConstraint`` (``models.py``) — a set would make ``makemigrations``
#: detect a spurious diff on every run.
ROUTABLE_JOB_STATUSES: tuple[str, ...] = ("CANCELLED", "COMPLETED", "FAILED")
