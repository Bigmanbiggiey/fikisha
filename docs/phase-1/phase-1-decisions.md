# Phase 1 — Architecture Decision Records

Every significant architectural decision, in the format required by Phase 1 brief
§33. Each is labelled:

- **CONFIRMED** — fixed by Phase 0 (a founder decision) or an unavoidable
  consequence; recorded here for traceability, not re-litigated.
- **RECOMMENDED** — a Phase 1 technical choice; reversible by the founder / Phase 2
  team with the trade-offs stated.
- **OPEN** — still needs a founder answer, a commercial input, or a spike.
- **REQUIRES VALIDATION** — depends on qualified Kenyan legal/tax/insurance advice.

Assumptions are **not** silently turned into requirements (brief §33).

---

## ADR-001 — Modular monolith, not microservices

- **Status:** CONFIRMED (Phase 1 brief §7, §34 P15) / RECOMMENDED in detail.
- **Context:** Pilot scale (NFR-PERF-1); one small team; a bootstrapped budget;
  a job lifecycle + ledger with cross-cutting invariants.
- **Options:** (a) modular monolith; (b) a few services (jobs, payments, notify);
  (c) full microservices.
- **Chosen:** (a). One API app + one worker app, one PostgreSQL, internal
  **bounded modules** (Django apps) that talk via public service APIs and a
  **transactional outbox**.
- **Reason:** Distributed transactions across the state machine/ledger would be a
  large tax for no pilot benefit; a monolith is cheaper to build, deploy, and
  reason about; the outbox + narrow module facades keep a later extraction cheap.
- **Trade-offs:** One deploy unit; a runaway module can affect others (mitigated
  by isolated Celery queues + resource limits).
- **Consequences:** [architecture.md](architecture.md),
  [domain-architecture.md](domain-architecture.md).

## ADR-002 — Backend: Django + Django REST Framework

- **Status:** RECOMMENDED.
- **Context:** Requirements in [technology-stack.md](technology-stack.md) §1; the
  internal **admin surface** is a large slice of MVP scope; the state machine and
  ledger need strong transactions.
- **Options:** Django+DRF; Node/TypeScript (NestJS + Prisma); Rails; Laravel; Go.
- **Chosen:** Django + DRF.
- **Reason:** Django Admin covers much of the verification queue / config / audit
  viewer cheaply; a mature transactional ORM (`select_for_update`); first-class
  migrations; app→module mapping; large talent pool.
- **Trade-offs:** Not the same language as the PWA (no shared types); Python
  async is weaker (irrelevant at pilot scale).
- **Consequences:** If the founder prefers Node, the admin-surface build cost
  (weeks) moves into Phase 2 (TR-16). The other Phase 1 docs are framework-agnostic
  at the seam level.

## ADR-003 — Frontend: React + TypeScript + Vite + PWA

- **Status:** RECOMMENDED (PWA form factor is CONFIRMED — D-CLIENT-1).
- **Context:** Low-end Android, poor connectivity, camera, mobile-first,
  bilingual.
- **Options:** React+TS+Vite; SvelteKit; Preact.
- **Chosen:** React+TS+Vite with `vite-plugin-pwa`; `preact/compat` + a strict
  dependency budget as the first size lever; a **Svelte spike** as the
  contingency.
- **Reason:** Largest ecosystem/hiring pool; mature PWA + i18n tooling;
  manageable bundle with code-splitting.
- **Trade-offs:** Heavier runtime than Svelte/Preact on the lowest-end devices.
- **Consequences:** Device-lab test in Phase 2 iteration 1 (TR-4);
  [pwa-architecture.md](pwa-architecture.md) §8.

## ADR-004 — Row-level authorization: app-layer primary + PostgreSQL RLS second layer

- **Status:** RECOMMENDED (RLS adoption timing is OPEN).
- **Context:** IDOR/BOLA is a top risk (brief §25); one platform instance, many
  parties.
