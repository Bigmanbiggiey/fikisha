# PHASE 1 — SUMMARY REPORT

**Project:** Fikisha — Local Logistics Marketplace
**Pilot:** Kitengela, Kajiado County + environs · **UI:** English + Swahili
**Phase:** 1 — Architecture & Technical Design
**Date:** 2026-09-08

---

## 1. Phase status

Phase 1 is **design only**. Every Phase 0 document under `docs/phase-0/` was read
in full; the architecture is built from those documents and does not restart
discovery, reinterpret the business model, invent features, or silently change a
confirmed founder decision. Contradictions found between documents are recorded
in [technical-risks.md](technical-risks.md) §1 and
[phase-1-decisions.md](phase-1-decisions.md), not resolved silently.

**No application code, migrations, dependencies, frontend/backend scaffold,
containers, databases, or deployment configuration were created.** The output is
26 documents in `docs/phase-1/`.

---

## 2. Documents created

`docs/phase-1/`:

| Document | Contents |
|----------|----------|
| `README.md` | Index + status-marker legend |
| `phase-1-summary.md` | This report |
| `phase-1-decisions.md` | 20 ADRs + a list of OPEN technical decisions + the REQUIRES-VALIDATION map |
| `technology-stack.md` | Stack evaluation → one recommended stack |
| `system-context.md` | Actors, external systems, trust boundaries (+ 2 diagrams) |
| `architecture.md` | Layered system architecture, component responsibilities, dependency rules, failure isolation (+ 3 diagrams) |
| `domain-architecture.md` | 19 bounded modules: responsibility, entities, invariants, interfaces, events (+ 2 diagrams) |
| `database-design.md` | Relational design: ~55 tables, keys, constraints, indexes + rationale, enums, soft-delete, tenancy, sensitive-data handling, the `job_event` consolidation |
| `job-state-machine.md` | The authoritative lifecycle: states, the full transition catalogue, guards, side effects, concurrency, idempotency, the DB backstop (+ 2 diagrams) |
| `negotiation-architecture.md` | Offer/counter/accept/decline/expiry, agreement-freeze, the confirm race, the "sealed thread" justification (+ 1 diagram) |
| `verification-architecture.md` | Per-domain records, per-domain lifecycles, expiry, derived eligibility (+ 1 diagram) |
| `trust-architecture.md` | VERIFIED ≠ TRUSTED, L1/L2/L3 evidence-based admin-confirmed progression, value bands, the high-value approval flow (+ 3 diagrams) |
| `chain-of-custody.md` | Append-only custody timeline, the mandatory pickup OTP, location-evidence privacy (+ 1 diagram) |
| `recipient-access.md` | The no-account link: token model, scoped view, actions, full threat model |
| `evidence-storage.md` | Private storage, API-mediated upload, envelope encryption, signed access, retention (+ 1 diagram) |
| `authentication-authorization.md` | Phone+OTP, admin MFA, sessions, the authorization engine, the permission matrix (+ 1 diagram) |
| `security-architecture.md` | The full control set mapped to the brief §25 checklist + threat models for 7 sensitive workflows + audit integrity + privacy controls |
| `api-architecture.md` | Conventions (versioning, errors, pagination, idempotency, concurrency) + per-module resource design |
| `notification-architecture.md` | Channel-agnostic service, in-app + SMS + WhatsApp, OTP SMS-primary, WhatsApp→SMS fallback, templates, cost accounting (+ 1 diagram) |
| `commission-ledger.md` | Immutable per-job records, the one implemented calculator, statements, settlement, adjustments, config-version pinning, eTIMS adapter (+ 2 diagrams) |
| `admin-architecture.md` | Queues + consoles, config management, dashboard, export, "the founder is not above the audit" |
| `events-and-background-jobs.md` | Sync vs async, the transactional outbox, the domain-event catalogue, the scheduled-job catalogue (+ 1 diagram) |
| `pwa-architecture.md` | Service worker + caching, the offline-safe vs server-confirmed line, camera, geolocation, sync engine, performance targets |
| `localization.md` | English + Swahili from day one: catalogs, keys, server templates, formatting, translation-quality plan |
| `observability.md` | Logging, error tracking, metrics, health checks, and the pilot-metric → source-event mapping (+ 1 diagram) |
| `testing-strategy.md` | Unit / integration / API / state-machine / negotiation / trust / custody / security / E2E, with the required scenarios and coverage gates |
| `deployment-architecture.md` | Dev/staging/prod, backups + rehearsed restore, migrations, data residency, bootstrapped cost (+ 1 diagram) |
| `technical-risks.md` | 7 contradictions + 18 technical risks + architecture assumptions that could be wrong |

