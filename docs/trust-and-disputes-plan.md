# Trust engine and dispute rules — plan

**Status:** APPROVED by the founder 2026-10-20 ("approved as recommended"),
after three review rounds (Claude Code ↔ ChatGPT ↔ founder). Every decision
below is the recommended option. **One item is still open: RC-1** (recipient
completion) had no recommendation and is not part of this plan.

Nothing in this plan is built yet. Each increment (§8) still needs the
founder's go-ahead to start, and stops at a founder gate when done.

**Order (founder, 2026-10-20):** the trust engine first (Part A), then the
dispute rules (Part B).

**Baseline verified 2026-10-20** on `main` at `bdfad69`: 1,231 backend and
368 frontend tests passing.

---

## 1. What exists today (verified in the repository)

| Area | Behaviour | Where |
|------|-----------|-------|
| Lifecycle writer | `transition()` locks the job row, checks `If-Match`, replays idempotency keys; the only writer of `job.status` | `jobs/service.py:253–391` |
| Disputes | Entered from ASSIGNED…DELIVERED, or from COMPLETED inside the post-completion window; left only to COMPLETED / FAILED / CANCELLED. `pre_dispute_status` stored server-side under the job lock | `jobs/transitions.py:155–304`, `incidents/services.py:475–547` |
| Resume | Not possible: `ck_resolution_routed_status_no_resume`; `routed_job_status` only holds job statuses; `JobEventType.RESUMED` reserved, never written (ADR-2D-07, founder decision 10) | `incidents/constants.py:101`, `incidents/models.py:213–218` |
| Resolution | Admin; above STANDARD a Platform Admin (`AdminBandAuthorised`); step-up in the view; locks dispute → job; marks **all** linked incidents RESOLVED in one bulk update; `actions` flags stored, never executed (ADR-2D-21) | `incidents/services.py:550–690`, `incidents/api/views.py:335` |
| Incident closure | Only through dispute resolution — an incident outside a dispute can never close | `incidents/services.py:643–645` |
| Who an incident is about | Not recorded (job + reporter only) | `incidents/models.py:47–89` |
| Tiers | Per driver `OperatorProfile`; verification floor (L0); proposals confirmed by a Platform Admin; manual change (ADR-2D-52) | `trust/services.py`, `jobs/driver_record.py:32` |
| Tier incident criterion | Counts every open incident (except NON_PAYMENT) on the driver's jobs, including ones the driver reported | `incidents/trust_facts.py:28–34` |
| Tier late-cancellation criterion | Counts cancellations by the operator's own user — always 0 for real operator activity, wrong if that user is also a business member | `jobs/driver_record.py:36–41` |
| Who can cancel | Only a business party (`cancel_job`) or staff, since `b7d38b7`. Operator-side initiators in the transition table are unreachable | `jobs/creation.py:224–245` |
| Cancellation record | user, `audit_role` (USER / OPERATIONS_OFFICER / PLATFORM_ADMIN), `at_status`, reason, `penalty_class` (ASSIGNED → late; AT_PICKUP+ → wasted trip), `created_at` | `jobs/models.py:321–339`, `jobs/constants.py:163–176` |
| Reassignment | Not built (schema field only; "reassign … deferred") | `jobs/ops.py:9` |
| High-value approval | One per job, append-only, not tied to driver or vehicle | `jobs/models.py:616–650` |
| Custody confirmations | Tied to job + stage only (no assignment); the proof check reads every row for the stage | `jobs/models.py:449–468` |
| Step codes | Pickup / recipient codes issued on arrival, live 5 minutes | `jobs/apply_fns.py:187–191`, `jobs/otp.py:92` |
| Recipient link | Issued on arrival at destination; actions VIEW / CONFIRM_RECEIPT / REPORT_ISSUE; confirm only at AT_DESTINATION and single-use; 7-day rolling expiry, not extended during a dispute | `jobs/recipient.py:57–62`, `:99–169`, `:312–372` |
| Completion | Only the sender's close (`sender_close_job`), which writes the payment record in the same transaction; the `RECIPIENT` initiator on DELIVERED → COMPLETED is unreachable (see RC-1) | `jobs/custody.py:291–335` |
| `completed_at` | Stamped once, never again on re-completion | `jobs/service.py:330–333` |
| "Restricted" | Tier RESTRICTED = STANDARD only; operator **account** RESTRICTED never set by any code; business / group RESTRICTED have no effect | `jobs/eligibility.py:22`, `admin_console/services.py:135` |
| TD-4 | Says Restricted exits to L1 only; `set_level` allows any tier | `trust/services.py:345–366` |
| Ratings | None | — |

