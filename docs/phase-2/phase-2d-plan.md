# FIKISHA — Phase 2D — Jobs & Core Coordination Backend — ARCHITECTURE & PLAN

**Status:** **FOUNDER-APPROVED WITH AMENDMENT (2026-09-10)** — implementation
authorized per §19. Not merged; second Founder gate required before merge.
**Branch:** `feat/phase-2c-vehicles-verification` @ `e58e3aa` · working tree clean.

---

## 0. Founder Gate — DECISIONS (2026-09-10)

The Founder reviewed this plan and **approved it to proceed to implementation**,
with the decisions and the one required amendment below.

| Ref | Decision |
| --- | --- |
| §4 module layout, §5 schema | **APPROVED** (subject to the amendment). Do not modify Phase 2A–2C models or semantics. |
| **E-1 `RESUME_PRIOR`** | **APPROVED — NOT implemented in 2D.** Persist `pre_dispute_status` only. **No** resume endpoint / service / algorithm / implicit auto-resumption. The only dispute resolutions built are `DISPUTED → {COMPLETED, FAILED, CANCELLED}`. |
| **E-2 trust ceiling** | **APPROVED — ADR-2D-05 Option (b).** Conservative deterministic interim rule from approved verification facts + `config.value_bands[].min_trust_level`. **No** Trust score/level engine, ratings, stars, ranking, recommendation, or opaque scoring. Assigned-driver eligibility is the authoritative basis for assignment. HIGH/VERY_HIGH still require `high_value_approval`. Documented as **interim, pending the dedicated Trust phase**. |
| **E-3 SMS/WhatsApp provider** | **APPROVED.** Implement OTP generation + verification + challenge state + provider-neutral outbox events. **Do NOT** select/purchase/configure/wire any commercial SMS or WhatsApp provider. WhatsApp remains a channel, not the system of record. |
| **E-4 location storage** | **APPROVED.** Plain `DecimalField` lat/lng + `geo_state`. **No** PostGIS, **no** routing/distance optimization. Recorded as an **approved Phase 2D deviation** from the PostGIS-oriented Phase 1 schema (not "verbatim" — see §5, ADR-2D-10). |
| **Q-5 scheduled sweeps** | **APPROVED.** `request_expiry` and `DELIVERED → COMPLETED` auto-complete may be beat-wired (authoritative lifecycle behaviour). Post-completion-window close stays command-driven. **Every** scheduled job calls `JobLifecycleService.transition()` — it must not become a competing writer. |
| **Q-6 `CONFIRMED → ASSIGNED`** | **APPROVED.** Keep confirmation and assignment **separate** in 2D. Do **not** build the combined convenience path. |
| **Q-7 RLS** | **APPROVED — deferred to hardening.** Application `authorize()` is the primary control in 2D and must be comprehensively tested. Add the `SET LOCAL app.actor_id` seam so RLS can be added later without a schema redesign. |

### REQUIRED AMENDMENT — recipient access-link uniqueness

The plan's proposed partial-unique predicate
`UNIQUE(job_id) WHERE revoked_at IS NULL AND expires_at > now()` **must not be
implemented** — PostgreSQL cannot use `now()` (a non-`IMMUTABLE` expression) in a
partial-index predicate, and "active" is a request-time evaluation, not an index
condition.

**Approved replacement (supersedes §5 / §11 / ADR-2D-06 for `recipient_access_link`):**

- **`UNIQUE(job_id)`** — a plain, immutable uniqueness rule: **at most one
  recipient-link record per Job at a time.**
- Keep `expires_at` and `revoked_at` columns.
- **Request-time authorization** for a recipient token explicitly verifies, in
  order: (1) token resolves (via `token_lookup` HMAC) to a link row; (2)
  `link.job_id == requested job`; (3) `revoked_at IS NULL`; (4) `now() <
  expires_at`; (5) the requested action ∈ `allowed_actions`. Any failure →
  `403`/`410`, no data.
- **Replacement after expiry or on re-issue:** within a single transaction under
  `SELECT … FOR UPDATE` on the `job` row (and the existing link row if present),
  **explicitly set `revoked_at = now()` (+ `revoke_reason`) on the current link,
  then `DELETE` it** (so `UNIQUE(job_id)` allows the new insert) **or** — if an
  immutable history of links is wanted — move to an explicit
  `recipient_access_link` + `recipient_link_event` split with the unique on a
  `superseded_at IS NULL` immutable flag (no time expression). **2D takes the
  simpler path: one row per job, revoke-then-replace under lock.** Concurrent
  issuance is serialised by the job-row lock.
- Tests required (added to §13): valid unexpired link · expired link · revoked
  link · replacement after expiry · replacement after explicit revocation ·
  concurrent replacement attempts (job-row lock serialises; exactly one live
  link) · `token_lookup` · `token_hash` verification · wrong-job token · token
  reuse (after `used_at`) · action outside `allowed_actions` · expired/revoked
  link cannot access the Job. Fresh-DB migration test.

### Delivery-proof (and pickup-proof) — reconcile against the authoritative sources

Before implementing the proof service, the exact band-specific proof
requirements are reconciled **directly** against `docs/phase-0/trust-and-safety.md`,
`docs/phase-1/chain-of-custody.md §3–4`, `docs/phase-1/trust-architecture.md`
(D-TRU-5), and `docs/design-phase-2-user-flows.md §39/§44` — not from the
shorthand in this plan. Encode exactly; invent nothing; weaken nothing. (§10
carries the reconciled matrix; the proof service tests assert against the
authoritative combinations.)

---
**Authoritative sources reconciled:** `CLAUDE.md`, `docs/team-skills-policy.md`,
`docs/phase-0/` (job-lifecycle, trust-and-safety, pricing-and-negotiation,
users-and-roles, mvp-scope, decisions, decision-memo, business-model,
legal-scope, functional/non-functional requirements, domain-model),
`docs/phase-1/` (job-state-machine, database-design §4.6–4.11, §6.x,
negotiation-architecture, chain-of-custody, trust-architecture,
commission-ledger, recipient-access, admin-architecture, api-architecture,
security-architecture, events-and-background-jobs, phase-1-decisions),
`docs/phase-2/` (2A/2B/2C decisions + summaries), and the actual Phase 2A–2C
code.

> This document is the **pre-implementation architecture** the brief requires
> before "substantial implementation". It presents the proposed Job schema,
> lifecycle transition matrix, authorization matrix, negotiation / assignment /
> custody-proof / recipient / incident-dispute models, the API boundary, the
> migration plan, the test strategy, the ADRs, and the **identified ambiguities /
> escalations**. It changes no code and no approved decision.

---

## 1. Repository inventory (brief §3)