Mermaid diagrams (brief §32): all 10 required diagrams are present — system
architecture, system context/trust boundaries, module relationships, job
lifecycle, negotiation flow, chain of custody, auth/authz, operator/group/vehicle,
commission flow, notification architecture, high-value approval flow (11
delivered).

---

## 3. Recommended technology stack

| Layer | Recommendation | Status |
|-------|----------------|--------|
| Client | **React + TypeScript + Vite + Tailwind + vite-plugin-pwa (Workbox)**; `react-i18next` (+ ICU), TanStack Query, `idb`, MapLibre or static maps | RECOMMENDED (PWA form factor CONFIRMED — D-CLIENT-1) |
| API / domain | **Django + Django REST Framework** (Python); modular monolith (Django apps as bounded modules); an in-house state-machine module; an authorization policy engine; a transactional outbox | RECOMMENDED |
| Async | **Celery** (worker + beat) on Redis | RECOMMENDED |
| Database | **PostgreSQL 16** (+ PostGIS if the host supports it) | RECOMMENDED (relational CONFIRMED) |
| Object storage | **S3-compatible** (managed regional bucket, or MinIO co-located) | RECOMMENDED; provider/region OPEN + REQUIRES VALIDATION |
| Cache / broker / locks | **Redis 7** | RECOMMENDED |
| Edge | **Caddy** (automatic TLS, HSTS, security headers) | RECOMMENDED |
| Runtime | **Docker + docker compose**, one host per environment | RECOMMENDED |
| CI/CD | **GitHub Actions** | RECOMMENDED |
| Adapters (vendors OPEN) | SMS gateway · WhatsApp BSP · geo/distance · eTIMS · M-Pesa paybill reconcile · error tracking · file scan | interface-first |

The example stack in the Phase 1 brief §6 was evaluated: **Django + DRF +
PostgreSQL + S3 + Redis/Celery + Docker + SMS/WhatsApp adapters is endorsed**;
React is chosen for the frontend (with a Svelte contingency for device
performance). Full evaluation and the "why not Node / why not microservices"
reasoning: [technology-stack.md](technology-stack.md),
[phase-1-decisions.md](phase-1-decisions.md) ADR-001/002/003.

---

## 4. Architecture summary

- **Modular monolith**: one API app + one worker app + one PostgreSQL; internal
  **bounded modules** that call each other's public service APIs and react to
  **domain events** via a **transactional outbox** (no message broker).
- **Layers**: PWA → Edge (Caddy) → thin API (DRF viewsets) → **authorization
  policy engine (default deny, RBAC + ABAC)** → application services → **domain
  services** → persistence. Nothing calls "up". External calls happen only in
  workers (or with a timeout + fallback for geocoding), never on a state
  transition's critical path.
- **One atomic transaction** per state change: side-effect rows + `job.status` +
  `job_event` (status + custody) + hash-chained `audit_log_entry` + `outbox_event`
  rows commit together; notifications/metrics/eTIMS happen after commit via the
  outbox.
- **Cross-cutting subsystems**: Notifications (channel-agnostic + adapters),
  Audit (append-only, hash-chained), Evidence (validate/hash/encrypt/sign),
  Configuration (versioned singleton), Pilot Metrics (event → `analytics_event` →
  nightly `metric_daily` → dashboard + CSV export — "no spreadsheets").
- **Failure isolation**: an SMS/WhatsApp/geo/eTIMS outage degrades gracefully;
  core job actions keep working; the outbox is durable in PostgreSQL so no event
  is lost.

---

## 5. Major domain boundaries

Identity & Access · Business · Operators · Operator Groups · Vehicles ·
Verification · Trust & Reputation · **Jobs** (requirements · discovery ·
**lifecycle** · assignment) · Negotiation · Custody · Recipients ·
Incidents & Disputes · Commission & Statements · Notifications · Evidence ·
Audit · Platform Configuration · Administration · Reporting & Pilot Metrics.

The **Job** is the aggregate root; the **assigned driver + vehicle are always a
specific person and vehicle** (solo or group); **value-band gating uses the
assigned driver's trust ceiling**, never the group's. Full per-module
responsibility / entities / invariants / interfaces / events:
[domain-architecture.md](domain-architecture.md).

