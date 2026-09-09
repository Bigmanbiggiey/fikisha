# Phase 2C — Privacy & Security Decisions

Verification evidence contains sensitive personal and regulatory information
(national IDs, driving licences, Certificates of Good Conduct, vehicle papers).
This documents how Phase 2C handles it. It is **not** a DPIA — legal / privacy
compliance remains a broader project gate (Phase 0 `legal-scope.md`).

---

## 1. Evidence is never public, always API-mediated

- Bytes are stored through the Phase 2A `storage` abstraction
  (`PrivateStorage` — `LocalPrivateStorage` in dev, `S3PrivateStorage` stub).
  The application only ever deals with a **storage key + metadata row**
  (`EvidenceObject`), never a provider bucket URL (NFR-SEC-8).
- There is **no client-facing pre-signed PUT or GET** in 2C. Upload is a
  multipart `POST` through the API; download streams bytes back through the API
  (`GET /api/v1/verification/evidence/{id}/content`) after an explicit
  authorization check (ADR-013). No `<a href>` to storage.
- Key layout: `evidence/<purpose>/<yyyy>/<mm>/<uuid4>` — no PII, not walkable.

## 2. Explicit evidence authorization (brief §26)

Access is **not** granted just because the caller can see the parent record.
`GET /verification/evidence/{id}/content` resolves the evidence's parent
`VerificationRecord` and runs the `verification.evidence.read` policy:

| Caller | Access |
| --- | --- |
| The **subject owner** (the operator whose profile / whose vehicle / whose operating base the record is about) | ✅ (they uploaded it) |
| A **reviewer** (`verification.decide` permission — Ops Officer / Platform Admin) | ✅ |
| Anyone else (another operator, a business user, unauthenticated) | ❌ 403 / 401 |

The stricter Phase 1 refinement — "the operator sees only a low-resolution
thumbnail of their own HIGH-PII" — is **deferred**. In 2C the owner can fetch
the full document they submitted; no third party can.

## 3. HIGH-PII access is logged

`EvidenceObject.pii_class` is `HIGH` for `IDENTITY` / `LICENCE` /
`GOOD_CONDUCT` domains and for ID / passport / selfie / licence / good-conduct
document kinds; `MEDIUM` otherwise. Every fetch of a `HIGH` object writes an
append-only `EvidenceAccessLog` row (`accessed_by`, `accessed_by_role`,
`reason`, `created_at`) — NFR-SEC-4. `MEDIUM`/`LOW` fetches are not logged.

## 4. Upload hardening present / deferred

| Control | 2C | Notes |
| --- | --- | --- |
| Per-purpose **type allowlist** | ✅ | `VERIFICATION_DOC` → JPEG / PNG / PDF only; photo purposes → JPEG / PNG / WebP |
| **Size cap** | ✅ | 10 MB |
| SHA-256 recorded on the object | ✅ | integrity (NFR-INT-4) |
| ClamAV scan of non-images | ❌ deferred | evidence-storage.md §3 — production hardening |
| EXIF / GPS strip + image re-encode | ❌ deferred | same |
| Envelope encryption of HIGH-PII objects (KMS data-key wrap) | ❌ deferred | Phase 2A ships the seam only (ADR-2A); documented production control |

These deferrals match the Phase 2A foundation posture and are called out here so
nobody mistakes the 2C state for the full production control set.

## 5. Reviewer integrity

- A verification decision can only be made by a holder of the
  `verification.decide` permission — an operator or business user has no path to
  self-approve (403 at the policy).
- A permitted reviewer **cannot act on a record they submitted** (422
  `reviewer_is_submitter`) — the submit / approve separation of duties (brief
  §17), enforced in the service layer regardless of permissions.
- Every decision carries the reviewer's identity and role (brief §18); the
  decision log is append-only at three layers.

## 6. Cross-organisation isolation

Vehicle and verification-record detail endpoints resolve the target and run the
object-level policy **before** the handler. An authenticated non-owner /
non-reviewer gets **403** (consistent with Phase 2B org resources — ADR-2B-06).
Covered by `test_vehicles_security.py`,
`test_verification_security` cases, and the smoke test.

## 7. What is deliberately out of scope

No trust score, value-band eligibility, job eligibility, notifications, GPS,
insurance products, or automated decision-making. Verification here records
**facts**; a human always decides (no auto-approve), keeping the trust decision
out of "solely automated decision-making" (legal-scope §3.4).
