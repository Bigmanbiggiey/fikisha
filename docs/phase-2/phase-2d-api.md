# Phase 2D — API Reference

The HTTP boundary over the Jobs / Negotiation / Incidents & Disputes domain
(plan §19 Step 10, ADR-2D-25–28), promoted from the plan doc as part of
closing out Phase 2D (plan §19 Step 15). Every view here is a thin adapter:
authenticate → parse/validate (named serializer fields only) → resolve the
target → call the already-approved domain service → serialize. **No
lifecycle, negotiation, assignment, proof, incident, dispute, or commission
rule is implemented in this layer** — see `phase-2d-decisions.md` for why
each module is placed where it is.

All routes, including the recipient-scoped ones, are mounted under
`/api/v1/` via `fikisha.api.urls` (`jobs.api.urls`'s `/r/<token>...` routes
included the same way as everything else — confirmed directly against
`config/urls.py` + `fikisha/api/urls.py` while building the frontend API
client, correcting an earlier version of this doc that said "outside
/api/v1/"). What actually makes them different is auth: they authenticate
via the link token itself, not a bearer session.

---

## 1. Conventions (shared with every other Fikisha module)

- **Auth:** `Authorization: Bearer <token>` (`BearerSessionAuthentication`).
  Absent → anonymous; malformed → `401`, never `500`. Recipient routes
  (`/r/<token>...`) use the link token in the URL instead — no bearer header.
- **Authorization:** every state-changing or object-scoped view declares an
  `action_get`/`action_post` string, checked by the central
  `authorize(actor, action, resource)` (default-deny). List views scope
  their own queryset (`job_authz.jobs_visible_to()` etc.); detail views
  resolve the object and check `is_job_party()`/equivalent.
- **Errors:** RFC 9457 `application/problem+json` — every error body carries
  `code` and `request_id`; no stack trace, DB error text, or internal detail
  ever appears in a response (`test_error_responses_never_include_a_stack_
  trace_or_db_detail`).
- **Pagination:** cursor-based, `{data, page: {next_cursor, prev_cursor}}`,
  on every collection endpoint.
- **Idempotency — `Idempotency-Key` header:**
  - Plain creates (job creation, incident report, dispute open) use the
    existing cache-based `common.idempotency.idempotent()` (Phase 2B).
  - Lifecycle-transition actions (submit, cancel, assign, every custody
    confirm, negotiation accept, dispute resolve) forward the header into
    the domain layer's own `JobTransitionIdempotency` DB-row store (built in
    Increment 1) — a retried call with the same key replays the original
    result rather than re-executing (ADR-2D-28). One documented exception:
    a retried `resolve_dispute()` does not replay byte-for-byte — it hits
    `dispute.status == RESOLVED` and cleanly returns `409
    dispute_already_resolved` instead (no duplicate `Resolution`/
    `CommissionAdjustment` is possible either way).
- **Optimistic concurrency (`If-Match` / `job.version`):** the domain layer
  (`TransitionContext.if_match_version` → `StaleJob`/`412`, ADR-2D-02) has
  supported this since Increment 1, but **no current API view actually
  parses an `If-Match` request header and forwards it** — this is a real,
  honest gap between what the domain layer can do and what Step 10 wired at
  the HTTP layer, not a designed limitation. Recorded here rather than
  silently assumed to be covered; a candidate for a future small addition,
  not a Phase 2D product decision.
- **Multipart uploads:** custody/incident evidence photos go through
  `fikisha.evidence.services.store()` — never a DB blob, never a signed
  bucket URL; a validation failure (empty file, oversized, disallowed
  content-type) is a clean `422` (`code="evidence_validation_error"`).
