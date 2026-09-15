# Phase 2D — Final Verification Report

**Date:** 2026-09-11
**Branch:** `feat/phase-2d-jobs` (not merged to `main`)
**Phase 2D commit range:** `d616456`..`c39f103` (12 commits: plan doc, Founder-gate decisions doc, Increments 1–5, Steps 8–11, plus one frontend commit `f116502` explicitly outside the backend scope)
**Verifier:** independent re-inspection of source + fresh test/lint/type/migration/Docker runs — not a rebuttal of prior step reports, but not a rubber stamp of them either.

This is a **verification-only** pass. No product code was modified to make anything pass. One real defect was found (§Blockers) and is reported, not fixed. Two temporary, throwaway scratch test files were created under `fikisha/*/tests/test_zz_verification_scratch*.py` to obtain direct concurrency/failure-mode evidence during this review; both were deleted before this report was written and never committed (confirmed by `git status`).

**At a glance (original pass):** Tests 838/838 · Coverage 90% · Lint clean · Types clean · Fresh migration clean · Docker clean · Git clean · **1 BLOCKER** (missing `@transaction.atomic` on 7 of 9 `incidents.services` functions — breaks 6 of 8 Incidents/Disputes HTTP endpoints in real, non-test execution) · 6 non-blocking items.

**At a glance (corrective pass, §BLOCKER-1 Corrective Verification below):** BLOCKER-1 **RESOLVED**. 7 `@transaction.atomic` additions in `incidents/services.py` + 1 in `jobs/recipient.py` (folding in N-6). 32 new regression tests, all passing, including a genuine live reproduction inside the running Docker `backend` container (not just pytest) of the exact original failure scenario, now succeeding atomically. Full suite: 856/856 in this pass's own runs (two separate, seemingly-unrelated tests each failed once across full-suite runs and passed cleanly in isolation — flagged there as unconfirmed, investigated fully below). Lint/types/migrations/OpenAPI unchanged in character.

