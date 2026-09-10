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
| Design Phase 3 — Wireframes | **NOT STARTED** |

Working branch: `feat/phase-2c-vehicles-verification` (design-track docs committed
here; **not merged to `main`**).

> **CURRENT STOP LINE — Do not begin Design Phase 3 until separately instructed.**
> Also not started / not permitted without explicit founder approval: any Jobs,
> job lifecycle, negotiation, pricing, assignment, dispatch, trust score / trust
> levels / value-band eligibility engine, ratings, incidents, disputes, custody,
> pickup OTP, delivery, recipient links, commission, payments, M-Pesa, eTIMS,
> SMS, WhatsApp, GPS, route optimisation, AI matching, fleet scheduling, or
> native apps. Recommended next build phase = Trust & Reputation, then Jobs.

---

## 8. Quick pointers

- Backend modules: `backend/fikisha/{common,audit,outbox,platform_config,identity,storage,business,operators,groups,evidence,vehicles,verification}`.
- ADRs: `docs/phase-2/phase-2a-decisions.md`, `phase-2b-decisions.md`, `phase-2c-decisions.md`.
- Repro/verify commands: `docs/phase-2/phase-2X-summary.md` files; `scripts/smoke-test.sh`.
- Design lineage: `design-brief.md` (P0) → `design-phase-1-ia.md` (P1) → `design-phase-2-user-flows.md` (P2) → Design Phase 3 (wireframes, not started).
- Memory index for cross-session context lives outside the repo (Claude auto-memory).
