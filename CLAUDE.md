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
**Repo:** `C:\Users\ndira\PROJECTS\LOGISTIX` (GitHub: `Bigmanbiggiey/fikisha`).

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
  `RESUME_PRIOR`) is **Platform-Admin-only**, with a fresh step-up; its
  preconditions were decided by the founder 2026-10-20 (ADR-2D-54,
  `docs/trust-and-disputes-plan.md` Part B): disputed before COMPLETED, within
  7 days of the dispute opening, a finding on every serious-type incident, the
  same driver and vehicle still eligible (no replacement), both parties'
  agreement recorded; the pending pickup / delivery is confirmed again. Binding
  dispute resolution **above the Standard band** is also Platform-Admin-only
  (D-ADM-1).

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
  founder approves before any merge. Commits are scoped and conventionally
  messaged. **The founder is the sole author** (founder instruction
  2026-10-13): no `Co-Authored-By: Claude` / `Claude-Session` trailers on
  commits, and no "Generated with Claude Code" lines in PR bodies or comments.
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
| Design Phase 6 — Jobs Frontend: Architecture & Build Plan (`docs/design-phase-6-jobs-frontend-plan.md`) | **APPROVED 2026-09-15**, including the proposed defaults for all 6 open questions (§9 Q1–Q6): single role-aware route tree, no real offline-sync engine this phase, a simple role-switch control, `StaleBadge` presentational-only pending a separate `If-Match` fix, the stated increment order, `RESUME_PRIOR`/rating still out of scope. **Increments 1–3 DONE** (1: frontend infrastructure, 2026-09-15; 2: Business create/monitor a Job, 2026-09-15; 3: Negotiation, 2026-09-16) — see plan §7. Each increment's mandatory live-browser verification caught real defects invisible to the jsdom-based test suite: Increment 2 found `ADR-2B-11` (`GET /businesses` never populated `my_role`, so a fresh business never showed up as a workspace); Increment 3 found a backend CORS gap blocking every job-creation/lifecycle request in a real browser (missing `Idempotency-Key` in `CORS_ALLOW_HEADERS`, present since Increment 1) plus `ADR-2D-31`/`ADR-2D-32` (negotiation thread payload gaps). **Increments 4–7 DONE** (4: Operator discover/negotiate/assign, 2026-09-21; 5: Driver physical delivery, 2026-09-22; 6: Recipient scoped link, 2026-09-22; 7: Incidents & Disputes, 2026-09-22), plus Increment 3 code-review fixes (2026-09-17). Each closed a small backend gap its approved scope required (operator work discovery + assignment-candidates endpoints; recipient report-issue photos; incident evidence/statements read + evidence content streaming; see `phase-2d-api.md`). Later live checks found: raw error codes shown to users (`localizeError`), arrival geo silently dropped + photo/signature uploads impossible in `jobsApi`, a Geolocation permission-prompt hang, a stale dispute cache. Recorded scope decisions: Group Manager driver-pool assign deferred; recipient OTP always mandatory; Resume is a permanently disabled shell (O-P1 open); no MFA UI (backend has no step-up enforcement yet); no cross-job incident queue until Increment 8. **Increment 8 DONE** (Operations Officer console, 2026-09-23; ADR-2D-33..36): Ops overview/monitor/high-value/audit screens, a Job Detail staff panel (operational note visible to parties, audited contact reveal, band-limited staff cancel — Ops ≤ STANDARD, above → Platform Admin, enforced by the new `AdminCancelBandAuthorised` guard), and the Ops Officer config permissions now actually enforced. Founder declared it done; the in-browser walkthrough was **not** performed (browser extension unavailable) — endpoints were verified over real HTTP instead. Fixed on the way: a `Modal` focus-steal bug (also broke Increment 4's counter-offer), Ops Officers wrongly getting a Platform Admin workspace. 966 backend + 190 frontend tests green. Merged to `main` via PR #3 (2026-09-23). |
| Increment 9a — Admin MFA + step-up (ADR-2D-39) | **DONE, merged via PR #12** (founder decision D-1 (a), `docs/founder-decisions-2026-10-14.md`). TOTP enrolment on an admin's first sign-in (QR + setup key, ten one-time backup codes), a code on every later admin sign-in, step-up before suspend/offboard, config apply, dispute resolution, high-value decisions and staff HIGH-PII views. **An admin's roles apply only on a session that passed MFA.** Secret Fernet-encrypted; production requires `TOTP_ENCRYPTION_KEY`. Full-stack Docker smoke test passes (first on this machine) and now enrols the smoke admin. |
| Follow-ups batch 1 (ADR-2D-40) | **DONE, merged via PR #13 (2026-10-16)** (founder decisions 7–9): contact phones hidden from operators until the job is assigned to them (closes ADR-2D-36); a Platform Admin can reverse a high-value rejection with a reason (append-only `high_value_reversal`, step-up); one 6-character job reference everywhere. |
| Group driver-pool assignment (ADR-2D-41) | **DONE, merged via PR #14 (2026-10-16)** (founder decision 19; scope approved as built 2026-10-15). A Group Manager (or staff) picks any active group member and a group vehicle; in a `DRIVER_ACCEPTS` group a member sees only themselves; a suspended group's pool shows as ineligible. Candidates list and assign screen only — the assign step already enforced group rules. No migration. |
| Design Phase 7 — UI/UX Pass (`docs/design-phase-7-ui-ux-pass-brief.md`) | **APPROVED 2026-09-23** (all recommendations, D-6 amended). Findings-and-proposals phase over the whole Jobs frontend (~38 screens, EN/SW, 360/768/1280px, exception states) against the approved baseline. Docs, screenshots and mockups only, **no code**. Runs **before Increment 9**. It is the audit half of Increment 10; Increment 10 now implements the approved proposals. Capture is a headless Playwright script with seeded accounts. **FINDINGS COMPLETE 2026-09-23** (`design-phase-7-ui-ux-findings.md`): 18 findings (3 Blocker: phone layouts split by the `sm:`=360px breakpoint misuse; one-tap business cancel with no reason or late-cancel warning; the driver gets the business screen and wording instead of the P3 §10.1 Current Job) and 16 proposals. Decision sheet returned 2026-09-23: **all 16 proposals approved**. Once assigned, the driver may see the sender's and receiver's contacts. **Mockups delivered** (private artifact, 8 before/after). **Increment 10 implementation plan drafted** (`docs/design-phase-7-increment-10-plan.md`, 2026-09-23): six stacked sub-increments 10a–10f, frontend only, no backend change. **APPROVED 2026-09-23**, plus a founder-added **Messages inbox** (10g: an aggregate of existing offer threads, Fikisha notes and incident statements, with unread markers; no new chat channel; one read-only endpoint and a read-marker table). Order: 10a→10b→10c→10g, then Increment 9, then 10d/10e/10f. **10a DONE**, merged to `main` via PR #4 (2026-09-28): single-column phone layouts (P-01), business cancel reason + consequence sheet (P-02), recipient code labels (P-10). **10b, 10c, 10g DONE, merged to `main` via PR #5 (2026-10-13)**, built on one branch, `feat/increment-10b-driver-journey`: proof method rows (P-12) and the driver "Current job" view (P-03); role navigation shell with a group-DRIVER workspace (P-04, founder ruling 2026-09-28); Messages inbox (new backend app `fikisha.inbox`, `GET /messages` + `POST /messages/read`, read-marker table only, ADR-2D-37). Last recorded runs: 758 backend tests in the touched modules (2026-09-29), 252 frontend tests (2026-10-13). Re-reviewed 2026-10-13, nothing blocking, four follow-ups posted on PR #5; 988 backend tests passed on its code (2026-10-13). **10d DONE, merged via PR #8** (P-05 translation-driven shared components + login language switcher + an ESLint `react/jsx-no-literals` guard on `src/components`/`src/shell`; P-06 "Online" not "Synced"; P-14 one Kenya-time date helper `services/datetime.ts`, timeline rows show the date when older than today, Ops attention rows get a reason chip, urgency-then-age order and relative age). **10e DONE, merged via PR #9** (P-07 44px targets; P-08 one `<h1>` job header with route + staff context; P-09 DELIVERED is a status, not an action; P-11 "Replaced by a newer offer"; P-13 shared `Textarea`/`Select`; P-15 single-flight token refresh, since the backend revokes the session on refresh-cookie reuse, plus confirmed no duplicate start-up requests in a production build; P-16). **10f DONE, merged via PR #10**: close-out re-capture (43 screens × 360/768/1280 × EN/SW + P3 §22 exception states; scratch Playwright per D-6), no overflow, 0 axe violations, no server errors; fixed F-19 (offline looked empty) and F-20 ("Try again" on 403/404/410). **Increment 10 is COMPLETE.** |
| Design Phase 6 Increment 9 — Platform Admin console (`docs/design-phase-6-increment-9-scope.md`, ADR-2D-38) | **Scope APPROVED 2026-10-13** (D-2 to D-6 as recommended; D-1 admin MFA decided 2026-10-14 and built as 9a). **DONE, merged via PR #7**: Control, Users & organizations (masked phones, audited reveal), suspend/reinstate/offboard (append-only `admin_intervention`), Configuration (read, preview, apply; allowlist commission + timeouts), read-only Commission ledger. New backend module `fikisha.admin_console`. Suspend/offboard and config apply sit behind the step-up gate, which admin MFA (9a) now satisfies. Suspension now really blocks new work (closed gaps: suspended business posting jobs; offboarded operator / suspended group negotiating). 1,042 backend tests, 90% coverage; 265+ frontend tests; live Chrome walkthrough in EN and SW. Not built: weekly statements/settlement/eTIMS (separate increment). |
| Commission & Statements (`docs/commission-statements-plan.md`, ADR-2D-42) | **Plan APPROVED 2026-10-15** (founder decision 5; D-1 to D-8 all as recommended; paybill number to follow; tax-advisor confirmation needed before the first statement reaches a real operator). **S-1 (backend) DONE, merged via PR #16**: new module `fikisha.statements`; append-only `commission_statement` / `statement_line` / `statement_settlement`; weekly run (beat Monday 06:00 EAT, admin run, management command) billing commission once the dispute window has closed; Platform-Admin payment recording and reversal behind step-up; payee, per-job earnings and admin reads; nightly reconciliation. **S-2 (payee screens) DONE, merged via PR #17**: Statements list + detail (unseen marker, "not a tax invoice", how to pay, printable), Home "New statement" card, Job Detail "Earnings for this job"; adds a per-payee `statement_seen` marker. **S-3 (staff screens) DONE, merged via PR #18**: `/ops/statements` list (week and payee filters, invoiced vs paid totals, Platform Admin "Run a week") and detail (Platform Admin record payment / reverse, behind step-up; Ops read-only), Control figure, Commission page link. **Commission & Statements (S-1 to S-3) is complete** (plan PR #15; all merged 2026-10-16). eTIMS still out of scope. |
| Swahili review list (founder decision 20) | **Compiled 2026-10-15, merged via PR #19 (2026-10-16)** (`docs/swahili-review/`): 1,096 strings in one CSV with English source, screen, automatic flags and reviewer columns; `frontend/scripts/swahili-review.mjs` regenerates it (run again on `main` before launch). Needs a native-speaker review; applying corrections is a separate small change. |
| PR #5 follow-ups + placeholders (ADR-2D-43) | **DONE, merged via PR #20 (2026-10-16)** (founder approval 2026-10-16): per-user cache keys for businesses/groups/vehicles; `GET /jobs?status=&assigned=me` so Current job reads past page 1; `GET /messages?kind=` so Messages filters cover the whole inbox; `Incident.last_changed_by` replaces the 2-second "written by you" guess; disputed-job "coming in a later update" placeholders replaced. |
| Edit-conflict protection (ADR-2D-44) | **DONE, merged via PR #21 (2026-10-16)** (founder approval 2026-10-16): `GET /jobs/<id>` sends `ETag`; a job action carrying a stale `If-Match` is refused `412 stale_job` and the app refreshes and says so. Covers every job action through the single lifecycle writer. Deviation recorded: a missing header is still accepted (negotiation, recipient link and sweeps hold no version); making it mandatory is a later one-line switch. |
| Founder assessment 2026-10-19 (`docs/assessment-2026-10-19-plan.md`, ADR-2D-45..48) | **DONE, merged via PR #23** (D-1 to D-6 approved as recommended 2026-10-19). Six parts on one branch chain: plates stored in capitals; pickup from a saved business location; **business and group verification** (registering submits; a reviewer's approval sets the flag; before this no real business could send a job); **operator approval** (`PENDING → ACTIVE` by a verification reviewer) with pending operators locked to their approval screens and refused work server-side; the verification queue **by applicant** (tabs Operators · Businesses · Groups, one page per applicant); cargo categories validated, suggested by EN/SW keywords, taught by a Platform Admin, and setting `latent_risk_cargo` (the 7-day window now applies). 1,156 backend + 330 frontend tests green. |
| Maps (`docs/maps-plan.md`, ADR-2D-49) | **DONE, merged via PR #24** (MD-1 to MD-6 approved as recommended 2026-10-19). Leaflet, loaded only on map screens; tiles from config (MapTiler in production, OpenStreetMap tiles in dev only). Business locations pinned and named; destination picked on the map (pin required while the map loads, typed address as the fallback); pickup copies the saved pin. Exact pins only for the business, staff and the assigned side; an operator still looking sees a ~1 km area (`COARSENED`). Job detail, opportunity and driver views show the pins with "Open in Google Maps". No tracking, no routing. Privacy notice + cross-border transfer for the provider still need legal sign-off. 1,160 backend + 336 frontend tests green. |
| Founder assessment 2026-10-20 (`docs/assessment-2026-10-20-plan.md`, ADR-2D-50) | **DONE, merged via PR #25** (LD-1 to LD-5 approved as recommended 2026-10-20; built on the maps branch). Job screens refresh every 10 s while open; destination by pin or by name; one Kenyan phone rule on every entry point (`07…`/`01…`/`+254…`, 10 digits, stored `+254…`); contact phones by stage (recipient's from pickup, none once closed: changes decision 7); **two-party pickup and delivery** per band (config `custody_proof_rules`, the driver completes, the sender's in-app and recipient's link confirmations recorded in append-only `custody_confirmation`, operator-only fallback retired `410`, changes chain-of-custody §4); admin icons. **Follow-up (PD-1..PD-5, ADR-2D-51):** the sender takes part at every pickup and the driver's photo is proof only (required at every delivery); a job completes when the sender confirms the goods arrived and records paying the operator (`POST /jobs/<id>/close`, append-only `job_payment_record`, Fikisha moves no money); no automatic completion (D-JOB-5 auto-complete superseded; sweep retired); recipient close-off kept until SMS; operator "I haven't been paid" (`NON_PAYMENT` incident); Ops `awaiting_sender` filter. 1,204 backend + 360 frontend tests green. |
| Operator tiers (`docs/operator-tiers-plan.md`, ADR-2D-52) | **DONE, merged via PR #25** (TD-1 to TD-6 approved as recommended 2026-10-20; built on the assessment 2026-10-20 branch). New module `fikisha.trust` replaces the interim rule (decision 12): a stored tier per operator (L1 / L2 / L3 / Restricted; none recorded = L1) with verification as the floor (lapsed = L0), append-only `trust_level_change`. Fikisha **proposes** the next tier when every measured criterion is met (after a job completes and nightly); a Platform Admin confirms or rejects, or promotes / demotes directly (shown as manual), each with a reason and step-up (changes trust-architecture §3). Ratings and at-fault findings show as "not yet measured"; no automatic demotion (TD-5). Restricted = STANDARD only (changes decision 13). "Your tier" card with progress on operator Home and profile; staff panel on the applicant and directory pages; Tier reviews on Control; tiers on the driver pool. 1,231 backend + 368 frontend tests green. |
| Trust engine & dispute rules (`docs/trust-and-disputes-plan.md`, ADR-2D-53) | **Plan APPROVED 2026-10-20** (all decisions as recommended after three review rounds; RC-1 recipient completion left open until before launch). **Part A (trust engine) BUILT, awaiting founder review** on `feat/trust-engine`: incidents close without a dispute (append-only closure; tier checks ignore the operator's own reports); Fikisha's findings (AT_FAULT / NO_FAULT / UNDETERMINED naming business, driver or group, supersedable) and unfounded-report records; two-way ratings (new module `fikisha.ratings`, window = 7 days in COMPLETED, comments staff-only); ratings and findings count toward tiers once a Platform Admin switches `trust_tiers.live_criteria` on (fewer than 3 ratings blocks); admin-confirmed demotion proposals after a serious at-fault finding or a rating drop, remediation exit to L1; business late-cancellation flags; staff business track record; completed jobs + rating shown to businesses while negotiating. 1,331 backend + 387 frontend tests green; PR #26. **Part B (resume a disputed job, ADR-2D-54) BUILT, awaiting founder review** on `feat/dispute-resume` (stacked on PR #26; lifts founder decision 10): Platform Admin + step-up, the checklist above, closures for every linked incident, a resume resolution and attestation, fresh codes for the pending step (recipient link reissued at the destination), earlier confirmations no longer count; resume card on the dispute page, 'resumed' notice on the job. 1,347 backend + 388 frontend tests green. |

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
procedural. Hardening: GitHub branch protection on `main` — **applied
2026-10-14** (founder decision 4, `docs/founder-decisions-2026-10-14.md`):
PRs required (0 approvals, so the founder can merge their own), admins
included, force-pushes and deletion blocked; see `docs/phase-2/phase-2d-final-verification.md`
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
update). From Increment 8 onward, work reaches `main` only through GitHub
PRs that the founder merges: #3 (Increment 8), #4 (10a), #5 (10b/10c/10g),
#6 (docs + lint), then the Increment 9 PR.