- **OpenAPI:** `manage.py spectacular` generates a schema successfully but
  with pre-existing warnings (104 warnings / 372 errors as of the final-
  verification pass) — all of one class ("unable to guess serializer" for
  plain `APIView`s not using `GenericAPIView`, and `operationId` collisions
  on shared list/detail paths). Predates Phase 2D; cosmetic, not a runtime
  disclosure issue (§21 of the final-verification report). Treat this
  document, not the generated schema, as the accurate endpoint reference
  until that's cleaned up.

---

## 2. Jobs (`fikisha.jobs.api`)

| Method | Path | Action (authz) | Purpose |
| --- | --- | --- | --- |
| GET | `/jobs` | `job.read` | List jobs visible to the actor (cursor-paginated, `-created_at`) |
| POST | `/jobs` | `job.create` | Create a `DRAFT` job (`jobs.creation.create_draft`) |
| GET | `/jobs/opportunities` | `job.discover` | Operator work discovery: open `REQUESTED`/`NEGOTIATING` jobs matching the operator's own vehicle class(es) and not already threaded, each row with a server-computed eligibility marker (Design Phase 6 Increment 4; individual operators only) |
| GET | `/jobs/<job_id>/opportunity` | `job.discover` | One job's opportunity view, reachable before the operator is a negotiation party; only while the job is still open (Increment 4) |
| GET | `/jobs/<job_id>` | `job.read` | Job detail (object-level `is_job_party` check) |
| POST | `/jobs/<job_id>/submit` | `job.transition` | `DRAFT → REQUESTED` |
| POST | `/jobs/<job_id>/cancel` | `job.transition` | `* → CANCELLED` (wherever a rule allows it) |
| GET | `/jobs/<job_id>/assignment-candidates` | `job.assign.candidates` | Read-only driver/vehicle eligibility preview with concrete reasons; shares its predicates with the `assign` guard so the two cannot drift (Increment 4) |
| POST | `/jobs/<job_id>/assign` | `job.assign` | `CONFIRMED → ASSIGNED` — driver + vehicle eligibility, high-value gate |
| GET | `/jobs/<job_id>/commission` | `commission.read` | Read the job's commission record — **Platform-Admin-only** (ADR-2D-27) |
| POST | `/jobs/<job_id>/custody/arrive-pickup` | `job.proof.pickup` | `ASSIGNED → AT_PICKUP` |
| POST | `/jobs/<job_id>/custody/confirm-pickup/otp` | `job.proof.pickup` | `AT_PICKUP → PICKED_UP` via pickup-contact OTP |
| POST | `/jobs/<job_id>/custody/confirm-pickup/business` | `job.proof.pickup` | `AT_PICKUP → PICKED_UP` via in-app business confirmation |
| POST | `/jobs/<job_id>/custody/confirm-pickup/attested` | `job.proof.pickup` | `AT_PICKUP → PICKED_UP` — STANDARD-only operator-attested fallback (photo + contact name) |
| POST | `/jobs/<job_id>/custody/fail-at-pickup` | `job.transition` | `AT_PICKUP → FAILED` |
| POST | `/jobs/<job_id>/custody/start-transit` | `job.transition` | `PICKED_UP → IN_TRANSIT` |
| POST | `/jobs/<job_id>/custody/arrive-destination` | `job.proof.delivery` | `IN_TRANSIT → AT_DESTINATION` — also issues the recipient OTP + access link |
| POST | `/jobs/<job_id>/custody/confirm-delivery` | `job.proof.delivery` | `AT_DESTINATION → DELIVERED` (driver-side; recipient has its own route below) |

### Recipient scoped access (no bearer session — `/r/<token>...`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/r/<token>` | Minimal-disclosure job view (`recipient.view()` — exact plan §11 field set, no price/value/staff/location-history) |
| POST | `/r/<token>/confirm` | `AT_DESTINATION → DELIVERED` via the recipient's own OTP (the identical transition the driver uses) |
| POST | `/r/<token>/report-issue` | Append-only issue report (`RecipientReportedIssue`) — does **not** move `job.status`. Accepts multipart `photos`, stored as `INCIDENT_EVIDENCE` (Design Phase 6 Increment 6) |