---

## 2. Decisions (founder, 2026-10-20)

| ID | Decision |
|----|----------|
| **TE-1** Rating window | Each side may rate until the job has spent **7 days in COMPLETED in total** (configurable). Time spent DISPUTED does not count; a job that ends FAILED or CANCELLED can no longer be rated. (Option C.) |
| **TE-2** Publication | Published when both sides have rated, or when the job has spent 7 days in COMPLETED in total. Once published, always published. |
| **TE-3** Comments | Staff only. The rated party sees scores. |
| **TE-4** Minimum sample | 3 counted ratings before an average is shown or used. |
| **TE-5** Serious at-fault finding | A current DRIVER at-fault finding on a LOSS / DAMAGE / MISSING_GOODS / MISCONDUCT incident creates a **proposal** to tier Restricted; a Platform Admin confirms or rejects it (FR-T-4 "administrator-applied"). |
| **TE-6** Rating drop | Mean of the newest 10 counted ratings below 3.5 → a proposal one tier down (L3→L2, L2→L1, L1→Restricted); a Platform Admin confirms. |
| **TE-7** What businesses see | On the negotiation thread of a job the business owns: the operator's completed-job count and average rating (once ≥ 3 counted). No incident count; no tier (TD-6). |
| **TE-8** Ratings of businesses | Staff only. |
| **TE-9** Group jobs | One business rating per job, attached to both the assigned driver and the group (FR-O-8). |
| **TE-10** Who rates the business on a group job | The assigned driver or the group manager; the first to submit is the side's rating. |
| **TE-11** Too few ratings | Fewer than 3 counted ratings **blocks** a proposal (D-TRU-6 as written). Manual promotion (TD-1) remains. |
| **FN-1** Findings at closure | Optional, except that resuming needs a current finding on every serious-type incident (UNDETERMINED satisfies it). |
| **UF-1** Unfounded reports | A separate record, Platform Admin only, allowed only on a closed incident whose current finding is NO_FAULT; no automatic effect. |
| **Q3** SHARED | A shared finding (business and operator side both at fault) creates no proposal; the manual tier change remains. |
| **Q7 / ST-1** Business & group "restricted" | No new effect. Suspension stays the only hard lever. |
| **CF-1** Operator cancellations / no-shows | Not recorded in this plan; the operator late-cancellation criterion shows "not yet measured". |
| **CF-2** Staff cancellations | Count against no party. |
| **Q1** Resume | **Allowed** under §6 — lifts founder decision 10 (2026-10-14) and supersedes ADR-2D-07. |
| **DR-1** Agreement to continue | A structured attestation (below), not free text alone. |
| **DR-2** Eligibility | The existing assignment is re-checked against today's rules. |
| **DR-3** Replacement | **No** driver or vehicle replacement. |
| **DR-4** Resume window | Within 7 days of the dispute opening (configurable); after that resume is refused and the job **stays DISPUTED** — no timer changes job state. |
| **DR-5** High-value | The existing approval must still be effective (not reversed); never re-approved. |
| **DR-6** Dispute again | Allowed; each dispute is its own record. |
| **DR-7** Confirmations after resume | Per the table in §6. |
| **DR-8** Recipient link after a resume to DELIVERED | Not reissued (nothing is pending for the recipient). |
| **RC-1** Recipient completion | **OPEN — not decided.** See §9. Out of scope for this plan. |

---

## 3. Vocabulary

**Restricted — four different things, kept apart**