| # | Finding |
| --- | --- |
| 1 | Branch `feat/phase-2c-vehicles-verification`, commit `e58e3aa`, working tree **clean**. |
| 2–3 | No `jobs` app. **No partial Job implementation anywhere** (`grep` for `Job`/`job` hits only unrelated identity/outbox/config code). |
| 4 | Backend apps: `common · audit · outbox · platform_config · identity · storage · business · operators · groups · evidence · vehicles · verification · api · observability`. |
| 5 | Schema: Phase 2A–2C tables only (identity, audit hash-chain, outbox, config + versions, business/membership/location, operator profile/base/basemembership, group/groupmembership, zone, evidence_object + access_log, vehicle + vehicleclass, verification_record/decision/evidence). No job tables. |
| 6 | **API conventions** (`common/api.py`, `common/idempotency.py`): `OrgApiView` base — HTTP method → authz action, `required_action`, `get_authz_resource()`, `.actor(request)`, `paginated()`. RFC-9457 problem+json with `code`/`request_id`. Cursor pagination `{data, page:{next_cursor,prev_cursor}}`. `Idempotency-Key` via `idempotent(request, actor_id, run)` (24h cache, `409 idempotency_in_progress` on concurrent replay). No `If-Match` helper yet — 2D adds one. |
| 7 | **Service layer**: module `services.py` functions assert `in_atomic_block`, call `audit.record(...)` (asserts atomic; hash-chained) and `emit(...)` (transactional outbox; asserts atomic) in the same transaction. `SystemActor` class pattern for scheduled work. Deterministic. |
| 8 | **Authz**: central `authorize(actor, action, resource) -> Decision`, default-deny, `@policy` decorator, exact-then-longest-wildcard resolution. Per-app `policies.py` registers `@policy` handlers; per-app `authz.py` has `can_view` / `can_manage` helpers reused across apps. `role_permissions` in `platform_config.defaults` grant admin actions. |
| 9 | **Audit**: `audit.record()` — append-only (`AppendOnlyModel` + service refusal + Postgres BEFORE UPDATE/DELETE triggers), hash-chained (`prev_hash`/`row_hash`), `ActorRole` enum incl. `USER`. |
| 10 | **Outbox**: `emit()` writes `outbox_event(aggregate, aggregate_id, type, payload)` in-txn; `drain_outbox` Celery task publishes with retry + dead-letter. No provider wired. |
| 11 | **Config**: versioned singleton + append-only version history; `ConfigService.apply_change` audits + emits. **Already carries** `commission` (`FLAT_WITH_MIN_CAP` 10% / min 4000 / cap 500000 minor units), `value_bands` (STANDARD ≤ 5,000,000 / ELEVATED ≤ 25,000,000 / HIGH ≤ 100,000,000 / VERY_HIGH ∞ minor units; `min_trust_level` L1–L3), `high_value_threshold_kes` = 25,000,000 (KES 250,000), `timeouts` (`request_expiry_hours` 24, `delivery_acceptance` {standard 24h, high 48h}), and negotiation/offer-expiry keys. **No new config keys needed for the core lifecycle** — 2D reads what exists. |
| 12 | **Verification / eligibility** (Phase 2C): `verification.services.subject_meets(subject, domains)` / `eligibility(subject)` / `requirements_status(subject)` — **facts only, no trust**. `verification.requirements.required_domains_for_subject(subject)`. `VehicleClass.heavy` config flag. `Vehicle` control (`owner_operator` XOR `owner_group`), class, `is_active` (`status == ACTIVE`). **There is no Trust module yet** — see §14 / Escalation E-2. |
| 13 | **Tests**: ~1300 backend test functions across 2A–2C; ruff/format/mypy(pragmatic)/migrations clean; 87% coverage on 2C. Frontend: 81 vitest, unaffected by 2D. |
| 14 | No partial Job code. Confirmed by search. |

---

## 2. Phase 2D scope (what this phase builds / does not build)

### In scope

A new **`fikisha.jobs`** app (+ a thin **`fikisha.negotiation`**, **`fikisha.custody`**,
**`fikisha.incidents`** split — see §4) providing:

- The **Job aggregate** and its supporting rows (schema per `database-design.md
  §4.6–4.11`, verbatim).
- **`JobLifecycleService.transition()`** — the single authoritative writer of
  `job.status`, with the full `ALLOWED_TRANSITIONS` table, guards, side effects,
  `job_event`, hash-chained audit, transactional outbox, `Idempotency-Key`,
  `If-Match` (`job.version`), and `SELECT … FOR UPDATE` — atomic.
- A Postgres `BEFORE UPDATE OF status ON job` **trigger backstop** +
  `allowed_job_transition` helper table seeded from the same source.
- **Negotiation** — sealed per-`(job × operator/group)` threads, append-only
  `negotiation_entry`, agreement freeze.
- **Assignment + eligibility** — server-side driver/vehicle eligibility
  (verification + value-band/trust + heavy-class + control + not-suspended +
  requester≠provider).
- **Value-band gating** — computed from `declared_value_kes` vs `config.value_bands`
  at publish, frozen at `CONFIRMED`; `is_high_value` generated;
  `high_value_approval` gate for HIGH/VERY_HIGH at `ASSIGN`.
- **Pickup proof matrix** (STANDARD OTP / in-app business-confirm /
  operator-attested fallback → capped; ELEVATED+ OTP / business-confirm, **no
  fallback**, `422 pickup_confirmation_required`). First valid proof wins.
- **Delivery proof matrix** (STANDARD: name + one of OTP/signature/photo;
  ELEVATED+: name + OTP **and** photo).
- **Custody** — append-only `job_event` rows (`is_custody = true`) + the
  `chain_of_custody` / `job_status_event` / `job_timeline` views.
- **Business pickup confirmation** — a Business-user server-confirmed proof path
  driving `AT_PICKUP → PICKED_UP`, equivalent within the matrix.
- **Recipient scoped access** — `recipient_access_link` (≥ 32-byte CSPRNG token,
  `token_hash` + HMAC `token_lookup`, time-limited, per-Job, `allowed_actions`),
  `recipient_otp_challenge`, a link-scoped authorization principal, and the
  minimal-disclosure read contract. **Backend + authorization boundary only — no
  recipient UI.**
- **Incidents & disputes foundation** — `incident` (11 categories) +
  `incident_evidence` + `incident_statement` + `dispute` (with
  `pre_dispute_status`) + `resolution` + `escalation`; the `* → DISPUTED` freeze
  and the `DISPUTED → {COMPLETED|FAILED|CANCELLED}` admin resolution transitions.
  **`DISPUTED → RESUME` is NOT implemented** — see §18 / Escalation E-1.
- **Commission integration** — on `DELIVERED → COMPLETED`, create an immutable
  `commission_record` pinned to `config_version_id` (`DUE`, or `HELD` if the Job
  passed through `DISPUTED`); `commission_adjustment` (admin-signed) for
  corrections. **No** `commission_record` for `CANCELLED`/`FAILED`. No wallet, no
  escrow.
- **API** — a `jobs` URL module under `/api/v1/` following the existing
  conventions; endpoint groups per §12.
- **Tests** — lifecycle cross-product, concurrency/idempotency, negotiation,
  assignment/eligibility, pickup/delivery proof, recipient, incident/dispute,
  authorization, audit/outbox atomicity, financial, and invariant/property tests
  (§13).
- **Docs** — this plan promoted to `phase-2d-summary.md` + `phase-2d-decisions.md`
  (ADRs) + API contract doc, on completion.

### Explicitly OUT of scope (brief §36)

Any frontend (Job screens, nav, workspaces). AI dispatch, route optimization,
dynamic/recommended/historical pricing, auction, continuous GPS, fleet
management, wallets/escrow/fare custody, automated insurance/refunds/compensation,
public ratings/ranking/recommendation, predictive analytics, native apps,
payroll, driver scheduling, vehicle transfers, autonomous matching, a Trust
score/level *engine* (see E-2), a commercial SMS/WhatsApp provider commitment
(E-3), any legal/commercial conclusion.

---

## 3. Reconciliation with approved decisions (no contradictions found)

