# CLAUDE.md — Fikisha operating contract

This file is a **navigation and operating contract**, not a substitute for the
source-of-truth documentation. Read it first, then follow the linked docs.

**Authoritative sources (in precedence order):**

1. The **founder / product owner** (final product decision-maker).
2. **Approved product decisions** — `docs/phase-0/` (esp. `decisions.md`,
   `decision-memo-2026-09-08.md`, `functional-requirements.md`, `legal-scope.md`).
3. **Approved architecture** — `docs/phase-1/` (esp. `database-design.md`,
   `job-state-machine.md`, `trust-architecture.md`, `verification-architecture.md`,
   `negotiation-architecture.md`, `notification-architecture.md`,
   `commission-ledger.md`, `security-architecture.md`,
   `authentication-authorization.md`).
4. **Implemented foundation** — `docs/phase-2/` (2A foundation, 2B identity/orgs,
   2C vehicles/verification) + the `phase-2X-decisions.md` ADR files.
5. **Design track** — `docs/design-brief.md` (Design Phase 0),
   `docs/design-phase-1-ia.md` (IA), `docs/design-phase-2-user-flows.md` (User Flows).
6. **This file** and `docs/team-skills-policy.md` (how Claude works here).

If any instruction, skill, or generated plan conflicts with 1–5, **STOP** (see
§ "STOP rule") — do not silently reconcile it.

---

## 1. Authority hierarchy

```
FOUNDER / PRODUCT OWNER
   → APPROVED PRODUCT DECISIONS
   → PROJECT PHASE + APPROVAL GATE
   → PROJECT RULES / CLAUDE.md
   → RELEVANT SKILLS
   → CLAUDE / SUBAGENTS
   → IMPLEMENTATION → VERIFICATION → REVIEW
   → FOUNDER APPROVAL
   → MERGE / RELEASE
```

**Fundamental rule:** *Skills advise and execute within an approved phase. Skills
do not define the phase, override product decisions, or bypass founder approval
gates.*

No installed skill, plugin, subagent, MCP server, slash command, or automated
workflow has authority to: change an approved product decision · change
architecture without approval · skip a phase · bypass an approval gate · merge
code · deploy · introduce a new business rule · silently expand scope.

Claude may **recommend**; the founder **decides**.

---

## 2. Project identity

**Fikisha** — a local logistics coordination marketplace/platform connecting
businesses/customers with **verified local transport operators** across all
vehicle classes (motorcycle → trailer). It **digitises existing practice**
(stages/bases/yards, direct phone/WhatsApp contact, price negotiation, amicable
dispute resolution) rather than replacing it. It coordinates non-owned capacity.

**Pilot:** Kitengela, Kajiado County + environs. **Languages:** English + Swahili,
both first-class (Swahili prominent on operator/driver screens).
**Repo:** `C:\Users\PCMF\PROJECTS\LOGISTIX`.

---

## 3. Architecture (as approved & implemented)

- **Backend:** Django 5.2 + DRF, **modular monolith** (Django apps as bounded
  modules).
- **Frontend:** React 18 + TypeScript + Vite, **PWA**, mobile-first, offline-aware.
- **Data:** PostgreSQL 16. **Async:** Celery 5.4 + Redis 7.
- **Storage:** S3-compatible object storage behind a `PrivateStorage` ABC /
  `get_storage()` resolver — evidence bytes stream through the API, never a signed
  bucket URL.
- **Local dev:** Docker Compose (`db` / `redis` / `backend` / `worker` / `beat` /
  `frontend`; host ports offset 5433/6380).
- **Transactional outbox** — `emit()` writes in the caller's DB transaction;
  Celery `drain_outbox` publishes with retry + dead-letter.
- **External providers behind adapters** — SMS / WhatsApp / M-Pesa / eTIMS / maps
  are all provider-agnostic seams; none is wired in yet.

**Module boundary rule:** never import another module's model class. Interact only
via that module's public `services` / `authz` surface or domain events.
Cross-module FKs use string references (e.g. `"operators.OperatorProfile"`).

---

## 4. Critical invariants (do not violate; changing one is a STOP)

**Jobs & lifecycle** *(design-level until the Jobs phase is approved)*
- The **Job** is the fundamental domain object.
- **One authoritative Job lifecycle — exactly 14 states:** `DRAFT · REQUESTED ·
  NEGOTIATING · CONFIRMED · ASSIGNED · AT_PICKUP · PICKED_UP · IN_TRANSIT ·
  AT_DESTINATION · DELIVERED · COMPLETED · CANCELLED · FAILED · DISPUTED`. The UI
  may use human-friendly labels but must not invent, rename, collapse, or
  re-map states.
