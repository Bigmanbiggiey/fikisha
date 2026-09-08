"""Audit module — the immutable, append-only, hash-chained record of every
state-changing action by every actor (including automated timers and the
founder). See docs/phase-1/security-architecture.md §4 and admin-architecture.md
§6 ("the founder is not above the audit").
"""