| Area | Approved source | Plan honours it by |
| --- | --- | --- |
| 14 states, verbatim | `job-lifecycle.md` D-JOB-3, `job-state-machine.md §1` | `job_status` enum = the 14, no additions/renames; UI labels are a frontend concern |
| One authoritative writer | `job-state-machine.md §2`, FR-J-3, NFR-INT-2 | `JobLifecycleService.transition()` only; trigger backstop; no serializer/save/task/signal writes `status` |
| Transaction boundary | `job-state-machine.md §2.1`, security-architecture | side effects + status + `job_event` + audit + outbox + idempotency row = one commit; external I/O never in-txn |
| Concurrency / idempotency | `job-state-machine.md §6` | `SELECT … FOR UPDATE` on `job`; `If-Match: job.version` → `412`; `Idempotency-Key` (24h, `(actor, job, key)`) |
| Negotiation | `pricing-and-negotiation.md`, `negotiation-architecture.md`, D-A-NEG-1/2/3 | sealed per-thread, append-only `negotiation_entry`, agreed price frozen in `agreement` (append-only, `U(job_id)`), sibling threads `SUPERSEDED`; **no** auto/recommended/historical pricing |
| Value bands / thresholds | `trust-architecture.md §1`, decision-memo §3, config `value_bands` | read from `config.value_bands` (already KES 50k/250k/1M in minor units); `high_value_threshold_kes` = 25,000,000; frozen at CONFIRMED |
| Trust ≠ verified; driver ceiling gates | `trust-and-safety.md §1`, `trust-architecture.md`, phase-1-summary | eligibility uses the **assigned driver's** trust ceiling (see E-2 for how, given no Trust module); verification consumed via `verification.services`, not duplicated |
| Pickup/delivery proof matrix | `chain-of-custody.md §3–4`, D-CUS-2, D-TRU-5, design-phase-2 §39/§44 | implemented exactly; `proof_of_pickup.attestation = OPERATOR_ATTESTED_UNVERIFIED` insertable only when `value_band = STANDARD` and caps the band; ELEVATED+ `422 pickup_confirmation_required` |
| Business pickup confirmation | design-phase-3 §6.6 (approved amendment) | a Business `confirm_pickup` path → `AT_PICKUP → PICKED_UP` via the same service; first valid proof wins |
| Recipient model | `recipient-access.md`, D-RCP-1, design-phase-3 §20.0 | `recipient_access_link` schema verbatim; link-scoped principal; minimal-disclosure serializer (name = first + last-initial per founder decision; driver first name; cargo summary; proof interaction only) |
| Amicable-first disputes; admin bands | `trust-and-safety.md`, D-ADM-1, `job-state-machine.md §5` | `incident_status` incl. `AMICABLE_PENDING`; binding resolution above STANDARD band gated to Platform Admin (`ActorIsPlatformAdmin` guard); no auto-liability/refund |
| Cancellation flag rule | `job-state-machine.md §3` (`penalty_class` from `at_status`), design-phase-2 §80 | `cancellation_record.penalty_class` computed: before ASSIGNED → NONE; ASSIGNED→AT_PICKUP → LATE_CANCELLATION; after AT_PICKUP → WASTED_TRIP. The "3 in rolling 30d per side" is a **query**, not a stored counter; a `JobCancelled` outbox event carries the inputs for a later reputation phase. **No reputation engine built.** |
| Commission | `commission-ledger.md`, config `commission` | `commission_record` immutable + `config_version_id`-pinned, created only on `→ COMPLETED`; `HELD` if it passed through DISPUTED; `commission_adjustment` for corrections; none for CANCELLED/FAILED |
| Audit / outbox | `security-architecture.md`, events-and-background-jobs | every state-changing op → `audit.record()` + `emit()` in the same txn; reuse — no second mechanism |
| Append-only | database-design §1, ADR-009 | `job_event`, `negotiation_entry`, `proof_of_*`, `agreement`, `incident_*`, `resolution`, `escalation`, `high_value_approval` (decision immutable), `commission_*` — `AppendOnlyModel` + `app_rw` grants + triggers |
| RESUME_PRIOR | phase-1-decisions, `job-state-machine.md §5.4`, design 2–4 | **OPEN — not implemented.** `dispute.pre_dispute_status` is recorded (so a future resume is deterministic); no resume operation, endpoint, or algorithm exists; the state cannot be left resumable by accident (see E-1). |

**No approved product decision is contradicted by this plan. No Phase 0–2C
contradiction was found.**

---

## 4. Module layout (matches the 2A–2C pattern)

```
backend/fikisha/jobs/          the Job aggregate + JobLifecycleService + transitions + guards + API
  models.py       job, job_location, cargo_details, vehicle_requirement, agreement,
                  assignment, cancellation_record, failure_record, job_event,
                  proof_of_pickup, proof_of_delivery, pickup_otp_challenge,
                  recipient_access_link, recipient_otp_challenge, high_value_approval,
                  allowed_job_transition (seed table)
  transitions.py  ALLOWED_TRANSITIONS table (data) + Rule dataclass
  guards.py       the §4 guards of job-state-machine.md (each independently tested)
  services.py     JobLifecycleService.transition() + create_draft/publish helpers +
                  compute_value_band + eligibility gate
  authz.py        can_view_job / can_act helpers; recipient-link principal resolution
  policies.py     @policy handlers: job.create/read/list/transition/assign/
                  negotiate/proof.pickup/proof.delivery/recipient.* /incident.* /
                  dispute.* /highvalue.approve
  api/            serializers.py (incl. the minimal recipient serializer), views.py, urls.py
  migrations/     0001_initial + 0002 triggers/grants/views (RunSQL, reversible)
  management/commands/  jobs_expire_requests, jobs_autocomplete_delivered,
                        jobs_close_post_completion_window (NOT beat-wired in 2D; §23)
  tests/

backend/fikisha/negotiation/   thin — negotiation_thread, negotiation_entry, NegotiationService
                               (propose/counter/accept/decline) that then calls
                               JobLifecycleService.transition for CONFIRMED
backend/fikisha/incidents/     incident, incident_evidence, incident_statement, dispute,
                               resolution, escalation + IncidentService / DisputeService
                               (DisputeService calls JobLifecycleService for the freeze
                               and the resolution transitions)
```

Rationale (**ADR-2D-01**): keep the lifecycle writer and the guards in one app
(`jobs`) so "one authoritative mechanism" is physically obvious; split
negotiation and incidents into sibling apps because they have their own
append-only tables, their own services, and their own API surface, and they
depend **inward** on `jobs` (they call `JobLifecycleService`), never the reverse.
Custody has **no** app of its own — it is `job_event` rows written by
`JobLifecycleService` (ADR-009 consolidation), read through DB views. This mirrors
2C's `evidence` (pure dependency, no API) vs `verification` (owns its API) split.

`common/` gains: `IfMatch` parsing helper (`If-Match` / `412 stale_job`), a
`JobStatus` / `ValueBand` / `TrustLevel` enum home if not already in config, and
a `recipient` auth principal type.

---

## 5. Job schema (verbatim from `database-design.md §4.6–4.11`)

Implemented exactly as specified — **not re-derived here**. Key points the
implementation will enforce:

- `job`: `status` default `DRAFT`, `version` default 0; `value_band` /
  `required_trust_level` **CK non-null once `status <> 'DRAFT'`**; `is_high_value`
  **GENERATED** from `value_band IN ('HIGH','VERY_HIGH')`; `config_version_id` FK
  pins the bands/thresholds; the 6 partial indexes (discovery / my-jobs /
  active-assignment / dispute / auto-complete / post-completion). **No**
  `deactivated_at`. Money columns `*_kes BIGINT` minor units.
- `job_location`: immutable snapshot copied from `business_location` at creation
  (a later edit to the source must not rewrite history). `geo` nullable
  (`GEOGRAPHY(POINT,4326)` — needs PostGIS; **see E-4**).
- `agreement`: append-only, `U(job_id)`; `agreed_price_kes` frozen;
  `accepting_entry_ids UUID[2]`.
- `assignment`: one row per attempt; `job.assignment_id` points at the current;
  `assigned_driver_profile_id` + `vehicle_id` **both NOT NULL** (brief §12);
  `admin_override_reason` nullable; `config_version_id` pinned.
- `job_event`: append-only, `U(job_id, seq)` (per-job monotonic `seq` assigned
  inside the already-`FOR UPDATE`-locked transaction); `category` ∈
  `{STATUS_TRANSITION, CUSTODY, SYSTEM, ADMIN_ACTION}`; `type` = the superset
  enum; `is_custody` bool; `geo_state` default `NOT_CAPTURED`;
  `confirmation_method` ∈ `{OTP, SIGNATURE, PHOTO, IN_APP, NONE}`; `corrects_event_id`
  self-FK for corrective NOTEs. Views `job_status_event`, `chain_of_custody`,
  `job_timeline`.