- **`JobLifecycleService.transition()` is the single writer** of `job.status`.
  No raw `UPDATE` of job status anywhere else; guards + concurrency control live
  in the service.
- `DISPUTED` is a freeze. `DISPUTED → <pre_dispute_status>` (RESUME /
  `RESUME_PRIOR`) is **Platform-Admin-only**; its exact preconditions remain an
  **open Phase-0 item** — do not invent them. Binding dispute resolution **above
  the Standard band** is also Platform-Admin-only (D-ADM-1).

**Integrity & security**
- **Append-only** where specified: `audit_log_entry`, `job_event` (custody /
  status / system / admin), `commission_record` / `commission_adjustment` /
  `commission_statement` / `statement_line` / `statement_settlement`,
  `VerificationDecision`, `EvidenceAccessLog`. Enforced at service + model +
  Postgres `BEFORE UPDATE/DELETE` trigger layers.
- **Hash-chained audit** — `audit.record()` asserts `in_atomic_block`; every
  sensitive change (incl. founder/admin actions) is audited in the same
  transaction. No code path performs a sensitive change without `audit.record()`.
- **Server-side authorization is authoritative** — central
  `authorize(actor, action, resource) -> Decision`, default-deny, `@policy`
  decorator, exact-then-longest-wildcard resolution. Navigation scoping / hiding
  links is UX only, never the enforcement mechanism.
- IDOR/BOLA tests are required for every org-scoped or subject-scoped endpoint.

**Trust, verification, value bands**
- **Verification ≠ trust.** Verification records independently-checked **facts**
  (per subject × domain; states `NOT_SUBMITTED · SUBMITTED · IN_REVIEW ·
  INFO_REQUESTED · VERIFIED · REJECTED · EXPIRED`; `effective_state()` folds
  expiry deterministically on read). It computes **no** trust, reputation,
  eligibility, or job eligibility.
- An operator/reviewer **cannot act on a verification record they submitted**
  (`reviewer_is_submitter`).
- Evidence is **not** a DB blob — it goes through the storage abstraction;
  access is authorised **explicitly per fetch** (subject owner or reviewer only,
  never inherited from the parent); HIGH-PII fetches write `EvidenceAccessLog`.
- **Value-band gating uses the assigned driver's (and vehicle's) eligibility** —
  the specific person + vehicle, solo or in a group. A group is **not** a
  substitute for the driver's required trust eligibility. Bands:
  `STANDARD ≤ 50,000` (L1) · `ELEVATED 50,001–250,000` (L2) ·
  `HIGH 250,001–1,000,000` (L3 + admin pre-assignment review) ·
  `VERY_HIGH > 1,000,000` (L3 + per-Job Platform-Admin approval).
  `high_value_threshold_kes = 250,000`.

**Payments / revenue**
- **No wallet, no escrow, no fare custody.** Fikisha never holds the transport
  fare.
- Approved model: **commission on completed Jobs** — `rate = 10%`,
  `min = KES 40`, `cap = KES 5,000` per Job (config: `rate=0.10, min_fee_kes=4000,
  cap_kes=500000` minor units); **weekly M-Pesa statement**; **eTIMS**
  records/invoices as legally validated. `commission_record` is **immutable** and
  **config-version-pinned**; corrections are `commission_adjustment` rows
  (admin-signed, reasoned, audited). No `commission_record` for `CANCELLED` /
  `FAILED` Jobs.
- Cancellation flag = **3 *late* cancellations** (after `ASSIGNED`, before
  `AT_PICKUP`) or wasted trips in a rolling 30-day window → admin-review flag,
  tracked **per side**. Not a generic all-cancellations counter.

**Communication & scope limits (MVP)**
- **Negotiation is the authoritative in-app record** — parallel per-(Job×operator)
  sealed threads, immutable append-only history, agreed price frozen on
  agreement. **WhatsApp is a notification/link channel, not the system of
  record.** OTP is **SMS-primary**; WhatsApp may additionally carry OTP;
  ordinary Job notifications fall back **WhatsApp → SMS**; an in-app notification
  is always written.
- Pickup/delivery proof is **band-dependent** (see
  `docs/phase-1/chain-of-custody.md` + `docs/design-phase-2-user-flows.md` §38–44):
  STANDARD allows an operator-attested fallback (photo + contact name → capped at
  STANDARD); ELEVATED+ has none (transition refused).
