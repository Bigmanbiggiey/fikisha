# Security Architecture

Phase 0 makes security, privacy, authorization, and auditability **first-class
MUST requirements** (`D-SEC-1/2/3`, `NFR-SEC-*`, `NFR-AUD-*`, `NFR-PRIV-*`).
This document is the security control set plus threat models for the most
sensitive workflows (brief §25).

Companion documents: [authentication-authorization.md](authentication-authorization.md),
[evidence-storage.md](evidence-storage.md), [recipient-access.md](recipient-access.md),
[commission-ledger.md](commission-ledger.md).

---

## 1. Control set (mapped to the brief §25 checklist)

| # | Area | Control |
|---|------|---------|
| 1 | **Authentication** | Phone + OTP (hashed, 5-min TTL, 5-attempt lockout, rate-limited, enumeration-safe). Admin: **+ mandatory TOTP MFA**, ≤ 8 h sessions, step-up for sensitive actions. Recipient: link-scoped bearer + per-job OTP. |
| 2 | **Authorization** | One `authorize(actor, action, resource)` engine; **default deny**; RBAC + ABAC; object-level checks on every id-bearing endpoint; admin permissions from `platform_config.role_permissions`. Covered by an authorization test matrix. |
| 3 | **Session security** | Access token ~15 min, **in memory only**; refresh token `HttpOnly; Secure; SameSite=Strict`, rotated every use, **reuse → family revoke**; server-side sessions → instant revocation; device/session list. |
| 4 | **CSRF** | Bearer-header API not CSRF-exposed; refresh endpoint checks `SameSite=Strict` cookie + `Origin`/`Sec-Fetch-Site` allowlist. |
| 5 | **XSS** | Strict CSP (`default-src 'self'`; no inline script; nonce/hash for the few needed; `connect-src` = API + tile host; `img-src 'self' data: <tiles>`); React auto-escaping; no `dangerouslySetInnerHTML`; token never in `localStorage`; `Trusted Types` where supported. |
| 6 | **Injection** | Parameterised ORM/queries everywhere; no string-built SQL; input validation (DRF serializers + `zod` on the client mirroring the same codes); output encoding; allowlisted query params (no arbitrary field filtering). |
| 7 | **Rate limiting** | Redis token buckets per endpoint class: auth/OTP (tight, **fail closed**), negotiation entries, evidence upload, recipient-link resolve/incident, general API. `429 + Retry-After`. |
| 8 | **OTP abuse** | Per-phone + per-IP request limits; per-challenge verify limits; exponential backoff on resend; hashed codes; single-use; alert on OTP-request bursts. |
| 9 | **Brute force** | Account soft-lock + alert after N failed auths; recipient `/r/` 404-storm alert; CAPTCHA is **not** used for the pilot (low volume, known network) but is a documented fallback. |
| 10 | **IDOR / BOLA** | UUIDv7 ids (non-sequential); mandatory object-level checks; **PostgreSQL RLS** as a second layer on `job`, `negotiation_thread`, `negotiation_entry`, `evidence_object`, `verification_record` (RECOMMENDED — ADR-004). |
| 11 | **Recipient-link attacks** | Full threat model in [recipient-access.md](recipient-access.md) §5. |
| 12 | **File upload** | API-mediated; magic-byte sniffing; size + type allowlist per `purpose`; image re-encode + **EXIF/GPS strip**; ClamAV scan for non-images with quarantine; private bucket; signed short-TTL URLs only. |
| 13 | **Malware** | ClamAV in a worker; `scan_status` gate; infected → delete + alert; images neutralised by re-encode. |
| 14 | **Sensitive-data encryption** | TLS in transit; bucket SSE at rest; **application envelope encryption (AES-256-GCM, KMS-wrapped)** for HIGH-PII objects **and** fields (ID number, `payout_number`); blind index (HMAC) only where lookup is required. |
| 15 | **Secrets management** | All secrets in a secrets manager / Docker secrets / KMS, injected as env at runtime; **never in VCS**; separate per environment; rotation runbook; `.env.example` only in the repo; pre-commit secret scanning + CI secret scanning. |
| 16 | **Audit logs** | Immutable, append-only, **hash-chained** (`prev_hash`/`row_hash`), DB role has no `UPDATE`/`DELETE`; monthly partitions; nightly chain verification; optional daily export to write-once storage. |
| 17 | **Admin MFA** | TOTP mandatory; enrolment forced on first login; backup codes hashed; step-up re-auth for config change, suspension, dispute resolution, high-value approval, HIGH-PII view. |
| 18 | **Database security** | Least-privilege DB roles: `app_rw` (SELECT/INSERT + UPDATE/DELETE only where the domain allows; **no** UPDATE/DELETE on append-only tables), `app_ddl` (migrations, separate credential, used only by CI/deploy), `app_ro` (read replica / reporting). Row-level checks + RLS. Network: DB only reachable from the app/worker subnet; no public IP. Backups encrypted. |
| 19 | **API security** | TLS-only; auth on every non-public route; input validation; idempotency; concurrency via `If-Match`; documented rate limits; `problem+json` errors with stable codes (no stack traces / internal detail to clients); OpenAPI schema kept in sync. |
| 20 | **Abuse prevention** | Negotiation anti-spam; recipient-link rate limits; cancellation-flag detection (D-DIS-3); bad-faith-report tracking; per-phone link auto-revoke on abuse. |
| 21 | **Account takeover** | Phone-OTP + (admin) MFA; refresh-token reuse detection; new-device / new-location login notification; session revocation UI; SIM-swap risk noted (see §3.1). |
| 22 | **Privilege escalation** | Role changes Platform-Admin-only + step-up + audited; `role_permissions` versioned; no client-trusted role claims; the state machine + DB trigger prevent forging a job into a privileged state. |
| 23 | **Replay attacks** | `Idempotency-Key` on all creating/transitioning POSTs (dedupe table, 24 h); OTPs and step-up nonces single-use; webhook events deduped by provider event id. |
| 24 | **Webhook verification** | HMAC/signature check + IP allowlist where published + shared secret; reject unsigned; idempotent by provider event id; fast-ack then enqueue; never trust webhook body for authorization decisions beyond what it asserts about its own delivery. |
| 25 | **Payment / statement integrity** | Commission records **immutable** + config-version-pinned; statements & lines append-only; adjustments are new admin-signed rows; settlement records reference a payment ref; M-Pesa C2B webhook signature-verified; the platform **holds no fare** so there is no balance to steal. See [commission-ledger.md](commission-ledger.md) §7. |