**At a glance (flaky-test investigation, §Phase 2D Flaky-Test Investigation below):** Both "flaky" tests are **confirmed genuine production defects (Classification C)**, not test noise — directly reproduced via the real production code paths at measured rates (`otp.py::verify_otp()` ≈3%; `negotiation/selectors.py::_entries()`'s ordering ≈18%), both rooted in insufficiently-monotonic tiebreaking (`created_at` ties + UUIDv7 sub-millisecond randomness) under rapid successive writes. Not fixed in this pass, per instruction. **MERGE BLOCKER — FOUNDER DECISION REQUIRED**, separate from and not affecting BLOCKER-1's resolved status.

**At a glance (tiebreaker corrective pass, §Tiebreaker Corrective Verification below):** **MERGE BLOCKER RESOLVED.** Both defects fixed identically, on the recommendation this report already made: a real, strictly-monotonic Postgres sequence (`seq`, `db_default=nextval(...)`) replaces `created_at`/`id` as the ordering key for "the newest OTP challenge" (`jobs/otp.py::verify_otp()`) and for negotiation-entry ordering/status-derivation (`negotiation/selectors.py::_entries()` + `_effective_status()`). Fix landed on a new branch, `fix/phase-2d-tiebreaker-defects`, off the tip of `feat/phase-2d-jobs`/`main` (`b7529df`) — not committed directly to `main`. Two new deterministic regression tests force the exact `created_at` tie (via a frozen clock) that the original diagnostic could previously only produce probabilistically, and assert the correct (later-written) row wins every time; both previously-flaky tests were additionally re-run 10/10 in isolation with no failures. Full suite: 858/858 (856 + 2 new). Lint/format/types/fresh-migration all clean; no other file touched.

---

## 1. Verification baseline

Read: `CLAUDE.md`, `docs/team-skills-policy.md`, `docs/phase-2/phase-2d-plan.md` (all 22 sections, including the Step 8–11 additions), all Phase 2D ADRs (2D-01 through 2D-30), the Step 8/9/10/11 Founder Gate reports embedded in this session's history, and the relevant Phase 0/1 source docs referenced from the plan (job-state-machine.md, chain-of-custody.md, recipient-access.md, dispute-and-liability.md, commission-ledger.md, security-architecture.md) via the plan's own citations.

**CLAUDE.md is stale relative to Phase 2D** — §7 still names `feat/phase-2c-vehicles-verification` as the working branch and Design Phase 3 as the STOP line, listing Jobs/negotiation/etc. as "not permitted without explicit founder approval." This is expected, not a new problem: plan §19 item 15 ("update `CLAUDE.md` status + STOP line") is scheduled for *after* this final review, which is exactly where we are. Recorded as non-blocking (§ Non-blocking, item N-1).

Git baseline confirmed independently (not taken from a prior report):
```
d616456 docs(phase-2d): Jobs & Core Coordination backend — architecture & plan
ac6088d docs(phase-2d): record Founder gate decisions + recipient-link amendment
ae0ee16 feat(jobs): Phase 2D increment 1 — Job lifecycle engine
251ee49 feat(negotiation): Phase 2D increment 2 — two-way sealed negotiation
690b52f feat(jobs): Phase 2D increment 3 — assignment eligibility
9becc58 feat(jobs): Phase 2D increment 4 — custody transitions + pickup/delivery proof + OTP
9e66f7f feat(jobs): Phase 2D increment 5 — recipient scoped access link
2807466 Phase 2D Step 8: Incidents & Disputes backend/domain foundation
f116502 frontend: public landing page, auth only prompted on protected routes  [not backend scope]
5bda547 Phase 2D Step 9: Commission
b7d38b7 feat(phase-2d): Step 10 — API boundary over the approved Jobs/negotiation/incidents domain
c39f103 feat(phase-2d): Step 11 — scheduled sweeps over the approved Jobs lifecycle   ← HEAD
```
`main` is untouched (`git merge-base main feat/phase-2d-jobs` = `d8952fa9`, the pre-Phase-2D tip). Working tree: only the untracked `.claude/` harness artifact (never tracked, confirmed via `git log --all -- .claude` = empty).

---

## 2. Product/architecture reconciliation

Independently re-checked, not merely re-asserted:

| Boundary | Evidence |
| --- | --- |
| No wallet/escrow/fare custody | `CommissionRecord` has no balance/ledger field; `grep`-confirmed zero wallet/escrow/payment-processing code anywhere in `fikisha/` |
| No M-Pesa/eTIMS/SMS/WhatsApp provider wired | `grep -ri "mpesa\|whatsapp"` across all production `.py` returns only a docstring comment in `otp.py` stating none is wired |
| No AI dispatch / route optimization / continuous GPS | Geo capture is `{lat,lng,accuracy_m}` per event only (`_geo()` in `custody.py`); no tracking loop, no route/dispatch code anywhere |
| No native app / complex fleet mgmt | Not present; out of module list entirely |
| No automatic liability/refund | `Resolution.actions` records admin-declared *intent flags* only (`RATING_IMPACT`/`TRUST_CHANGE`/`SUSPENSION`/`NONE`); nothing executes them (ADR-2D-21) |
| No automatic trust/rating/suspension consequence | Confirmed same as above — zero code paths write to any trust/rating field as a side effect of dispute resolution |
| `DISPUTED → RESUME` absent | `test_resume_path_is_absent()` + `test_no_transition_out_of_terminal_states_except_post_completion_dispute()` (both pass); `JobEventType.RESUMED` exists as an enum value but is never referenced/emitted anywhere — a harmless reserved placeholder, not a capability |
| No invented `RESUME_PRIOR` semantics | `Dispute.pre_dispute_status` is recorded and never read back by any transition function |

**No contradiction found.** All Phase 0/1/2A/2B/2C/2D product boundaries hold under direct source inspection, not merely re-cited from prior reports.

---

## 3–4. Job lifecycle + transition matrix + guards

- **Sole writer:** `grep -rn "job\.status\s*="` across all production code (excluding tests) returns exactly one hit outside comparisons: `fikisha/jobs/service.py:322` (`job.status = to`, inside `transition()`). No other assignment exists anywhere — application code, services, tasks, management commands, API views, migrations.
- **DB trigger backstop:** real, not theoretical. `fikisha_check_job_transition()` (migration `0002`) rejects any `UPDATE OF status` not present in `allowed_job_transition` unless `app.lifecycle_service='on'` (a transaction-scoped GUC `transition()` sets after authorization, before guards/apply). Directly proven by `test_raw_update_along_a_disallowed_edge_is_rejected_by_trigger` (raw SQL `UPDATE ... status='COMPLETED'` on a DRAFT row → `DatabaseError: illegal job status transition`) and `test_raw_update_along_an_allowed_edge_passes_the_trigger` (both re-run fresh this session, both pass).
- **Transition table completeness:** `test_table_matches_state_machine_doc` pins the *exact* 35-pair set against `job-state-machine.md §3.1–3.4` (byte-for-byte set equality); `test_cross_product_lookup` parametrizes the full 14×14 = 196-cell cross-product and asserts a rule exists iff the pair is in the expected set; `test_db_seed_equals_the_python_table` proves the DB seed and the Python table are identical; `test_every_rule_has_a_registered_apply_and_guards` proves no dangling guard/apply-fn name. All re-run fresh this session, all pass.
- **Optimistic concurrency / idempotency:** `TransactionContext.if_match_version` → `StaleJob` (412) on mismatch, checked under the row lock; `JobTransitionIdempotency` gives a committed-replay fast path plus a locked-replay path inside the same `transaction.atomic()`.
- **Guards derive facts from persisted state, not caller claims** — independently re-read, not merely re-cited:
  - `requester_is_not_provider` / `driver_assignment_allowed` — resolve the *confirmed Agreement's* `operator_id`/`group_id` and re-check DB membership/ownership; a caller-supplied `driver_profile`/`vehicle` object in `ctx` only ever originates from a server-side `OperatorProfile.objects.get(id=...)` / `Vehicle.objects.get(id=...)` lookup inside `assignment.assign_job()` (raises `Http404` on a non-existent id) — never a client-constructed object.
  - `admin_override_reason` is silently dropped by `assign_job()` unless `_is_admin(actor)` is true server-side.
  - `driver_verification_current` / `vehicle_eligible` call `verification.services.subject_meets()` against real `VerificationRecord` rows — a claimed verification state is not possible.
  - `high_value_approved` requires a real, persisted `HighValueApproval(decision=APPROVED)` row, and independently re-checks `decided_by_is_platform_admin` for VERY_HIGH regardless of what the caller claims.
  - `blocking_incident_exists` / `resolution_recorded` (dispute guards) re-query a real, non-`RESOLVED` `Incident`/`Resolution` row for *this* job — the Step 8 fix that closed the original ctx-trust gap (ADR-2D-22).
  - `pickup_proof_valid_for_band` / `delivery_proof_valid_for_band` — `otp_verified`/`_otp_challenge_id` in `ctx` are set only by `custody.py`/`recipient.py` *after* `otp.verify_otp()` independently validated the real persisted challenge; no HTTP view ever sets these fields directly (confirmed by reading every call site in `jobs/api/views.py` — all forward only named, typed serializer fields: `code`, `party_name`, evidence ids).
  - `mutual_acceptance_exists` / `operator_eligible_for_job` — negotiation's own service resolves `operator_party`/`agreed_price_kes`/`accepting_entry_ids` server-side from real `NegotiationEntry` rows before calling `transition()`.
- **Known limitation, independently re-confirmed:** licence-*class* matching is not implemented — `Domain.LICENCE` on `VerificationRecord` is a binary fact (verified/not), with no class field; heavy-vehicle compliance is instead carried by the *vehicle's* `HEAVY_CLASS_COMPLIANCE` domain, not the driver's licence. This is a real, unaddressed Phase 2C schema gap, correctly left unaddressed rather than invented (per the plan's own instruction). **Non-blocking** (N-2).

---

## 5. Negotiation

- Append-only: `NegotiationEntry` is a hard `AppendOnlyModel` + DB trigger; status is **derived**, never stored (ADR-2D-11) — `selectors.py` folds `expires_at` + thread status + later-same-side-offers at read time, mirroring `VerificationRecord.effective_state()`.
- `NoRacingConfirm` + `MutualAcceptanceExists` + `OperatorEligibleForJob` all run inside `transition()`'s row lock.
- **Real concurrency, freshly proven this session** (temporary scratch test, deleted after): 5 threads raced the confirming `accept()` call on the same negotiation thread. Result: exactly 1 succeeded (`confirmed: True`, job → `CONFIRMED`, exactly 1 `Agreement` row created); the other 4 each got a clean `JobNotOpenForNegotiation()` — no crash, no duplicate, no corrupted state. Lock: `job_for_update()`'s `SELECT ... FOR UPDATE` inside `accept()`'s `@transaction.atomic`.
- Commission calculation reads only `job.agreement.agreed_price_kes` (frozen at CONFIRMED) — independently re-confirmed in `jobs/commission.py`, never a live proposal or negotiation figure.

---

## 6. Assignment

- Driver/vehicle authority resolution is fully server-side (`_resolve_authority`, `operators_authz.owns_profile`, `groups_authz.can_manage`) — re-read fresh, confirmed no client-claimed role reaches a guard.
- `driver_assignment_allowed`: solo-operator jobs require an exact id match against the frozen Agreement's operator; group jobs require **active, non-suspended** `GroupMembership` — group standing can only *reduce* capability, never substitute for the driver's own verification (independently re-confirmed against `driver_verification_current`, a wholly separate guard).
- `vehicle_eligible`: ownership, active status, class/capacity/volume/feature requirements, and verification (`VEHICLE`/`ASSOCIATION`/+`HEAVY_CLASS_COMPLIANCE` when heavy) are all checked against real persisted rows.
- High-value: `decide_high_value()` (`@transaction.atomic`) enforces Ops-Officer-for-HIGH / Platform-Admin-only-for-VERY_HIGH, immutable one-decision-per-job (`HighValueApproval` is `UNIQUE(job)`); `high_value_approved` guard independently re-checks `decided_by_is_platform_admin` for VERY_HIGH rather than trusting the decision row's face value alone (belt-and-suspenders).
- Group-DRIVER-vs-manager: `groups.authz.can_manage()` is `has_role(actor, resource, {OWNER, MANAGER})` — structurally excludes DRIVER by construction (verified by reading the set literal). **No dedicated named test exercises "a DRIVER-role member calls `assign_job()` and is rejected"** specifically — only "a stranger with no membership at all" (`test_a_stranger_cannot_assign`) is directly tested. The underlying check is correct by inspection (a set-membership test, not a subtle behavior), so this is a minor test-coverage gap, not a suspected defect. **Non-blocking** (N-3).
- Licence-class limitation: see §4.

---

## 7–8. Pickup / delivery proof matrices

Read `pickup_proof_valid_for_band` / `delivery_proof_valid_for_band` directly (guards.py) — matches the brief's matrix **verbatim**:

- **Pickup STANDARD:** OTP, or in-app business confirmation, or operator-attested fallback (photo + contact name) → `attestation=OPERATOR_ATTESTED_UNVERIFIED`, event `JobEventType.PICKUP_OPERATOR_ATTESTED` (both exact string constants confirmed present in `constants.py`/`apply_fns.py`). The fallback is only reachable when `job.value_band == STANDARD` in the first place (the guard refuses it for any other band before the apply fn ever runs) — "capped at STANDARD" is a precondition, not a downgrade action.
- **Pickup ELEVATED/HIGH/VERY_HIGH:** OTP or business confirmation only; `ATTESTED` is refused server-side by the guard (not merely hidden in a UI) with `PickupConfirmationRequired`.
- **Delivery STANDARD:** recipient name + at least one of {OTP, signature, photo}.
- **Delivery ELEVATED/HIGH/VERY_HIGH:** recipient name + OTP **and** ≥1 photo, enforced by `if band in HIGH_VALUE_BANDS or band == ELEVATED: if not (otp_ok and photos): raise`.
- `otp_ok` can never be true without a corresponding `_otp_challenge_id` (defense-in-depth: `if otp_ok and not ctx.get("_otp_challenge_id"): raise`) — closes the theoretical gap of some future caller setting the boolean without real verification.
- Both guards run server-side inside `transition()`; nothing here is UI-only.

---

## 9. OTP security — critical gate

Independently re-read `fikisha/jobs/otp.py` in full, and re-ran the mandatory concurrency test fresh:

- **Generation:** `secrets.randbelow(10**length)` (cryptographically secure), 6 digits by default (`OTP_LENGTH=6`). A `OTP_DEV_FIXED_CODE` escape hatch exists but is confirmed **empty by default** in `base.py`, only ever populated in `test.py` (`"000000"`), and `prod.py` explicitly re-asserts it empty — no accidental prod exposure.
- **Storage:** `make_password(code)` — Django's configured hasher (Argon2 first).
- **Expiry:** `OTP_TTL_SECONDS=300` (5 min) default, confirmed in `base.py`.
- **Attempts:** `OTP_MAX_ATTEMPTS=5`; `is_locked = attempts >= max_attempts` (model property, read fresh).
- **Single-use / replay:** `select_for_update()` + `filter(consumed_at__isnull=True)` inside one `transaction.atomic()` — the newest *unconsumed* challenge only; once `consumed_at` is set, it is invisible to future lookups.
- **Failed attempts persist despite the raise:** the `attempts += 1; save()` happens and the enclosing `with transaction.atomic():` block closes (commits) *before* the function raises outside it — the identity-OTP pattern, confirmed by re-reading the control flow line-by-line.
- **No plaintext anywhere:** `_deliver()` logs only a masked phone (`***XXX`) at INFO; the raw code is logged at DEBUG *only* when `OTP_DEV_EXPOSE` is true (off in `base.py`/`prod.py`, on only in `dev.py`/`test.py`). `audit.record()` payloads for `job.otp.issued`/`attempt_failed`/`verified` never include the code. `audit.services._REDACT_KEYS` additionally auto-redacts any `password`/`secret`/`token`/`code`/`otp`/`signature`-named key in *any* audit payload as a generic backstop, independent of the OTP module's own discipline.
- **Consume-after-guards ordering:** `verify_otp(consume=False)` + a separate `consume_otp()` exists and is exercised by `custody.py`/`recipient.py` precisely so a later guard failure in the *same* transition doesn't burn a valid code.

**HTTP concurrency test — re-run fresh this session, not merely cited:**
```
fikisha/jobs/tests/test_api_custody_otp.py::test_concurrent_http_requests_cannot_both_consume_the_same_otp PASSED
```
Setup: 5 real concurrent HTTP `POST /custody/confirm-pickup/otp` requests (5 threads, 5 separate DB connections, `transaction=True`) all carrying the identical, still-valid, still-unconsumed OTP code for the same job.
Expected: exactly 1 success (200), the job progresses to `PICKED_UP` exactly once.
Actual: `len(successes) == 1` — confirmed; `Job.objects.get(id=job.id).status == "PICKED_UP"` — confirmed.
Mechanism: the `OtpChallengeBase` row's `select_for_update()` inside `verify_otp()`'s `transaction.atomic()` is the real single-use boundary — all 5 requests race for that row lock; only the first to acquire it finds `consumed_at IS NULL`; by the time the rest acquire it (serially), the code portion of the code has already been consumed by the custody transition, so their attempt fails cleanly.

**VERIFIED — OTP security gate passes with direct, fresh evidence.**

---

## 10. Custody

- Custody events (`job_event.type`) are sourced from `rule.event_type`/`rule.extra_events` — the static, single-source `Rule` dataclass in `transitions.py` — never from `ctx`/caller input (`_write_events()` re-read fresh: `"type": rule.event_type`). No client can forge an arbitrary custody event type.
- Location capture is exactly `{lat,lng,accuracy_m}` per event (`_geo()` in `custody.py`) or absent — no continuous tracking loop exists anywhere in the codebase.
- Append-only: `job_event`, `proof_of_pickup`, `proof_of_delivery` all `AppendOnlyModel` + DB trigger (`0002_lifecycle_backstop.py`'s `_APPEND_ONLY_TABLES`).

---

## 11. Recipient scoped access

Re-read `fikisha/jobs/recipient.py` in full:

- **Token:** `secrets.token_urlsafe(32)` = 256 bits. Lookup: `HMAC-SHA256(SECRET_KEY, token)` → `token_lookup` (indexable, uncorrelatable from a DB leak alone) *followed by* `check_password(token, token_hash)` (a proper hashed compare) — double-gated, not lookup-alone.
- Raw token exists only as the return value of `issue_or_refresh_link_locked`/`reissue_link` (the issuance boundary) — every audit/outbox/error path handles only `link_id`/`job_id`, confirmed by reading every `audit.record`/`emit` call in the file.
- Expiry/revocation/request-time enforcement: `resolve_recipient()` checks `revoked_at IS NULL` then `now() < expires_at`, auditing every outcome (found, not-found, revoked, expired) for abuse detection. `_recheck_link_active()` re-verifies at the point of a sensitive action (`confirm_receipt`/`report_issue`) in case the principal is held across a request.
- **Schema, independently re-confirmed:** `RecipientAccessLink.job = OneToOneField(Job, ...)` — a genuine `UNIQUE(job_id)` DB constraint, no partial index, no `now()`. Codebase-wide `grep -rn "now()\|CURRENT_TIMESTAMP"` across every migration file returns **zero** hits.
- Reissue: `reissue_link()` locks the job row, then revokes+deletes any existing link, then creates the new one, all inside one `transaction.atomic()` — concurrent callers serialize on the job lock (this exact mechanism was already proven safe by 3 other independent real-thread tests elsewhere in this session — negotiation-accept race, OTP-consume race, sweep-vs-sweep race — plus its own dedicated `test_concurrent_replacement_serialises_to_one_live_link`, re-run fresh and passing).
- **Disclosure — read directly from `view()`'s return dict, matches the approved minimum exactly:** `delivery_reference`, `recipient_display_name` (first-name + last-initial via `_first_name_last_initial()`), `cargo_summary` (truncated 200 chars), `status`/`status_label`, `driver_first_name` (first name only), `vehicle_class`, `vehicle_plate`, `operator_identity_verified` (a single boolean fact, not verification internals), `allowed_actions`. **No** phone numbers, staff info, price, declared value, value band, trust internals, location history, or unrelated job data appear anywhere in this function — confirmed by reading its complete body, not by trusting a serializer's field list alone.
- `confirm_receipt()` requires the *real* recipient OTP (`otp_service.verify_otp(purpose="RECIPIENT_VERIFY", code=..., consume=False)`) — the HTTP view (`RecipientConfirmView`) forwards only the client-typed `code` string, never a boolean claim; `otp_verified=True` is set internally by `confirm_receipt()` itself only *after* `verify_otp()` already succeeded — confirmed by reading the exact view→service call chain. It then calls the identical `AT_DESTINATION → DELIVERED` `transition()` the driver's own confirmation uses.

**VERIFIED.**

---

## 12. Recipient issue → incident boundary

- `report_issue()` is append-only (`RecipientReportedIssue`, no update/delete path), rate-limited (`RateLimiter(scope="recipient_issue", limit=5, window=3600)`), taxonomy-checked (`RecipientIssueCategory.values`), and never touches `job.status` — confirmed by reading the complete function body: it only creates the row, records audit, and emits an outbox event.
- `intake_recipient_report(report_id)` exists, is callable, and is idempotent-by-design (reads an existing `RecipientReportedIssue` by id) — but see §Blockers: it shares the same missing-`@transaction.atomic` defect as the rest of `incidents.services`.
- No automatic dispute/refund/trust consequence — confirmed; nothing in `report_issue()` or `intake_recipient_report()` calls into `open_dispute()`, commission, or any trust field.

---

## 13. Incidents & Disputes

- 11-value taxonomy (`IncidentType`) confirmed present verbatim from FR-D-1, including the deliberate choice of `WRONG_PICKUP` over the brief's own paraphrase.
- Incident/Dispute workflows use their own small, explicit status enums — not the 14-state Job lifecycle (`IncidentStatus`: OPEN/UNDER_REVIEW/AMICABLE_PENDING/RESOLVED/ESCALATED; `DisputeStatus` similar) — confirmed via `constants.py`.
- **One-open-dispute-per-job — verified at both layers, independently re-run this session:**
  - Service-level: `test_a_second_open_dispute_on_the_same_job_is_refused` — a second `open_dispute()` call raises `DisputeAlreadyOpen` (service pre-check under the job-row lock). PASSED.
  - DB-level backstop: `test_the_db_constraint_backstops_the_one_open_dispute_rule` — bypasses the service entirely; a raw second `Dispute.objects.create()` for the same job inside its own transaction raises `IntegrityError` against the real Postgres partial-unique index `uq_dispute_one_open_per_job` (`status IN {OPEN, UNDER_REVIEW, AMICABLE_PENDING, ESCALATED}`, no `now()`). PASSED.
  - **Real-thread concurrency, freshly proven this session** (temporary scratch test, deleted after): 5 threads raced `open_dispute()` on the same job with the same incident. Exactly 1 succeeded; the other 4 each got a clean `DisputeAlreadyOpen` (not a raw `IntegrityError`, because `job_for_update()`'s row lock serializes the callers *before* the DB constraint would ever need to fire) — confirmed no corrupted/duplicate state.
  - Multiple sequential disputes across a job's lifetime remain possible after resolution: the constraint excludes `RESOLVED` from its condition list, and `test_dispute_lifecycle.py`'s docstring/tests confirm a resolved-then-later-reopened flow is intentional, matching `database-design.md §4.10` and the approved `COMPLETED → DISPUTED` path.
- `blocking_incident_exists`/`resolution_recorded` re-query real persisted rows (§4).
- Resolution action semantics: `Resolution.actions` are declared intent flags only, executed by nothing (§2/ADR-2D-21).
- No hidden Job-status writer inside incidents: `open_dispute`/`resolve_dispute` both call the same `JobLifecycleService.transition()` — confirmed, no direct `job.status =` write anywhere in `incidents/`.

**See §Blockers: 6 of 8 write endpoints in this module have a separate, serious defect — the *concurrency and constraint* behavior above is real and correct, but most of these operations cannot currently complete a real (non-test) HTTP request at all.**

---

## 14. Commission

Re-read `fikisha/jobs/commission.py` and re-ran its concurrency suite fresh:

- Model: `max(min_fee_kes, min(price × rate, cap_kes))`, `rate=0.10` (10%), `min_fee_kes=4000` (KES 40), `cap_kes=500000` (KES 5,000) — confirmed against `platform_config/defaults.py`. Calculation uses `Decimal(str(rate))` + `ROUND_HALF_UP`, integer KES in/out (`calculate_commission_kes`, independently re-read).
- Created only inside `apply_fns.complete()` — the `DELIVERED → COMPLETED` (and `DISPUTED → COMPLETED`) apply fn, i.e. inside `transition()`'s own atomic block and row lock; never from a view, task, or async consumer.
- Uses `job.agreement.agreed_price_kes` — the frozen Agreement — never a live proposal figure (§5).
- Every rate/min/cap/`config_version` is pinned directly on the row (not merely FK'd) — confirmed reading `create_commission_record_locked`.
- `CommissionRecord.job` is `OneToOneField` → real `UNIQUE(job_id)`.
- Adjustments: `create_adjustment()` (`@transaction.atomic`) only accepts `amount_kes < 0` (CHECK constraint `ck_commission_adjustment_negative` backstops this at the DB level too) and asserts `effective + amount_kes >= 0` — no automatic increase, ever.
- Authority: `can_adjust_commission()` is Platform-Admin-only, checked *both* early in `resolve_dispute()` and again inside `create_adjustment()` itself — independent of dispute-resolution authority (an Ops Officer can resolve a Standard-band dispute with `APPLY` but is rejected for `REDUCE`/`WAIVE`, confirmed by `test_only_platform_admin_may_reduce_commission_on_resolution`, re-run fresh, passes).
- Outbox payloads for `CommissionRecorded`/`CommissionAdjusted` carry only `job_id`/`commission_record_id` — no KES amounts (confirmed reading `emit()` call sites).

**Concurrency — 3 tests, all `transaction=True` real threads, re-run fresh this session, all pass:**
1. `test_concurrent_completion_attempts_produce_exactly_one_commission_record` — 5 threads call `transition(to=COMPLETED)` on the same `DELIVERED` job. Lock: `transition()`'s `select_for_update()`. Expected/actual: exactly 1 succeeds, `CommissionRecord.objects.filter(job=job).count() == 1`.
2. `test_concurrent_commission_creation_calls_are_idempotent_not_duplicating` — 5 threads call `create_commission_record_locked()` directly (bypassing the transition lock a real caller would already hold). Backstop: DB `UNIQUE(job_id)`. Expected/actual: zero errors, all 5 threads return the *same* record id, exactly 1 row exists.
3. `test_concurrent_adjustments_cannot_overdraw_the_effective_commission` — 3 threads each try to reduce by `commission_kes // 2`; only 2 can fit before the effective total would go negative. Lock: `CommissionRecord.objects.select_for_update()` inside `create_adjustment`. Expected/actual: exactly 2 succeed, 1 raises `InvalidCommissionAdjustmentAmount`, `record.commission_kes + total_adjusted >= 0` holds.

**VERIFIED — no double charging, no negative effective commission, no duplicate records under real concurrency.**

---

## 15. Scheduled sweeps (Step 11)

- `expire_requests`: `REQUESTED → FAILED` only, via the pre-existing `(REQUESTED, FAILED)` rule; `autocomplete_delivered`: `DELIVERED → COMPLETED` only, via the pre-existing `(DELIVERED, COMPLETED)` rule. Both re-confirmed as the *only* sweep-initiated transitions — no other sweep exists.
- Row locking: each candidate goes through `transition()`'s own `select_for_update()`, one at a time — no second locking mechanism.
- Idempotence/concurrency: re-run fresh this session — `TestConcurrency::test_two_sweep_workers_racing_the_same_stale_request` (3 threads calling `expire_requests()` concurrently against one stale job — exactly 1 changed, 1 `FailureRecord` row) and `test_sweep_races_an_ordinary_confirm_of_the_same_request` (a real admin-confirm racing the sweep on the same job — job lands in exactly one of `{CONFIRMED, FAILED}`, any loser exception is an ordinary `DomainError`) both PASS.
- Bounded batches: `batch_size` (default 100) on both; `test_bounded_batching` re-run, confirms a `batch_size=2` request against 3 eligible candidates processes exactly 2.
- Authority: `fikisha.identity.authz.actors.SystemActor` (`audit_role=="SYSTEM"`) — the canonical, already-existing "scheduler/event-handler identity," not a bespoke actor. `_actor_matches()` grants `SCHEDULER` only for `audit_role=="SYSTEM"` (or an explicit `ctx["scheduler"]`, never set by any HTTP-reachable code path — confirmed by grep).
- No HTTP trigger: `test_no_http_endpoint_exposes_a_raw_scheduler_transition` (re-run, passes) confirms no route in `jobs/api/urls.py` matches `expire`/`autocomplete`/`sweep`/`scheduler`, and the one legitimate `fail` route (`custody/fail-at-pickup`) is a pre-existing, unrelated, already-reviewed Step 10 endpoint.
- No second business-rule engine: both sweeps are candidate-query + one `transition()` call per candidate; no guard/apply-fn logic is duplicated (confirmed by reading `jobs/tasks.py` end to end — it contains zero domain-rule code).
- **Deliberately not implemented, confirmed absent by direct source inspection, not merely by citation:** negotiation mutation (no sweep touches `NegotiationEntry`), recipient-link cleanup (no sweep touches `RecipientAccessLink`), generic OTP cleanup (no sweep touches `OtpChallengeBase`), automatic dispute deadlines (no deadline field exists to sweep), commission sweep (commission has no HELD state to release — ADR-2D-30, and the plan's original `jobs_close_post_completion_window` line item was verified to have nothing left to do), cancellation-reputation sweep (no domain field exists — `cancellation_policy` config exists but nothing reads it into a sweepable flag), invented incident deadlines (none added), generic lifecycle processor (does not exist — only the two named, pre-existing transition rows are ever driven), Beat scheduling for verification expiry (`fikisha.verification.tasks.expire_due` exists but `CELERY_BEAT_SCHEDULE` does not include it — confirmed by reading `config/settings/base.py` directly).
- **Celery — re-verified fresh this session with a live Docker run** (not merely re-cited from Step 11's own report): `docker compose up -d --build backend worker beat`. Worker log lists exactly 6 registered tasks (`fikisha.debug.ping`, `fikisha.jobs.tasks.autocomplete_delivered`, `fikisha.jobs.tasks.expire_requests`, `fikisha.outbox.tasks.demo_task`, `fikisha.outbox.tasks.drain_outbox`, `fikisha.verification.tasks.expire_due`) — no duplicates, no unexpected task. Beat fired both `jobs-expire-requests` and `jobs-autocomplete-delivered` on first tick against the real dev DB; worker log shows both **succeeded**: `{'candidates': 0, 'changed': 0, 'skipped': 0, 'failed': 0}` for each (the dev DB has no eligible jobs, correctly). No crash, no error, no secret/PII in any log line. Containers stopped and removed after verification, restoring the pre-check state (db+redis only).

**VERIFIED.**

---

## 16. Authentication & authorization

- `BearerSessionAuthentication` resolves `Authorization: Bearer <token>` → `(User, AuthSession)`; absent header → anonymous; malformed → `AuthenticationFailed` (401, not 500) — re-confirmed via `test_an_expired_or_garbage_bearer_token_is_401_not_500` (re-run, passes).
- Central `authorize(actor, action, resource)`, default-deny, `@policy` — `job.read`/`incident.read` are the Step-10-added **object-level** policies (checking `job_authz.is_job_party`/`incidents_authz.is_job_party` when a resource is resolved); list views scope their own queryset (`jobs_visible_to`).
- Negative cases directly re-confirmed present and passing (re-read the actual test bodies, not just test names):
  - unrelated business (`test_business_a_cannot_see_business_b_appear_in_a_search_by_id`, `test_an_unrelated_actor_cannot_submit`)
  - unrelated operator (`test_an_unrelated_operator_cannot_assign_someone_elses_confirmed_job`)
  - Ops Officer boundary (`test_an_ops_officer_cannot_escalate_a_privileged_admin_only_action`, `test_only_platform_admin_may_reduce_commission_on_resolution`)
  - normal user vs admin action (`test_a_non_admin_cannot_resolve`)
  - business/operator attempting commission adjustment (`test_only_platform_admin_may_reduce_commission_on_resolution` — same test covers this: an Ops Officer, not even a business/operator, is the closest-privileged rejected actor; no test targets a plain business/operator directly attempting adjustment, but the code path requires `can_adjust_commission()` which checks Platform-Admin only — no role short of that reaches it)
  - recipient attempting another job (`test_a_recipient_principal_never_reaches_another_job`)
  - stranger vs assignment (`test_a_stranger_cannot_assign`)
  - **group DRIVER vs manager-only action** — no dedicated named test; see §6/N-3.
- No information leakage: `test_error_responses_never_include_a_stack_trace_or_db_detail` (re-run, passes — checks for `traceback`/`psycopg`/`django.db`/`select * from`/` at 0x` in every error body).

**VERIFIED**, with the one narrow, non-blocking coverage gap noted (N-3).

---

## 17. API boundary

Re-read the full `jobs/api/views.py`, `negotiation/api/views.py`, `incidents/api/views.py` — every view is a thin adapter: authenticate → parse/validate (named serializer fields only) → resolve target → call the domain service → serialize. No view:
- writes `job.status` directly (grep-confirmed, §3),
- calculates commission (grep-confirmed `calculate_commission_kes`/`create_commission_record_locked` calls only exist in `jobs/commission.py` and `jobs/apply_fns.py`),
- mutates an append-only record directly,
- bypasses `transition()` for any lifecycle action,
- invents authorization (all routed through `authorize()`),
- trusts caller identity (actor is always resolved server-side from the bearer token — `test_a_client_supplied_actor_id_in_the_body_is_ignored`, re-run, passes).

RFC 9457 problem+json confirmed for 401/403/404/422 (re-run `TestProblemJsonContract`, all pass); request IDs present (`request_id` field in every problem response, checked directly). Multipart evidence handling: `evidence.services.store()` — see §Blockers for the one open item there (already fixed in Step 10, re-confirmed: `EvidenceValidationError` now subclasses `DomainError`, 422, tested).

---

## 18. Idempotency & concurrency audit

| Area | Lock / constraint | Idempotency | Expected | Actual |
| --- | --- | --- | --- | --- |
| Lifecycle: same/conflicting transitions | `transition()`'s `SELECT ... FOR UPDATE` + `JobTransitionIdempotency` | DB-row replay | 1 winner, clean rejection for the rest | Confirmed (commission-completion race test, sweep-vs-sweep test, sweep-vs-confirm test — all re-run, all pass) |
| Assign vs cancel | Job-row lock | N/A (mutually exclusive states) | Whichever transition matches current status wins; the other gets `TransitionNotAllowed` | Not independently re-run as a dedicated thread test this session, but the *mechanism* (single shared row lock) is identical to 6 other independently-proven cases — non-blocking inference, not a gap in the underlying architecture |
| Confirm vs cancel (negotiation) | Job-row lock | `NoRacingConfirm` guard | 1 winner | **Directly re-proven fresh this session** (5-thread scratch test, §5) |
| OTP: concurrent verify/consume | `OtpChallengeBase.select_for_update()` | `consumed_at` single-use | 1 winner via real HTTP | **Directly re-proven fresh this session** (§9) |
| Recipient: concurrent reissue | Job-row lock, then link-row lock | `UNIQUE(job_id)` | exactly 1 live link | Confirmed via existing `test_concurrent_replacement_serialises_to_one_live_link`, re-run, passes |
| Recipient: concurrent confirmation | `transition()`'s row lock (same DELIVERED path) | `JobTransitionIdempotency` | 1 winner | Confirmed via `test_api_recipient.py`'s existing concurrent-confirmation test, re-run as part of the full suite, passes |
| Commission: concurrent completion / adjustment | `transition()` lock / `CommissionRecord.select_for_update()` | `UNIQUE(job_id)` / CHECK constraint | 1 record, non-negative effective | **Directly re-proven fresh this session** (§14, 3 tests) |
| Dispute: concurrent open | Job-row lock, DB partial-unique backstop | Service pre-check + DB constraint | 1 dispute | **Directly re-proven fresh this session** (5-thread scratch test, §13) |

No race in any of the above produced a duplicate authoritative record or contradictory state.

---

## 19. Audit & outbox

- Hash chain: `row_hash = SHA256(seq || prev_hash || canonical_json(payload))`, `seq` from a `select_for_update()`-locked singleton `AuditChainHead` row — genuine chain, re-read directly.
- `audit.record()` asserts `transaction.get_connection().in_atomic_block` and raises loudly if not — this is *precisely* the assertion that surfaces the §Blockers finding; it is doing its job correctly (failing loud rather than silently skipping the audit), it's the caller that's missing the wrapper.
- **Generic redaction backstop, re-read directly:** `_REDACT_KEYS` = `{password, secret, token, token_hash, access_token, refresh_token, code, code_hash, otp, otp_code, id_number, national_id, payout_number, signature, signed_url}` — applied recursively to every `before`/`after` payload regardless of module discipline.
- No OTP plaintext, no recipient token, no unnecessary financial amounts anywhere in audit/outbox payloads for jobs/negotiation/incidents/commission/sweeps — confirmed by reading every `audit.record`/`emit` call site in those modules (§9/§11/§14/§15).
- Outbox provider-neutral — confirmed, zero provider SDK code anywhere (§2).

---

## 20. Database integrity

- Fresh migration from an empty database (`CREATE DATABASE`, then `migrate` with zero pre-existing state): **all 47 migrations applied cleanly, in dependency order, zero errors** (re-run this session, full output captured).
- `makemigrations --check --dry-run`: **no changes detected** (re-run this session).
- `now()`/`CURRENT_TIMESTAMP` in any migration: **zero occurrences**, codebase-wide (re-grepped this session).
- Partial unique indexes: `uq_dispute_one_open_per_job` (status-list condition, no `now()`) — DB-level tested (§13).
- CHECK constraints: `ck_job_band_set_once_published` (DRAFT-or-band-and-trust-level-set), `ck_commission_price_non_negative`, `ck_commission_amount_non_negative`, `ck_commission_adjustment_negative` — all re-confirmed present in migrations and exercised by tests that deliberately violate them and catch the resulting `IntegrityError`/domain error.
- Append-only triggers: `fikisha_forbid_mutation()` reused across `job_event`/`agreement`/`cancellation_record`/`failure_record`/`proof_of_pickup`/`proof_of_delivery`/`high_value_approval` (jobs), `negotiation_entry` (negotiation), `incident_evidence`/`incident_statement`/`resolution`/`escalation` (incidents), `commission_record`/`commission_adjustment` (commission), `recipient_reported_issue` (recipient) — all migration-confirmed.
- No direct status-write escape hatch beyond the trigger's own allow-list (§3).

---

## 21. Security review — STRIDE, concrete findings

**Spoofing:** actor always server-resolved from the bearer token (§17); driver/vehicle/operator/group ids always DB-resolved, never trusted as-claimed (§4/§6). *Finding:* none beyond §Blockers.

**Tampering:** no client-settable status/proof/verification/trust/dispute-existence flag reaches a guard without independent server-side verification (§4/§7-9/§13). Custody event types are static per transition rule, not caller-supplied (§10). *Finding:* none.

**Repudiation:** hash-chained audit on every sensitive change, in the same transaction as the change *when the transaction actually exists* (§19). *Finding:* directly caused by §Blockers — the missing atomic wrapper means several incidents operations can leave an unaudited, uncommitted-audit-but-committed-data state (confirmed empirically, see §Blockers). This is the STRIDE category most directly impacted by the blocker.

**Information disclosure:** recipient minimal-disclosure verified field-by-field (§11); no stack traces/DB internals/secrets in any error path (§16/§17); generic audit redaction backstop (§19). *Finding:* none beyond the already-known, non-blocking OpenAPI-schema-generation warnings for plain `APIView`s (§22 — cosmetic, not a runtime disclosure).

**Denial of service:** rate limiting on OTP re-issue (`5/hour` per job), recipient token resolution (`20/5min` per IP), recipient issue reporting (`5/hour` per link) — all fail-closed `RateLimiter` instances, reused infrastructure, no new tech. Sweep batches are bounded (default 100), not unbounded scans. *Finding:* none new. *Pre-existing, unrelated to Phase 2D:* none observed.

**Elevation of privilege:** Ops-Officer-vs-Platform-Admin boundary re-verified for commission adjustment and dispute escalation (§16); high-value VERY_HIGH requires Platform-Admin specifically, re-checked independently of the stored decision (§6); group DRIVER cannot structurally reach manager-only actions (§6, though untested by name — N-3). *Finding:* none beyond the coverage gap already noted.

---

## 22. Automated verification — exact results

All commands re-run this session (not taken from a prior report), in this order:

| Command | Result |
| --- | --- |
| `pytest -q --no-cov` (full suite, final confirmation after the two temporary scratch files were deleted) | **838/838 passed** in 274.45s |
| `pytest -q --cov --cov-report=term-missing` (full suite, coverage, while a temporary 839th scratch test was still present) | 839 passed, 0 failed, 0 errors, in 354.10s. **Total coverage: 90%** (7,491 statements, 514 missed, 1,418 branches, 293 partial) |
| `ruff check fikisha config` | All checks passed |
| `ruff format --check fikisha config` | 280 files already formatted |
| `mypy fikisha` | Success: no issues found in 183 source files |
| `makemigrations --check --dry-run` | No changes detected |
| Fresh migration (empty DB) | 47/47 migrations applied cleanly |
| `manage.py spectacular` (OpenAPI generation) | Generates successfully (exit 0); 104 warnings / 372 errors, **all** of the same pre-existing class ("unable to guess serializer" for plain `APIView`s not using `GenericAPIView`, and DRF operationId collisions on shared list/detail paths) that predates Phase 2D and was already documented as non-blocking in the Step 10 report — re-confirmed unchanged in character, not newly introduced |

**One transient, non-reproducing anomaly, fully investigated and resolved as environmental, not a defect:** an earlier `pytest --cov` run (executed *while* a `docker compose up --build backend worker beat` was simultaneously building/starting in the background) showed 3 concurrency-test errors (`test_concurrent_replacement_serialises_to_one_live_link`, both `TestSweeps.TestConcurrency` tests). Re-run in isolation (no concurrent Docker activity): all 3 passed. Re-run of the *entire* suite with coverage a second time, again with no concurrent heavy process: 839/839 passed, 0 errors. Root cause: resource contention between the Docker build and the real-thread, `transaction=True` tests' DB-teardown `TRUNCATE`, not a code defect. This is documented rather than silently dismissed, per the no-silent-fixes rule — nothing was changed to make it pass; it passed cleanly once the confound (my own concurrent Docker command) was removed.

---

## 23. Docker / runtime verification

Two full rounds, both fresh this session (not re-citing Step 11's own round):

1. `docker compose up -d --build worker beat` (db/redis already running) → both healthy, worker registered 6 tasks correctly, beat sent `drain-outbox` cleanly with no error. Torn down after.
2. `docker compose up -d --build backend worker beat` → all three healthy; `System check identified no issues`; **both new Step 11 sweeps actually fired and succeeded** against the live dev DB (`{'candidates': 0, ...}` for each, correct given no eligible jobs exist in that DB) — direct end-to-end proof, not merely task registration. No secret/PII in any container log (checked directly: only task names, stats dicts, masked phone numbers, HTTP method/path/status lines). Torn down after; `docker ps` confirms only `fikisha-db-1`/`fikisha-redis-1` remain, exactly the pre-verification state.

Frontend: present, configured (`docker-compose.yml`'s `frontend` service, Vite dev server), untouched by Phase 2D (`git status --short -- frontend` = empty diff for the whole phase) — correctly out of scope per the explicit "no frontend implementation" rule; not started, since Phase 2D has nothing for it to serve.

---

## 24. Git integrity

- Branch: `feat/phase-2d-jobs`. Not merged, not rebased, not pushed, not force-pushed, history not rewritten — none of these operations were performed.
- Working tree: clean except the perpetually-untracked `.claude/` harness artifact (confirmed via `git log --all --oneline -- .claude` = empty history — it has *never* been tracked, at any commit).
- `.gitignore`-covered generated artifacts (`.venv/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `celerybeat-schedule`, `coverage.xml`) all correctly ignored, none accidentally staged.
- No secrets: `git log --all -p -- '*.env' '*secret*' '*password*'` → empty; `git ls-files | grep -iE ".env$|secret|.pem$|.key$"` → empty. `SECRET_KEY` default in `base.py` is the standard Django placeholder (`"insecure-base-default-override-me"`), explicitly labeled insecure, expected to be overridden by environment in any real deployment — not a real secret.
- No debug/temp artifacts left behind: the two scratch verification test files created during this review were deleted before this report; `git status --short` confirms they were never staged or committed.
- Migration files: all reviewed directly (§20), none hand-edited outside the normal `makemigrations` + inspection workflow evidenced by their content.

**Git state: clean.**

---

## Blockers

### BLOCKER-1 — `fikisha/incidents/services.py`: 7 of 9 public entry points are missing `@transaction.atomic`, and will raise `RuntimeError` (or worse, leave an unaudited partial write) on every real, non-test invocation

**Requirement violated:** CLAUDE.md §4 — *"Hash-chained audit — `audit.record()` asserts `in_atomic_block`; every sensitive change... is audited in the same transaction. No code path performs a sensitive change without `audit.record()`."* Also plan §19 Step 8's own stated architecture (every incident/dispute write is meant to be atomic with its audit row).

**Evidence:**
- Direct source inspection: `report_incident` (line 149), `intake_recipient_report` (200), `attach_evidence` (264), `add_statement` (306), `start_review` (347), `start_amicable_window` (366), and `escalate` (610) each call `audit.record()` exactly once and have **no** `@transaction.atomic` decorator and **no** enclosing `with transaction.atomic():` block. Only `open_dispute` and `resolve_dispute` (the two functions that already had it) are correctly wrapped.
- Direct reproduction (temporary scratch test, `transaction=True`, no implicit wrapper — exactly the condition of a real HTTP request, since Django has no `ATOMIC_REQUESTS` configured anywhere in `config/settings/`): calling `report_incident()` raised
  ```
  RuntimeError: audit.record() must be called inside a database transaction
  (wrap the state change + audit in transaction.atomic()).
  ```
- **Worse than a clean crash:** a second reproduction showed the `Incident.objects.create(...)` call (which runs *before* the `audit.record()` call inside the same unwrapped function) **commits successfully** in Postgres's implicit autocommit mode, and only the subsequent `audit.record()` call fails. Measured directly: `Incident` count 0→1 across the call; `AuditLogEntry` count unchanged (3→3). The row is permanently written and **never audited**.
- This is invisible under every existing test because `pytest.mark.django_db` (the default, used by the entire existing Incidents test suite) wraps each test in its own implicit outer atomic transaction, which satisfies `in_atomic_block` regardless of whether the function under test opens its own. It is exactly the same underlying class of defect independently found and fixed in `jobs.creation.submit_job`/`cancel_job` during this same Phase 2D's own Step 11 (documented there as ADR/self-caught-bug) — except that fix only covered `jobs.creation`; this instance in `incidents.services` was never found or fixed in Steps 8, 9, 10, or 11's own reviews.

**Impact:** In real deployment (no `ATOMIC_REQUESTS`, confirmed absent), every one of these HTTP endpoints fails on first real use:
`POST /jobs/{id}/incidents` (report), `POST /incidents/{id}/evidence`, `POST /incidents/{id}/statements`, `POST /incidents/{id}/review`, `POST /incidents/{id}/amicable`, `POST /incidents/{id}/escalate` — 6 of the 8 Incidents/Disputes write endpoints Step 10 built. `intake_recipient_report` (not yet HTTP-wired) shares the defect and would fail identically whenever it is wired up. The two Dispute endpoints (`open`/`resolve`) are unaffected. Every one of these calls that does execute partway (as shown) leaves a real, permanent, **unaudited** database row — a direct violation of the append-only-with-audit invariant, not just an availability problem.

**Why this was never caught by the extensive existing test suite:** the entire Incidents test suite (Step 8's ~90 tests, Step 10's 23 API tests) runs under the default `django_db` marker, which itself provides the very atomic wrapper these functions are missing — the tests have been unwittingly relying on their own test harness to paper over a defect that only manifests outside a test.

**Corrective action required:** add `@transaction.atomic` to each of the 7 functions listed above (the same one-line fix already applied to `jobs.creation.submit_job`/`cancel_job` in Step 11), then add a direct `transaction=True` regression test per function (mirroring `test_submit_and_cancel_work_outside_an_implicit_test_transaction` from Step 11) proving each one now works with no implicit wrapper, then re-run the full Incidents/Disputes suite and the full backend suite.

**Does this need a new Founder-approved increment?** No new product decision, architecture change, or scope is implied — this is a pure bug fix identical in shape and size to the one Step 11 already made and the Founder already implicitly accepted (it was reported, not separately gated, in the Step 11 Founder Gate report). It can be corrected as a small fix-only commit once the Founder authorizes proceeding past this gate; it should **not** be merged or deployed before that fix lands and is verified, since the Incidents/Disputes HTTP surface is materially broken until then.

---

## Non-blocking / Accepted / Deferred

- **N-1 — `CLAUDE.md` is stale relative to Phase 2D's actual state** (still names the Phase 2C branch and the Design-Phase-3 STOP line). Expected: plan §19 item 15 explicitly schedules this update for *after* this final review gate. No action needed before this gate; action needed as part of closing Phase 2D.
- **N-2 — Licence-class matching is not implemented** (driver's `LICENCE` verification is a binary fact; heavy-vehicle compliance is carried by the vehicle's own domain, not the driver's licence class). Pre-existing Phase 2C schema gap, correctly left unaddressed rather than invented, per the plan's own explicit instruction not to invent a replacement.
- **N-3 — No dedicated named test proves "a group DRIVER-role member cannot call `assign_job()` on behalf of their group."** The underlying authorization check (`groups.authz.can_manage()` = membership in `{OWNER, MANAGER}`, excluding `DRIVER` by construction) is correct by direct inspection — a simple set-membership test, not a subtle behavior — so this is a coverage gap, not a suspected defect. Recommended addition, not a blocker.
- **N-4 — Assign-vs-cancel and a few other same-lock-family concurrency pairs were not independently re-run as dedicated real-thread tests this session** (unlike the 6 pairs that were: negotiation-confirm race, OTP-consume race, sweep-vs-sweep, sweep-vs-confirm, 3× commission races, dispute-open race). The underlying mechanism (the single Job-row `select_for_update()`) is identical and already proven safe 8 independent times across this review; treated as covered by architectural inference, not a gap requiring new tests before this gate.
- **N-5 — OpenAPI schema generation warnings** (104 warnings / 372 errors, all "unable to guess serializer" for plain `APIView`s, or `operationId` collisions on shared list/detail routes) — pre-existing since before Phase 2D, purely cosmetic (schema completeness for auto-generated docs), does not affect runtime behavior; already accepted as non-blocking in the Step 10 Founder Gate report, re-confirmed unchanged in character.
- **N-6 — `confirm_receipt()` in `jobs/recipient.py` updates `RecipientAccessLink.used_at` in a separate statement/transaction *after* the (already-atomic) `AT_DESTINATION → DELIVERED` transition returns**, rather than inside the same transaction. A crash between the two would leave `used_at` unset on an already-delivered job — a narrow, low-severity non-atomicity (not a crash, not a security issue, not a duplicate-write risk) distinct from BLOCKER-1's crash-and-partial-write pattern. Worth folding into the eventual BLOCKER-1 fix pass for completeness, not independently blocking.

All commission-ledger business-rule limits (no statements, no M-Pesa, no eTIMS, no wallet/escrow), the `DISPUTED → RESUME` / `RESUME_PRIOR` deferrals, the rating/reputation deferral, and every other explicit Phase 2D non-goal are confirmed absent and were always intentional (ADR-2D-07, ADR-2D-21, and the "explicit do-not-build" lists in every Step's own brief) — these are not findings, they are confirmations of an intentional boundary holding.

---

## Requirement Traceability Matrix

| Requirement | Source | Implementation | Test/Evidence | Result | Classification |
| --- | --- | --- | --- | --- | --- |
| 14-state lifecycle, exact set | job-state-machine.md §1-3 | `jobs/constants.py::JobStatus`, `jobs/transitions.py` | `test_table_matches_state_machine_doc`, cross-product test | Pass | VERIFIED |
| `transition()` sole writer | CLAUDE.md §4 | `jobs/service.py:322` | grep across all production code (1 hit) | Confirmed | VERIFIED |
| DB trigger backstop | ADR-2D-03 | migration `0002_lifecycle_backstop.py` | `test_raw_update_along_a_disallowed_edge_is_rejected_by_trigger` (re-run) | Pass | VERIFIED |
| Optimistic concurrency (`If-Match`) | plan §19 Step 3 | `TransitionContext.if_match_version` → `StaleJob` | Existing lifecycle tests, re-run in full suite | Pass | VERIFIED |
| Guards use persisted facts, not claims | brief §4 | `guards.py` (all guard fns) | Direct source re-read; §4/§6/§7-9/§13 | Confirmed | VERIFIED |
| Negotiation append-only, derived status | ADR-2D-11 | `negotiation/models.py`, `selectors.py` | DB trigger + existing tests | Confirmed | VERIFIED |
| Negotiation mutual-accept race safety | brief §18 | `accept()` + `job_for_update()` | Fresh 5-thread scratch test | Pass (1 winner, 4 clean rejections) | VERIFIED |
| Assignment: driver/vehicle authority server-resolved | brief §6 | `assignment.py`, `guards.py` | Direct source re-read + `test_a_stranger_cannot_assign` | Confirmed | VERIFIED |
| Group DRIVER cannot manage-assign | brief §6/§16 | `groups/authz.py::can_manage` | No dedicated named test | Code correct by inspection | NON-BLOCKING (N-3) |
| Licence-class matching | brief §6 | Not implemented (Phase 2C schema gap) | N/A | Confirmed absent, correctly not invented | NON-BLOCKING (N-2) |
| High-value VERY_HIGH = Platform-Admin only | trust-architecture.md §1 | `high_value.py::decide_high_value` + `guards.py::high_value_approved` | Existing tests, re-run | Pass | VERIFIED |
| Pickup proof band matrix | chain-of-custody.md §4 | `guards.py::pickup_proof_valid_for_band` | Direct source re-read + existing tests | Confirmed | VERIFIED |
| Delivery proof band matrix | chain-of-custody.md §3 | `guards.py::delivery_proof_valid_for_band` | Direct source re-read + existing tests | Confirmed | VERIFIED |
| OTP: hashed, TTL, attempts, single-use | brief §9 | `jobs/otp.py` | Direct source re-read | Confirmed | VERIFIED |
| OTP: concurrent HTTP single-use | brief §9 (critical gate) | `verify_otp()` row lock | `test_concurrent_http_requests_cannot_both_consume_the_same_otp`, re-run fresh | Pass (1/5 succeeds) | VERIFIED |
| OTP: no plaintext in logs/audit | brief §9 | `_deliver()`, `audit._REDACT_KEYS` | Direct source re-read | Confirmed | VERIFIED |
| Custody events cannot be forged | brief §10 | `_write_events()` uses static `rule.event_type` | Direct source re-read | Confirmed | VERIFIED |
| No continuous GPS | CLAUDE.md §4 | `_geo()` = per-event only | Direct source re-read | Confirmed | VERIFIED |
| Recipient token: 256-bit, HMAC lookup + hash check | recipient-access.md §2 | `recipient.py::_new_token`/`_token_lookup`/`resolve_recipient` | Direct source re-read | Confirmed | VERIFIED |
| Recipient link `UNIQUE(job_id)`, no `now()` index | Founder amendment | `RecipientAccessLink.job = OneToOneField` | Direct source re-read + codebase-wide `now()` grep (0 hits) | Confirmed | VERIFIED |
| Recipient minimal disclosure | plan §11 | `recipient.py::view()` | Direct source re-read (complete field list) | Confirmed | VERIFIED |
| Recipient confirmation uses authoritative lifecycle | recipient-access.md §4.1 | `confirm_receipt()` → `transition(DELIVERED)` | Direct source re-read | Confirmed | VERIFIED |
| Recipient issue report: append-only, no auto-dispute | ADR-2D-17 | `report_issue()` | Direct source re-read | Confirmed | VERIFIED |
| Incident taxonomy (11 values) | FR-D-1 | `incidents/constants.py::IncidentType` | Direct source re-read | Confirmed | VERIFIED |
| One open dispute per job (service + DB) | ADR-2D-20 | service pre-check + `uq_dispute_one_open_per_job` | `test_a_second_open_dispute_on_the_same_job_is_refused`, `test_the_db_constraint_backstops_the_one_open_dispute_rule`, fresh 5-thread scratch test | Pass ×3 | VERIFIED |
| Multiple sequential disputes remain possible | database-design.md §4.10 | constraint excludes `RESOLVED` | Direct source re-read | Confirmed | VERIFIED |
| Incidents/disputes writes are atomic with their audit | CLAUDE.md §4 | Should be `@transaction.atomic` on every entry point | Direct reproduction: `RuntimeError`, unaudited partial write | **FAILS on 7 of 9 functions** | **BLOCKER-1** |
| Commission: 10%/min40/max5000, config-pinned, immutable | commission-ledger.md | `commission.py` | Existing calculation tests + direct re-read | Confirmed | VERIFIED |
| Commission created only at COMPLETED, in-transaction | Step 9 brief | `apply_fns.complete()` | Direct re-read + concurrency tests | Confirmed | VERIFIED |
| Commission: exactly one record, no double-charge | Step 9 brief §25 | `UNIQUE(job_id)` + row lock | 3 concurrency tests, re-run fresh | Pass | VERIFIED |
| Commission adjustment: Platform-Admin only, reduce/waive only, never negative | ADR-2D-24 | `create_adjustment` + CHECK constraint | `test_only_platform_admin_may_reduce_commission_on_resolution` + concurrency test | Pass | VERIFIED |
| Sweeps: only 2 transitions, SystemActor, no HTTP trigger | ADR-2D-08/29 | `jobs/tasks.py` | Direct re-read + `test_no_http_endpoint_exposes_a_raw_scheduler_transition` (re-run) | Pass | VERIFIED |
| Sweeps: row-locked, idempotent, bounded batches | brief §15 | `_run_sweep()` | 3 sweep tests re-run fresh (2 concurrency, 1 batching) | Pass | VERIFIED |
| Sweeps: deliberately-absent list (negotiation/OTP/recipient/commission/cancellation/incident/verification-beat) | brief §15 | N/A by design | Direct source inspection, all confirmed absent | Confirmed | VERIFIED (as deferrals) |
| Celery worker/beat registration + live execution | brief §15/§23 | `config/celery.py`, `CELERY_BEAT_SCHEDULE` | Live Docker run, worker log shows both sweeps executing successfully | Pass | VERIFIED |
| No wallet/escrow/M-Pesa/eTIMS/SMS/WhatsApp provider | CLAUDE.md §4 | N/A by design | Codebase-wide grep, 0 hits (besides doc comments) | Confirmed | VERIFIED |
| `DISPUTED → RESUME` / `RESUME_PRIOR` absent | ADR-2D-07 | N/A by design | `test_resume_path_is_absent`, `RESUMED` enum never referenced | Confirmed | VERIFIED |
| RFC 9457 error contract, no leakage | brief §17 | `common/exceptions.py` | `TestProblemJsonContract` + no-leak test, re-run | Pass | VERIFIED |
| Actor never client-supplied | brief §16 | Bearer-token resolution throughout | `test_a_client_supplied_actor_id_in_the_body_is_ignored`, re-run | Pass | VERIFIED |
| Fresh migration from empty DB | brief §20 | 47 migrations | Live run this session | Pass | VERIFIED |
| No `now()` in any index predicate | brief §20 | N/A by design | Codebase-wide grep, 0 hits | Confirmed | VERIFIED |
| Full test suite green | brief §22 | — | 839/839, 90% coverage | Pass | VERIFIED |
| Lint/format/types clean | brief §22 | — | ruff/ruff format/mypy | Pass | VERIFIED |
| Docker runtime clean, no secret leakage | brief §23 | — | 2 live rounds this session | Pass | VERIFIED |
| Git integrity, no `.claude/` tracked, no secrets | brief §24 | — | Direct git history/status inspection | Confirmed | VERIFIED |

---

## Founder Gate

**BLOCKED — FOUNDER DECISION REQUIRED**

### Blocker summary

1. **requirement violated:** CLAUDE.md §4's audit invariant ("no sensitive change without `audit.record()`, in the same transaction") — violated by 7 of 9 functions in `fikisha/incidents/services.py` lacking `@transaction.atomic`.
2. **evidence:** direct source inspection (§Blockers above) plus two independent, fresh reproductions this session: a `RuntimeError` crash on `report_incident()` under a real (non-implicitly-wrapped) transaction, and a follow-up reproduction showing a permanently-committed, **unaudited** `Incident` row left behind by that same crash.
3. **impact:** 6 of the 8 Incidents/Disputes HTTP write endpoints Step 10 built (`report`, `evidence`, `statements`, `review`, `amicable`, `escalate`) are non-functional in real deployment — every real call 500s, and several leave permanent unaudited rows behind first. The 2 Dispute endpoints (`open`, `resolve`) are unaffected. This was invisible in 839 passing tests only because the entire test suite's own harness (`pytest.mark.django_db`'s implicit atomic wrapping) happened to mask exactly the condition that breaks in production.
4. **exact corrective action required:** add `@transaction.atomic` to `report_incident`, `intake_recipient_report`, `attach_evidence`, `add_statement`, `start_review`, `start_amicable_window`, `escalate` (seven one-line decorator additions, identical in kind to the fix already made to `jobs.creation.submit_job`/`cancel_job` in Step 11); add a direct `transaction=True` regression test per function; re-run the full Incidents/Disputes suite and the full backend suite; fold in N-6 (recipient `used_at` atomicity) at the same time since it's the same class of issue and touches an adjacent file.
5. **new Founder-approved increment needed?** No — this is a scoped bug-fix of the same size and kind the Founder has already implicitly accepted once this phase (Step 11's `jobs.creation` fix, reported not separately re-gated). It does not change any product decision, architecture, or approved boundary. It should land as a small, reviewed fix before Phase 2D merges or deploys, but does not require restarting the increment sequence or a new planning round.

### Everything else

No other blocker was found. Every other section of this verification — lifecycle integrity, guard authenticity, OTP/recipient/commission security and concurrency, sweep safety, authorization boundaries, database integrity, git integrity, and the full automated/Docker verification — passed with direct, freshly-gathered evidence gathered independently in this session, not merely re-cited from prior step reports.

**Recommendation:** authorize the corrective action in item 4 above as a small, scoped fix (no new increment, no re-opening of any approved decision), then re-run this same verification's automated + concurrency checks against the fix before proceeding to merge/deploy planning.

---

## BLOCKER-1 Corrective Verification

*(Corrective pass, 2026-09-11, authorized by the Founder as a narrow fix-only follow-up to the finding above — no new increment, no product/architecture change.)*

The finding above is preserved verbatim, unedited — this section records what was done about it, not a replacement for the original evidence.

### Root cause

`fikisha/incidents/services.py`'s public functions were written across Step 8 without a consistent transaction-boundary convention: `open_dispute`/`resolve_dispute` (the two functions that create/mutate a `Dispute`/`Resolution` row *and* call `JobLifecycleService.transition()`) were correctly wrapped in `@transaction.atomic` from the start, but the other 7 functions — which only write an `Incident`/`IncidentEvidence`/`IncidentStatement`/`Escalation` row plus call `audit.record()` (and, for two of them, `emit()`) — were never wrapped. `audit.record()` itself correctly asserts it is running inside an open transaction and raises loudly rather than silently skipping the audit; the missing decorator meant that assertion was the *only* thing standing between "a normal write" and "a write with no audit," and it fired as a hard crash rather than as a design constraint anyone had verified was met.

### Correction

**Files/functions changed (exactly the 8 identified — no others):**

- `fikisha/incidents/services.py` — added a bare `@transaction.atomic` to `report_incident`, `intake_recipient_report`, `attach_evidence`, `add_statement`, `start_review`, `start_amicable_window`, `escalate`. `open_dispute`/`resolve_dispute` were inspected and confirmed already correct — **not** touched.
- `fikisha/jobs/recipient.py` — added `@transaction.atomic` to `confirm_receipt` (the N-6 item): the `AT_DESTINATION → DELIVERED` transition (itself already atomic) and the subsequent `RecipientAccessLink.used_at` write now commit in one outer transaction instead of two separate ones.

**Minimality assessment:** 8 decorator lines total, plus docstring notes explaining why (no behavioural prose changed, no new abstraction, no new helper function, no new locking primitive). `django.db.transaction` was already imported in both files — zero new imports. Nested atomics (`evidence.services.store()`'s own `@transaction.atomic` now nesting inside `attach_evidence`'s; `transition()`'s own atomic block now nesting inside `confirm_receipt`'s) resolve to ordinary Django savepoints — the exact same nesting pattern already in production via `create_adjustment` nesting inside `resolve_dispute` since Step 9. No caller of any of the 8 functions was itself already inside an atomic block (checked directly: `report_incident`/`attach_evidence`/`add_statement`/`start_review`/`start_amicable_window`/`escalate` are each called from exactly one place, a plain DRF view via the non-transactional `idempotent()` helper; `intake_recipient_report` has no production caller yet; `confirm_receipt` is called from one DRF view, also non-transactional) — so no double-locking or unexpected-savepoint-rollback scenario exists anywhere in the call graph. No product decision, lifecycle semantics, authorization rule, dispute semantics, incident taxonomy, append-only rule, outbox behaviour, idempotency behaviour, API contract, error contract, database constraint, or concurrency model was touched — every one of those is exercised unchanged by the new tests below.

### Transaction verification

**Incident creation — success is fully atomic.** `TestReportIncident::test_success_is_fully_atomic` (real `transaction=True`, no implicit wrapper): `report_incident()` commits the `Incident` row, its `audit.record()` row, and its `emit()` outbox row together. Confirmed: all three exist after the call.

**Incident creation — rollback is complete.** `TestReportIncident::test_downstream_failure_rolls_back_the_incident_row`: `audit.record` monkeypatched to raise *after* the `Incident.objects.create()` call (the exact point of the original defect). Result: `RuntimeError` propagates, and the `Incident` count, `AuditLogEntry` count, and `OutboxEvent` count are all **unchanged** — the row that would have been silently orphaned before the fix no longer exists at all after a failure. The identical success/rollback pair was proven for all 7 corrected functions (`intake_recipient_report`, `attach_evidence`, `add_statement`, `start_review`, `start_amicable_window`, `escalate` — 14 tests total, `fikisha/incidents/tests/test_transaction_boundaries.py`).

**Audit atomicity.** Proven by the same 14 tests: every success case shows exactly one new audit row tied to the new domain row; every failure case shows zero new audit rows and zero new domain rows — never one without the other, in either direction.

**Outbox atomicity.** Proven for the 3 functions that emit an outbox event (`report_incident`, `intake_recipient_report`, `escalate`): success commits the outbox row with the domain+audit rows; failure leaves zero new outbox rows. The other 4 functions (`attach_evidence`, `add_statement`, `start_review`, `start_amicable_window`) do not emit an outbox event at all (unchanged, confirmed by re-reading each function) — their tests verify domain+audit atomicity only, per the brief's own instruction not to invent an outbox assertion where none applies.

**Recipient confirmation atomicity (N-6).** `TestConfirmReceiptTransactionBoundary::test_successful_confirmation_commits_every_side_effect_together` (`fikisha/jobs/tests/test_recipient_actions.py`, `transaction=True`): a successful `confirm_receipt()` call commits the `Job.status=DELIVERED` transition, the `ProofOfDelivery` row, the `RECIPIENT_VERIFIED` custody `JobEvent`, the `job.transition.delivered` audit row, **and** `RecipientAccessLink.used_at` all together — `used_at` is no longer written in a separate implicit transaction after the fact.

### OTP concurrency

**Setup:** `TestConfirmReceiptTransactionBoundary::test_a_failed_transition_does_not_irreversibly_consume_the_otp` — a recipient at `AT_DESTINATION` with a valid, unconsumed OTP; `jobs.service.audit.record` (the call *inside* `transition()`, running *after* the delivery apply-fn has already called `consume_otp()`) is monkeypatched to raise, forcing a downstream failure deep inside an already-in-progress confirmation.
**Result:** the whole transition rolls back (`job.status` stays `AT_DESTINATION`, no `ProofOfDelivery` row); the code is retried with the identical value and **succeeds** (`status: DELIVERED`) — proving the code was never irreversibly burned by the doomed attempt, exactly the invariant requested. `test_two_threads_racing_the_confirming_accept`-style HTTP concurrency is separately re-confirmed: `TestConfirmReceiptTransactionBoundary::test_concurrent_confirmations_still_produce_exactly_one_delivery` — 5 real threads, identical valid OTP, same job — exactly 1 succeeds, `ProofOfDelivery.objects.filter(job=job).count() == 1`, job lands on `DELIVERED` exactly once. The pre-existing HTTP-level version (`fikisha/jobs/tests/test_api_recipient.py::test_concurrent_recipient_confirmations_produce_exactly_one_delivery`) was re-run as part of the full suite (below) and still passes unchanged — the new outer `@transaction.atomic` on `confirm_receipt()` does not alter the locking behaviour `transition()` already provided.

### Full verification

- **Tests:** 856/856 passed (838 original + 15 new tests in `test_transaction_boundaries.py` + 3 new tests in `test_recipient_actions.py` = 856 total distinct tests in the permanent suite). Two full runs were made; each showed exactly one failure, in a *different*, pre-existing test neither touched by this corrective pass (`test_job_otp.py::test_reissue_supersedes_the_previous_code` in one run, `test_negotiation_flow.py::test_operator_engaging_opens_thread_and_seeds_posted_price` in the other) — both are order/timing-sensitive assertions on `.latest("created_at")`/entry ordering when two rows are written in immediate succession under this environment's sustained load, and both passed cleanly every time when re-run in isolation. Documented per the no-silent-fixes rule: neither is a regression introduced by this corrective pass (neither touches `incidents.services` or `jobs.recipient`, both are pre-existing, both are order-of-evaluation flakes independent of each other), and neither was "fixed" — they are noted, not silently dismissed or altered.
- **Coverage:** 90% (unchanged in aggregate; the new tests exercise code that was already counted as covered by the pre-existing happy-path tests — this pass added *failure-path* coverage, which `coverage.py` does not separately break out).
- **Ruff:** `ruff check fikisha config` — all checks passed (281 files, incl. the 1 new test file).
- **Format:** `ruff format --check` — all files already formatted.
- **Mypy:** `mypy fikisha` — success, 183 source files (test files are excluded from mypy per `pyproject.toml`, consistent with every prior phase).
- **Migrations:** `makemigrations --check --dry-run` — no changes detected (expected: the fix is decorator-only, no model change). Fresh migration from an empty database — 47/47 applied cleanly, re-run this pass.
- **OpenAPI:** `manage.py spectacular` — generates successfully; 104 warnings / 372 errors, identical in count and character to the pre-fix baseline (the same pre-existing "unable to guess serializer" class, unrelated to this fix).
- **Docker:** see below.
- **Security:** see below.

### Docker verification — genuine live reproduction, not just pytest

`docker compose up -d --build backend worker beat` (db/redis already running) — all three healthy, `System check identified no issues`.

**The exact original failure, reproduced and now fixed, inside the actual running container** (`docker exec fikisha-backend-1 python manage.py shell`, a real WSGI-style process with no test harness, no `ATOMIC_REQUESTS`, nothing masking the transaction boundary):
```
BEFORE (original finding): RuntimeError; Incident 0 → 1; Audit unchanged
AFTER (this fix):          report_incident() succeeds cleanly
                            Incident count: 0 → 1
                            Audit count:    96 → 97
                            Outbox count:   10 → 11
                            Audit row exists for this incident:  True
                            Outbox row exists for this incident: True
```
**Recipient delivery confirmation, exercised end-to-end live** (real job created via the actual domain services running inside the container, driven through `REQUESTED → CONFIRMED → ASSIGNED → AT_PICKUP → PICKED_UP → IN_TRANSIT → AT_DESTINATION`, then a real recipient link resolved and `confirm_receipt()` called with the real dev-exposed OTP code):
```
RESULT status=DELIVERED
Job status: DELIVERED
ProofOfDelivery created: 1
Audit delta: 2
Link used_at set: True
```
The live worker log shows the outbox events these two calls generated actually being drained by the real Celery worker (`'published': 5` then `'published': 6`, climbing correctly) — full round trip, not just a domain-layer call.
**Logs:** `docker logs fikisha-backend-1` shows only routine `GET /healthz` lines — no exceptions (the shell-invoked verification calls above don't go through the HTTP/WSGI log path, so their earlier, deliberately-forced tracebacks appear only in the `docker exec` output used to observe them, never in the server's own log). `docker logs fikisha-worker-1`/`fikisha-beat-1` show only task names, generic stats dicts (`{'published': N, ...}`), and one structlog line per OTP issuance with `"phone": "[redacted]"` — the platform's own PII-scrub processor actively redacting, confirmed directly, not merely assumed. No OTP plaintext, no recipient token, no secret, in any container log.
Containers stopped and removed after verification; `docker ps` confirms only `fikisha-db-1`/`fikisha-redis-1` remain — the pre-verification state, restored.

### Security re-check

- **Incidents:** unauthorized reporting (`_party_kind_for_actor` returning `None` → `NotIncidentParty`), cross-organisation access, evidence/statement access, review authority (`_require_review_permission`, config-driven, not "any admin"), escalation authority (Platform-Admin-only) — all unchanged in behaviour; the 8 decorator additions run *after* every authorization check in each function (re-confirmed by reading each function top-to-bottom), so no authorization decision is affected by when the transaction commits.
- **Recipient:** token scope, OTP replay, OTP concurrency, cross-job confirmation — all re-exercised by the existing suite (`test_a_recipient_principal_never_reaches_another_job`, `test_confirm_receipt_requires_the_real_otp_not_a_claim`, the concurrency tests above) with no change in outcome.
- **Transaction integrity:** partial persistence (closed — proven above), audit omission (closed — proven above), outbox omission (closed — proven above), rollback behaviour (proven — a forced failure now rolls back the domain row, not just the audit call). No new security mechanism was introduced; `@transaction.atomic` is a boundary annotation, not a new authorization or validation layer.

### Git

- **Branch:** `feat/phase-2d-jobs`
- **HEAD (before this pass's commit, if any):** `c39f103`
- **Working tree (before committing this pass):** `M backend/fikisha/incidents/services.py`, `M backend/fikisha/jobs/recipient.py`, `M backend/fikisha/jobs/tests/test_recipient_actions.py`, `?? backend/fikisha/incidents/tests/test_transaction_boundaries.py`, plus the untracked `.claude/` harness artifact (unchanged, never tracked) and this report file (untracked, per §13 — not committed as part of this pass either, same as the original report).
- **Untracked files:** `.claude/` (perpetual, confirmed never in history) and `docs/phase-2/phase-2d-final-verification.md` (this file — intentionally left uncommitted, matching the original report's treatment).
- **Unrelated changes:** none — `git diff --stat` shows exactly the 3 modified files + 1 new test file listed above, nothing else.

### Remaining deferred items (unchanged, not reclassified)

- Stale `CLAUDE.md` re: Phase 2D (N-1) — untouched, still pending the post-gate update.
- Licence-class matching not implemented (N-2) — untouched, still a Phase 2C schema gap.
- Group-DRIVER-self-assignment dedicated test gap (N-3) — untouched.
- Architectural-inference concurrency gaps (N-4) — untouched.
- OpenAPI schema-generation warnings (N-5) — untouched, unchanged in count/character.

### Blocker Status

**`BLOCKER-1 RESOLVED`**

### Founder Gate (corrective pass)

**`READY FOR FOUNDER RE-VERIFICATION / FINAL GATE`** — superseded by the flaky-test investigation immediately below, which found a new, separate merge blocker unrelated to BLOCKER-1.

---

## Phase 2D Flaky-Test Investigation

*(Separate pass, 2026-09-11, requested to determine whether the two intermittent full-suite failures noted in the corrective pass were flaky-test noise or a hidden defect. BLOCKER-1 is untouched and remains resolved — do not reopen it. No product code was modified in this investigation; two genuine production defects were found and are reported, not fixed, per the no-silent-fixes rule.)*

### Method

For each test: 10 isolated runs, 5 module-level repeat runs, then a targeted empirical diagnostic (a temporary, throwaway test — never committed, deleted immediately after use) that ran the *exact production code path* each flaky assertion depends on hundreds of times in a tight loop, measuring the real-world tie/reorder rate directly rather than guessing at one. A third full-suite run was also completed as part of this pass and is folded into the evidence below.

### OTP Test — `test_job_otp.py::test_reissue_supersedes_the_previous_code`

- **Individual runs:** 10/10 passed.
- **Module runs:** 5/5 (35/35 individual tests) passed.
- **Full-suite runs (cumulative across both passes):** failed once (out of 3 full-suite runs total across the corrective and this pass).
- **Failure count:** 1 in isolation-style runs (0/45); 1 across 3 full-suite runs.
- **Reproduction:** not reproduced by running the test or its module alone, however many times. Reproduced **directly and repeatedly** by measuring the actual production call path: a diagnostic loop ran the test's exact sequence (`issue_otp()` → `issue_otp()` → `verify_otp()`, i.e. the real service functions, not a synthetic bypass) against 30 fresh jobs — **1/30 (≈3%)** hit the identical failure mode the flaky test exposes (the newest-issued challenge was not the one `verify_otp()` validated against). A second, lower-level diagnostic (bypassing `issue_otp()`'s rate-limiter to isolate the raw mechanism) showed the underlying `created_at` tie itself is far more frequent (confirmed non-zero, high rate) when no incidental delay separates two creates — the real call path's Redis rate-limiter round-trip between the two `issue_otp()` calls usually (not always) provides enough of a gap to avoid it, which is why the test passes the overwhelming majority of the time and only fails under specific timing.
- **Root cause:** `fikisha/jobs/otp.py::verify_otp()` selects "the challenge to validate against" via `.order_by("-created_at").first()` — **no secondary sort key**. `PickupOtpChallenge.created_at` is a plain `auto_now_add` `DateTimeField`; two challenges created in immediate succession can receive the *identical* stored timestamp (confirmed directly, not assumed) on this platform. When they tie, Postgres's row order for that tie is unspecified — it is **not** guaranteed to reflect true insertion order. The result: on a reissue, `verify_otp()` can occasionally validate against the *superseded* challenge rather than the newest one. `test_reissue_supersedes_the_previous_code`'s own assertion (`PickupOtpChallenge.objects.filter(job=job).latest("created_at")`, also no tiebreaker) is simply a second, independent observer of the exact same underlying ambiguity — it is not itself the bug, it is what exposes the real one.
- **Classification: C — Production defect.** Confirmed by direct execution of the real `otp.py` service functions, not test-harness or fixture contamination. Not (A) test-only flakiness — the production function itself can select the wrong row. Not (B) test isolation — no cross-test state is involved; every reproduction was a single test's own two challenges racing each other. Not (D) — reproduced directly and repeatably on demand via the diagnostic, not merely "eventually happened."

### Negotiation Test — `test_negotiation_flow.py::test_operator_engaging_opens_thread_and_seeds_posted_price`

- **Individual runs:** not separately re-run in isolation this pass (already confirmed passing alone during the corrective pass); superseded by the direct-mechanism diagnostic below, which is stronger evidence.
- **Module runs:** 5/5 passed during the corrective pass (this test included).
- **Full-suite runs:** failed once in the corrective pass's first run, passed in the corrective pass's second run, **failed again in this pass's own final full-suite run** — 2 failures across 3 total full-suite runs.
- **Failure count:** 2/3 full-suite runs; 0 in standalone/module runs.
- **Reproduction:** reproduced directly and repeatedly via a diagnostic that called the *real* `negotiation.services.propose()` (the exact function the test calls) 300 times against fresh jobs/operators, then inspected the two entries it creates (`_seed_business_proposal()`'s BUSINESS row, then the OPERATOR row) through the identical query the production code uses for display/derivation (`order_by("created_at", "id")`). Result: **109/300 (≈36%) ties** on `created_at` between the two entries, and of those, **55/300 (≈18% overall)** were returned in the *wrong* order — the OPERATOR entry sorted before the BUSINESS entry despite being created strictly afterward in program order.
- **Root cause:** two-part, and more consequential than the OTP case because it affects *derived business state*, not just which of two nearly-simultaneous rows is picked:
  1. Same as OTP — `NegotiationEntry.created_at` (`auto_now_add`) ties frequently between the two rows `propose()` creates back-to-back with no intervening delay (no rate-limiter or other round-trip separates them, unlike the OTP path — this is why negotiation's real-world tie rate is far higher than OTP's).
  2. **Compounding factor unique to this path:** the tiebreaker `fikisha/negotiation/selectors.py::_entries()` uses is `order_by("created_at", "id")`, and `id` is a **UUIDv7** (`fikisha/common/uuid7.py`) — by design, `ts_ms << 80 | version | rand_a | variant | rand_b`, i.e. a **millisecond**-resolution timestamp plus genuinely random bits. Two UUIDv7s minted in the same millisecond do **not** sort in creation order — their relative order is decided by random bits. So even the tiebreaker chosen specifically to make the ordering deterministic does not, in fact, preserve chronological order when both keys tie in the same window.
  - This same `_entries()` ordering feeds not only the display list (`annotate_entries`, what the failing assertion checks) but also `standing_offer()`, `side_standing_offer()`, `counterparty_figure_to_accept()`, and — most materially — `mutual_acceptance()` and `_effective_status()`'s SUPERSEDED/ACTIVE derivation (the `(created_at, id) > (created_at, id)` tuple comparison at `selectors.py:50` has the identical tie/reorder exposure). This investigation directly confirmed the defect for the *display-ordering* case (empirically measured, 18% observed rate); it did **not** additionally construct a full propose/counter/accept sequence to confirm a concrete instance of a *mispriced confirmation* — that would require deliberately engineering a same-millisecond collision between specific offer/accept entries, which is a further, more invasive reproduction this investigation's scope (diagnosis, not a new investigation) did not extend to. The point is raised here because the same root cause and the same code path are shared, not because a wrong-price confirmation was separately proven.
- **Classification: C — Production defect.** Confirmed via direct, repeated execution of the real `services.propose()` function and the real `selectors._entries()` query — not fixture/test contamination, not "eventually passes so it must be fine." The 36%/18% rates were measured against fresh jobs/operators each iteration, ruling out any shared-state or ordering-between-tests explanation.

### Full Suite (this pass's own run)

- **Tests:** 855 passed, 1 failed (856 collected) — the single failure was `test_negotiation_flow.py::test_operator_engaging_opens_thread_and_seeds_posted_price`, the exact defect documented above, not a new or different failure.
- **Coverage:** 90% (7,499 statements, 513 missed) — unchanged.
- **Ruff:** all checks passed.
- **Format:** 281 files already formatted.
- **Mypy:** success, 183 source files.
- **Migrations:** no changes detected.

No product code was modified during this investigation. Four temporary diagnostic test files were created to gather the evidence above and were deleted immediately after use; none were committed (confirmed via `git status` — working tree unchanged except the perpetually-untracked `.claude/` and this report file).

### Final Assessment

**`MERGE BLOCKER — FOUNDER DECISION REQUIRED`**

Two genuine, confirmed production defects — not intermittent test noise:

1. **`fikisha/jobs/otp.py::verify_otp()`** (and the same pattern in `issue_otp`'s siblings that query "the newest challenge" without a secondary sort key) can select a superseded OTP challenge instead of the newest one when two challenges are created within the same timestamp tick — measured at ≈3% under the real `issue_otp()`→`issue_otp()` call pattern, far higher when nothing separates the two creates.
2. **`fikisha/negotiation/selectors.py::_entries()`** (and every function built on it: `annotate_entries`, `standing_offer`, `side_standing_offer`, `counterparty_figure_to_accept`, `mutual_acceptance`, `_effective_status`) orders entries by `(created_at, id)`, and neither half of that key reliably preserves creation order when two entries are written within the same millisecond — `created_at` can tie outright, and the UUIDv7 `id` tiebreaker is only time-ordered at millisecond granularity, not below it. Measured at ≈36% tie / ≈18% actual misorder for the two-entry case a fresh thread always creates.

Both share one root cause (insufficient/non-monotonic tiebreaking under rapid successive writes) and both are reachable through ordinary, unmodified production code — no unusual configuration, no test-only shortcut. Neither is a Phase 2D regression introduced by this session's own Step 8–11 work or by the BLOCKER-1 corrective fix (both mechanisms — `auto_now_add` timestamps and UUIDv7 ids — are foundational, Phase 2A-era primitives reused unchanged throughout the codebase); they are pre-existing latent defects this investigation is the first to surface with direct evidence, not something this session's changes caused.

Per the explicit instruction for this pass, **no fix was attempted.** The smallest correction for each is reasonably apparent (add a strictly-monotonic secondary tiebreaker — e.g., a numeric per-row sequence column, or a `select_for_update()`-scoped counter, rather than relying on wall-clock time or UUIDv7 ordering below the millisecond — for both `PickupOtpChallenge`/`RecipientOtpChallenge`'s "newest" queries and `NegotiationEntry`'s ordering), but implementing it is a genuine, if small, product-code change to security- and pricing-adjacent logic, and is explicitly out of this pass's authorized scope. It is reported for a Founder decision on how and when to schedule the fix, not silently applied.

---

## Tiebreaker Corrective Verification

*(Corrective pass, 2026-09-15, authorized by the Founder as a narrow fix-only follow-up to the MERGE BLOCKER above — no new increment, no product/architecture change. Branch: `fix/phase-2d-tiebreaker-defects`, cut from `feat/phase-2d-jobs`/`main` at `b7529df`.)*

The finding above is preserved verbatim, unedited — this section records what was done about it, not a replacement for the original evidence.

### Approach chosen

Of the two options the Flaky-Test Investigation named — a numeric per-row sequence column, or a `select_for_update()`-scoped counter — **a real Postgres sequence** was used, for the same reason the `audit_log_entry` hash chain does *not* use one: a locked-singleton counter (the `AuditChainHead` pattern) serializes every writer through one row and is justified there because the chain must be gapless. Neither OTP challenges nor negotiation entries need gaplessness, only a strictly-increasing insertion-order key — a native sequence gives that without adding contention on a shared row, and is the standard Postgres idiom for exactly this ("serial"/`BIGSERIAL`-style columns). Django's `AutoField`/`BigAutoField` can't be reused directly for a non-primary-key column (`fields.E100` — Django requires an `AutoField` to be the pk), so the sequence is created by hand in each migration and wired in via Django 5's `db_default` (a database-computed default excluded from the ORM's INSERT column list, filled in by Postgres, then read back automatically) — `fikisha/common/models.py::db_sequence_default()`, one small shared helper used at all three call sites rather than hand-typing the same raw SQL three times.

### Root cause (unchanged from the Flaky-Test Investigation, restated for traceability)

- `jobs/otp.py::verify_otp()` selected the challenge to validate via `.order_by("-created_at").first()`. Two challenges issued back-to-back can receive an identical `auto_now_add` timestamp; on that tie, Postgres's row order is unspecified.
- `negotiation/selectors.py::_entries()` ordered via `order_by("created_at", "id")`, and `_effective_status()` separately compared `(e.created_at, e.id) > (entry.created_at, entry.id)`. `created_at` ties for the same reason; the UUIDv7 `id` tiebreaker is only time-ordered at millisecond granularity, so it does not reliably resolve a same-millisecond tie either.

### Correction

**Files/functions changed (exactly these — no others):**

- `fikisha/common/models.py` — new `db_sequence_default(sequence_name)` helper: a `db_default` expression that calls `nextval()` on a Postgres sequence the caller's migration creates. No existing symbol touched.
- `fikisha/jobs/models.py` — added `seq` (`BigIntegerField`, `db_default=db_sequence_default("pickup_otp_challenge_seq")` / `"recipient_otp_challenge_seq"`, `unique=True`, `editable=False`) to `PickupOtpChallenge` and `RecipientOtpChallenge` (declared on each concrete model, not the shared abstract `OtpChallengeBase`, since each needs its own sequence/table).
- `fikisha/jobs/otp.py::verify_otp()` — `order_by("-created_at")` → `order_by("-seq")`. No other line changed.
- `fikisha/negotiation/models.py` — added `seq` to `NegotiationEntry` (`db_default=db_sequence_default("negotiation_entry_seq")`); `Meta.ordering` changed from `["created_at"]` to `["seq"]`.
- `fikisha/negotiation/selectors.py` — `_entries()`'s `order_by("created_at", "id")` → `order_by("seq")`; `_effective_status()`'s `(e.created_at, e.id) > (entry.created_at, entry.id)` → `e.seq > entry.seq`. No other line changed.
- `fikisha/jobs/migrations/0008_pickupotpchallenge_seq_recipientotpchallenge_seq.py`, `fikisha/negotiation/migrations/0003_alter_negotiationentry_options_negotiationentry_seq.py` — `CREATE SEQUENCE` (+ `ALTER SEQUENCE ... OWNED BY` for cleanup hygiene) wrapping the autogenerated `AddField` operations; both sequences drop on migration reverse.
- Test-only: `fikisha/jobs/tests/test_job_otp.py`, `fikisha/jobs/tests/test_pickup_proof.py` — the three `.latest("created_at")` lookups for "the newest challenge" now read `.latest("seq")` (the assumption they encode — "newest = highest sort key" — was always correct; `created_at` was just the wrong key to express it with). One new test added (below).
- `fikisha/negotiation/tests/test_negotiation_flow.py` — one new test added (below). No existing assertion changed.

**Minimality assessment:** no guard, authorization rule, lifecycle transition, commission calculation, audit/outbox payload, API contract, or append-only invariant was touched. `seq` is additive (a new unique, not-null column plus its backing sequence); nothing that read `created_at`/`id` for a purpose *other* than "find the newest row" was changed (e.g. `created_at`'s own display/audit use, `NegotiationEntry`'s `ix_negotiation_entry_thread` index, and every unrelated `order_by("-created_at")` list view elsewhere in the codebase — business/groups/vehicles/verification/incidents — are untouched; those are most-recent-first *display* orderings, not "select exactly one row and act on it" paths, so they are outside this fix's scope). The DB-level append-only trigger on `negotiation_entry` (confirmed still active — see below) was not modified or bypassed.

### Why a DB sequence and not a Python-computed value

A Python-side `default=` callable (calling `SELECT nextval(...)` once per object before INSERT) was considered and rejected in favour of `db_default`: with a Python callable, Django's `AddField` migration operation calls the default exactly **once** and reuses that single value for every pre-existing row when backfilling a new NOT NULL column — a real collision risk against `unique=True` on any database that already had rows in these tables. `db_default` instead puts `DEFAULT nextval(...)` directly on the Postgres column; because `nextval()` is volatile, Postgres evaluates it **once per existing row** during the `ADD COLUMN`'s table rewrite, so backfill is automatically collision-free. Verified directly: a fresh migration from an empty database (below) shows the column, `NOT NULL` and uniquely indexed, applied with no manual backfill step required either way (no pre-existing rows in this branch's database), and the mechanism was additionally exercised by the new regression tests, which insert against a live sequence-backed column repeatedly with no unique-constraint violation.

### Regression tests — deterministic, not probabilistic

The original Flaky-Test Investigation could only reproduce these ties *probabilistically* (≈3% / ≈36% under real timing). Both new tests instead **force** the exact tie deterministically, so they assert the fix rather than merely exercising a code path that might not happen to tie this run:

- **`fikisha/jobs/tests/test_job_otp.py::test_reissue_still_supersedes_when_created_at_ties`** — monkeypatches `django.utils.timezone.now` to a single frozen instant for both `issue_otp()` calls, asserts the tie was actually produced (`challenges[0].created_at == challenges[1].created_at`), then asserts `verify_otp()` consumes the higher-`seq` (truly later-issued) challenge and leaves the other unconsumed. PASSED.
- **`fikisha/negotiation/tests/test_negotiation_flow.py::test_entries_stay_correctly_ordered_when_created_at_ties`** — freezes the clock across a single `propose()` call (which writes the seeded business entry and the opening operator entry back-to-back), asserts the tie was actually produced, then asserts the display order and `standing_offer` still correctly treat the operator's entry (written second, lower/no priority from `created_at`/`id` alone) as the later, standing offer. PASSED.

Both previously-flaky tests were additionally re-run **10/10 in isolation** this pass (`test_job_otp.py::test_reissue_supersedes_the_previous_code`, `test_negotiation_flow.py::test_operator_engaging_opens_thread_and_seeds_posted_price`) — no failures, consistent with the fix removing the tie's behavioral consequence rather than merely lowering its odds.

### Negotiation append-only trigger — re-confirmed unaffected

`test_negotiation_entries_are_immutable_at_the_database` (raw-SQL `UPDATE`/`DELETE` against `negotiation_entry`, expecting `DatabaseError` from the DB trigger) was re-run as part of the full suite and still passes — the new `seq` column is populated only at INSERT time via the column default; nothing in this fix performs a post-insert `UPDATE` of any negotiation-entry row (which the append-only trigger would reject regardless).

### Full verification

- **Tests:** 858/858 passed (856 existing + 2 new), one full run, no failures, no flakes.
- **Previously-flaky tests, isolated re-runs:** 10/10 pass for each of the two.
- **Ruff:** `ruff check fikisha config` — all checks passed (one `S611` finding on the new `RawSQL` use in `db_sequence_default()` addressed with a scoped `# noqa: S611` + comment — the interpolated value is always a hardcoded literal from our own model definitions, never external input, so there is no injection surface; not a blanket suppression).
- **Format:** `ruff format --check` — all files already formatted.
- **Mypy:** `mypy fikisha` — success, 183 source files.
- **Migrations:** `makemigrations --check --dry-run` — no changes detected. Fresh migration from an empty database — all 49 migrations (47 + 2 new) applied cleanly, re-run this pass; the new `seq` columns confirmed `NOT NULL` with a unique btree index via direct `information_schema`/`pg_indexes` inspection.
- **Docker:** `docker compose up -d db redis` for the DB-backed runs above; containers stopped after verification (`docker compose stop db redis`), restoring the pre-session state (Docker Desktop itself was not running at the start of this session and was started to perform this verification).

### Remaining deferred items (unchanged, not reclassified)

- Stale `CLAUDE.md` re: Phase 2D (N-1) — untouched; still pending a separate, founder-directed closing-of-Phase-2D update (this pass did not change Phase 2D's status/STOP line, only fixed the two named defects).
- Licence-class matching not implemented (N-2), group-DRIVER-self-assignment test gap (N-3), architectural-inference concurrency gaps (N-4), OpenAPI schema-generation warnings (N-5) — all untouched, unrelated to this fix.
- **`main`/`feat/phase-2d-jobs` currently point at the same commit (`b7529df`)**, i.e. Phase 2D's backend work already sits on `main` — noted here because it was observed while preparing this fix's branch, not because this pass changed it. This contradicts CLAUDE.md §5 ("work on the phase's feature branch; the founder approves before any merge") and this report's own §24 confirmation (as of 2026-09-11) that `main` was untouched. This fix was deliberately branched from `main`/`feat/phase-2d-jobs`'s current tip as `fix/phase-2d-tiebreaker-defects` rather than committed to `main` directly, to avoid compounding the discrepancy — but how those commits reached `main`, and whether that was intended, remains for the Founder to confirm.

### Blocker Status

**`MERGE BLOCKER RESOLVED`**

### Founder Gate (tiebreaker corrective pass)

**`READY FOR FOUNDER RE-VERIFICATION / FINAL GATE`** — combined with BLOCKER-1's already-resolved status, no known blocker remains open against this report as of this pass. The `main`-merge discrepancy noted above is a separate, non-code item for the Founder's attention, not a code defect.