- **Not in MVP:** continuous GPS / live-tracking UI · AI dispatch · route
  optimization · nationwide scope · complex fleet management (payroll, shift
  scheduling, driver transfers, enterprise fleet) · native mobile apps · Stripe
  or any third-party fare-custody. Driver is **not** a standalone account — it is
  a `GroupMembership(role=DRIVER)` or an individual operator acting as their own
  driver; a group DRIVER sees work/discovery only when the group is
  `DRIVER_ACCEPTS`.

**Engineering conventions**
- **Money:** integer **KES minor units** everywhere (no floats for money).
- **IDs:** UUIDv7 primary keys (`fikisha/common/uuid7.py`).
- **API:** RFC 9457 problem+json (`code`, `request_id`); cursor pagination
  (`{data, page:{next_cursor, prev_cursor}}`); `Idempotency-Key` on creates.
- **Typing:** **pragmatic mypy** (ADR-2A-08) — not `--strict`; keeps
  `disallow_untyped_defs` / `check_untyped_defs`; relaxes
  `disallow_any_generics` / `warn_return_any`; documented per-module overrides.
  Do not "upgrade" to strict without approval.
- **Lint/format:** ruff (configured `ignore` list + per-file-ignores) + ruff
  format. **Tests:** pytest (backend) with required security tests; vitest
  (frontend). A phase is not done until the full suite is green and a smoke run
  is recorded.
- **Logging:** structlog JSON with PII scrub.

---

## 5. How work proceeds here — the phase model

Fikisha runs **phase by phase**. Each phase: founder pastes a detailed brief →
Claude executes exactly that scope → Claude **STOPS** and awaits founder review /
approval. Phases deliberately separate **research → plan → architecture → [gate]
→ implement → test → verify → security → review → [gate] → merge → release**.

- **No premature implementation.** Documentation/design phases produce docs only.
- **No silent product or architecture decisions.** Where a brief leaves a detail
  open, record it as an ADR (`docs/phase-2/phase-2X-decisions.md` style) or an
  open question — never decide it silently.
- **Branch, don't merge to `main`.** Work on the phase's feature branch; the
  founder approves before any merge. Commits are scoped, conventionally messaged,
  and carry the `Co-Authored-By` + `Claude-Session` trailers.
- **Deviations** from an approved doc must be documented with rationale and a
  "why it's safe" note, and must not touch an approved **product** decision.

### STOP rule

Claude must **stop and request founder direction** when:

- a product decision is required;
- architecture must change;
- a phase boundary is reached;
- an approved invariant (§4) would need to change;
- requirements conflict (brief vs. approved docs, or two approved docs);
- legal/compliance interpretation is required;
- a security decision exceeds implementation detail;
- a new external service or payment mechanism is proposed;
- scope expansion is discovered.

Claude may recommend a solution in the same breath — but must not silently decide.

---

## 6. Skills & tooling

The full policy is `docs/team-skills-policy.md`; the inventory and rationale are
`docs/claude-code-toolkit-audit.md`. Operating summary:

- **Curated, phase-gated, opt-in.** Load the **minimum relevant skill set** for
  the current project + phase + task + risk level. More skills ≠ better result.
- **Standard quality gates** (apply by task risk, not mechanically):
  *verification-before-completion* (evidence, not intention, backs any "complete"
  claim) · `/code-review` → `/full-review` review ladder · STRIDE / `claude-security`
  scan-changes / backend-API-security review for security-sensitive changes ·
  migration observability + rollback check before significant migrations.
- **Rejected / not part of the standard model:** superpowers `using-superpowers`
  (forced skill preamble); full-auto feature orchestrators (`/feature-development`,
  `/full-stack-feature`, `/feature-dev` end-to-end) that bundle
  architecture→impl→deploy; automatic `using-git-worktrees` /
  `dispatching-parallel-agents` / `subagent-driven-development` (parallel work is
  approval-gated); broad autonomous refactor/cleanup sweeps without explicit
  scope; **Stripe** (out of scope — commission + M-Pesa statement + eTIMS, no
  wallet/escrow/fare custody).
- **Plugin/skill updates are governed** — never auto-update; never update
  community plugins mid-phase; record plugin · old→new version · reason · impact ·
  affected projects · approval status (see `docs/team-skills-policy.md`).
- MCP servers (`github`, `figma`) act on real accounts — explicit per-action
  instruction only. `stripe` MCP stays disabled.

---

## 7. Current status & STOP LINE