---

## 2. Trust boundaries & network posture

(See [system-context.md](system-context.md) §4.) Summary:

- **Edge** (Caddy): TLS termination, HSTS, security headers, request-size limits,
  webhook IP allowlist, basic bad-bot / flood shedding.
- **App/worker subnet**: no inbound except from the edge; outbound to providers
  over TLS.
- **Data subnet**: PostgreSQL, Redis, object storage, KMS — **no public IP**,
  reachable only from the app/worker subnet.
- **Secrets**: KMS + secrets manager; app reads at boot / on demand; never
  written to disk or logs.
- **Backups**: encrypted; stored off the primary host; restore tested.

---

## 3. Threat models — sensitive workflows

### 3.1 OTP login

| Threat | Mitigation |
|--------|-----------|
| Code brute force | 6 digits + 5 attempts + 5-min TTL + per-challenge & per-IP rate limit → ~vanishing success probability; lockout + alert |
| OTP flooding (cost + nuisance) | per-phone request limit (1/30 s, 5/h), per-IP limit, backoff; monitor SMS spend per phone; block a phone that trips it |
| Phone-number enumeration | `request` always returns `202` with a challenge id; timing kept uniform |
| Interception (SIM swap, SS7, shoulder-surf) | Accepted residual risk for the pilot's user base; **admin accounts get TOTP** so an admin takeover needs both factors; a **new-device login notification** to the existing session/phone gives the user a chance to react; sensitive user actions (change payout number) require a fresh OTP (step-up) |
| Replaying a verified OTP | single-use (`consumed_at`); the resulting session is what carries forward |

### 3.2 Job state machine / IDOR