- `proof_of_pickup` / `proof_of_delivery`: `U(job_id)`; `attestation` ∈
  `{VERIFIED, OPERATOR_ATTESTED_UNVERIFIED}`; the `OPERATOR_ATTESTED_UNVERIFIED`
  row is **only insertable when `job.value_band = 'STANDARD'`** (app + trigger CK)
  and it caps the band.
- `recipient_access_link`: `token_hash` unique, `token_lookup BYTEA` indexed
  (HMAC), **partial unique** `U(job_id) WHERE revoked_at IS NULL AND expires_at >
  now()`, `allowed_actions TEXT[]`, `expires_at`, `used_at`, `revoked_at`.
- `high_value_approval`: `U(job_id)`; decision immutable; for `VERY_HIGH` the
  approving actor must be a Platform Admin.
- `commission_record` / `commission_adjustment`: per `commission-ledger.md` —
  immutable, `config_version_id`-pinned, `U(job_id)`; adjustments admin-signed +
  reasoned + audited.

All append-only tables: `AppendOnlyModel` base + service refuses update/delete +
Postgres `BEFORE UPDATE/DELETE` trigger + `app_rw` role `SELECT, INSERT` only.

---

## 6. Lifecycle transition matrix (the `ALLOWED_TRANSITIONS` table)

Implemented **exactly** as `job-state-machine.md §3` (39 rows across §3.1–3.4).
The table is data; a `Rule` carries `initiators`, `guards`, `apply` (side-effect
fn), `events`, `is_custody`, `event_type`. Summary of the enforced set:

| From → To (allowed) | Initiator(s) | Key guards |
| --- | --- | --- |
| DRAFT→REQUESTED | Business owner/dispatcher, Admin | RequiredFieldsComplete, BusinessVerifiedWithLocation, CargoNotProhibited, ValueBandComputed |
| DRAFT→CANCELLED | Business, Admin | — |
| REQUESTED→NEGOTIATING | Business / eligible Operator·Group (via Negotiation) | OperatorEligibleForJob |
| REQUESTED→CONFIRMED | Business (accepts operator PROPOSE at posted price) / Operator (accepts business `proposed_price`) | MutualAcceptanceExists, OperatorEligibleForJob (re-checked), NoRacingConfirm |
| REQUESTED→CANCELLED | Business, Admin | — |
| REQUESTED→FAILED | Scheduler, Admin | request-expiry elapsed, no acceptable offer |
| NEGOTIATING→NEGOTIATING | Business / Operator (via Negotiation) | thread ACTIVE, amount valid *(no-op on `status`; resets timer)* |
| NEGOTIATING→CONFIRMED | Business / Operator | MutualAcceptanceExists, OperatorEligibleForJob, NoRacingConfirm |
| NEGOTIATING→CANCELLED | Business, Admin | — |
| NEGOTIATING→FAILED | Scheduler, Admin, either party (walk-away) | negotiation-expiry, or explicit end |
| CONFIRMED→ASSIGNED | Operator (self+own vehicle) / Group MANAGER / Admin | VehicleEligible, DriverTrustCeilingCoversValue (or admin override), HighValueApproved, RequesterIsNotProvider, driver id+licence+good-conduct VERIFIED & current |
| CONFIRMED→CANCELLED | Business, Operator·Group, Admin | — |
| ASSIGNED→AT_PICKUP | Assigned driver | — (location capture attempted) — issues pickup OTP |
| ASSIGNED→CANCELLED | Business, Operator·Group, Admin | `penalty_class = LATE_CANCELLATION` |
| ASSIGNED→FAILED | Admin | operator abandoned, no replacement |
| ASSIGNED→DISPUTED | Any participant, Admin | BlockingIncidentExists |
| AT_PICKUP→PICKED_UP | Assigned driver **or** Business (in-app confirm) | PickupSideOtpVerifiedOrStandardFallback (STANDARD fallback → `OPERATOR_ATTESTED_UNVERIFIED` + band cap; ELEVATED+ → no fallback, `422 pickup_confirmation_required`), EvidenceScanned |
| AT_PICKUP→CANCELLED | Business, Operator·Group, Admin | only before custody; `penalty_class = WASTED_TRIP` |
| AT_PICKUP→FAILED | Assigned driver, Admin | reason + evidence required |
| AT_PICKUP→DISPUTED | Any participant, Admin | BlockingIncidentExists |
| PICKED_UP→IN_TRANSIT | Assigned driver | — |
| PICKED_UP→DISPUTED | Any participant, Admin | BlockingIncidentExists |
| PICKED_UP→FAILED | **Admin only** | — |
| IN_TRANSIT→AT_DESTINATION | Assigned driver | — (location capture attempted) — issues recipient link + OTP |
| IN_TRANSIT→DISPUTED | Any participant, Admin | BlockingIncidentExists |
| IN_TRANSIT→FAILED | **Admin only** | — |
| AT_DESTINATION→DELIVERED | Assigned driver (records POD) **or** Recipient (via link) | RecipientVerificationPresent (STANDARD: name + 1 of OTP/signature/photo; ELEVATED+: name + OTP **and** photo), EvidenceScanned |
| AT_DESTINATION→DISPUTED | Any participant, Recipient, Admin | recipient refuses / wrong recipient / damage |
| AT_DESTINATION→FAILED | **Admin only** | — |
| DELIVERED→COMPLETED | Business/Recipient (explicit) **or** Scheduler (auto after `delivery_acceptance` window) | no open blocking dispute → creates `commission_record` |
| DELIVERED→DISPUTED | Business, Recipient, Operator·Group, Admin | within acceptance window |
| COMPLETED→DISPUTED | Business, Recipient, Operator·Group, Admin | within post-completion window (72h; 7d for High/Very-high or `latent_risk_cargo`) → `commission_record.status = HELD` |
| DISPUTED→COMPLETED | Admin (**Platform Admin** above STANDARD band) | `Resolution.routed_job_status = COMPLETED`; apply `commission_treatment` |
| DISPUTED→FAILED | Admin | `routed_job_status = FAILED`; no/WAIVE commission |
| DISPUTED→CANCELLED | Admin | `routed_job_status = CANCELLED`; commission waived |
| DISPUTED→\<pre_dispute_status\> (RESUME) | **NOT IMPLEMENTED** | — RESUME_PRIOR OPEN (E-1) |

Everything **not** in this table → `422 transition_not_allowed`, no side effects,
transaction rolls back. Parametrized tests run the full `state × state`
cross-product.

---

## 7. Authorization matrix (uses `authorize(actor, action, resource)`)

Default-deny. `@policy` handlers registered in `jobs/policies.py`,
`negotiation/policies.py`, `incidents/policies.py`. New actions:

