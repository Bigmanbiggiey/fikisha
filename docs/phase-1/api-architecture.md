# API Architecture

REST over HTTPS/JSON, served by Django REST Framework. This document defines the
**conventions** and then the **resource design per module**. Endpoint
implementations are Phase 2, not Phase 1.

---

## 1. Conventions

| Concern | Rule |
|---------|------|
| **Base path / versioning** | `/api/v1/...`. Version in the URL prefix. Breaking changes → `/api/v2`; `Sunset` header + a changelog during any overlap. |
| **Transport** | TLS 1.2+ only. HSTS. No plaintext. |
| **Auth** | `Authorization: Bearer <access>` on every non-public route. Refresh via `POST /api/v1/auth/refresh` reading the `HttpOnly` cookie. Recipient routes live under `/r/...` (not `/api`) and use a link-scoped bearer. |
| **Content type** | `application/json` request + response. File upload: `multipart/form-data` to the evidence endpoint only. |
| **Identifiers** | UUIDv7 in payloads; a short human `reference` (e.g. `FKS-7QK2`) on jobs/statements for people to quote. |
| **Errors** | RFC 9457 `application/problem+json`: `{ type, title, status, code, detail, errors: [{ field, code, params }] }`. `code` is a **stable machine string** the client localizes (e.g. `job.transition_not_allowed`, `otp.too_many_attempts`, `authz.forbidden`, `job.stale`). No stack traces or internal detail to clients. |
| **Validation** | DRF serializers server-side; the client mirrors the same `code`s with `zod`. Unknown fields rejected. |
| **Pagination** | **Cursor-based**: `?cursor=<opaque>&limit=<n>` (`limit` default 25, max 100). Response: `{ data: [...], page: { next_cursor, prev_cursor } }`. No offset pagination (unstable under inserts). |
| **Filtering / sorting** | Only **allowlisted** params per endpoint (e.g. `?status=REQUESTED&vehicle_type=CANTER&sort=-created_at`). No arbitrary field filtering (injection + performance). |
| **Concurrency** | `GET` returns `ETag: "<job.version>"`. Job mutations require `If-Match`; mismatch → `412 { code: "job.stale" }`. |
| **Idempotency** | `Idempotency-Key: <uuid>` **required** on every `POST` that creates or transitions. Server stores `(actor, route, key) → response` for 24 h and replays exactly. Missing key on such a route → `400 { code: "idempotency.key_required" }`. |
| **Rate limits** | Per endpoint class (see [security-architecture.md](security-architecture.md) §1.7). `429` + `Retry-After` + `RateLimit-*` headers. |
| **Resource naming** | Plural nouns: `/jobs`, `/operators`, `/negotiation-threads`. Non-CRUD actions as **sub-resources**, never verbs on the collection: `POST /jobs/{id}/transitions`, `POST /jobs/{id}/custody-events`, `POST /verification-records/{id}/decision`. |
| **Status codes** | `200` ok · `201` created · `202` accepted (async) · `204` no content · `400` validation · `401` unauthenticated · `403` authorized-but-forbidden · `404` not found / not visible · `409` conflict (race, duplicate) · `412` stale `If-Match` · `422` domain rule violated (e.g. transition not allowed) · `429` rate limited. |
| **Time** | All timestamps ISO-8601 UTC (`Z`). The client renders in `Africa/Nairobi`. |
| **Money** | Integer **KES minor units** in payloads (`amount_kes: 400000` = KSh 4,000). A `currency` field is always `"KES"` for the MVP. |
| **Localization** | The API returns `code`s + `params`, not prose, for anything user-visible; the client renders localized strings. Server-rendered text (SMS) uses the recipient's `locale`. See [localization.md](localization.md). |
| **Schema** | `drf-spectacular` generates OpenAPI 3.1 at `/api/v1/schema`; a Redoc/Swagger page in non-prod. The schema is a CI artifact and a contract test. |
| **Deprecation** | `Deprecation` + `Sunset` headers; changelog in `docs/`. |
| **CORS** | The PWA is same-origin in production (served from the same domain) → CORS effectively off; a tight allowlist in dev only. |

---

## 2. The single write path for job status