| Threat | Mitigation |
|--------|-----------|
| Forcing a job into a state to skip a control (e.g. straight to `PICKED_UP` without the pickup OTP) | `ALLOWED_TRANSITIONS` table + per-transition guards; **no endpoint writes `job.status` directly**; DB `BEFORE UPDATE` trigger rejects illegal `(from,to)` pairs; guards re-checked at transition time |
| Acting on another party's job | object-level ownership check on every id-bearing endpoint; RLS second layer; UUIDv7 ids |
| Race to branch a job | `SELECT job FOR UPDATE` + `version` check; idempotency keys |
| Replaying a captured "confirm delivery" request | `Idempotency-Key` + single-use OTP + the guard rejecting a second `DELIVERED` |
| Operator self-confirming pickup | the OTP goes to the **pickup contact's** phone; the driver enters what the contact reads; a driver-only "attested" path exists **only** for Standard band and **caps** the job |

### 3.3 Recipient link

Full model in [recipient-access.md](recipient-access.md) §5. Key points: ≥128-bit
token, hashed at rest, minimal scoped view, OTP-gated confirm, expiry + revoke,
rate limits, `Referrer-Policy: no-referrer`, token scrubbed from logs.

### 3.4 Evidence access

| Threat | Mitigation |
|--------|-----------|
| Downloading someone's ID document | Verifier permission only + step-up + `evidence_access_log` row per fetch; never a bucket URL; envelope encryption so a storage leak isn't a plaintext leak |
| Enumerating objects | UUIDv7 keys; access always via the authorizing API; no list endpoint that crosses ownership |
| Swapping a file after the fact | `sha256` stored on the referencing domain row + the object row; weekly sample re-hash; bucket versioning |
| Malware via an uploaded "insurance PDF" | ClamAV quarantine gate; images re-encoded |
| Location leak via photo EXIF | EXIF/GPS stripped on ingest |

### 3.5 Commission statement integrity

| Threat | Mitigation |
|--------|-----------|
| An operator disputes a statement claiming a job was miscounted | Each `CommissionRecord` is immutable, links its `job_id`, and stores `config_version_id` + resolved `rate/min/cap/band`; the statement lists the exact records; recomputation is deterministic |
| An insider edits a statement to reduce/inflate an amount | Statement + line + record tables are append-only (DB role); corrections are `commission_adjustment` rows signed by an admin with a reason and audited; nightly reconciliation compares Σ(records+adjustments) to the statement total |
| A forged M-Pesa "paid" webhook marks a statement settled | Webhook HMAC verified + IP allowlist; `statement_settlement.source = WEBHOOK` vs `MANUAL`; amounts reconciled; the pilot's default is **manual settlement recording** anyway |
| Theft of held funds | **There are no held funds** — the platform never touches the fare (D-BIZ-6); the only money movement is the operator paying the platform its own commission by paybill |

### 3.6 Admin console

| Threat | Mitigation |
|--------|-----------|
| Compromised admin laptop | TOTP MFA; ≤ 8 h sessions; step-up for the dangerous actions; device/session list; all actions audited so blast radius is *visible*; ability to revoke an admin's role + sessions instantly |
| Malicious insider (incl. the founder) | **Every** admin action is hash-chained-audited with actor + reason + before/after — no silent superuser (FR-ADM-9, brief §34 P11); config changes are versioned with a rationale; trust level can only be confirmed/rejected/Restricted, never set arbitrarily; PII-doc views are individually logged |
| Privilege creep via `role_permissions` | that config is a guarded, versioned, step-up resource; changes are audited and reviewable in the weekly pilot governance meeting |

### 3.7 Negotiation

| Threat | Mitigation |
|--------|-----------|
| An operator scraping rivals' offers | per-thread read scoping (the "sealed thread") — see [negotiation-architecture.md](negotiation-architecture.md) §1/§5 |
| Tampering with the agreed price after confirmation | `agreement` table append-only + `U(job_id)`; frozen column never rewritten; audit corroboration |
| Offer spam | per-`(actor, thread)` rate limit |
| Confirm race exploiting a check-then-act gap | job row lock + `NoRacingConfirm` guard |

---

## 4. Audit integrity (NFR-AUD-1..6)

- **What is audited**: every state-changing action by every actor, including
  automated scheduler transitions and the founder. Reads are **not** audited
  except HIGH-PII document access (`evidence_access_log`) and audit-log export.
- **Where**: `audit_log_entry`, written **synchronously in the same transaction**
  as the change (so it cannot be lost and cannot describe a change that rolled
  back).