---

## 6. Database strategy

- PostgreSQL 16. **Money = integer KES minor units** everywhere. **UTC**
  timestamps; client-reported times stored separately.
- **UUIDv7 primary keys** (non-guessable, time-ordered). FKs always declared;
  historical rows survive parent soft-delete.
- **Enums**: native `ENUM` for code-controlled sets (job status, verification
  state); **lookup tables** for admin-extensible sets (vehicle types, cargo
  categories, zones).
- **Append-only tables** (audit, `job_event`, negotiation entries, all
  commission/statement tables, trust changes, verification decisions, config
  versions, incident statements, evidence access log, analytics events):
  enforced by a DB role with `SELECT, INSERT` only **and** by the absence of
  update/delete service paths **and** by tests.
- **`job_event` consolidation** (ADR-009): one physical table; `chain_of_custody`,
  `job_status_event`, `job_timeline` are views — a permitted refinement of the
  *conceptual* Phase 0 model.
- **Optimistic locking** (`job.version`) + `SELECT job FOR UPDATE` for lifecycle
  serialisation; a `BEFORE UPDATE` trigger backstops illegal `(from,to)` pairs.
- **Sensitive data**: bucket SSE + **application envelope encryption** (AES-256-GCM,
  KMS-wrapped) for HIGH-PII objects and columns (ID numbers, `payout_number`);
  blind index only where lookup is required; access-logged.
- **Tenancy** = row-level authorization (one platform instance); **RLS** as a
  second layer on the highest-risk tables (RECOMMENDED, adoption timing OPEN).
- **Retention**: `retention_windows` config drives daily sweeps (evidence,
  geo-coarsening, link expiry); exact periods REQUIRES VALIDATION.

Full catalogue: [database-design.md](database-design.md).

---

## 7. Security strategy

- Security, privacy, authorization, auditability are **first-class MUSTs**
  (D-SEC-1/2/3). The full control set is mapped to the brief §25 checklist in
  [security-architecture.md](security-architecture.md) §1.
- **TLS-only**; strict CSP; secrets in a manager/KMS, never in VCS.
- **OTP** hashed, TTL'd, attempt-locked, rate-limited, enumeration-safe.
- **Admin MFA (TOTP) mandatory**; step-up re-auth for config change, suspension,
  dispute resolution, high-value approval, HIGH-PII document view.
- **IDOR/BOLA**: default-deny authorization engine + mandatory object-level
  checks + UUIDv7 ids + RLS second layer.
- **File upload**: API-mediated, magic-byte sniffing, size/type allowlist, image
  re-encode + EXIF/GPS strip, ClamAV for non-images with quarantine, private
  bucket, signed short-TTL URLs only.
- **Audit integrity**: append-only + DB role restriction + **hash-chained rows**
  + nightly chain verification + off-box write-once export. **No admin path
  bypasses the audit — including the founder's.**
- **Payment integrity**: commission records immutable + config-pinned; statements
  append-only; adjustments are new admin-signed rows; **the platform holds no
  fare**, so there is no balance to steal.
- Threat models for OTP login, the state machine/IDOR, the recipient link,
  evidence access, statement integrity, the admin console, and negotiation:
  [security-architecture.md](security-architecture.md) §3.
- Pre-pilot: a threat-model review + a lightweight internal security review
  (NFR-SEC-10); a third-party pen test is a pre-scale item.

---

## 8. Authentication / authorization strategy

- **Users**: phone + OTP; opaque server-side sessions; short access token in
  memory; rotating `HttpOnly` refresh cookie with **reuse detection** (family
  revoke).
- **Admins**: phone + OTP **+ mandatory TOTP**; ≤ 8 h sessions; step-up for
  sensitive actions; **provisioned internally**, never self-service.
- **Recipient**: no auth; a link-scoped bearer bound to `job_id` +
  `allowed_actions`; a per-job OTP gates confirm-receipt.
- **One `authorize(actor, action, resource)` engine**, default deny, RBAC + ABAC,
  called by every viewset **and** by services for object-level checks.
- **Admin permissions come from `platform_config.role_permissions`** — the
  pilot's **2 roles** (Platform Admin + Operations Officer) switch to the
  **4-role split** by **configuration**, no deploy (D-ADM-1, FR-ADM-8).