| Phase | State |
| --- | --- |
| Phase 0 — Product | APPROVED |
| Phase 1 — Architecture | APPROVED |
| Phase 2A — Foundation | APPROVED |
| Phase 2B — Identity / Organizations | APPROVED |
| Phase 2C — Vehicles / Verification | APPROVED |
| Design Phase 0 — Product Design Foundation (`docs/design-brief.md`) | APPROVED |
| Design Phase 1 — Information Architecture (`docs/design-phase-1-ia.md`) | APPROVED |
| Design Phase 2 — User Flows (`docs/design-phase-2-user-flows.md`) | APPROVED |
| Design Phase 3 — Wireframes (`docs/design-phase-3-wireframes.md`) | APPROVED (documentation baseline) |
| Design Phase 4 — Visual System (`docs/design-phase-4-visual-system.md`) | APPROVED (visual system baseline; final brand hex values were gated separately — see Phase 5A) |
| Design Phase 5A — Brand Palette (`docs/design-phase-5-brand-palette.md`) | APPROVED — Option A "Stage & Yard" |
| Design Phase 5B — Production Tokens (`docs/design-phase-5-implementation.md`) | COMPLETE — tokens + 13 foundational primitives implemented in `frontend/` |
| Design Phase 5C — Screen Migration (`docs/design-phase-5c-screen-migration.md`) | PARTIAL — all 15 pre-existing screens migrated; the Job/workspace screens (Business/Operator/Driver/Ops/Platform Admin/Recipient) are **escalated, not built** — they need a Jobs backend, which did not exist when 5C ran |
| Phase 2D — Jobs & Core Coordination (backend) (`docs/phase-2/phase-2d-summary.md`, `-decisions.md`, `-api.md`, `-final-verification.md`) | **APPROVED — second founder gate (plan §19 Step 16) cleared 2026-09-15.** Increments 1–11 + 2 verification corrective passes (BLOCKER-1, tiebreaker fix) + Steps 12–15 (invariant/atomicity tests, static+migration+Docker verification, a manual STRIDE security pass, doc promotion) all done. 904 backend tests, 90% coverage, full-stack Docker smoke test passed. Still no merge-to-`main` gate exception beyond the ratified Process Exception, no deploy. |
| Design Phase 6 — Jobs Frontend: Architecture & Build Plan (`docs/design-phase-6-jobs-frontend-plan.md`) | **APPROVED 2026-09-15**, including the proposed defaults for all 6 open questions (§9 Q1–Q6): single role-aware route tree, no real offline-sync engine this phase, a simple role-switch control, `StaleBadge` presentational-only pending a separate `If-Match` fix, the stated increment order, `RESUME_PRIOR`/rating still out of scope. **Increments 1–3 DONE** (1: frontend infrastructure, 2026-09-15; 2: Business create/monitor a Job, 2026-09-15; 3: Negotiation, 2026-09-16) — see plan §7. Each increment's mandatory live-browser verification caught real defects invisible to the jsdom-based test suite: Increment 2 found `ADR-2B-11` (`GET /businesses` never populated `my_role`, so a fresh business never showed up as a workspace); Increment 3 found a backend CORS gap blocking every job-creation/lifecycle request in a real browser (missing `Idempotency-Key` in `CORS_ALLOW_HEADERS`, present since Increment 1) plus `ADR-2D-31`/`ADR-2D-32` (negotiation thread payload gaps). **Increments 4–7 DONE** (4: Operator discover/negotiate/assign, 2026-09-21; 5: Driver physical delivery, 2026-09-22; 6: Recipient scoped link, 2026-09-22; 7: Incidents & Disputes, 2026-09-22), plus Increment 3 code-review fixes (2026-09-17). Each closed a small backend gap its approved scope required (operator work discovery + assignment-candidates endpoints; recipient report-issue photos; incident evidence/statements read + evidence content streaming; see `phase-2d-api.md`). Later live checks found: raw error codes shown to users (`localizeError`), arrival geo silently dropped + photo/signature uploads impossible in `jobsApi`, a Geolocation permission-prompt hang, a stale dispute cache. Recorded scope decisions: Group Manager driver-pool assign deferred; recipient OTP always mandatory; Resume is a permanently disabled shell (O-P1 open); no MFA UI (backend has no step-up enforcement yet); no cross-job incident queue until Increment 8. 169 frontend tests green. Next: Increment 8 (Operations Officer console), pending founder review of Increments 4–7. |