| Term | Effect | Changed by this plan? |
|------|--------|-----------------------|
| Tier **Restricted** | STANDARD jobs only (TD-4) | Reachable also through confirmed TE-5 / TE-6 proposals; exits **only to L1** via `REMEDIATION_EXIT` |
| Operator account **RESTRICTED** | Would block all new work; never set | No |
| Business / group standing **RESTRICTED** | None | No (ST-1) |
| **Suspension** | Blocks new work / posting | No |

**Criterion states** (extends MET / NOT_MET / NOT_MEASURED)

| State | Meaning | Blocks a proposal? |
|-------|---------|--------------------|
| `MET` | Measured and satisfied | no |
| `NOT_MET` | Measured and not satisfied | yes |
| `INSUFFICIENT_DATA` | Measurable, too little data (e.g. < 3 counted ratings) | yes (TE-11) |
| `NOT_MEASURED` | No way to record it yet (e.g. operator no-shows) | no (TD-3); always shown "not yet measured", never as a pass |
| `NOT_APPLICABLE` | Doesn't apply to this move | no; not shown |

**Evidence states:** `COUNTED` · `NOT_COUNTED_TEMPORARILY` (job DISPUTED) ·
`EXCLUDED` (job ended FAILED / CANCELLED) · `SUPERSEDED` (a replaced finding).
**Proposal states (computed on read):** `OPEN` · `CONFIRMED` · `REJECTED` · `STALE`.

**Parties around an incident:** *involved* (derived from the job: business,
assigned driver, group or solo operator) · *reporter* (the incident's
reporter fields) · *found at fault* (finding party rows) · *trust consequence
subject* (always a driver's `OperatorProfile`, on the tier-change row).

---

## 4. Part A — Trust engine: requirements

### A1. Closing an incident (outside or inside a dispute)

- Allowed for a holder of `incident.intake`; above STANDARD a Platform Admin.
  Uses the permission check, not the looser `incidents_authz.is_admin`.
- Requires a closure reason — `RESOLVED_BETWEEN_PARTIES` · `PAYMENT_MADE` ·
  `WITHDRAWN` · `NO_ACTION_NEEDED` · `DISPUTE_RESOLVED` · `OTHER` — and a note
  of at least 10 characters.
- Writes an append-only `incident_closure` row, status RESOLVED, audit
  `incident.closed` and outbox `IncidentClosed`, in one transaction.
- Never changes job status, a tier or a standing. Closing a closed incident →
  `409 incident_already_resolved`.
- Dispute resolution writes one closure row per linked incident (replacing the
  bulk update).

### A2. Findings

- Append-only `incident_finding`: incident, `outcome` (`AT_FAULT` ·
  `NO_FAULT` · `UNDETERMINED`), reason, decided by, `decided_by_is_platform_admin`,
  `supersedes` (nullable). At most one current finding per incident (database).
- Append-only `incident_finding_party` (only when `AT_FAULT`): `kind`
  (`BUSINESS` · `DRIVER` · `GROUP`) + subject id. The server builds the
  choices from the job — the business, the assignment's driver profile (the
  operator on a solo job), the assignment's group. Anything else → `422`.
- "Shared" is displayed when BUSINESS and an operator-side party are both
  named; it is not stored.
- Above STANDARD only a Platform Admin may record `AT_FAULT`.
- Naming GROUP never implies DRIVER, and the reverse. Group membership alone
  never makes a driver responsible.
- A correction is a new finding pointing at the one it replaces; replaced rows
  stay readable. Audit `incident.finding.recorded` / `.superseded`.
- Existing resolutions keep their `actions` flags, shown as "Recorded intent
  (before findings)"; the flags leave the resolve screen. Incidents closed
  before this change show "No finding recorded".

### A3. Unfounded-report record (UF-1)

Append-only, against the reporter (derived server-side). Platform Admin, step-up,
own reason; only on a closed incident whose current finding is `NO_FAULT`.
No automatic effect; shows on the staff record. `NO_FAULT` alone never means
unfounded.

### A4. Ratings