- **Options:** (a) app-layer scoping only; (b) app-layer + RLS on the highest-risk
  tables; (c) RLS everywhere.
- **Chosen:** (b) — app-layer scoping is primary and covered by the authorization
  test matrix; **RLS** on `job`, `negotiation_thread`, `negotiation_entry`,
  `evidence_object`, `verification_record` as defence-in-depth (a query that
  forgets the `WHERE` returns nothing).
- **Reason:** RLS everywhere adds friction to reporting/admin paths; the top-risk
  tables get the belt-and-braces.
- **Trade-offs:** RLS policies are a second place the ownership rule lives (kept
  minimal, generated from one definition where feasible).
- **Consequences:** OPEN — adopt RLS in Phase 2 iteration 1, or defer to the
  pre-pilot hardening pass. [database-design.md](database-design.md) §2.

## ADR-005 — Single authoritative job-state-machine service + DB trigger backstop

- **Status:** CONFIRMED (FR-J-3, NFR-INT-2, brief §10).
- **Context:** "No arbitrary API endpoint may mutate job status."
- **Options:** (a) a shared helper each endpoint calls; (b) one service function
  as the sole writer; (c) a third-party workflow engine.
- **Chosen:** (b) `JobLifecycleService.transition(...)` is the **only** writer of
  `job.status`; a `BEFORE UPDATE` DB trigger rejects illegal `(from,to)` pairs as
  a backstop.
- **Reason:** One place to enforce the allowed-transition table, guards,
  concurrency, side effects, audit, and the outbox atomically; the trigger stops
  a stray raw `UPDATE` from any source.
- **Trade-offs:** Every lifecycle path funnels through one function (by design).
- **Consequences:** [job-state-machine.md](job-state-machine.md).

## ADR-006 — Negotiation: per-(job × operator) thread with read scoping ("sealed")

- **Status:** RECOMMENDED. Resolves contradiction C-1.
- **Context:** FR-N-3 wants operators not to see rivals' offers; brief §11 warns
  against unnecessary "sealed thread" complexity.
- **Options:** (a) one shared negotiation log per job visible to all operators;
  (b) per-operator threads with an authorization `WHERE` scoping reads.
- **Chosen:** (b) — no encryption, no isolation infra; "sealed" = one policy rule
  + one `WHERE` clause.