- The permission matrix (representative) is in
  [authentication-authorization.md](authentication-authorization.md) §3, and is
  a CI-enforced test matrix.

---

## 9. Job lifecycle architecture

- **14 states** exactly as Phase 0 (D-JOB-3). The allowed-transition set is a
  **single declared table**; a `(from,to)` not in it is rejected with **no side
  effects** (FR-J-3).
- **`JobLifecycleService.transition(...)` is the only writer of `job.status`**
  (brief §10). Algorithm: idempotency check → `SELECT job FOR UPDATE` →
  `If-Match` → allowed-transition lookup → initiator check → guards → side
  effects → status + `version` → status event + custody event → hash-chained
  audit → outbox rows → idempotency row — **one commit**.
- **Concurrency**: the job row lock serialises transitions; a job cannot branch.
  **Idempotency**: `Idempotency-Key` on every transitioning POST.
- **Guards** (reusable, individually tested): eligibility, trust-ceiling-covers-value
  (driver's ceiling for group jobs), high-value-approved, pickup-side-OTP-or-
  Standard-fallback, recipient-verification-present, within-window, etc.
- **DISPUTED** freezes the job and pauses the acceptance/post-completion timers;
  a `Resolution` routes it to `COMPLETED / FAILED / CANCELLED`, or (OPEN — ADR-012)
  **RESUME** to the recorded pre-dispute state, Platform-Admin only.
- A DB `BEFORE UPDATE` trigger is the backstop against any stray raw `UPDATE`.

Full catalogue + diagrams: [job-state-machine.md](job-state-machine.md).

---

## 10. Negotiation architecture

- Business **and** operator can propose / counter / accept / reject; entries are
  **immutable, append-only** (`INSERT, SELECT` DB role); a correction is a new
  entry.
- **Per-(job × operator) threads with read scoping** — the "sealed thread" —
  justified by NFR-PRIV-6 + preserving the two-sided negotiation + competition-law
  prudence; it is one policy rule + one `WHERE` clause, **not** heavyweight
  (ADR-006, resolves contradiction C-1).
- **CONFIRMED** happens in one atomic transaction under `SELECT job FOR UPDATE`:
  create the frozen `Agreement`, close the winning thread, `SUPERSEDE` siblings.
  Two racing ACCEPTs → first wins, second `409` (FR-N-6).
- Offers expire on a timer **without** changing `job.status` (FR-N-7). The MVP
  does not set/recommend prices or support in-flight re-negotiation.
- The `agreement` table role has no `UPDATE` — the frozen price is enforced by
  the database, not convention.

Full detail + diagram: [negotiation-architecture.md](negotiation-architecture.md).

---

## 11. Trust / verification architecture

- **Verification is per-domain, not a boolean** — `VerificationRecord` per
  (subject, domain: IDENTITY / LICENCE / GOOD_CONDUCT / VEHICLE /
  HEAVY_CLASS_COMPLIANCE / ASSOCIATION / BASE / DOCUMENT / HISTORY), each with its
  **own lifecycle** (document-expiry, point-in-time re-check, reviewed-on-change,
  continuously-computed). Derived eligibility functions are what other modules
  read.
- **Trust ≠ verification.** `TrustLevelState` (L0–L3 + Restricted) is backed by
  an **append-only `TrustLevelChange`** log. Progression is **system-proposed,
  admin-confirmed** (FR-T-3); an admin can only confirm/reject a proposal or
  impose Restricted with a reason — **there is no set-arbitrary-level action**
  (brief §14). Every change carries a `criteria_snapshot` + evidence links.
- **Value bands** (STANDARD ≤ 50k / ELEVATED ≤ 250k / HIGH ≤ 1M / VERY_HIGH) and
  the **KES 250,000 high-value threshold** are config-pinned per job. **Gating
  uses the assigned driver's ceiling**, never the group's; the group's standing
  is only a restrict/suspend lever.
- **High-value approval flow**: HIGH → Operations Officer or Platform Admin;
  VERY_HIGH → Platform Admin only; guarded at `CONFIRMED → ASSIGNED`; the
  platform underwrites nothing (records which cover is in place).
- Certificate of Good Conduct is **mandatory before L2/Elevated** (D-TRU-7).

Full detail + diagrams: [trust-architecture.md](trust-architecture.md),
[verification-architecture.md](verification-architecture.md).

---

## 12. Chain-of-custody architecture

- The custody trail is the **`is_custody = true` subset of `job_event`**
  (`chain_of_custody` view), append-only, strictly ordered by a per-job `seq`
  assigned inside the job's locked transaction.
- Each custody row records **who / when (server) / where (event-based single
  reading or `NOT_CAPTURED`) / what evidence (with SHA-256) / confirmation
  method**.
- **The mandatory pickup-side OTP** (D-CUS-2) is the key control: verified
  pickup-contact OTP or in-app business confirmation; a Standard-band-only
  operator-attested photo fallback that **caps the job at Standard**; **no
  fallback at Elevated+**.
- **Location privacy** (brief §16): event-based evidence only, **no continuous
  GPS**, lazy permission per action, raw points coarsened to zone level after 12
  months, never shown to recipients.
- Corrections are new `NOTE` rows referencing the original; nothing is edited or
  deleted.

Full detail + diagram: [chain-of-custody.md](chain-of-custody.md).

---

## 13. Commission architecture

- **MVP rule (brief §3): flat 10% of the agreed price, minimum KES 40, capped at
  KES 5,000 per completed job.** The taper and the introductory ramp from
  D-BIZ-5 are **not implemented** (brief §3 supersedes for the MVP — contradiction
  C-3, ADR-010), but the config schema + a calculator registry **reserve** them
  so the founder can switch later **without changing the transaction system**.
- A `commission_record` is written **once, on COMPLETED**, immutable, **pinned to
  the config version** in force at the job's confirmation — a later rate change is
  **never retroactive** (brief §21).
- **Corrections are new rows** (`commission_adjustment`, admin-signed, reasoned,
  step-up, audited) that net against a statement; the record is never mutated.
- **Weekly statement run** per payee (operator, or the **group** for a group
  job); an **eTIMS-compliant invoice** (adapter, with a `MANUAL_REFERENCE`
  fallback); settlement to a **merchant M-Pesa paybill** (**manual recording** in
  the pilot; optional signed C2B webhook).
- **The platform holds no fare, no escrow, no wallet** — there is no such table
  in the schema (D-BIZ-6). `PaymentReport` (the parties reporting the fare was
  paid directly) is informational only.

Full detail + diagrams: [commission-ledger.md](commission-ledger.md).

---

## 14. Notification architecture

- One channel-agnostic `NotificationService.send(...)`; business logic never
  talks to a provider.
- Channels: **in-app + SMS + WhatsApp**. **OTP is SMS-primary.** WhatsApp via a
  BSP with pre-approved templates; a **WhatsApp failure falls back to SMS**
  automatically.
- Per-channel `notification_message` rows with status from delivery-receipt
  webhooks; idempotent per `(recipient, template_key, dedupe_key)`; **cost per
  message recorded per job** for pilot economics.
- Notifications are triggered from the **outbox** after commit — a notification
  failure never rolls back a state change (NFR-AVAIL-4). Localized templates
  (`en`/`sw`) share the client's ICU placeholders.

Full detail + diagram: [notification-architecture.md](notification-architecture.md).

---

## 15. PWA strategy

- React + Vite + `vite-plugin-pwa`; small app shell (< 200 KB gz target),
  route-level code splitting, system fonts, lazy maps.
- Service worker: precache the shell; `NetworkFirst`/`StaleWhileRevalidate` for
  safe-to-stale reads (badged "as of HH:MM"); `NetworkOnly` for auth /
  transitions / OTP.
- **A hard line between offline-safe and server-confirmed** (brief §23):
  - *Offline-safe (queued, idempotent replay):* mark arrival AT_PICKUP /
    IN_TRANSIT / AT_DESTINATION, capture a custody photo, draft an incident, save
    a job draft.
  - *Server-confirmed only (blocked offline with a specific message):* login/OTP,
    **any negotiation action**, CONFIRMED/ASSIGNED, **pickup OTP (PICKED_UP)**,
    **delivery/recipient verification (DELIVERED)**, COMPLETED, ratings, any
    commission/verification/admin action.
- Sync engine drains the queue FIFO with the stored `Idempotency-Key` +
  `If-Match`; **conflicts are surfaced in a "Sync issues" tray, never
  auto-merged**.
- Camera via `<input capture>` + client-side downscale/compress + EXIF strip;
  geolocation requested lazily per custody action only.
- Web Push is SHOULD (Android) — nothing time-critical depends on it; SMS/WhatsApp
  + a polled in-app inbox carry the load.

Full detail: [pwa-architecture.md](pwa-architecture.md).

---

## 16. Testing strategy

Weighted toward the safety-critical invariants:

- **State-machine tests** over the full `JobStatus × JobStatus` cross-product:
  allowed pairs succeed and write exactly the right rows; forbidden pairs return
  `422` with **zero** side effects; failing guards return `409`/`422` with zero
  side effects.
- **Negotiation race tests**: two concurrent ACCEPTs → exactly one CONFIRMED;
  agreement-freeze / immutability.
- **Authorization matrix tests**: every cell of the permission matrix; IDOR/BOLA
  attempts; a new endpoint without a matrix entry fails CI.
- **Commission tests**: calculator boundaries (floor / cap / rounding),
  config-version pinning, dispute treatments, `CANCELLED/FAILED` → no record,
  group payee.
- **Trust / custody / recipient-link / security** suites as listed in
  [testing-strategy.md](testing-strategy.md).
- **E2E (Playwright)** — the three required scenarios (happy path; high-value +
  admin review; delivery problem → recipient incident → resolution) plus
  onboarding, group assignment, and offline-queue conflict.
- CI: lint → type-check → unit/integration/API → the required security &
  state-machine suites → schema contract fuzz → dep/image/SAST/secret scans →
  build → staging → E2E → manual gate → prod. Coverage is a **floor for the four
  critical modules** (~95–100%), pragmatic elsewhere.

---

## 17. Deployment strategy

- **Single VPS + Docker Compose** per environment (dev / staging / prod);
  `api` + `worker` + `beat` from one image; Redis + Caddy on the host.
- **Managed PostgreSQL with PITR** preferred (self-managed + WAL archiving as the
  fallback); S3-compatible object storage; region chosen for **data residency
  first** (OPEN + REQUIRES VALIDATION — DPIA).
- GitHub Actions CI/CD over SSH; additive migrations auto, non-additive via
  expand→migrate→contract or a short window; forward-only migrations; previous
  image kept for rollback.
- Backups: daily DB + WAL + object-storage versioning + a **write-once audit
  export**; a **rehearsed restore runbook** is a pre-go-live checklist item;
  RPO ≤ 24 h / RTO ≤ 8 h (founder to confirm).
- Explicitly **not**: Kubernetes, multi-region, autoscaling, a CDN for private
  media, a data warehouse.

Full detail + diagram + cost sketch:
[deployment-architecture.md](deployment-architecture.md).

---

## 18. Major technical risks

(Full register: [technical-risks.md](technical-risks.md) §2.)

| ID | Risk | Sev | Headline mitigation |
|----|------|-----|---------------------|
| TR-1 | eTIMS integration mode unknown | H | Adapter + `MANUAL_REFERENCE` fallback; tax advisor |
| TR-3 | No low-cost in-region managed Postgres may exist | H | Residency-first region choice; HIGH-PII envelope encryption; self-managed fallback; **DPIA** |
| TR-14 | Merchant paybill classification vs CBK PSP licensing | H | Platform holds no fare (no wallet/escrow tables); manual settlement; legal opinion |
| TR-15 | Retention periods / lawful basis / consent / cross-border basis all REQUIRES VALIDATION | H | All periods are config; consent/notice are content; **ODPC registration + DPIA gate go-live** |
| TR-2 | WhatsApp BSP onboarding + template approval lead time | M | Start week 1; automatic SMS fallback everywhere |
| TR-4 | Low-end-device / iOS PWA reliability | M | Device-lab test iteration 1; SMS carries critical steps; Svelte spike contingency |
| TR-5 | Single VPS = SPOF | M | Managed Postgres PITR + rehearsed restore; accepted for the pilot |
| TR-6 | SMS outage impacts OTP login | M | Second SMS provider behind the same interface; WhatsApp OTP option |
| TR-9 | Geo/distance coverage on Kitengela outskirts | M | Cache + ops manual override; OSRM self-host option; zones deferred anyway |
| TR-11 | Trust auto-proposal on thin data | M | Admin-confirm gate; `criteria_snapshot` review; repeat-pair monitoring |
| TR-17 | KMS may be a guarded key, not a managed HSM, on the smallest deployment | M | Documented rotation; upgrade on a compliance/scale trigger |

---

## 19. Open technical decisions

(Full list: [phase-1-decisions.md](phase-1-decisions.md) §"Open technical
decisions".)

| ID | Decision | Recommendation |
|----|----------|----------------|
| OD-1 | Backend: Django vs Node | **Django + DRF** |
| OD-2 | Frontend: React vs Svelte/Preact | **React**; Svelte spike as contingency |
| OD-3 | Hosting provider + region | Residency-first; managed Postgres if affordable; needs the **DPIA** |
| OD-4 / OD-5 | SMS provider (+ failover) / WhatsApp BSP | Africa's Talking primary; authorised BSP; commercial terms + Meta verification |
| OD-6 | Geo/distance provider | Commercial + caching, or self-host OSRM |
| OD-7 | eTIMS integration mode | Adapter + manual-reference fallback; tax advisor + KRA |
| OD-8 | M-Pesa settlement: manual vs C2B webhook | Manual for pilot week 1 |
| OD-9 | Web Push | In-app inbox + SMS/WhatsApp for MVP |
| OD-10 | RLS adoption timing | Phase 2 iteration 1 or pre-pilot hardening |
| **OD-11** | **`DISPUTED → RESUME` enabled for the MVP?** | **Support it, Platform-Admin-gated — founder decision needed** |
| OD-12 | Business multi-user in the pilot | Single `OWNER`; table present for later |
| OD-13 | Managed KMS vs guarded key | Managed KMS if budget allows |
| OD-14 | Same-origin vs `api.` subdomain | Same origin (CORS off) |

---

## 20. Phase 2 implementation sequence

Gated on: founder review of this set + the Phase 0 legal checklist
(`docs/phase-0/legal-scope.md` §9) progressing in parallel (incorporation, ODPC
registration + DPIA, NTSA query, Kajiado County permit, contract set, eTIMS,
insurance — **go-live is gated on these**).

1. **Foundations.** Repo + CI/CD + the three environments (compose). PWA shell
   (installable, i18n `en`/`sw`, offline indicator). Identity & Access: phone+OTP,
   admin TOTP, sessions, the **authorization policy engine** + the
   `role_permissions` map (2 pilot roles). **Audit subsystem** (append-only +
   hash chain). **Platform Configuration** (versioned singleton) + the config
   lookup tables. The **transactional outbox** + the publisher.
2. **The job state machine** as one authoritative module: the allowed-transition
   table, guards, the transition algorithm, the DB trigger backstop, `job_event`,
   the idempotency table — with the full state-machine test suite **before**
   anything else builds on it.
3. **Operator / Group / Vehicle / Base** registration + the **Verification**
   module (per-domain records, reviewer workflow, expiry sweeps, derived
   eligibility). **Business** + locations.
4. **Trust & Reputation** (levels, evidence-based admin-confirmed progression,
   value-band gating, the high-value approval queue, ratings, reputation
   summaries).
5. **Job creation + discovery** (FR-J-6 hard filters + ranking) + **Negotiation**
   (sealed threads, immutable entries, the atomic CONFIRM, offer expiry).
6. **Assignment** (solo and group — names a specific driver + vehicle) + the
   **Custody** module (arrival, the mandatory pickup OTP + Standard fallback,
   transit, destination, POD, event-based location, append-only rows) +
   **Evidence** (API-mediated upload, envelope encryption, signed access,
   retention).
7. **Recipients** (the no-account link: token model, scoped view, OTP-gated
   confirm, incident from a link) end-to-end with custody.
8. **Incidents & Disputes** (types, evidence + statements append-only,
   amicable-first, admin review + resolution, escalation, the DISPUTED freeze,
   commission hold/treatment) — including recipient-initiated.
9. **Commission & Statements** (accrual on COMPLETED, config-version pinning, the
   weekly run, the eTIMS adapter + manual fallback, settlement recording,
   adjustments) + the ledger reconciliation job.
10. **Notifications** end-to-end (in-app + SMS + WhatsApp via the BSP, templates
    `en`/`sw`, delivery receipts, WhatsApp→SMS fallback, cost accounting).
11. **Admin surface** (verification queue, job monitor + interventions, dispute
    console, high-value approvals, trust confirmations, account actions, config
    UI, audit viewer) + **Django Admin** hardening.
12. **Reporting & Pilot Metrics** (`analytics_event`, nightly `metric_daily`, the
    operational dashboard, the access-controlled CSV export).
13. **Scheduled jobs** (all beat sweeps) + **observability** (structured logs,
    error tracking, metrics, health checks, alerts) + the **security review** +
    the **restore drill**.
14. **Staging pilot dry-run** (the Kitengela seed dataset; 2–3 end-to-end test
    jobs across vehicle classes; a group job; a dispute) → fix → **go-live gate**.

Then **Phase 3 — run the Kitengela pilot** per `docs/phase-0/pilot-strategy.md`:
phased onboarding, weekly metric + governance reviews, config tuning, decision-log
updates.

---

## 21. Founder decisions required

Before Phase 2 build starts (or early in it):

1. **Confirm the recommended stack** — Django + DRF backend, React PWA (OD-1,
   OD-2). If Node is preferred, accept the admin-surface cost moving into Phase 2
   (TR-16).
2. **Acknowledge the commission clarification** — the MVP uses **flat 10% / KES
   40 min / KES 5,000 cap**; the **D-BIZ-5 taper and introductory ramp are not
   implemented** (Phase 1 brief §3 supersedes for the MVP; the config schema
   keeps them switchable later). — contradiction C-3.
3. **`DISPUTED → RESUME`** — enable the admin-only resume-to-pre-dispute-state
   path for the MVP? (OD-11 / contradiction C-4; Phase 0 left this OPEN.)
4. **Hosting region / provider** — approve a **residency-first** choice pending
   the DPIA; decide managed vs self-managed PostgreSQL against the pilot budget
   (OD-3, TR-3).
5. **Provider selection & budgets** — SMS (+ a failover provider), WhatsApp BSP,
   geo/distance; approve starting BSP onboarding immediately given the lead time
   (OD-4/5/6, TR-2).
6. **Zone breakdown** — still deferred (D-PIL-5); the architecture treats the
   pilot area as one zone until supplied (config, not a blocker).
7. **RPO/RTO** — confirm RPO ≤ 24 h / RTO ≤ 8 h is acceptable for the pilot
   (Phase 0 D-A-SCALE-1).
8. **Business multi-user** — single `OWNER` per business for the pilot? (OD-12.)
9. **Pilot kill / iterate / scale targets** — still open from Phase 0
   (pilot-strategy §6); needed before the pilot, not before Phase 2 build.

---

## 22. Legal / commercial dependencies

All originate in `docs/phase-0/legal-scope.md`. **Phase 1 hard-codes none of
them** — each is behind config, an adapter, or contract text
([phase-1-decisions.md](phase-1-decisions.md) §"REQUIRES VALIDATION"). The founder
is engaging a lawyer; these **gate pilot go-live**, not Phase 2 build:

- **Data protection**: ODPC registration (controller + processor), the **DPIA**
  (location + ID documents + trust profiling), a DPO/contact, the retention
  schedule (the periods the config will hold), a breach-response plan, DPAs with
  every processor (SMS, **WhatsApp BSP / Meta — US cross-border**, geo, hosting,
  error tracking), the lawful-basis map, consent wording, and the **recipient
  short terms**. — TR-15.
- **Platform characterisation** — a written opinion that "neutral intermediary /
  digital marketplace" holds for a goods platform (the whole design assumes it).
- **NTSA** — a formal query on Transport Network Company licence applicability to
  a goods platform; the validated **operator-side commercial-vehicle obligation
  list** to load into `verification_requirements`.
- **Commission collection** — a legal opinion + bank/PSP confirmation that a
  merchant paybill for the platform's **own** commission stays outside CBK PSP
  licensing (the design holds no fare regardless). — TR-14.
- **Tax** — VAT registration timing, the **eTIMS integration mode**, WHT on
  payees; the invoice template's VAT line. — TR-1.
- **Consumer Protection Act** — enforceable liability-exclusion wording for the
  ToS.
- **Insurance** — operator statutory cover + goods-in-transit / carrier's cover
  for the higher value bands (verified as documents); **the platform underwrites
  nothing**.
- **Contract set** — Terms of Service, Operator Agreement (+ a **Group Agreement**
  schedule), Privacy Notice, DPAs, Acceptable Use / Prohibited Goods, Dispute &
  Liability policy, Recipient short terms — all advocate-drafted.
- **Company + county** — the Kenyan private limited company + company KRA PIN +
  the **Kajiado County Single Business Permit** for the Kitengela premises.
- **Dangerous / hazardous goods** — excluded from the pilot (enforced by the
  `CargoNotProhibited` guard + config).

---

PHASE 1 — COMPLETE — AWAITING FOUNDER REVIEW

No application implementation has been started.