- Append-only `rating`: job, side (`BUSINESS_RATES_OPERATOR` /
  `OPERATOR_RATES_BUSINESS`), score 1–5, optional comment, rater user,
  `submitted_at`. Subjects derived server-side from the job: business-side rows
  store the driver profile and the group (if the assignment was the group's);
  operator-side rows store the business. One rating per job per side
  (database unique).
- Raters: the business's party; for the operator side, the solo operator, or
  on a group job the assigned driver or the group manager (first wins, TE-10).
- **Window (TE-1):** submission allowed while the job is COMPLETED, the side
  hasn't rated, and the job's total time in COMPLETED (summed from its status
  events) is under 7 days.
- **Publication (TE-2):** both sides rated, or 7 days total in COMPLETED.
  Computed on read from stored rows and an explicit `now` — no sweep, no
  stored flag. Both conditions only ever become true, so publication is
  permanent and can never newly happen during a dispute.
- **Counting:** published **and** the job is COMPLETED now.
- **Visibility:** staff see everything incl. comments; the rated party sees
  published scores; a published score on a disputed job is marked "not
  counted while this job is under dispute"; on a FAILED / CANCELLED job "not
  counted: the job's outcome changed"; unpublished ratings on such a job are
  never published.
- **Average:** mean of the newest 10 counted ratings (submission time, then
  id). Driver average groups by driver; group average (staff information
  only) by group — no aggregate counts a rating twice.

### A5. Criteria going live

- `avg_rating`: `INSUFFICIENT_DATA` below 3 counted ratings (blocks, TE-11),
  else MET / NOT_MET on the approved thresholds (4.2 for L2, 4.5 for L3).
- `at_fault_findings`: current DRIVER at-fault parties (L2: ≤ 1 in the last 20
  jobs; L3: none on serious types unless remediated). An incident closed
  without a finding counts as "no adverse finding recorded".
- `unresolved_incidents`: excludes incidents reported by the driver or their
  own operator side.
- `no_cancellation_flag` (operator): `NOT_MEASURED` (CF-1).
- Proposal snapshots record each criterion's state with evidence ids, and each
  piece of evidence's state.
- Anti-gaming (T-5): the proposal shows "N of M ratings from one business";
  information only.
- A config switch turns the live criteria on, so ratings can accumulate first.

### A6. Proposals (TE-5, TE-6) and remediation

- New tier-change triggers: `INCIDENT`, `RATING_DROP`, `REMEDIATION_EXIT`;
  new column `evidence_key`.
- **TE-5:** recording a qualifying finding creates, in the same transaction, a
  `PROPOSED` change to Restricted (`trigger=INCIDENT`, `evidence_key` = the
  finding id), plus audit and outbox. A Platform Admin confirms or rejects
  through the existing decision action (step-up). SHARED creates no proposal.
- **TE-6:** evaluated on rating submission, completion and nightly.
  `evidence_key` = SHA-256 of the 10 counted rating ids in window order; the
  ids go in the snapshot. Proposed only when ≥ 10 ratings count and no
  INCIDENT / RATING_DROP proposal is open.
- **Deduplication:** partial unique indexes on (operator, trigger,
  evidence_key) for RATING_DROP and on (evidence_key) for INCIDENT. The
  existing 30-day re-proposal cooldown after a rejection stays.
- **Openness and staleness are computed, not stored:** open = PROPOSED, no
  decision, made from the current tier (existing `_open_proposal`). At
  confirmation the service re-checks that the condition still holds (the
  finding still current and qualifying; the rating mean still below 3.5 on
  current data); otherwise `409 tier_proposal_not_open`. A proposal whose
  evidence counts again becomes confirmable again — no duplicate is created.
- No promotion proposal while an INCIDENT / RATING_DROP proposal is open;
  confirming a demotion makes a promotion proposal stale (tier check).
- Concurrency: every evaluation locks the operator's tier-state row first;
  a duplicate insert hitting a unique index is a no-op.
- A superseded finding never undoes an applied restriction. Leaving Restricted
  is `REMEDIATION_EXIT` by a Platform Admin with a reason and step-up, **to L1
  only** — and `set_level` from Restricted is fixed to L1 only (TD-4).

### A7. Business cancellation flags (D-DIS-3, CF-2)

- New columns on `cancellation_record` for new rows: `cancelling_side`
  (`BUSINESS` / `STAFF`, from the initiator token actually granted) and
  `business_id`. Older rows are not rewritten: read-time attribution from the
  **stored** role only — PLATFORM_ADMIN / OPERATIONS_OFFICER → STAFF, USER →
  BUSINESS (valid since `b7d38b7`, the only non-staff path).
- A flag opens when a business has ≥ 3 qualifying records (late cancellation
  or wasted trip) in the last 30 days, `now` inclusive. At most one open flag
  per business (database). The flag lists the record ids; staff clear it with
  a note or close it as mistaken. Append-only.
- Staff cancellations count against no one. A driver's failed pickup is not
  counted.

### A8. Staff business record (T-8)

Staff only. Four separate sections: reports open · incidents closed (with how)
· current findings against the business (superseded in history) · reports
marked unfounded — plus its average rating from operators and cancellation
flags. Standing is changed only by the existing admin control.

### A9. Business-facing operator summary (TE-7)

On the negotiation thread of a job the business owns: completed-job count and
average rating (once ≥ 3 counted). No incident count, no tier, no identity data
(NFR-PRIV-6). Not used for ranking.

---

## 5. Part B — Dispute rules: requirements

### B1. Resume contract

- **Who:** Platform Admin only; step-up checked in the service.
- **Preconditions:** the dispute is unresolved; `pre_dispute_status` ∈ {ASSIGNED,
  AT_PICKUP, PICKED_UP, IN_TRANSIT, AT_DESTINATION, DELIVERED}; every linked
  incident is closed, and each serious-type incident has a current finding
  (FN-1); within 7 days of the dispute opening (DR-4); the existing assignment
  passes today's checks (driver verification, driver tier covers the band,
  operator account usable, group not suspended, vehicle eligible, high-value
  approval still effective).