- **Reason:** NFR-PRIV-6 (operators see only job-required data); preserving the
  two-sided negotiation the founder is digitising (visible rival offers →
  race-to-the-bottom the platform appears to orchestrate); competition-law
  prudence (legal-scope §8 — the platform must not facilitate operators observing
  each other's prices).
- **Trade-offs:** N threads per job instead of 1 (negligible at pilot scale).
- **Consequences:** [negotiation-architecture.md](negotiation-architecture.md).

## ADR-007 — Confirmation is one atomic transaction with a row lock

- **Status:** CONFIRMED (FR-N-6, NFR-INT-1).
- **Context:** Two operators could accept at once.
- **Chosen:** `NegotiationService.accept` takes `SELECT job FOR UPDATE`, checks
  `job.status ∈ {REQUESTED, NEGOTIATING}` and mutual acceptance, then calls the
  Lifecycle Service to CONFIRM in the **same** transaction (create `Agreement`,
  close winning thread, `SUPERSEDE` siblings). The loser gets `409`.
- **Reason:** Serialisability for a given job without `SERIALIZABLE` isolation.
- **Trade-offs:** A brief lock on the `job` row during confirm (microseconds).
- **Consequences:** [negotiation-architecture.md](negotiation-architecture.md) §3.3.

## ADR-008 — Idempotency keys + `If-Match` on all mutations

- **Status:** CONFIRMED (NFR-INT-6) / RECOMMENDED in detail.
- **Context:** PWA offline queue replays; flaky mobile networks; the confirm race.
- **Chosen:** `Idempotency-Key` header **required** on every creating/transitioning
  `POST`; `(actor, route, key) → response` stored 24 h and replayed exactly.
  `GET` returns `ETag: job.version`; job mutations require `If-Match` → `412` on
  mismatch.
- **Reason:** Safe retries; a stale client can't clobber.
- **Trade-offs:** An `idempotency_key` table + a client discipline to generate
  keys.
- **Consequences:** [api-architecture.md](api-architecture.md) §1, §4.

## ADR-009 — Unified `job_event` table; `ChainOfCustodyEntry` + `JobStatusEvent` become views

- **Status:** RECOMMENDED. Resolves contradiction C-2.
- **Context:** Phase 0 named three near-identical append-only concepts; brief §15
  wants one append-only history with a finer event vocabulary.
- **Options:** (a) three tables as conceptually listed; (b) one `job_event` table
  with a `category` + fine `type` + `custody` flag, exposed as views.
- **Chosen:** (b). `chain_of_custody`, `job_status_event`, `job_timeline` are
  **views** over one table. `NegotiationEntry` and `AuditLogEntry` stay separate
  (richer shape / platform-wide scope).
- **Reason:** Avoids three near-duplicate tables and the risk they diverge; they
  are written by the same transition transaction; the distinct **consumers** are
  preserved as views with their own access rules.
- **Trade-offs:** Consumers must use the right view; a wide-ish table.
- **Consequences:** This refines a **conceptual** Phase 0 model (explicitly the
  Phase 1 team's job) — it is **not** a change to a founder decision.
  [database-design.md](database-design.md) §4.7.

## ADR-010 — Commission: one implemented calculator (`FLAT_WITH_MIN_CAP`), a reserved registry

- **Status:** CONFIRMED by the Phase 1 brief §3. Resolves contradiction C-3.
- **Context:** D-BIZ-5 described a taper + intro ramp; brief §3 says flat 10% /
  KES 40 min / KES 5,000 cap and **do not** implement the taper/ramp, but keep it
  configurable.
- **Options:** (a) hard-code the flat rule; (b) a `CommissionCalculator` registry
  with `FLAT_WITH_MIN_CAP` implemented and `BANDED_TAPER` / `RAMPED`
  schema-reserved but not implemented.
- **Chosen:** (b).
- **Reason:** Satisfies "configurable later without rewriting the transaction
  system" while honouring "do not implement" — the state machine calls
  `compute(...)` and stores the `ResolvedCommission`, whatever the model.
- **Trade-offs:** A small unused registry seam.
- **Consequences:** [commission-ledger.md](commission-ledger.md) §2, §6. **Founder
  attention:** brief §3 supersedes the D-BIZ-5 taper/ramp for the MVP — confirm
  this is understood.

## ADR-011 — Sessions: opaque server-side, not stateless JWT

- **Status:** RECOMMENDED.
- **Context:** Need instant revocation (suspension, logout, refresh-reuse); a
  small deployment.
- **Options:** (a) opaque server-side sessions; (b) stateless JWT access +
  refresh; (c) JWT with a revocation list.
- **Chosen:** (a) — a `session` row; a short access token carrying only
  `session_id`; a rotating `HttpOnly` refresh cookie with reuse detection.
- **Reason:** Revocation is a `DELETE`, not key-rotation choreography; simpler to
  reason about at pilot scale; no signing-key management surface.
- **Trade-offs:** A DB lookup per request (cheap; cached).
- **Consequences:** [authentication-authorization.md](authentication-authorization.md) §1.

## ADR-012 — `DISPUTED → prior state` (RESUME) supported but OPEN

- **Status:** OPEN. Carries forward contradiction C-4 (Phase 0 job-lifecycle §2.3).
- **Context:** Phase 0 marks resume-from-dispute an open question, recommended
  admin-only.
- **Chosen (design):** the state machine **supports** a `RESUME` transition to
  `dispute.pre_dispute_status`, **gated to `PLATFORM_ADMIN`**, with paused timers
  resumed on elapsed-time compensation.
- **Reason:** Real operational need (breakdown fixed, replacement vehicle) without
  losing the job.
- **Open:** the founder must confirm the path is wanted for the MVP; if not, it is
  disabled by config and disputes only route to `COMPLETED / FAILED / CANCELLED`.
- **Consequences:** [job-state-machine.md](job-state-machine.md) §5.4.

## ADR-013 — Evidence uploads are API-mediated (not client pre-signed PUT) for the MVP

- **Status:** RECOMMENDED.
- **Context:** Data-protection posture (EXIF/GPS strip), deterministic hashing,
  malware scanning, low-end devices.
- **Options:** (a) API-mediated upload; (b) client pre-signed `PUT` + async
  validation.
- **Chosen:** (a).
- **Reason:** Server-side type sniffing, EXIF strip, re-encode, hashing, and
  quarantine are simpler and safer done inline; files are already small
  (client-compressed).
- **Trade-offs:** The API handles upload bytes (fine at pilot volume).
- **Consequences:** Revisit if field upload latency is a real problem (TR-4);
  [evidence-storage.md](evidence-storage.md) §3.

## ADR-014 — Envelope encryption for HIGH-PII objects and fields

- **Status:** CONFIRMED intent (NFR-SEC-4, D-SEC-2) / RECOMMENDED mechanism.
- **Chosen:** Bucket SSE for all objects; **plus** application AES-256-GCM
  envelope encryption (data key wrapped by a KMS master key) for `pii_class =
  HIGH` objects (ID/licence/good-conduct images) and columns (ID number,
  `payout_number`); HMAC blind index only where a lookup is required.
- **Reason:** Region choice / disk-image leak is not a full exposure; access is
  Verifier-only + step-up + logged.
- **Trade-offs:** Key management (KMS or a guarded secrets-store key on the
  smallest deployment — TR-17); decrypt happens in the API.
- **Consequences:** [evidence-storage.md](evidence-storage.md) §5,
  [security-architecture.md](security-architecture.md) §1.14.

## ADR-015 — Transactional outbox for async fan-out (no message broker)

- **Status:** RECOMMENDED (brief §27 — no event-driven arch for fashion).
- **Options:** (a) direct calls into the notification/metrics code from domain
  services; (b) a message broker (Kafka/RabbitMQ); (c) a DB `outbox_event` table
  + a publisher loop + Celery.
- **Chosen:** (c).
- **Reason:** Exactly-once *capture* (same txn as the state change), at-least-once
  delivery, no broker to run; a state change never rolls back because a
  notification failed; a later broker is additive.
- **Trade-offs:** A publisher loop to run and monitor (outbox-lag metric); handlers
  must be idempotent.
- **Consequences:** [events-and-background-jobs.md](events-and-background-jobs.md) §2.

## ADR-016 — Location: event-based evidence only, no continuous GPS

- **Status:** CONFIRMED (brief §16, NFR-PRIV-4).
- **Chosen:** A single `getCurrentPosition` reading at four custody moments (+ an
  optional prompted in-transit check-in for HIGH/VERY_HIGH); `NOT_CAPTURED` is a
  valid value; raw points coarsened to zone level after 12 months.
- **Reason:** Proportionate to the dispute-evidence need; avoids operator
  surveillance; minimises PII (legal-scope §7).
- **Consequences:** [chain-of-custody.md](chain-of-custody.md) §5.

## ADR-017 — Recipient link: hashed high-entropy token, link-scoped session, OTP-gated confirm

- **Status:** RECOMMENDED (D-RCP-1).
- **Chosen:** ≥128-bit token in the URL; stored as `token_hash` + an HMAC
  `token_lookup`; `GET /r/<token>` exchanges it once for a short-lived
  link-scoped bearer bound to `job_id` + `allowed_actions`; confirm-receipt needs
  an OTP to the recipient's phone; incident creation allowed without OTP but
  rate-limited.
- **Reason:** A leaked/forwarded link cannot complete a delivery or read anything
  beyond the minimal doorstep view; a DB leak yields no working tokens.
- **Trade-offs:** A second token-hashing scheme (`token_lookup`) for O(1)
  resolution.
- **Consequences:** [recipient-access.md](recipient-access.md).

## ADR-018 — Admin surface: purpose-built PWA area + hardened Django Admin; founder is audited

- **Status:** CONFIRMED (D-ADM-1, FR-ADM-9, brief §20) / RECOMMENDED mechanism.
- **Chosen:** Operational workflows in a PWA admin area; config/audit/lookup
  maintenance in Django Admin; both through the **same authorization engine** and
  the **same audit + step-up rules**. `job.status` and append-only rows are not
  editable from Django Admin (no form; DB roles + trigger would reject anyway).
  **Every** admin action — including the founder's — writes
  `admin_intervention` + a hash-chained `audit_log_entry` with actor + reason +
  before/after. No silent superuser.
- **Consequences:** [admin-architecture.md](admin-architecture.md).

## ADR-019 — Deployment: single VPS + Docker Compose; managed Postgres preferred

- **Status:** RECOMMENDED (brief §30, §34 P15).
- **Chosen:** Dev/staging/prod each a `docker compose` stack; `api` + `worker` +
  `beat` from one image; Redis + reverse proxy (Caddy) on the host; **managed
  PostgreSQL with PITR** preferred (self-managed + disciplined backups as the
  fallback); S3-compatible object storage; GitHub Actions CI/CD over SSH.
- **Reason:** Cheapest thing that meets NFR-AVAIL-2/3 with a rehearsed restore;
  no Kubernetes tax.
- **Trade-offs:** Single point of failure (TR-5) — accepted for the pilot.
- **Consequences:** [deployment-architecture.md](deployment-architecture.md).

## ADR-020 — Data residency drives region choice; app-encryption reduces the stakes

- **Status:** OPEN + REQUIRES VALIDATION (legal-scope §3.4).
- **Context:** Phase 0 prefers Kenya-region hosting; a low-cost acceptable-region
  managed Postgres may not exist.
- **Chosen (design):** choose the DB + object-storage region for residency first;
  self-managed Postgres in a Kenyan-region VPS as the fallback; HIGH-PII envelope
  encryption so region is not the only control; a full processor register + DPAs.
- **Open:** the actual provider/region, pending the founder's budget and the
  **DPIA**.
- **Consequences:** [deployment-architecture.md](deployment-architecture.md) §7,
  TR-3.

---

## Open technical decisions (need a founder answer, a commercial input, or a spike)

| ID | Decision | Recommendation | Needs |
|----|----------|----------------|-------|
| OD-1 | Backend framework — Django vs Node | **Django + DRF** (ADR-002) | Founder confirmation at Phase 1 review |
| OD-2 | Frontend — React vs a lighter Svelte/Preact | **React+TS+Vite**; Svelte spike as contingency | A device-perf spike in Phase 2 iteration 1 |
| OD-3 | Hosting provider + region | Residency-first; managed Postgres if affordable in-region, else self-managed | Founder budget + **DPIA** (REQUIRES VALIDATION) |
| OD-4 | SMS provider (and a second for failover) | **Africa's Talking** primary; a second behind the same interface | Commercial terms |
| OD-5 | WhatsApp BSP | An authorised BSP (Africa's Talking / 360dialog / Twilio) | BSP onboarding + Meta business verification (lead time — TR-2); **cross-border transfer basis** REQUIRES VALIDATION |
| OD-6 | Geo/distance provider | Commercial (Google/Mapbox) with heavy caching; OSRM self-host if weak/costly | Coverage + cost evaluation for Kitengela outskirts (TR-9) |
| OD-7 | eTIMS integration mode | Adapter + `MANUAL_REFERENCE` fallback to start | Tax advisor + KRA (REQUIRES VALIDATION — TR-1) |
| OD-8 | M-Pesa settlement: manual vs C2B webhook | **Manual recording** for pilot week 1; add the webhook if the paybill supports it | Paybill setup; PSP classification opinion (REQUIRES VALIDATION — TR-14) |
| OD-9 | Web Push inclusion | In-app inbox + SMS/WhatsApp for MVP; Web Push as SHOULD on Android | — |
| OD-10 | RLS adoption timing | Phase 2 iteration 1, or the pre-pilot hardening pass | Team capacity |
| OD-11 | `DISPUTED → RESUME` path enabled for the MVP? | Support it, gated to Platform Admin | **Founder decision** (ADR-012 / C-4) |
| OD-12 | Business multi-user in the pilot? | Single `OWNER` per business; table present for later | Founder preference (FR-A-6) |
| OD-13 | Managed KMS vs a guarded secrets-store key for envelope encryption | Managed KMS if budget allows; documented rotation either way | Budget / compliance (TR-17) |
| OD-14 | Same-origin (`/api` on the PWA host) vs split `api.` subdomain | **Same origin** (CORS off, simpler) | Ops preference |

---

## REQUIRES VALIDATION items surfaced or reinforced by Phase 1

(All originate in `docs/phase-0/legal-scope.md`; Phase 1 isolates each behind
config or an adapter so **no assumption is hard-coded**.)

| Item | Where it lives in the architecture (isolated, not assumed) |
|------|-----------------------------------------------------------|
| Platform legal characterisation (neutral intermediary) | The whole design assumes it (no fare holding, no custody, no price-setting); a contrary opinion would change the ToS/Operator Agreement, not the code |
| NTSA Transport Network Company licence applicability to a goods platform | No code dependency; an operational/licensing matter |
| NTSA commercial-service-vehicle operator obligations per vehicle class | `verification_requirements` config + the `HEAVY_CLASS_COMPLIANCE` domain — the validated list is applied by configuration |
| Which driving-licence classes / endorsements per vehicle class | `LICENCE` verification config (class-vs-vehicle check) |
| Certificate of Good Conduct legal necessity | Already required by D-TRU-7; a `GOOD_CONDUCT` domain |
| Data-protection: ODPC registration, DPIA, lawful basis, consent wording, retention periods, cross-border transfer basis | Retention periods are **config** (`retention_windows`); consent/notice are **content**; the processor register + DPAs are documents; **DPIA + ODPC registration gate pilot go-live** |
| WhatsApp/Meta US cross-border transfer basis | The DPA + Privacy Notice + recipient short terms; the WhatsApp adapter can be disabled by config |
| Recipient no-account link processing of a non-user's data | Recipient short terms on the link; minimal scope + expiry in the design |
| Tax: VAT registration timing, eTIMS mode, WHT on payees | `EtimsService` adapter + `MANUAL_REFERENCE` fallback; a VAT line toggle on the invoice template |
| CBK PSP licensing avoided only if the platform never holds the fare | Enforced by the **absence** of any wallet/escrow/fare table (database-design §7); manual settlement in the pilot |
| Consumer Protection Act limits on liability-exclusion wording | ToS content, not code |
| Insurance: operator statutory cover + goods-in-transit/carrier cover for higher bands; no platform "cover" | Verified as documents (`VEHICLE`, `HEAVY_CLASS_COMPLIANCE`, `DOCUMENT` domains); the platform underwrites nothing |
| Platform-worker / "dependent contractor" Bill | Operator Agreement content; the product already avoids employment indicia (no price-setting, self-toggle availability) |
| Dangerous/hazardous goods | Excluded by the `CargoNotProhibited` guard + config prohibited set |
