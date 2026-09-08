"""Platform Configuration — the single versioned ``PlatformConfig`` and its
append-only change history (Phase 1 domain-architecture §3.17, admin-architecture
§3).

Phase 2A builds the *mechanism* (a versioned singleton + a deep-merge change API
+ audit + outbox event). It seeds a coherent default; business values are tuned
via ``apply_change`` later without a deploy.
"""