> **CURRENT STOP LINE.** Design Phase 3–5B, Phase 2D (backend), and Design
> Phase 6 (Jobs-frontend plan) are all founder-APPROVED as of 2026-09-15.
> Implementation is authorized, increment by increment per the plan's §7
> sequence; Increments 1–9 are done (frontend infrastructure; Business
> create/monitor a Job; Negotiation; Operator; Driver; Recipient; Incidents &
> Disputes; Operations Officer console; Platform Admin console, except admin
> MFA). Each increment should land reviewably,
> the way Phase 2D's eleven increments did — not as one giant diff.
> **Design Phase 7 (UI/UX Pass)**: findings and all 16 proposals approved
> 2026-09-23; **Increment 10 is complete** (10a–10g merged). Increment 9 is
> merged; admin MFA (9a) is merged. The founder's 2026-10-14 decisions
> (`docs/founder-decisions-2026-10-14.md`) set the next work: a follow-ups
> batch (phones hidden until assignment, reversible high-value rejection,
> 6-character references), group driver-pool assignment, then Commission &
> Statements (weekly statements + manual settlement; eTIMS later).
> Still not started / not permitted without explicit founder approval:
> anything in the Trust & Reputation engine beyond the operator tiers of
> ADR-2D-52 and `docs/trust-and-disputes-plan.md` (founder-approved
> 2026-10-20: ratings, findings, admin-confirmed demotion proposals, and the
> `RESUME_PRIOR` contract of its Part B — replacing the driver or vehicle on
> resume is not approved) · recipient
> completion (RC-1, open until before launch) · any wired
> SMS/WhatsApp/M-Pesa/eTIMS provider · GPS/route optimisation · AI dispatch
> · fleet scheduling · native apps · deploy · merging further work to `main`
> without asking first.