- **Immutability**:
  - Application: no update/delete path.
  - Database: `app_rw` has `SELECT, INSERT` only on `audit_log_entry`.
  - **Hash chain**: `row_hash = SHA-256(seq ‖ prev_hash ‖ canonical_json(payload))`;
    `prev_hash` = previous row's `row_hash`. `seq` from a dedicated sequence.
  - **Nightly verifier**: walks the chain, flags any break; the daily audit
    export to write-once storage (e.g. object-lock bucket) is the tamper-evident
    off-box copy.
- **Content minimisation**: `before`/`after` JSONB have HIGH-PII fields
  **redacted/masked** — the audit records *that* a payout number changed and by
  whom, not the number (NFR-OBS-1, NFR-PRIV-1). Timestamps UTC, server-authoritative
  (NFR-AUD-4); NTP on all hosts (NFR-AUD-6).
- **Export** (NFR-AUD-5): per-job or per-account audit + timeline export, admin
  only, itself audited.

---

## 5. Privacy controls (NFR-PRIV-1..7, legal-scope alignment)

| Requirement | Implementation |
|-------------|----------------|
| Data minimisation | analytics/exports use a minimal-PII projection (`analytics_event.dims` has zone/band/vehicle_type/role, **no names/phones**); logs scrub PII |
| Configurable retention windows | `platform_config.retention_windows`; daily sweeps for evidence, raw geo coarsening, link expiry, and (per validated policy) account data; **legal hold** flag skips a sweep |
| Lawful basis / privacy notice / consent | **REQUIRES VALIDATION** (Data Protection Act 2019 / DPIA — legal-scope §3.4); the product surfaces a consent step at onboarding and a privacy notice; the recipient short terms cover the non-user case; the architecture does not hard-code a basis |
| Location only at custody events, only with permission | the PWA requests geolocation lazily per custody action; `NOT_CAPTURED` is valid; raw points coarsened after 12 months |
| Data-subject requests (access/correct/delete) | `DSAR` tooling (SHOULD): an admin can export a subject's data and action a deletion consistent with the validated legal position |
| Role-based visibility | businesses see operator reputation status only; operators see only job-required data; recipients see only their delivery |
| Processor register | maintained for SMS, WhatsApp/Meta, geo, tiles, error tracking, hosting — feeds the DPAs (legal-scope §4 item 4) |

**REQUIRES VALIDATION (not hard-coded):** the exact retention periods, the
lawful-basis mapping, consent wording, cross-border transfer basis for
WhatsApp/Meta and any non-Kenya hosting, and whether business users / recipients
are "consumers" under the Consumer Protection Act. Each is behind config or
contract text, not code.

---

## 6. Secure SDLC (NFR-SEC-9/10, NFR-MNT-3)

- **CI gates**: dependency vulnerability scan (pip-audit / `safety`, npm audit),
  container image scan (Trivy), SAST (Bandit / Semgrep), secret scanning
  (gitleaks), lint, the full test suite including the **security test set**
  ([testing-strategy.md](testing-strategy.md) §"Security tests").
- **Pre-pilot**: a **threat-model review + a lightweight internal security
  review** before real operators and real goods (NFR-SEC-10); a third-party pen
  test is a **pre-scale** item (NFR-SEC-11).
- **Dependencies**: pinned; renovate/dependabot; a documented patch cadence.
- **Least privilege** everywhere: DB roles, storage IAM, provider API keys scoped
  to what's used.
- **Incident response**: a written runbook — breach detection, containment,
  **ODPC 72-hour notification** path (legal-scope §3.4), user notification,
  post-mortem.

---

## 7. Known accepted risks for the pilot

| Risk | Why accepted | Revisit trigger |
|------|--------------|-----------------|
| Single VPS (no HA) | Bootstrapped budget; NFR-AVAIL-1 ~99% is met with fast restore | any scaling decision |
| SIM-swap / SS7 on user OTP | User base is the founder's known network; admins have TOTP | wider public onboarding |
| No CAPTCHA | Low volume, known network; rate limits suffice | abuse observed |
| KMS may be a guarded secrets-store key rather than a full HSM-backed KMS on the smallest deployment | Cost; rotation plan documented | scale / compliance requirement |
| No CDN for private media | Pilot volume; signed short-TTL URLs suffice | latency complaints in the field |