**Process exception — read before assuming `main` reflects an approved gate.**
On 2026-09-11 21:24 +0300, `feat/phase-2d-jobs` was fast-forward-merged into
`main` and pushed to `origin/main` (GitHub) in a local operation with no
founder approval recorded and no PR — a direct violation of §5's "founder
approves before any merge" rule. It happened shortly after (ordering not
fully reconstructable) the Phase 2D final-verification report identified a
still-open **MERGE BLOCKER** (`docs/phase-2/phase-2d-final-verification.md`
§"Phase 2D Flaky-Test Investigation") — i.e. it was not merged from an
approved-clean state either way. Discovered 2026-09-15; the MERGE BLOCKER
was fixed the same day (`fix/phase-2d-tiebreaker-defects`, commit `66f3b8c`,
see the report's "Tiebreaker Corrective Verification" section). The Founder
reviewed this finding on 2026-09-15 and **retroactively ratified `main`'s
current state** rather than reverting/force-pushing over public history —
the code itself is real, tested, and now blocker-free; the failure was
procedural. Hardening in progress: GitHub branch protection on `main`
(require PRs, block direct pushes) — **not yet applied**, no GitHub API
access from this environment; see `docs/phase-2/phase-2d-final-verification.md`
for full forensic detail. Treat any future direct push/fast-forward to
`main` outside an explicit founder instruction as the same class of
violation, branch protection or not.

Working branch: `main` (Phase 2D's Steps 12–15 closing work, the Design
Phase 6 plan, and the plan's Increments 1–3 were all done and committed
directly to `main` 2026-09-15/16, per explicit founder instruction to close
out Phase 2D and then proceed to the Jobs frontend; see
`docs/phase-2/phase-2d-summary.md` and `docs/design-phase-6-jobs-frontend-plan.md`).
From the Increment 3 code-review fixes onward, each increment was built on its
own stacked feature branch (`fix/increment-3-code-review-findings` →
`feat/phase-6-increment-4-operator` → `-5-driver` → `-6-recipient` →
`-7-incidents-disputes`); on 2026-09-23 the founder instructed that `main` be
updated to include them (fast-forward to the Increment 7 tip plus this docs
update).

> **CURRENT STOP LINE.** Design Phase 3–5B, Phase 2D (backend), and Design
> Phase 6 (Jobs-frontend plan) are all founder-APPROVED as of 2026-09-15.
> Implementation is authorized, increment by increment per the plan's §7
> sequence; Increments 1–7 are done (frontend infrastructure; Business
> create/monitor a Job; Negotiation; Operator; Driver; Recipient; Incidents &
> Disputes). Each increment should land reviewably,
> the way Phase 2D's eleven increments did — not as one giant diff.
> Increment 8 (Operations Officer console) is next, pending founder review
> of Increments 4–7.
> Still not started / not permitted without explicit founder approval: a
> real Trust & Reputation engine (Phase 2D uses only the interim
> conservative deterministic rule, ADR-2D-05 Option b) · ratings ·
> `RESUME_PRIOR` preconditions (still an open Phase-0 item) · any wired
> SMS/WhatsApp/M-Pesa/eTIMS provider · GPS/route optimisation · AI dispatch
> · fleet scheduling · native apps · deploy · merging further work to `main`
> without asking first.

---

## 8. Quick pointers

- Backend modules: `backend/fikisha/{common,audit,outbox,platform_config,identity,storage,business,operators,groups,evidence,vehicles,verification,jobs,negotiation,incidents}`.
- ADRs: `docs/phase-2/phase-2a-decisions.md`, `phase-2b-decisions.md`, `phase-2c-decisions.md`, `phase-2d-decisions.md` (2D-01–2D-30, promoted out of `phase-2d-plan.md` §14 in Step 15).
- Repro/verify commands: `docs/phase-2/phase-2X-summary.md` files (incl. `phase-2d-summary.md`); `scripts/smoke-test.sh`; Phase 2D's full endpoint reference is `docs/phase-2/phase-2d-api.md`; its verification evidence is `docs/phase-2/phase-2d-final-verification.md`.
- Design lineage: `design-brief.md` (P0) → `design-phase-1-ia.md` (P1) → `design-phase-2-user-flows.md` (P2) → `design-phase-3-wireframes.md` (P3) → `design-phase-4-visual-system.md` (P4) → `design-phase-5-brand-palette.md` (P5A) → `design-phase-5-implementation.md` (P5B, tokens live in `frontend/src/design/tokens.ts`) → `design-phase-5c-screen-migration.md` (P5C, partial — see §7) → `design-phase-6-jobs-frontend-plan.md` (P6, APPROVED — the actual Jobs-frontend build plan; Increments 1–7 done, see §7 status table).
- Memory index for cross-session context lives outside the repo (Claude auto-memory).
- **Before assuming `main` is a clean, founder-approved baseline, read §7's Process Exception note.**