- **Target status:** read from `pre_dispute_status`; never from the client.
- **Attestation (DR-1):** sender agreed and operator agreed, each with a method
  (phone / in person / in-app message) and optional time, plus a reason of at
  least 10 characters. No transcripts, no phone numbers.
- **Writes, in one transaction:** a resolution of kind *resume* with the
  restored status (the `ck_resolution_routed_status_no_resume` check is
  replaced), the attestation, the status change through the lifecycle
  service (one rule per allowed restore state), a `RESUMED` job event, audit,
  outbox `JobResumed`. Locks dispute → job, the same order as resolve.
- **Failure:** any unmet precondition → `409` naming it, no side effects.
  Replaying the same idempotency key returns the original result.
- No commission is created (none exists before COMPLETED).

### B2. Proof after a resume (DR-7, DR-8)

| Restored to | Pending step | Treatment |
|-------------|--------------|-----------|
| ASSIGNED | — | nothing; arrival issues codes as usual |
| AT_PICKUP | pickup | confirmations before the resume stop counting; fresh pickup code; the sender confirms in the app again |
| PICKED_UP / IN_TRANSIT | — | completed pickup proof stays as history |
| AT_DESTINATION | delivery | confirmations before the resume stop counting; fresh recipient code; recipient link revoked and reissued with the same actions and a fresh 7-day expiry |
| DELIVERED | sender closes | delivery proof stands; no payment record exists yet, so no duplicate; recipient link **not** reissued (DR-8) |

"Stop counting" is by time: the proof check counts only confirmations made
after the latest `RESUMED` event for the pending stage. Old rows stay in the
append-only table, shown as "before the dispute". The recipient link is never
widened.

### B3. Resolve screen

The finding (A2) is chosen per incident when resolving; the old intent flags
leave the screen; the unfounded-report record (A3) is a separate action.
The disabled Resume control becomes live for a Platform Admin with the
precondition checklist and the attestation; Ops sees it read-only; parties see
"Fikisha resumed this job" on the timeline.

---

## 6. Data and migrations

- New tables: `incident_closure`, `incident_finding`, `incident_finding_party`,
  `unfounded_report`, `rating`, `cancellation_flag`, `resume_attestation` —
  append-only (trigger migrations) where they are records.
- `trust_level_change`: new triggers, `evidence_key`, partial unique indexes.
- `cancellation_record`: two nullable columns (no rewrite of existing rows).
- `resolution`: check constraint replaced to allow a *resume* kind.
- Indexes for rolling windows: rating (driver, submitted_at), (group,
  submitted_at); cancellation_record (business_id, created_at); finding
  (incident) current-row partial unique.