---

## 3. Negotiation (`fikisha.negotiation.api`)

| Method | Path | Action (authz) | Purpose |
| --- | --- | --- | --- |
| GET | `/jobs/<job_id>/negotiation/threads` | `negotiation.read` | List every thread for the job (sealed per-party visibility) |
| POST | `/jobs/<job_id>/negotiation/threads` | `negotiation.propose` | Open a thread (operator/group) or add a `PROPOSE` (business) — seeds the posted price on first open |
| GET | `/negotiation/threads/<thread_id>` | `negotiation.read` | Thread detail + full entry history + derived statuses |
| POST | `/negotiation/threads/<thread_id>/counter` | `negotiation.counter` | Add a `COUNTER` entry |
| POST | `/negotiation/threads/<thread_id>/accept` | `negotiation.accept` | Add an `ACCEPT`; mutual acceptance → `JobLifecycleService.transition(CONFIRMED)` in the same transaction, closes the winning thread + supersedes siblings |
| POST | `/negotiation/threads/<thread_id>/decline` | `negotiation.decline` | Add a `DECLINE` |

---

## 4. Incidents & Disputes (`fikisha.incidents.api`)

| Method | Path | Action (authz) | Purpose |
| --- | --- | --- | --- |
| GET | `/jobs/<job_id>/incidents` | `incident.read` | List incidents for the job |
| POST | `/jobs/<job_id>/incidents` | `incident.create` | Report an incident (`report_incident`) |
| GET | `/incidents/<incident_id>` | `incident.read` | Incident detail, with its `evidence` and `statements` arrays embedded (Design Phase 6 Increment 7) |
| POST | `/incidents/<incident_id>/evidence` | `incident.evidence.attach` | Attach evidence (reuses `fikisha.evidence`, append-only) |
| GET | `/incidents/evidence/<evidence_id>/content` | `incident.read` | Stream one evidence file through the API, never a signed bucket URL; mirrors verification's evidence content view (Increment 7) |
| POST | `/incidents/<incident_id>/statements` | `incident.statement.add` | Add a party statement (append-only) |
| POST | `/incidents/<incident_id>/review` | `incident.review` | Start formal review (config-driven `OPERATIONS_OFFICER` permission, not "any admin") |
| POST | `/incidents/<incident_id>/amicable` | `incident.review` | Start the amicable-resolution window |
| POST | `/incidents/<incident_id>/escalate` | `incident.escalate` | Escalate — **Platform-Admin-only** |
| GET | `/jobs/<job_id>/disputes` | `incident.read` | List disputes for the job |
| POST | `/jobs/<job_id>/disputes` | `dispute.open` | Open a dispute (`* → DISPUTED`; at most one open dispute per job, DB-backed) |
| GET | `/disputes/<dispute_id>` | `incident.read` | Dispute detail |
| POST | `/disputes/<dispute_id>/resolve` | `dispute.resolve` | Resolve (`DISPUTED → COMPLETED/CANCELLED/FAILED`); `commission_treatment=REDUCE/WAIVE` requires Platform-Admin specifically (ADR-2D-24), separate from resolution authority itself |

`intake_recipient_report(report_id)` (promotes a `RecipientReportedIssue`
into a full `Incident`) exists as a domain function but has **no HTTP route**
yet — plan §19 Step 8 built it as a plain callable, not auto-wired to an
outbox consumer; still true after Step 10.

---

## 5. What is deliberately absent

No route exposes: a raw scheduler/lifecycle transition (sweeps run only as
`SystemActor`, confirmed by `test_no_http_endpoint_exposes_a_raw_scheduler_
transition`) · `DISPUTED → RESUME`/`RESUME_PRIOR` (not implemented, ADR-2D-07)
· a trust/rating read or write of any kind · any M-Pesa/eTIMS/SMS/WhatsApp
provider callback · a wallet/escrow/fare-custody operation.