**No endpoint mutates `job.status` directly.** All lifecycle changes go through:

```
POST /api/v1/jobs/{id}/transitions
Headers: Authorization, Idempotency-Key, If-Match: "<version>"
Body: { "to": "PICKED_UP", "reason": "...", "context": { "otp": "4821", "evidence_ids": ["..."], ... } }
→ 200 { job }   |   422 { code: "job.transition_not_allowed" }   |   409 { code: "job.race" }   |   412 { code: "job.stale" }
```

The server routes it to `JobLifecycleService.transition(...)` (see
[job-state-machine.md](job-state-machine.md)). Custody sub-steps that don't
change status (arrival with no state change, re-issuing an OTP) use
`POST /api/v1/jobs/{id}/custody-events`.

---

## 3. Resource design per module

Selected endpoints — the shape, not every field. `[B]` business, `[O]` operator,
`[G]` group manager, `[A]` admin, `[R]` recipient link, `[P]` public.

### 3.1 Auth & profile

| Method & path | Who | Purpose |
|---|---|---|
| `POST /auth/otp/request` `{phone, purpose}` | [P] | Request an OTP (enumeration-safe, `202`) |
| `POST /auth/otp/verify` `{challenge_id, code}` | [P] | Verify → session (`200` + refresh cookie) |
| `POST /auth/refresh` | [P+cookie] | Rotate refresh, new access token |
| `POST /auth/logout` | any | Revoke session + refresh family |
| `GET /me` | any | Current identity, roles, profiles, `locale` |
| `PATCH /me` `{locale, display_name, ...}` | any | Update own profile |
| `GET /me/sessions` · `DELETE /me/sessions/{id}` | any | Device/session management |
| `POST /admin/mfa/enrol` · `POST /admin/mfa/confirm` `{code}` | [A] | TOTP enrolment |
| `POST /auth/step-up` `{code}` | [A] | Fresh TOTP for a sensitive action |

### 3.2 Business

| `POST /businesses` · `GET/PATCH /businesses/{id}` | [B] | Account |
| `GET/POST /businesses/{id}/locations` · `PATCH/DELETE /businesses/{id}/locations/{lid}` | [B] | Locations; `PATCH …/main` sets the single `MAIN` |
| `POST /businesses/{id}/verification` (multipart) | [B] | Submit business verification evidence |

### 3.3 Operators / Groups / Vehicles / Bases

| `POST /operators` · `GET/PATCH /operators/{id}` | [O] | Operator profile |
| `PUT /operators/{id}/availability` `{state}` | [O] | AVAILABLE/UNAVAILABLE (BUSY is system-set) |
| `GET/POST /operators/{id}/bases` · `GET/POST /operators/{id}/service-areas` | [O] | Bases / service areas |
| `POST /vehicles` · `GET/PATCH /vehicles/{id}` · `POST /vehicles/{id}/documents` (multipart) | [O][G] | Vehicle registry + docs |
| `POST /groups` · `GET/PATCH /groups/{id}` | [G] | Group profile |
| `GET/POST /groups/{id}/members` · `PATCH/DELETE /groups/{id}/members/{mid}` | [G] | Membership (OWNER/MANAGER/DRIVER) |
| `PUT /groups/{id}/assignment-mode` `{mode}` | [G] | MANAGER_ASSIGNS / DRIVER_ACCEPTS |

### 3.4 Verification (admin)