| Action | Business owner | Business dispatcher | Business VIEWER | Operator (self) | Group OWNER/MGR | Group DRIVER | Assigned driver | Recipient (link) | Ops Officer | Platform Admin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `job.create` / `job.draft.update` | ✓ (own biz) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| `job.read` / `job.list` | ✓ own | ✓ own | ✓ own (read-only) | ✓ where party / eligible-discovery | ✓ group jobs | ✓ *only* if `DRIVER_ACCEPTS* (discovery) or assigned | ✓ assigned | ✓ **this job only, minimal fields** | ✓ | ✓ |
| `job.transition:REQUESTED` (publish) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| `job.transition:CANCELLED` | ✓ (pre-terminal) | ✓ | ✗ | ✓ (as party, pre-AT_PICKUP) | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| `negotiation.propose/counter/accept/decline` | ✓ (business side) | ✓ | ✗ | ✓ (operator side, own thread) | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ (record-only) |
| `job.assign` (`CONFIRMED→ASSIGNED`) | ✗ | ✗ | ✗ | ✓ (self + own vehicle) | ✓ (name member DRIVER + group vehicle) | ✗ | ✗ | ✗ | ✗ | ✓ |
| `job.transition:AT_PICKUP` / `IN_TRANSIT` / `AT_DESTINATION` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ |
| `job.proof.pickup` (`AT_PICKUP→PICKED_UP`) | ✓ (**in-app business confirm** only) | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ (OTP / STANDARD fallback) | ✗ | ✗ | ✓ |
| `job.proof.delivery` (`AT_DESTINATION→DELIVERED`) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (records POD) | ✓ (confirm receipt) | ✗ | ✓ |
| `job.transition:COMPLETED` (explicit accept) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| `incident.create` | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ (curated categories) | ✓ | ✓ |
| `incident.review` / `dispute.open` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (facilitate, propose) | ✓ |
| `dispute.resolve:{COMPLETED,FAILED,CANCELLED}` **at/below STANDARD band** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| `dispute.resolve:*` **above STANDARD band** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (`ActorIsPlatformAdmin`) |
| `dispute.resume` (`DISPUTED→RESUME`) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **not implemented (E-1)** |
| `highvalue.approve` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (HIGH) | ✓ (HIGH + **VERY_HIGH**) |
| `job.evidence.read` (custody photos / POD) | ✓ own job | ✓ | ✓ | ✓ if party | ✓ | ✗ | ✓ | **✗ (recipient never)** | ✓ | ✓ |

`OPERATIONS_OFFICER` / `PLATFORM_ADMIN` permissions added to
`platform_config.defaults.role_permissions` (a code-default; live config picks it
up via `ConfigService.apply_change`). Ops Officer **cannot**: config changes,
suspend/offboard, binding dispute resolution above STANDARD, or resume (D-ADM-1).
Recipient principal: resolved from `token_lookup`; scoped to one `job_id`;
`allowed_actions` from the link row; every recipient read/write is audited;
HIGH-PII / evidence is never exposed to it.

IDOR/BOLA test matrix: cross-business, cross-operator, cross-group, wrong-job
recipient token, expired/revoked/reused token, VIEWER write attempt, Ops-Officer
over-reach, unauthenticated — each → `403`/`404` fail-closed, no data leak.

---

## 8. Negotiation model

- `negotiation_thread` per `(job, operator_id|group_id)` — `U(job_id, operator_id,
  group_id)`; `status ∈ {ACTIVE, SUPERSEDED, CLOSED}`. Operators never see each
  other's threads (sealed — FR-N-3).
- `negotiation_entry` **append-only**: `type ∈ {PROPOSE, COUNTER, ACCEPT,
  REJECT}`, `amount_kes` required for PROPOSE/COUNTER, `in_response_to_id`,
  `status ∈ {ACTIVE, SUPERSEDED, EXPIRED}`, `expires_at` (offer-expiry from
  config). Ordered by `created_at`; never rewritten.
- `NegotiationService.{propose, counter, accept, decline}` — writes the entry
  (in-txn, audited, `emit('negotiation.*')`), and on mutual `ACCEPT` in one
  thread calls `JobLifecycleService.transition(job, CONFIRMED, …)` which creates
  the `agreement` (frozen `agreed_price_kes`, `accepting_entry_ids`), sets other
  threads `SUPERSEDED`, and (optionally, same request) chains `→ ASSIGNED`.
- `MutualAcceptanceExists` guard: an `ACCEPT` from each side in the same thread
  referencing compatible amounts, both `ACTIVE`. `NoRacingConfirm`: `job.status ∈
  {REQUESTED, NEGOTIATING}` at the locked read, else `409 job_no_longer_available`.
- **Prohibited and not built:** dynamic pricing, price recommendations,
  historical price guidance, AI pricing, platform price fixing, auctions, hidden
  price scoring. No endpoint exposes an aggregate or suggestion.

---

## 9. Assignment & eligibility

`CONFIRMED → ASSIGNED` guards (all server-side, all auditable):

1. `RequesterIsNotProvider` — requester `User` ≠ assigned driver `User`; requester
   does not control the assigned group.
2. `VehicleEligible` — vehicle `is_active` (`status == ACTIVE`), controlled by the
   operator/group party, `vehicle_class` type + capacity match the
   `vehicle_requirement`; if `VehicleClass.heavy` → `verification.subject_meets`
   for the heavy-class domain set is `True`.
3. Driver verification — `verification.subject_meets(driver, {IDENTITY, LICENCE,
   GOOD_CONDUCT})` current (not effectively `EXPIRED`), for the correct licence
   class.
4. `DriverTrustCeilingCoversValue` — the **assigned driver's** trust ceiling ≥
   `job.declared_value_kes`, **or** a recorded `admin_override_reason`. *(How the
   ceiling is obtained absent a Trust module → Escalation E-2. Default proposal:
   a conservative deterministic rule — L1 = STANDARD only — derived from
   verification facts, with the config `value_bands[].min_trust_level` as the map,
   pending the Trust phase.)*
5. `HighValueApproved` — if `job.is_high_value`: a `high_value_approval` with
   `decision = APPROVED` exists; `VERY_HIGH` requires the approver be a Platform
   Admin.
6. Group `DRIVER_ACCEPTS` vs `MANAGER_ASSIGNS` respected (from Phase 2B group
   `assignment_mode`).

Ineligible → typed `DomainError` → `422` with a `code` naming the failing
condition (no scores, no client-side bypass).

---

## 10. Custody & proof

- Custody = `job_event` rows with `is_custody = true` written **only** by
  `JobLifecycleService` inside the transition transaction (assignment, arrival,
  pickup confirmation, goods received, transit, arrival at destination, recipient
  verified, delivery confirmed, completed). Read via `chain_of_custody` view.
  `geo` captured when the client provides it; `geo_state = NOT_CAPTURED` is an
  acceptable recorded value (NFR-PRIV-4 — the OTP, not the location, is the
  gating proof). **No continuous GPS.**
- `pickup_otp_challenge` issued on `ASSIGNED → AT_PICKUP` (SMS-primary via the
  outbox; `purpose = PICKUP_HANDOVER`; sent to the pickup contact). 6-digit,
  hashed at rest, short TTL, rate-limited re-issue.
- **Pickup proof (`AT_PICKUP → PICKED_UP`):**
  - STANDARD: (a) driver enters the pickup-contact OTP; **or** (b) a Business
    user calls `job.proof.pickup` (in-app confirm); **or** (c) OTP undeliverable →
    driver provides `fallback_photo_id` + `pickup_contact_name` →
    `proof_of_pickup(attestation = OPERATOR_ATTESTED_UNVERIFIED, captured_by =
    OPERATOR)` + `job_event(PICKUP_OPERATOR_ATTESTED)`; **the job is capped at
    STANDARD** (a later business in-app confirm can flip `attestation` to
    `VERIFIED` via a corrective `job_event`).
  - ELEVATED / HIGH / VERY_HIGH: only (a) or (b). No fallback. Missing → the
    transition raises `422 pickup_confirmation_required` (RFC-9457).
  - **First valid proof wins** — `proof_of_pickup` is `U(job_id)`; a second
    attempt after `PICKED_UP` is an idempotent no-op / `422
    transition_not_allowed`.
- **Delivery proof (`AT_DESTINATION → DELIVERED`):** `RecipientVerificationPresent`
  — STANDARD: `party_name` + ≥ 1 of {recipient OTP consumed, signature evidence,
  photo evidence}; ELEVATED+: `party_name` + recipient OTP **and** ≥ 1 photo.
  Recorded in `proof_of_delivery` (`U(job_id)`). Recipient-side (via link) and
  driver-side (records POD) both allowed; whichever is valid first wins.
- All non-image evidence referenced in a proof/incident context must have
  `scan_status = CLEAN` (`EvidenceScanned` guard). *(ClamAV is deferred per
  ADR-2C-08; the guard checks the field, which defaults per the 2C seam.)*

---

## 11. Recipient scoped access (backend + boundary only)

- `recipient_access_link` issued on `IN_TRANSIT → AT_DESTINATION` (and re-issued
  on dispute per `recipient-access.md`). Token ≥ 32 bytes CSPRNG in the URL;
  `token_hash` (argon2/sha256) verifies; `token_lookup` (HMAC with a server key)
  indexes. `expires_at` = COMPLETED + dispute window; **partial-unique one active
  link per job**.
- `RecipientPrincipal` — resolved by `token_lookup`, carries `job_id` +
  `allowed_actions` (`{VIEW, CONFIRM_RECEIPT, REPORT_ISSUE}`). Not a `User`. Every
  access → `audit.record` (actor kind `RECIPIENT_LINK`).
- **Minimal-disclosure read** (`RecipientJobSerializer`) — exposes only:
  delivery reference; recipient **first name + last initial** (founder decision);
  cargo **summary**; current status (human); **driver first name** + vehicle
  class + plate; "operator identity verified" as a plain boolean; the proof
  interaction affordances; short terms. **Never:** driver/business phone, business
  staff, verification documents/trust internals, price/band, location history,
  any other job, org info.
- Endpoints: `GET /r/<token>` (view), `POST /r/<token>/confirm` (delivery proof —
  band-appropriate), `POST /r/<token>/incident` (curated categories, rate-limited,
  no OTP). Expired / revoked / wrong-job / reused → `403`/`410`, no leak.
- **No recipient frontend** in 2D.

---

## 12. API boundary (`/api/v1/`, existing conventions)

Every endpoint = an approved domain operation. RFC-9457 problems; cursor
pagination; `Idempotency-Key` on creates + transitions; `If-Match` on Job
mutations.

| Group | Endpoints (sketch) |
| --- | --- |
| Jobs | `POST /jobs` (create DRAFT) · `PATCH /jobs/{id}` (edit DRAFT) · `GET /jobs` (role-scoped list; operator discovery filter) · `GET /jobs/{id}` (role-scoped detail: summary, status, **next allowed actions**, parties, price, timeline ref) |
| Transitions | `POST /jobs/{id}/transitions` `{to, context}` — the single lifecycle endpoint; `If-Match: <version>`, `Idempotency-Key`. Thin action aliases where useful: `POST /jobs/{id}/publish`, `/cancel`, `/arrive-pickup`, `/start-transit`, `/arrive-destination`, `/accept-completion` — each calls the same service. |
| Negotiation | `GET /jobs/{id}/negotiation` (own thread) · `POST /jobs/{id}/negotiation/propose|counter|accept|decline` |
| Assignment | `POST /jobs/{id}/assignment` `{driver_profile_id, vehicle_id, admin_override_reason?}` |
| High-value | `POST /jobs/{id}/high-value-approval` `{decision, rationale}` (Ops/Admin) |
| Pickup proof | `POST /jobs/{id}/pickup-proof` `{method: OTP|BUSINESS_CONFIRM|ATTESTED, otp?, fallback_photo_id?, pickup_contact_name?}` |
| Delivery proof | `POST /jobs/{id}/delivery-proof` `{party_name, otp?, signature_evidence_id?, photo_evidence_ids?}` |
| Custody / activity | `GET /jobs/{id}/timeline` · `GET /jobs/{id}/custody` (views) |
| Incidents | `POST /jobs/{id}/incidents` · `GET /jobs/{id}/incidents` · `POST /incidents/{id}/statements` · `POST /incidents/{id}/evidence` · `POST /incidents/{id}/review` (Ops) |
| Disputes | `POST /incidents/{id}/dispute` (Ops/Admin) · `POST /disputes/{id}/resolution` `{outcome_code, commission_treatment, routed_job_status, rationale, actions}` (band-gated) |
| Recipient | `GET /r/{token}` · `POST /r/{token}/confirm` · `POST /r/{token}/incident` |

Documented in `docs/phase-2/phase-2d-api.md` on completion, in the shape the
future frontend consumes (summary / detail / human status / next actions /
negotiation / assignment / custody / proof state / incidents / disputes /
recipient / relevant verification facts). **No frontend built.**

---

## 13. Test strategy (a primary deliverable — brief §31–32)

Pytest, matching the 2A–2C style. Target: parity with 2C's ~87 % coverage on the
new code; **security and invariant tests are not optional**.

| Suite | Coverage |
| --- | --- |
| Lifecycle cross-product | every `(from, to)` in `state × state` — allowed → succeeds with valid context + writes exactly the expected side-effect rows; disallowed → `422 transition_not_allowed`, **zero** side effects, tx rolled back |
| Terminal & interruption | CANCELLED/FAILED/DISPUTED entry from each legal state; `penalty_class` computed from `at_status`; terminal states reject all further transitions |
| Concurrency | two `transition()` calls racing the same job (`FOR UPDATE` serialises; loser replays or `422`); stale `If-Match` → `412`; duplicate `Idempotency-Key` → stored `JobView`, **no** second side effect; replay after commit; racing negotiation `ACCEPT` → first wins, second `409` |
| DB backstop | raw `UPDATE job SET status` outside the service → trigger raises |
| Negotiation | propose/counter/accept/decline; append-only (no update/delete path); agreed price frozen; sibling threads `SUPERSEDED`; sealed (operator B cannot read operator A's thread); unauthorized negotiation → `403` |
| Assignment | eligible operator+vehicle → ok; ineligible operator / wrong class / over-capacity / unverified driver / trust-ceiling < value / missing high-value approval / VERY_HIGH approved by non-Platform-Admin / requester==driver / cross-org → each `422`/`403` with the right `code` |
| Pickup proof | STANDARD OTP · STANDARD business-confirm · STANDARD attested fallback (→ `OPERATOR_ATTESTED_UNVERIFIED`, band capped) · ELEVATED OTP · ELEVATED business-confirm · **ELEVATED fallback rejected** (`422 pickup_confirmation_required`) · missing confirmation · **first valid proof wins** (second attempt no-ops) |
| Delivery proof | STANDARD (each of OTP / signature / photo) · ELEVATED+ (OTP **and** photo required; OTP-only or photo-only rejected) · incomplete → `422` · duplicate → no-op |
| Recipient | valid token view (minimal fields only — assert the excluded fields are absent) · expired · revoked · reused-after-`used_at` · wrong-job token · unauthorized action not in `allowed_actions` → `403`/`410` |
| Incidents / disputes | create (each of 11 categories) · evidence + statements append-only · access control (party vs non-party vs recipient) · `* → DISPUTED` freeze (timers paused) · Ops review · `DISPUTED → {COMPLETED,FAILED,CANCELLED}` by Admin; above-STANDARD binding resolution by Ops Officer → `403`; **no** `DISPUTED → RESUME` path exists |
| Authorization | the full §7 matrix — every role × action × org-boundary; fail-closed |
| Audit / outbox atomicity | successful transition → exactly one `audit_log_entry` (chain intact) + the expected `outbox_event` rows, same commit; a guard failure mid-transition → **no** audit, **no** outbox, **no** status change (assert via a forced exception in a side-effect fn) |
| Financial | `→ COMPLETED` creates `commission_record`: 10 % of `agreed_price_kes`, floored at 4000, capped at 500000 minor units; `config_version_id` pinned; `HELD` iff the job passed through `DISPUTED`; **no** record for CANCELLED/FAILED; a correction is a `commission_adjustment`, never a mutation |
| Invariant / property | (brief §32) no arbitrary state jump · `status` unwritable outside the service · COMPLETED never silently returns earlier · `negotiation_entry` immutable · `agreed_price_kes` immutable · `proof_of_*` immutable · `audit_log_entry` immutable · recipient token can't reach another job · no cross-org boundary crossing · ineligible driver can't be assigned to a restricted job · commission not generated before COMPLETED |
| Live smoke (`scripts/`) | a `docker compose` run of the full happy path (Business create → publish → operator negotiate → confirm → assign → arrive → OTP pickup → transit → arrive → recipient OTP delivery → auto/explicit complete → commission record) + one ELEVATED-band no-fallback rejection + one dispute freeze/resolve; `verify_chain()` returns `[]`; append-only `UPDATE` rejected. |

---

## 14. ADRs to be recorded (`phase-2d-decisions.md`)

- **ADR-2D-01** — `jobs` app owns the lifecycle writer + guards; `negotiation` /
  `incidents` are inward-depending sibling apps; custody has no app (ADR-009
  `job_event` consolidation). *(rationale in §4)*
- **ADR-2D-02** — `job.version` is the `If-Match` optimistic token; a new
  `common` helper parses `If-Match` and raises `412 stale_job`. `Idempotency-Key`
  reuses `common/idempotency.py`, scoped `(actor_id, job_id, key)`.
- **ADR-2D-03** — the DB trigger backstop + `allowed_job_transition` seed table
  (RunSQL migration, reversible); the `app.lifecycle_service` session flag is set
  only inside `transition()` after guards pass. Mirrors the 2A/2C append-only
  trigger pattern.
- **ADR-2D-04** — `job_event` is a single append-only table with `category` /
  `type` / `is_custody`; `chain_of_custody` / `job_status_event` / `job_timeline`
  are SQL **views** (no data duplication). Not full event sourcing — `job.status`
  remains authoritative current state (brief §26).
- **ADR-2D-05** — driver trust ceiling for `DriverTrustCeilingCoversValue`:
  **conservative deterministic derivation** from verification facts +
  `config.value_bands[].min_trust_level`, pending the Trust phase (E-2). No trust
  score/level engine, no ratings.
- **ADR-2D-06** — recipient principal is a first-class non-`User` auth subject
  resolved from `token_lookup`; `authorize()` accepts it; every access audited;
  minimal-disclosure serializer is the only recipient read path.
- **ADR-2D-07** — `DISPUTED → RESUME` is **not implemented**; `dispute.pre_dispute_status`
  is persisted so a future founder-approved `RESUME_PRIOR` is deterministic; no
  resume operation/endpoint/algorithm exists (E-1).
- **ADR-2D-08** — the three scheduled sweeps (`request_expiry`, `delivery_acceptance`
  auto-complete, post-completion window close) are implemented as management
  commands + are **beat-wired** (unlike 2C's optional command) because
  auto-complete is part of the approved lifecycle (`DELIVERED → COMPLETED` by
  Scheduler). *(Confirm at the gate — see Q-5.)*
- **ADR-2D-09** — provider-neutral outbox events only; **no** SMS/WhatsApp
  provider selected or wired (E-3). OTP issuance emits `otp.pickup.requested` /
  `otp.recipient.requested`; a later phase (or the pending provider decision)
  wires delivery.
- **ADR-2D-10** — `geo` columns: **defer PostGIS** — store pickup/destination/
  event location as plain `lat`/`lng` `DecimalField` + `geo_state`, mirroring
  ADR-2B-04 (business/operator locations are already plain lat/lng, no PostGIS in
  the stack). `GEOGRAPHY(POINT,4326)` in `database-design.md` becomes plain
  decimals; distance is informational. *(Confirm at the gate — see E-4 / Q-4.)*
- **ADR-2D-11** *(Increment 2)* — **`negotiation_entry` is truly immutable; its
  ACTIVE/SUPERSEDED/EXPIRED status is derived, not stored.** The plan (§5) and
  `negotiation-architecture.md §7.1` mandate `negotiation_entry` as a hard
  `AppendOnlyModel` + `BEFORE UPDATE/DELETE` trigger ("INSERT, SELECT only; an
  attempted UPDATE/DELETE raises"). That is incompatible with a mutable `status`
  column updated by the confirm txn / an `expire_stale_offers` sweep (as
  `database-design.md §4.8` and `negotiation-architecture.md §4` describe). We
  reconcile in favour of the stronger immutability statement: an entry row is
  never written after INSERT, and `selectors.effective_entry_status` folds in the
  thread status, `expires_at`, and later same-side offers at read time — exactly
  the `VerificationRecord.effective_state()` precedent (CLAUDE.md §4). The stored
  `status` column and the `IX(status, expires_at)` sweep index in
  `database-design.md §4.8` are dropped; no `expire_stale_offers` beat job is
  needed (it was not part of the approved Q-5 sweep set either). No product
  behaviour changes — an expired offer still cannot be accepted; superseded
  offers still stay visible in the history with their timestamps.
- **ADR-2D-12** *(Increment 2)* — **thread bookkeeping on confirm lives in the
  Negotiation Service, in the confirming transaction.** `job-state-machine.md`
  §3.1 and ADR-007 require "close winning thread; SUPERSEDE siblings" *inside*
  the CONFIRM transaction, but the `jobs`-app `apply_fns` may not import
  `negotiation` models. So `NegotiationService.accept` wraps
  `JobLifecycleService.transition(job, CONFIRMED, …)` in its own
  `transaction.atomic()` and, in that same transaction, sets the winning
  `negotiation_thread → CLOSED` and its siblings `→ SUPERSEDED` (thread status is
  mutable; entries are untouched — their effective status flips by derivation).
  If the transition raises (e.g. `NoRacingConfirm` → 409), the whole thing rolls
  back and no thread is altered.
- **ADR-2D-13** *(Increment 2)* — sibling apps read a Job through
  `jobs.selectors.{get_job, job_for_update}` and never write `job.status` except
  via `JobLifecycleService.transition`. This is the concrete read/write boundary
  the module-layout rule (§4) asks for.

---

## 15. Migration plan (brief §33)

- `jobs/migrations/0001_initial.py` — all `jobs`-app models. Generated, then
  **inspected** before commit.
- `jobs/migrations/0002_lifecycle_backstop.py` — `RunSQL` (reversible): create
  `allowed_job_transition` + seed from the `ALLOWED_TRANSITIONS` source; the
  `BEFORE UPDATE OF status ON job` trigger; the append-only `BEFORE UPDATE/DELETE`
  triggers on `job_event` / `agreement` / `proof_of_*` / `negotiation_entry` /
  `incident_*` / `resolution` / `escalation` / `high_value_approval`; the
  `job_status_event` / `chain_of_custody` / `job_timeline` views; the `app_rw`
  `SELECT, INSERT`-only grants on the append-only tables.
- `negotiation/migrations/0001_initial.py`, `incidents/migrations/0001_initial.py`
  — with their own append-only triggers/grants.
- `platform_config` — **no new migration**; `role_permissions` additions are a
  code-default in `defaults.py`, picked up by `ConfigService.apply_change` (as in
  ADR-2C-09).
- **No change to any Phase 2A–2C table.** No destructive operation. `makemigrations
  --check` clean. Nothing touches production data.
- If a schema decision turns out to require changing a 2A–2C model → **STOP and
  escalate** (§41).

---

## 16. Security review checklist (brief §29, run before "complete")

IDOR on every `job.*` resource; cross-business / cross-operator / cross-group
reads & writes; recipient token abuse (expired / revoked / reused / wrong-job /
guessable); unauthorized transition; stale mutation; replay; duplicate
submission; privilege escalation (VIEWER→write, Ops→config/suspend/above-band
resolution, operator→assign-others, group DRIVER→manage); unauthorized evidence /
proof access; unauthorized assignment; unauthorized dispute manipulation. All
fail-closed. No trust of client-supplied role / org / trust / verification /
lifecycle state. Then `claude-security` "scan changes" on the branch diff +
STRIDE notes for the pickup/delivery-proof and recipient-link surfaces
(team-skills-policy §4).

---

## 17. Verification gates before reporting COMPLETE (brief §40)

`pytest` (all green, coverage reported) · `ruff check` · `ruff format --check` ·
`mypy` (pragmatic, ADR-2A-08) · `python manage.py makemigrations --check
--dry-run` · `python manage.py migrate` on a fresh DB · a `docker compose` smoke
run of §13's live-smoke script (recorded output) · the security review (§16). A
green build alone is **not** sufficient.

---

## 18. Escalations / open items — FOUNDER DECISION REQUIRED (brief §41)

| ID | Item | Why it needs the founder | Plan's safe default (if not decided) |
| --- | --- | --- | --- |
| **E-1** | **`RESUME_PRIOR` semantics** — the conditions under which `DISPUTED → RESUME` is allowed, and its exact target. | Product/architecture decision, OPEN since Phase 0; carried through Phases 1–4. | **Not implemented.** `dispute.pre_dispute_status` recorded; no resume path exists; a disputed job can only be routed to COMPLETED/FAILED/CANCELLED by an admin. This is safe and explicit; RESUME can be added in one guarded transition later. |
| **E-2** | **Trust levels / ceilings** — `DriverTrustCeilingCoversValue` needs a driver "trust ceiling", but there is **no Trust module** (Phase 2C stopped before it; the brief's own "recommended 2D = Trust & Reputation, then Jobs" was reordered by this founder prompt to Jobs-first). | The value-band gate is a real money/liability control; how the ceiling is computed is a product decision. Options: (a) build a minimal Trust-level model in 2D (L1/L2/L3 from the `trust-architecture.md §1` criteria); (b) 2D uses a conservative deterministic rule (verification-facts → level, `config.value_bands[].min_trust_level` as the map) and the full Trust engine is a later phase; (c) gate only on verification + `high_value_approval` for now and treat the ceiling as "L1 unless an admin override". | **Option (b)** — ADR-2D-05: conservative, deterministic, auditable, no ratings/scores; HIGH/VERY_HIGH still require `high_value_approval`. Flagged for founder confirmation. |
| **E-3** | **SMS / WhatsApp provider** — pickup/recipient OTP delivery and job notifications need a carrier; the provider-selection decision is still pending (Phase 0). | Commercial commitment. | Provider-neutral **outbox events only** (`otp.pickup.requested`, `otp.recipient.requested`, `job.*`); no provider code. OTP **generation/verification** is implemented; **delivery** is a stub the outbox drains to nowhere until wired. |
| **E-4** | **Location storage** — `database-design.md` specifies `GEOGRAPHY(POINT,4326)` (PostGIS); the stack has no PostGIS (ADR-2B-04 already chose plain lat/lng for org locations). | Minor architecture choice, but it deviates from a Phase 1 doc. | ADR-2D-10: plain `lat`/`lng` decimals + `geo_state`, consistent with 2B. Distance is informational only (no routing). Confirm acceptable. |
| **Q-5** | **Scheduled sweeps** — 2C left its expiry command **not** beat-wired; 2D's `DELIVERED → COMPLETED (auto)` is part of the approved lifecycle, so the auto-complete sweep arguably **must** run. | Small ops decision. | ADR-2D-08: implement all three sweeps as management commands **and** beat-wire the auto-complete + request-expiry ones (they are lifecycle-critical); post-completion-window close can stay command-only. Confirm. |
| **Q-6** | **`CONFIRMED → ASSIGNED` in one request with the accept** — `job-state-machine.md §3.1` allows the accept endpoint to run `→ CONFIRMED` then `→ ASSIGNED` in one transaction for an individual operator. Build that convenience now, or keep them separate calls in 2D? | UX/contract shape. | Keep **separate** transitions in 2D (simpler, fully tested); the combined path is a thin wrapper a later phase can add. Confirm. |
| **Q-7** | **RLS** — `database-design.md §2` marks Postgres row-level security for `job` / `negotiation_*` / `evidence_object` as "OPEN: adopt in Phase 2 iteration 1 or defer to hardening". | Defence-in-depth scope. | Defer RLS to hardening (the application authz scope is the primary control and is fully tested); 2D adds the `SET LOCAL app.actor_id` seam so RLS can be switched on later without a schema change. Confirm. |

**No other ambiguity was found.** Every §5–§13 rule maps to an explicit approved
source.

---

## 19. Implementation sequence (after the gate)

1. `jobs` models + `0001` migration (inspected) → typecheck/migrate.
2. `transitions.py` table + `guards.py` + `0002` backstop migration.
3. `JobLifecycleService.transition()` + `create_draft`/`publish` + value-band
   computation → lifecycle cross-product tests.
4. `negotiation` app + service → CONFIRMED path → negotiation tests.
5. Assignment + eligibility (integrates `verification` + `vehicles` +
   `config.value_bands` + `high_value_approval`) → assignment tests.
6. Custody transitions + `pickup_otp_challenge` + pickup/delivery proof matrices
   → proof tests.
7. `recipient_access_link` + principal + minimal serializer + `/r/` endpoints →
   recipient tests.
8. `incidents` app + `dispute` + `resolution` + the `* → DISPUTED` /
   `DISPUTED → *` transitions → incident/dispute tests.
9. Commission integration on `→ COMPLETED` → financial tests.
10. API views/urls for all groups + `next allowed actions` computation → API +
    authorization tests.
11. Scheduled sweeps + beat wiring (per Q-5).
12. Invariant/property tests; audit/outbox atomicity tests.
13. `ruff` / `mypy` / `makemigrations --check` / fresh migrate / docker smoke.
14. `claude-security` scan-changes + STRIDE notes + full review vs Phases 0–2C.
15. Promote this doc → `phase-2d-summary.md` + `phase-2d-decisions.md` +
    `phase-2d-api.md`; update `CLAUDE.md` status + STOP line; update memory.
16. **STOP for the second founder gate.** No merge, no deploy.

Estimated: the largest phase to date (schema ≈ 20 tables, ≈ 39 transition rows,
≈ 16 guards, ≈ 25 endpoints, ≈ 150–200 tests). Delivered in the reviewable
increments above with `pytest`/`ruff`/`mypy` green at each step.

---

## 20. What remains unchanged (explicit)

No change to: Phase 2A foundation (auth, sessions, `authorize()`, audit hash
chain, outbox, config, storage, Money, UUIDv7, RFC-9457, cursor pagination) ·
Phase 2B (business/membership/location, operator profile/base, group/membership,
zone) · Phase 2C (evidence, vehicle/vehicleclass, verification
record/decision/evidence, `subject_meets`/`eligibility`) · any migration, model,
service, or API of 2A–2C · the frontend (Phase 5B/5C) · approved product
decisions · the 14 Job states · the 7 verification states · value bands /
thresholds · the commission model · `RESUME_PRIOR` (stays OPEN) · rating /
reputation (stays DEFERRED).

---

## 21. Founder gate — decision request

**Please confirm before implementation begins:**

1. Proceed with the module layout (§4) and the schema (§5, verbatim from Phase 1).
2. **E-1** — accept that `DISPUTED → RESUME` is **not** built in 2D (only the
   `pre_dispute_status` record); `RESUME_PRIOR` stays a separate founder
   decision.
3. **E-2** — accept **ADR-2D-05 Option (b)**: a conservative deterministic
   driver-trust-ceiling rule from verification facts + `config.value_bands[].
   min_trust_level`, with `high_value_approval` still gating HIGH/VERY_HIGH; the
   full Trust engine is a later phase. *(Or direct otherwise.)*
4. **E-3** — accept provider-neutral outbox events + implemented OTP
   generation/verification, with **no** SMS/WhatsApp provider wired.
5. **E-4 / Q-5 / Q-6 / Q-7** — accept ADR-2D-10 (plain lat/lng, no PostGIS),
   ADR-2D-08 (beat-wire auto-complete + request-expiry sweeps), separate
   `CONFIRMED`/`ASSIGNED` calls in 2D, and deferring RLS to hardening.
6. Confirm the API boundary (§12) is the right shape for the future frontend to
   consume.

On confirmation, implementation proceeds per §19; on any change, the plan is
revised and re-presented.
