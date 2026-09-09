"""Vehicles — the registry of vehicles controlled by an individual operator or an
operator group (Phase 1 domain-architecture §3.5, operator-model §2).

Phase 2C records **control and attributes**, not a legal vehicle-title registry.
Verification of vehicle facts (registration/ownership, inspection, insurance,
heavy-class compliance) lives in ``fikisha.verification``; nothing here computes
trust or job/assignment eligibility.
"""
