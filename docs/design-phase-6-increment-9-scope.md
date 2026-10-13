# Increment 9 — Platform Admin console: scope (DRAFT)

**Status:** DRAFT, 2026-10-13. For founder review. **No code is written until
this is approved.**
**Parent plan:** `design-phase-6-jobs-frontend-plan.md` §7, "Increment 9 —
Platform Admin console (P3 §19)".
**Sources:**
- Wireframes: `design-phase-3-wireframes.md` §19 and §16.
- Product decisions: `phase-0/decisions.md` D-ADM-1, and
  `functional-requirements.md` FR-ADM-4/7/8.
- Architecture: `phase-1/authentication-authorization.md` §1.2 and its
  permission matrix; `security-architecture.md` item 17;
  `commission-ledger.md` §3.3–3.5.
- What exists today: the backend code as of `main` @ `78e8835` (plus
  PR #5).

---

## 1. What §19 asks for

| § | Screen / action | One line |
|---|---|---|
| 19.1 | Control overview | Platform health, plus the queues only a Platform Admin can clear: above-Standard binding disputes, resume requests, suspension/offboarding requests, config change requests |
| 19.2 | Admin action shell | One pattern for every Platform-Admin-only action: review → **reason** → **fresh MFA** (resume, suspend/offboard, config) → confirm restating action and target → apply → audit row in the same transaction |
| 19.3 | Configuration | Live config shown **read-only**, with a "propose change" flow that produces a new version for approval |
| 19.4 | Commission & statements | Per-job `commission_record`s, adjustments, weekly statements, settlement status. No wallet, no balance, no pay action |
| 19.5 | Users & organizations | Businesses, operators, groups and memberships; view, plus the gated suspend/offboard action |

Navigation (P3 §19): **Control · Jobs · Verification** primary; Trust &
Reputation · Incidents & Disputes · Users & Organizations · Configuration ·
Commission · Audit · System secondary. Desktop-first, with a sidebar.

## 2. What the backend supports today

| Need | State | Evidence |
|---|---|---|
| Admin TOTP login + **step-up** re-auth | **Missing.** `is_step_up_fresh` is a stub that is always `False` and nothing reads it. There is no TOTP device, enrolment or challenge | `identity/authz/actors.py:20` |
| Above-Standard dispute queue | **Exists.** `GET /ops/disputes`; Platform Admin resolution with REDUCE/WAIVE shipped in Increment 7 | `phase-2d-api.md` §4a |
| High-value (HIGH / VERY_HIGH) approval | **Exists** (Increment 8) | `POST /jobs/<id>/high-value-decision` |
| `DISPUTED → RESUME` | **Blocked.** No backend; a CHECK constraint excludes it; O-P1 is still open | plan §7 Increment 7 |
| Suspend / restrict / offboard | **Statuses only.** `UserStatus`, `OperatorStatus`, `BusinessStanding`, `GroupStanding` and `VehicleStatus` each have a SUSPENDED or OFFBOARDED value, and the job guards already respect operator and group suspension. There is **no service, endpoint, reason/duration record or reinstate** for any of them | `operators/models.py`, `business/models.py`, `jobs/guards.py:85,172` |
| Configuration change | **Service only.** `platform_config.services.apply_change(patch, changed_by, rationale)` versions, validates, audits and emits. There is **no API**, no proposal/approval record and no diff endpoint | `platform_config/services.py:86` |
| Config read (admin) | **Partial.** `GET /reference` is the public subset; there is no full admin read | `identity/api/urls.py:20` |
| Commission records | **Per-job only:** `GET /jobs/<id>/commission`. No cross-job list | `jobs/api/urls.py:42` |
| Commission adjustments | **REDUCTION / WAIVER only**, and only from dispute resolution. The DB constrains them to always reduce commission. Phase 1's `MANUAL_CREDIT`, `MANUAL_DEBIT` and `REVERSAL` were never built | `jobs/constants.py:245` |
| Weekly statements, settlement, eTIMS | **Missing entirely.** No statement, statement-line or settlement models, and no statement run | `commission-ledger.md` §3.3–3.4 vs code |
| Users & orgs list (all orgs) | **Missing.** Collection endpoints list the caller's own orgs; `is_platform_admin` only widens *updates* | `business/services.py:146` |
| Trust-level confirmation queue | **Not permitted.** Trust is still the interim rule (ADR-2D-05); the real Trust & Reputation phase isn't approved | CLAUDE.md §7 stop line |
| Audit read | **Exists** (Increment 8): `GET /audit/entries` | |

**In short:** the "Platform-Admin-only" actions that §19.2 is built around
(suspend, configuration change, statements) have **no backend yet**, and the
MFA step that §19.2 and Phase 1 require for them has never been built.
Increment 9 is therefore not a frontend-only increment. That is the decision
below.

## 3. Decisions needed from the founder

Each has a recommendation. **Nothing here is decided until you say so.**

### D-1 — Admin MFA and step-up (blocking)

Phase 1 requires mandatory TOTP for admins and a **fresh TOTP step-up** for
config change, suspension, dispute resolution, high-value approval and HIGH-PII
views (`authentication-authorization.md` §1.2; D-ADM-1 "MFA mandatory"). None
of this exists, and Increments 7–8 already shipped dispute resolution and
high-value approval without it (recorded there as "revisit with Increment 9").

- **(a) Recommended: build it first, as sub-increment 9a.** TOTP device and
  forced enrolment on an admin's first login, TOTP at admin login, hashed
  backup codes, a step-up endpoint that sets a short freshness window, and a
  `StepUpFresh` check on the actions above, including the two already
  shipped. This is backend security work and gets a STRIDE pass. It adds an
  authenticator-app step for you and any Ops Officer.
- (b) Ship the console's actions without step-up and record a deviation ADR.
  This changes an approved security architecture, so it isn't mine to choose.
  It would also leave suspension and config change, the two most powerful
  actions, behind a single phone OTP.
- (c) Ship a read-only console now (overview, users and orgs, config view,
  commission view) and hold every new *action* until (a) is done.

### D-2 — Suspension: what it does to work in progress (blocking for 9c)

FR-ADM-4 says "suspend / restrict / offboard with reason and duration". The
statuses exist, but no approved doc says what happens to a suspended party's
**in-flight** jobs.

- **Recommended:** suspension blocks *new* work only (discovery,
  negotiation, assignment), and the existing guards already enforce that.
  In-flight jobs carry on, and an Ops note flags them for monitoring. Any
  cancellation is a separate, explicit staff action under the existing
  band-limited cancel.
- **Duration:** record it, but **no automatic reinstatement** in 9; a
  Platform Admin reinstates by hand. Auto-expiry needs a scheduled job and a
  rule for jobs blocked meanwhile; that can come later.
- **Targets:** operator profile, business account and group (each has its
  own standing), plus the user account (blocks sign-in). Vehicle suspension
  already exists (Phase 2C) and is unchanged.
- **Offboard:** terminal in 9; there's no un-offboard.
- **Restrict:** `OperatorStatus.RESTRICTED` exists, but nothing says what it
  allows. Recommendation: leave it out of 9 until you define it.

### D-3 — Configuration change: who approves a "proposal"?

§19.3 says "propose change → new version for approval". In the pilot the
Platform Admin is you, and there's no second Platform Admin to approve.
The Phase 1 matrix says "Platform Admin + step-up + rationale".

- **Recommended:** a two-step flow for **one** admin. (1) Draft the change:
  edit values, see a diff against the live version and the effect (e.g. "the
  commission on a KES 3,000 job goes from 300 to 240"). (2) Apply it, with
  reason + step-up + confirm, which creates the new version. "Approval" is
  your own confirmation, reviewed afterwards at the weekly pilot governance
  meeting (`pilot-strategy.md` §6). There is no pending-proposal queue in 9.
  If a second approver is wanted later, it fits into the same flow.
- **Which keys are editable in 9.** Recommended:
  - **Editable:** commission rate, minimum and cap; offer and timeout
    durations.
  - **Read-only in 9:** value-band thresholds, `role_permissions`, vehicle
    classes and verification requirements. Value bands and permissions
    underpin approved invariants (CLAUDE.md §4) and privilege boundaries;
    changing them from a screen deserves its own decision.

### D-4 — Commission & statements: how much of §19.4

Weekly statements, settlement and eTIMS have **no backend**, and eTIMS is a
still-unvalidated legal item. M-Pesa/eTIMS providers are also outside what's
currently permitted.

- **Recommended for 9:**
  - A read-only **commission ledger**: all `commission_record`s with filters
    (period, payee, status) and each record's adjustments. Needs one new
    admin list endpoint.
  - The statement and settlement panels show an honest "statements aren't
    produced yet" state.
  - The weekly statement run, manual settlement recording and eTIMS move to
    a separate **Commission & Statements** increment, scoped on its own.
- **Manual adjustments** (`MANUAL_CREDIT`/`MANUAL_DEBIT`/`REVERSAL`) aren't
  built and the DB only allows reductions. **Recommended:** none in 9.
  Adjustments stay as they are today, made only through dispute resolution.

### D-5 — Items to leave out of Increment 9

**Recommended exclusions** (each shown as a clear "not available yet" state,
not a dead control):
- **Trust & Reputation** nav item and the trust-level confirmation queue:
  the Trust phase isn't approved (ADR-2D-05).
- **Resume requests** queue and any `RESUME_PRIOR` logic: O-P1 is still open.
  The disabled Resume shell from Increment 7 stays.
- **System** health page: no defined content. A small "outbox dead-letter
  count" tile on Control is the most it would need. Recommended: include
  just that tile, or defer the whole thing.
- Cross-entity **search** (deferred by founder decision on 2026-09-22).

### D-6 — Who sees Users & Organizations

FR-ADM-1 lets admins review businesses and operators; the Ops Officer
processes verification and monitors jobs.
**Recommended:** in 9, the cross-org directory (list + detail) is
**Platform-Admin-only**, enforced server-side by a new
`admin.directory.read` permission that the config can later grant to Ops.
Phone numbers in the directory are masked until an audited reveal, the same
pattern as Increment 8's contact reveal. Raw verification documents stay in
the existing Verification flow (logged, HIGH-PII).

## 4. Proposed sub-increments (if D-1 (a) and the other recommendations are approved)

Stacked, each reviewable and live-checked in a browser like earlier
increments:

| # | Contents | Backend | Frontend |
|---|---|---|---|
| **9a** | **Admin MFA + step-up** | TOTP device model, enrolment, login TOTP, backup codes, `POST /auth/step-up`, a `StepUpFresh` policy check; retrofitted onto dispute resolution, high-value decision and staff cancel above Standard; STRIDE pass | Enrolment screen (QR + backup codes), TOTP at login, a reusable `StepUpDialog` |
| **9b** | **Console shell + Control + directory** | `GET /admin/overview` (queue counts), `GET /admin/directory/{businesses,operators,groups}` + detail, audited phone reveal | Platform Admin sidebar per P3 §19 (replacing today's shared Ops nav), Control overview, Users & Organizations list/detail |
| **9c** | **Suspend / reinstate / offboard** | Per-target services, a suspension record (reason, duration noted, actor), append-only + audited, step-up; endpoints | The §19.2 `AdminActionShell` (reason → step-up → confirm), on directory detail |
| **9d** | **Configuration** | `GET /admin/config` (full live + version history), `POST /admin/config/preview` (diff + effect), `POST /admin/config` (apply: step-up + rationale, editable-key allowlist) | Config view, version history, draft → diff → apply |
| **9e** | **Commission ledger (read)** | `GET /admin/commission` (records + adjustments, filters, cursor) | Ledger table, record detail, "statements not produced yet" state |

Every new endpoint gets the required IDOR/BOLA tests (an Ops Officer and an
ordinary user get 403), and every write gets `audit.record()` in the same
transaction. The suite, migrations check and Docker smoke run stay green.
That last needs Docker on this machine; it currently has none.

**Order:** 9a → 9b → 9c → 9d → 9e. If you choose D-1 (c), the order becomes
9b → 9d (read only) → 9e, then 9a → 9c → 9d (apply).

## 5. Out of scope (unchanged stop lines)

Real Trust & Reputation engine · ratings · `RESUME_PRIOR` preconditions ·
any wired SMS/WhatsApp/M-Pesa/eTIMS provider · weekly statement run ·
manual commission credits/debits · GPS · AI dispatch · fleet scheduling ·
native apps · deploy · merging to `main` without founder approval.

## 6. Decision sheet

| # | Question | Recommendation | Founder |
|---|---|---|---|
| D-1 | Admin MFA + step-up | (a) build first as 9a | |
| D-2 | Suspension effect / duration / targets / restrict / offboard | New work blocked, in-flight continues + Ops flag; manual reinstate; operator, business, group, user; RESTRICTED out; offboard terminal | |
| D-3 | Config approval + editable keys | Single-admin draft → diff → apply with step-up; commission + timeouts editable; bands, permissions, classes, verification read-only | |
| D-4 | Commission & statements | Read-only ledger in 9; statements/settlement/eTIMS a separate increment; no manual adjustments | |
| D-5 | Exclusions | Trust, Resume queue, Search out; System = one dead-letter tile or deferred | |
| D-6 | Directory access | Platform Admin only, masked phones + audited reveal | |

## 7. Progress and founder actions (2026-10-13)

**Built already** (branch `feat/increment-9b-admin-control`, commit
`8951c2f`, stacked on PR #5). This is the part of 9b that needs no new
backend and none of D-1 to D-6:
- The Platform Admin's own navigation.
- **Control** (`/admin`): above-Standard disputes and Very High value
  approvals, from the existing Ops queues.

Verified: 257 frontend tests, typecheck, lint, build (153.6 kB gzip).
**Not yet live-checked in a browser**: there's no backend running on this
machine.

**Blocked until the founder acts:**

| # | Founder action | Unblocks |
|---|---|---|
| F-1 | Answer D-1 to D-6 (§6 decision sheet) | Everything below |
| F-2 | Install Docker Desktop on this machine (Windows; WSL 2 backend), then `docker compose up` | Backend tests (Postgres), every backend change in 9a–9e, the live browser check of `8951c2f` |
| F-3 | Review and merge PR #5, then PR #6 | A clean base. 9b is stacked on #5 |
| F-4 | If D-1 (a): install an authenticator app (Google Authenticator, Microsoft Authenticator or similar) on your phone, for TOTP enrolment | 9a, then every gated admin action |
| F-5 | Optional: tell Claude to apply GitHub branch protection on `main` (`gh` is now authenticated) | Closes the 2026-09-11 process-exception hardening item |

**After F-1 and F-2**, the order is 9a → rest of 9b (directory) → 9c → 9d → 9e,
as in §4. Each one stops for founder review.
