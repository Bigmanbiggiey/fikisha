"""Evidence — private file objects and their access log (Phase 1
domain-architecture §3.15, evidence-storage.md).

A pure dependency module: it stores bytes through the Phase 2A ``storage``
abstraction, records metadata + a content hash, and streams bytes back **only**
when a consuming module (Verification, later Custody / Incidents) has already
authorized the caller. It never serves a bucket URL; every HIGH-PII fetch writes
an access-log row.

Phase 2C scope: store / stat / open / delete + the access log. No ClamAV, no
thumbnails, no EXIF re-encode, no envelope-encryption wiring — those are
documented production hardening (see docs/phase-2/phase-2c-privacy-security.md).
"""