---

## 8. Quick pointers

- Backend modules: `backend/fikisha/{common,audit,outbox,platform_config,identity,storage,business,operators,groups,evidence,vehicles,verification,jobs,negotiation,incidents,inbox,admin_console,statements}`.
- ADRs: `docs/phase-2/phase-2a-decisions.md`, `phase-2b-decisions.md`, `phase-2c-decisions.md`, `phase-2d-decisions.md` (2D-01–2D-30, promoted out of `phase-2d-plan.md` §14 in Step 15).
- Repro/verify commands: `docs/phase-2/phase-2X-summary.md` files (incl. `phase-2d-summary.md`); `scripts/smoke-test.sh`; Phase 2D's full endpoint reference is `docs/phase-2/phase-2d-api.md`; its verification evidence is `docs/phase-2/phase-2d-final-verification.md`.
- Design lineage: `design-brief.md` (P0) → `design-phase-1-ia.md` (P1) → `design-phase-2-user-flows.md` (P2) → `design-phase-3-wireframes.md` (P3) → `design-phase-4-visual-system.md` (P4) → `design-phase-5-brand-palette.md` (P5A) → `design-phase-5-implementation.md` (P5B, tokens live in `frontend/src/design/tokens.ts`) → `design-phase-5c-screen-migration.md` (P5C, partial — see §7) → `design-phase-6-jobs-frontend-plan.md` (P6, APPROVED — the actual Jobs-frontend build plan; Increments 1–8 done, see §7 status table).
- Memory index for cross-session context lives outside the repo (Claude auto-memory).
- **Before assuming `main` is a clean, founder-approved baseline, read §7's Process Exception note.**
