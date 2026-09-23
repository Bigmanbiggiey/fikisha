"""What ``audit.view.scoped`` means (Design Phase 6 Increment 8, founder
decision 2026-09-23; ADR-2D-35): an Operations Officer reads the audit
entries within the Ops remit — jobs, negotiation, incidents/disputes,
verification, high-value decisions. Commission, platform config, identity,
session and membership entries stay Platform-Admin-only (``"*"``).

An allowlist, not a denylist: a new ``entity_type`` added later is
Platform-Admin-only until someone deliberately adds it here.
"""

from __future__ import annotations

OPS_AUDIT_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "job",
        "negotiation_entry",
        "high_value_approval",
        "recipient_access_link",
        "recipient_reported_issue",
        "incident",
        "incident_statement",
        "incident_evidence",
        "dispute",
        "resolution",
        "escalation",
        "verification_record",
        "vehicle",
    }
)