| `GET /admin/verification-records?state=SUBMITTED&subject_type=OPERATOR` | [A] | The queue |
| `POST /admin/verification-records/{id}/decision` `{action, reason?, set_expires_at?}` | [A] | START_REVIEW / REQUEST_INFO / APPROVE / REJECT (step-up to view HIGH-PII) |
| `GET /admin/verification-records/{id}` | [A] | Detail incl. evidence links |
| `GET /operators/{id}/verification` / `GET /vehicles/{id}/verification` | [O][G][A] | Own status (states only, not others' docs) |

### 3.5 Trust

| `GET /operators/{id}/trust` | [O][G][A] | Current level + ceiling + progress toward next |
| `GET /admin/trust-changes?status=PROPOSED` | [A] | Confirmation queue |
| `POST /admin/trust-changes/{id}/confirm` `{decision, note}` | [A] | Confirm / reject a proposal |
| `POST /admin/operators/{id}/restrict` `{reason}` / `.../remediation-exit` | [A] | Impose / lift Restricted (step-up) |

### 3.6 Jobs & discovery

| `POST /jobs` (DRAFT) · `GET/PATCH /jobs/{id}` | [B] | Create / edit a draft |
| `POST /jobs/{id}/transitions` `{to, reason?, context}` | [B][O][G][A] | **The** lifecycle endpoint (§2) |
| `GET /jobs?status=&role=business` | [B] | My jobs (active / completed / cancelled-failed) |
| `GET /jobs/discover?vehicle_type=&zone=&sort=` | [O][G] | Filtered discovery list (FR-J-6 hard filters applied server-side) |
| `GET /jobs/{id}/timeline` | [B][O][G][A] | Full `job_timeline` |
| `GET /jobs/{id}/custody` | [B][O][G][A] · [R] milestones only | The `chain_of_custody` view |
| `POST /jobs/{id}/custody-events` `{type, geo?, evidence_ids?}` | [O][G] | Non-status custody steps (re-issue OTP, in-transit check-in) |
| `POST /jobs/{id}/assignment` `{driver_profile_id, vehicle_id}` | [O][G][A] | Assign (also expressible via a `to: ASSIGNED` transition) |
| `POST /admin/jobs/{id}/interventions` `{action, reason}` | [A] | reassign / cancel / force-transition / contact — always `reason`, always audited |
| `POST /admin/jobs/{id}/high-value-approval` `{decision, conditions?}` | [A] | Approve/reject a HIGH/VERY_HIGH job |

### 3.7 Negotiation

| `GET /jobs/{id}/negotiation-threads` | [B] all · [O][G] own only | Threads (scoped read — the "sealed" rule) |
| `POST /jobs/{id}/negotiation-threads` `{}` | [O][G] | Open a thread (or auto-opened on first offer) |
| `GET /negotiation-threads/{tid}/entries` | scoped | Immutable history |
| `POST /negotiation-threads/{tid}/entries` `{type, amount_kes?, note?, in_response_to?}` | [B][O][G] | PROPOSE / COUNTER / ACCEPT / REJECT (rate-limited; `Idempotency-Key`) |

An `ACCEPT` that completes mutual agreement triggers, server-side, the
`CONFIRMED` (and optionally `ASSIGNED`) transition in one transaction.

### 3.8 Incidents & disputes

| `POST /jobs/{id}/incidents` `{type, description, severity?, evidence_ids?}` | [B][O][G][A] · [R] via `/r/...` | Open an incident |
| `GET /jobs/{id}/incidents` · `GET /incidents/{id}` | parties + [A] | List / detail |
| `POST /incidents/{id}/statements` `{text}` · `POST /incidents/{id}/evidence` (multipart) | parties | Append-only |
| `POST /incidents/{id}/amicable-proposal` `{outcome}` / `.../amicable-accept` | parties + [A] facilitates | Amicable-first |
| `POST /admin/disputes/{id}/resolution` `{outcome_code, rationale, commission_treatment, actions, routed_job_status}` | [A] (Platform Admin above STANDARD) | Binding resolution (step-up) |
| `POST /admin/incidents/{id}/escalate` `{reason, escalated_to}` | [A] | Escalation record |

### 3.9 Ratings

| `POST /jobs/{id}/ratings` `{ratee_kind, score, dimensions?, comment?}` | [B][O][G] | Only for `COMPLETED` jobs, within the window |
| `GET /operators/{id}/reputation` / `GET /groups/{id}/reputation` | [B][O][G][A] | Summary only (no PII) |

### 3.10 Commission & statements

| `GET /operators/{id}/commission-records` · `GET /groups/{id}/commission-records` | [O][G] own · [A] | Per-job records |
| `GET /commission-statements?payee=me` · `GET /commission-statements/{id}` | [O][G] own · [A] | Weekly statements + lines + eTIMS ref |
| `GET /commission-statements/{id}/invoice` | [O][G] own · [A] | The eTIMS-compliant invoice document (signed URL) |
| `POST /admin/commission-statements/{id}/settlement` `{amount_kes, method, payment_ref}` | [A] | Record a settlement (manual pilot default) |
| `POST /admin/commission-statements/{id}/adjustments` `{kind, amount_kes, reason, dispute_id?}` | [A] | Append an adjustment (step-up) |
| `POST /webhooks/mpesa/c2b` | [P + HMAC] | Optional paybill confirmation → `SettlementRecord(source=WEBHOOK)` |

### 3.11 Evidence

| `POST /evidence` (multipart: `file, purpose, linked_entity`) | authorized uploader | Returns `{ evidence_id, sha256, scan_status }` |
| `GET /evidence/{id}` | authorized viewer | `302` → short-TTL signed URL |
| `GET /evidence/{id}/raw` · `GET /evidence/{id}/thumb` | authorized viewer | Stream / thumbnail (no thumb for HIGH-PII) |

### 3.12 Notifications

| `GET /me/notifications?unread=true` · `POST /me/notifications/{id}/read` | any | In-app inbox (polled) |
| `PUT /me/notification-preferences` `{channel_prefs, quiet_hours}` | any | FR-NOTIF-5 |
| `POST /webhooks/sms/dlr` · `POST /webhooks/whatsapp/status` | [P + HMAC] | Delivery receipts → `delivery_receipt`, status updates, WhatsApp→SMS fallback |

### 3.13 Recipient link (not under `/api`)

| `GET /r/{token}` | [P] | Resolve → link-scoped session + scoped delivery view |
| `GET /r/session/status` | [R] | Poll status |
| `POST /r/session/otp` | [R] | Send the recipient OTP |
| `POST /r/session/confirm` `{name, otp, signature?, photo?}` | [R] | Confirm receipt → `DELIVERED` |
| `POST /r/session/incident` `{type, description, photos?}` | [R] | Raise an incident (rate-limited, no OTP) |

### 3.14 Admin: config, audit, dashboard, export

| `GET /admin/config` · `POST /admin/config` `{patch, rationale}` | [A] Platform Admin | Read / apply a versioned config change (step-up, rationale required) |
| `GET /admin/config/versions` · `GET /admin/config/versions/{v}` | [A] | Change history + snapshots |
| `GET /admin/audit?entity_type=&entity_id=&actor=&from=&to=` | [A] | Audit-log viewer (scoped for Operations Officer) |
| `GET /admin/audit/export` `{scope}` | [A] | Async export (audited) |
| `GET /admin/dashboard?range=` | [A] | Funnel + incident SLA + weekly metrics (from `metric_daily`) |
| `POST /admin/exports` `{scope}` · `GET /admin/exports/{id}` | [A] | Pilot CSV export (async → signed download) |
| `GET /healthz` · `GET /readyz` | [P] | Liveness / readiness |
| `GET /api/v1/reference` | any authed | Cached enums + config lookups (vehicle types, cargo categories, zones, value bands) for the client |

---

## 4. Idempotency & concurrency worked example

```
1. Client GETs /jobs/{id}          -> 200, ETag: "7"
2. Client POSTs /jobs/{id}/transitions  {to: IN_TRANSIT}
      Idempotency-Key: 9f...   If-Match: "7"
3a. Success -> 200 { job (version 8) }, and (actor, route, 9f...) -> that response cached 24h
3b. Client network drops, retries with the SAME Idempotency-Key
      -> server returns the cached 200 (version 8). No second transition.
3c. Meanwhile another actor advanced the job to version 8 first
      -> the client's If-Match "7" != 8 -> 412 { code: "job.stale" }; client refetches, re-decides.
```

---

## 5. What the API deliberately does not expose

- No endpoint to set `job.status` directly, set a trust level to an arbitrary
  value, edit a negotiation entry, edit an agreed price, edit an audit/custody
  row, or fetch a bucket URL.
- No "list all operators' documents" / cross-tenant list endpoints.
- No fare-collection / wallet / escrow endpoints (D-BIZ-6).
- No auto-assign / bidding endpoints (D-A-DISC-1).
- No recommended-price endpoint (D-NEG-4).
