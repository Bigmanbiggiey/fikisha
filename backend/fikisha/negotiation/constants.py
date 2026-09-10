"""Negotiation enums (database-design.md §4.8, pricing-and-negotiation.md §4).

The MVP negotiation is a two-way propose / counter / accept / reject exchange
with an **immutable append-only history**. No dynamic pricing, no
recommendations, no platform price-setting (D-NEG-4).
"""

from __future__ import annotations

from django.db import models


class ThreadStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"  # another thread on the job won
    CLOSED = "CLOSED", "Closed"  # rejected/withdrawn, or this thread confirmed the job


class EntryType(models.TextChoices):
    PROPOSE = "PROPOSE", "Propose"
    COUNTER = "COUNTER", "Counter-offer"
    ACCEPT = "ACCEPT", "Accept"
    REJECT = "REJECT", "Reject"


#: PROPOSE/COUNTER put a figure on the table; ACCEPT copies the accepted figure in.
OFFER_TYPES: frozenset[str] = frozenset({EntryType.PROPOSE, EntryType.COUNTER})
AMOUNT_REQUIRED_TYPES: frozenset[str] = frozenset(
    {EntryType.PROPOSE, EntryType.COUNTER, EntryType.ACCEPT}
)


class EntryStatus(models.TextChoices):
    """**Derived at read time** — never stored (ADR-2D-11). ``negotiation_entry``
    is a hard append-only table; an entry's effective status folds in the
    thread's status, offer expiry, and later same-thread offers, exactly as
    ``VerificationRecord.effective_state()`` folds verification expiry."""

    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    EXPIRED = "EXPIRED", "Expired"


class EntryActorRole(models.TextChoices):
    BUSINESS = "BUSINESS", "Business"
    OPERATOR = "OPERATOR", "Operator"
    ADMIN = "ADMIN", "Administrator"
