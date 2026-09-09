"""Verification — per-domain verification records, their append-only decision
history, and the derived-state read helpers (Phase 1 verification-architecture,
FR-V-1..V-8, FR-T-6).

**Verification is per-domain, not a boolean.** There is no ``is_verified`` flag.
Whether a subject "currently satisfies" a domain is computed deterministically
from persisted data: ``state == VERIFIED and (expires_at is null or in future)``.

Phase 2C establishes the *facts*. It does NOT compute trust levels, value-band
eligibility, or job/assignment eligibility — those consume these facts later.
"""