- No data backfill on append-only tables.

---

## 7. Tests (by risk, per increment)

Authorization and IDOR on every new endpoint (rating, finding, closure,
unfounded, flag, resume) · Ops vs Platform Admin above STANDARD · step-up on
resume, unfounded and remediation · append-only triggers and the database
uniqueness rules · concurrency: two findings, two ratings for one side, two
evaluations creating one proposal, resume racing resolve · window and
publication computed from event fixtures with an explicit `now` (disputes
longer than 7 days, repeated disputes, FAILED / CANCELLED) · state-machine
regression for the new resume rules · migrations against existing data ·
frontend visibility (comments never reach non-staff) · full backend and
frontend suites before each PR.

---

## 8. Increments (each starts on the founder's go-ahead and ends at a founder gate)

1. **Closing incidents** (A1) + tier fixes: TD-4 exit to L1, remove the
   operator late-cancellation count (→ NOT_MEASURED), stop a driver's own
   reports counting against them.
2. **Findings and unfounded reports** (A2, A3), per-incident closure inside
   resolution, legacy flag display.
3. **Ratings** (A4): storage, submission, window, publication, visibility;
   criteria still "not yet measured".
4. **Criteria live** (A5) behind the config switch, with the state vocabulary
   and the anti-gaming indicator.
5. **Proposals and remediation** (A6).
6. **Business cancellation flags** (A7).
7. **Staff business record** (A8).
8. **Business-facing operator summary** (A9).
9. **Resume** (B1–B3).

Part A ships as one PR, Part B as another; commits per increment.

---

## 9. Open item — RC-1 (recipient completion)

ADR-2D-51, `CLAUDE.md` §7 and the assessment 2026-10-20 plan (PD-3) say the
recipient's close-off is *kept*. In the code it exists only as the `RECIPIENT`
initiator on DELIVERED → COMPLETED: no service or endpoint lets a recipient
complete a job, and none ever did (the test checks the rule table only). The
recipient's delivery confirmation at AT_DESTINATION works.

The founder must choose:

- **(a)** the recipient's delivery confirmation is the "close-off": remove the
  `RECIPIENT` initiator from the completion rule; correct ADR-2D-51,
  `CLAUDE.md` §7 and PD-3; replace the test; or
- **(b)** the recipient can complete a delivered job: a separate design (proof,
  whether payment must be recorded first, interaction with the sender's close),
  changing ADR-2D-51, `recipient-access.md` and `phase-2d-api.md`.

Not part of this plan: it changes who can complete a job and therefore when
commission is created.

---

## 10. Supersessions and document changes (made when the increments land)

| Document | Change |
|----------|--------|
| Founder decision 10 (2026-10-14), ADR-2D-07 | Superseded by Q1 / B1 |
| ADR-2D-21 | Superseded by findings (A2) |
| `trust-architecture.md` §3.1 | Restriction is administrator-confirmed (FR-T-4 governs), not auto-applied; rating drop and remediation as A6 |
| `trust-architecture.md` §5 | Ratings as A4 |
| `job-state-machine.md` §5.2 / §5.4 | Recipient link reissued on resume instead of extended during a dispute; resume contract B1 |
| `job-lifecycle.md` §2.3 | Resume question decided |
| `dispute-and-liability.md` §6 | Findings vocabulary; unfounded reports |
| FR-R-3 | Incident summary deferred for the pilot (TE-7) |
| TD-5 (ADR-2D-52) | Demotion now possible through confirmed proposals |
| New ADRs | ADR-2D-53 (trust engine), ADR-2D-54 (resume) |
| `CLAUDE.md` | §4 dispute bullet; §7 rows; STOP line (ratings and resume preconditions leave the not-permitted list); the pending maps / assessment / tiers status lines |

**Still needs outside sign-off before real users see it:** the wording of
findings and ratings in the Terms of Service (dispute-and-liability §7,
REQUIRES KENYAN PROFESSIONAL VALIDATION); native Swahili review of new strings.
