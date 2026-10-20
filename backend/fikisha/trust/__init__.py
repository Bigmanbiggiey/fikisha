"""Operator tiers (trust levels) — operator-tiers plan, ADR-2D-52.

Verification records facts; this module decides which value band of jobs a
driver may take. A tier changes only through an append-only, audited
``trust_level_change``: a system proposal a Platform Admin confirms or
rejects, or a Platform Admin's direct (manual) change.
"""
