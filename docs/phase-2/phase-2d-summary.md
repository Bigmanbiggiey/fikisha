# PHASE 2D — JOBS & CORE COORDINATION REPORT

## 1. Status

**IMPLEMENTATION + VERIFICATION COMPLETE — AWAITING FOUNDER APPROVAL (second gate).**

Establishes the Job as the fundamental domain object: the 14-state lifecycle,
two-way sealed negotiation, assignment (solo + group, high-value gating),
custody transitions with band-dependent pickup/delivery proof, recipient
scoped access (no account), incidents & disputes, commission-on-completion,
the full API boundary, and the two lifecycle-critical scheduled sweeps — on
top of Phases 2A (foundation), 2B (identity & organisation), and 2C
(vehicles & verification), reusing their auth, authorization engine, audit,
outbox, storage, API conventions, and test infrastructure unchanged.
**Fikisha still never holds the transport fare; no trust/rating engine
exists; no SMS/WhatsApp/M-Pesa/eTIMS provider is wired.**

Plan §19 Steps 1–11 (the eleven implementation increments) and Steps 12–15
(this closing pass: invariant/property tests, static+migration+Docker
verification, a security review, and this doc-promotion) are done. Step 16
— the second founder gate — is where this stands now: no merge (beyond what
is separately recorded in the Process Exception below), no deploy.

## 2. Branch history

Implemented on `feat/phase-2d-jobs` (off `feat/phase-2c-vehicles-
verification`'s tip). **Process exception, documented in `CLAUDE.md` §7 and
`phase-2d-final-verification.md`:** on 2026-09-11 that branch was fast-
forward-merged into `main` and pushed to `origin/main` with no PR and no
recorded founder approval — discovered 2026-09-15, investigated, and
retroactively ratified by the Founder rather than reverted (the code itself
is real and tested; the failure was procedural, not a defect in Phase 2D's
own work). The Steps 12–15 closing work in this report, plus the tiebreaker
corrective pass, were done directly on `main` from that point (`fix/phase-
2d-tiebreaker-defects`, fast-forward-merged into `main` on explicit founder
instruction, distinct from the earlier unauthorized merge).

## 3. Commits

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
c39f103 feat(phase-2d): Step 11 — scheduled sweeps over the approved Jobs lifecycle
b7529df fix(phase-2d): BLOCKER-1 corrective pass — atomic incidents/recipient services
66f3b8c fix(phase-2d): strictly-monotonic seq tiebreaker for OTP + negotiation ordering
0b48912 docs: reconcile CLAUDE.md status/STOP-line with what's actually on main
292df82 docs: update working-branch line now that the tiebreaker fix is on main
```

## 4. Files / Modules Added

**Backend (three new apps):** `fikisha/jobs/` (`models`, `service`
[`JobLifecycleService.transition()`], `transitions`, `guards`, `apply_fns`,
`eligibility`, `creation`, `assignment`, `high_value`, `custody`, `otp`,
`recipient`, `commission`, `selectors`, `job_authz`, `policies`, `dto`,
`tasks`, `management/commands/{jobs_expire_requests,
jobs_autocomplete_delivered}`, `api/{serializers,views,urls}`, `migrations`
0001–0008, `tests/`), `fikisha/negotiation/` (`models`, `services`,
`selectors`, `authz`, `policies`, `api/{serializers,views,urls}`,
`migrations` 0001–0003, `tests/`), `fikisha/incidents/` (`models`,
`services`, `authz`, `policies`, `api/{serializers,views,urls}`,
`migrations` 0001–0002, `tests/`).
**Backend (modified):** `fikisha/common/models.py` (`db_sequence_default` —
tiebreaker fix), `fikisha/api/urls.py` (mounts the three new `api/`
subpackages under `/api/v1/`), `fikisha/evidence/services.py`
(`EvidenceValidationError` now subclasses `DomainError`, self-caught fix),
`scripts/smoke-test.sh` (Windows Python-interpreter-resolution fix, unrelated
portability bug found while re-running Step 13's Docker smoke check).
**Docs (new):** this file + `phase-2d-plan.md`, `phase-2d-decisions.md`,
`phase-2d-api.md`, `phase-2d-final-verification.md`.

13 new migrations total: `jobs` 0001–0008, `negotiation` 0001–0003,
`incidents` 0001–0002.

## 5. Domain Model

Full detail: `phase-2d-plan.md` §5 (schema), `phase-2d-decisions.md` (every
implementation decision + deviation), `docs/phase-1/job-state-machine.md`.

```
Job (14-state lifecycle, JobLifecycleService.transition() the sole writer)
 ├─< NegotiationThread >─< NegotiationEntry (append-only, status DERIVED not stored)
 ├─< Agreement (append-only, frozen agreed_price_kes)
 ├─< Assignment (driver + vehicle, solo or group)
 ├─< HighValueApproval (append-only, one per job, HIGH/VERY_HIGH gate)
 ├─< JobEvent (append-only, category+type; chain_of_custody/job_status_event/
 │             job_timeline are SQL views over this one table)
 ├─< PickupOtpChallenge / RecipientOtpChallenge (hashed, TTL, seq-ordered)
 ├─< ProofOfPickup / ProofOfDelivery (append-only, band-dependent method)
 ├─< RecipientAccessLink (UNIQUE(job_id), revoke-then-replace under the job lock)
 ├─< RecipientReportedIssue (append-only boundary, not the incident model)
 ├─< CancellationRecord / FailureRecord (append-only)
 ├─< CommissionRecord (append-only, config-version-pinned) >─< CommissionAdjustment
 └─< Incident (mutable workflow) >─< IncidentEvidence / IncidentStatement (append-only)
       └─< Dispute (mutable, partial-unique "one open per job") >─< Resolution (append-only)
                                                                   >─< Escalation (append-only)
```

## 6. Job Lifecycle

Exactly the 14 approved states; 35 transition rows (`ALLOWED_TRANSITIONS`),
pinned byte-for-byte against `job-state-machine.md` and mirrored into a DB
seed table + `BEFORE UPDATE` trigger backstop (rejects any status write
outside the approved edges, even raw SQL, unless the transitioning session
flag is set — and that flag is only ever set inside `transition()` after
every guard has passed). 21 guards, each re-deriving its fact from persisted
state — never trusting a caller-supplied claim. `job.version` is the
`If-Match` optimistic-concurrency token (domain layer only — see
`phase-2d-api.md` §1 for the one honest HTTP-wiring gap); `Idempotency-Key`
reuses `JobTransitionIdempotency`. Full transition-table/guard/apply-fn
completeness is itself covered by a dedicated invariant test suite
(`jobs/tests/test_transitions_table.py`), extended in Step 12 with a
generic append-only-model sweep, two new atomicity rollback proofs, and the
two coverage gaps the final-verification report flagged (N-3: a group
DRIVER cannot exercise manager authority over another member; N-4: a real
`assign_job()` vs `cancel_job()` concurrency race).

## 7. Negotiation, Assignment, Custody, Recipient Access

- **Negotiation:** parallel per-(job×operator/group) sealed threads;
  `NegotiationEntry` is truly append-only (ADR-2D-11) — status is derived at
  read time, never stored. Mutual acceptance closes the winning thread,
  supersedes siblings, and confirms the job, all in one transaction.
- **Assignment:** eligibility is evaluated against the specific driver +
  vehicle, never the operator/group alone (ADR-2D-14); a group's standing
  can only *reduce* what it may do. High-value jobs need a real,
  independently-re-checked pre-assignment decision (Ops Officer for HIGH,
  Platform Admin only for VERY_HIGH).
- **Custody:** band-dependent pickup proof (STANDARD allows an
  operator-attested fallback; ELEVATED+ does not) and delivery proof
  (STANDARD: OTP/signature/photo; ELEVATED+: OTP **and** photo). OTP is
  hashed at rest, 5-minute TTL, attempt-capped, single-use under a real row
  lock (proven with genuine concurrent HTTP requests) — and, as of the
  tiebreaker fix, selects "the newest challenge" via a strictly-monotonic
  DB sequence rather than a timestamp that can tie.
- **Recipient access:** a non-account, single-job, time-limited, revocable
  link (256-bit token, HMAC lookup + hashed compare); minimal-disclosure
  read (no price, no value, no staff info, no location history); the same
  `AT_DESTINATION → DELIVERED` transition the driver uses, gated by the
  recipient's own OTP.

## 8. Incidents, Disputes, Commission

- **Incidents & Disputes:** the 11-value FR-D-1 taxonomy; small, explicit
  Incident/Dispute status workflows (not the 14-state Job lifecycle reused);
  at most one open dispute per job (service pre-check + a DB partial-unique
  index as the concurrency backstop, proven with real racing threads);
  `Resolution.actions` records admin-declared intent flags only — nothing
  executes a rating/trust/suspension consequence anywhere in Phase 2D
  (ADR-2D-21).
- **Commission:** `max(min_fee, min(price × rate, cap))`,
  `Decimal`-exact, `rate=10%`/`min=KES 40`/`cap=KES 5,000`, created as a
  literal same-transaction side effect of `DELIVERED → COMPLETED`; every
  rate/min/cap/config-version is pinned directly on the row, never merely
  FK'd. Adjustments are Platform-Admin-only, always a reduction, never
  automatic. No wallet, no escrow — Fikisha never holds the fare.

## 9. API Boundary

Full endpoint inventory: [`phase-2d-api.md`](phase-2d-api.md). Three new
`api/` subpackages, all thin adapters over the already-approved domain
services — no lifecycle/negotiation/assignment/proof/incident/dispute/
commission rule duplicated in HTTP. RFC 9457 problem+json throughout; cursor
pagination; `Idempotency-Key` reuses the existing two mechanisms
(cache-based for plain creates, the DB-row store for lifecycle actions).

## 10. Scheduled Sweeps

A sweep is candidate selection + one `transition()` call per candidate,
nothing else — no second business-rule engine. `expire_requests`
(`REQUESTED → FAILED`) and `autocomplete_delivered` (`DELIVERED →
COMPLETED`) are beat-wired at 300s each, running as the canonical
`SystemActor`; no HTTP route exposes a raw scheduler transition. The
originally-planned `jobs_close_post_completion_window` was not built —
verified, not assumed, that there is nothing left for it to do (ADR-2D-30).

## 11. Authentication & Authorization

Extends the Phase 2A engine unchanged: `authorize(actor, action, resource)`,
default-deny, `@policy`. `job.read`/`incident.read` are genuine object-level
policies (not just coarse action gates) as of Step 10. Negative-case
coverage: unrelated business/operator, Ops-Officer-vs-Platform-Admin
boundaries, stranger-vs-assignment, recipient-principal cross-job isolation,
client-supplied-actor-id ignored. No stack trace, DB error text, or other
internal detail ever reaches an error response.

## 12. Tests

**Backend — 904 pass (858 + 46 new), 90% coverage (unchanged from the
final-verification baseline — the new tests exercise failure/rollback paths
`coverage.py` doesn't separately break out from already-covered happy
paths).** New Step 12
invariant/atomicity coverage on top of the 858 tests the eleven increments
and two prior verification passes already built:

| File | Covers |
| --- | --- |
| `common/tests/test_append_only_sweep.py` | every concrete `AppendOnlyModel` in the app registry rejects bulk `.update()`/`.delete()` — a generic sweep, not per-table, so a future table that forgets the wiring fails CI immediately |
| `jobs/tests/test_atomicity_sweep.py` | forced-failure rollback proofs for `transition()`, `create_draft()`, `decide_high_value()` — the same BLOCKER-1 defect class, checked directly rather than only by inspection |
| `negotiation/tests/test_negotiation_flow.py::test_a_downstream_audit_failure_rolls_back_the_whole_propose_call` | same, for `propose()` |
| `jobs/tests/test_assignment_groups.py::test_a_driver_role_member_cannot_assign_a_fellow_member` | final-verification report N-3: a DRIVER-role member cannot exercise manager authority over another member (isolated from the mode-gate, already separately tested) |
| `jobs/tests/test_assign_vs_cancel_concurrency.py` | final-verification report N-4: a real `assign_job()`/`cancel_job()` race — found the pair is not symmetric (cancellation reaches its target from either `CONFIRMED` or `ASSIGNED`), asserts the actual deterministic property instead |
| `jobs/tests/test_job_otp.py`, `negotiation/tests/test_negotiation_flow.py` | tiebreaker-fix regressions: force the exact `created_at` tie via a frozen clock and assert the strictly-monotonic `seq` column resolves it correctly every time |

Every previously-flaky test (`test_reissue_supersedes_the_previous_code`,
`test_operator_engaging_opens_thread_and_seeds_posted_price`) re-run 10/10
clean since the tiebreaker fix landed.

## 13. Verification / Definition of Done

| Gate | Result |
| --- | --- |
| Backend `pytest` | **904 passed**, 90% coverage |
| Backend `ruff check` / `ruff format --check` | clean |
| Backend `mypy` | clean, 183 source files |
| Backend `makemigrations --check` | "No changes detected" |
| Fresh migration (empty PostgreSQL 16) | 49/49 migrations applied cleanly |
| Docker full-stack smoke (`scripts/smoke-test.sh`) | **SMOKE TEST PASSED** — all 12 steps (health, PWA served, OTP auth round-trip, authenticated request, 403 enforcement, admin creation, atomic DB+audit+outbox write, Celery worker drain, audit chain integrity) |
| Security review (STRIDE + `claude-security`) | see §14 |

## 14. Security Review

The final-verification report (`phase-2d-final-verification.md` §21) already
ran a full STRIDE pass across the whole Phase 2D surface, closed the one
finding it produced (BLOCKER-1 — Repudiation: an unaudited write was
possible under a real transaction) with a corrective pass, and separately
found + closed the tiebreaker MERGE BLOCKER (also STRIDE-relevant: picking a
superseded OTP challenge or misordering negotiation entries under a tie is
an integrity/Tampering-adjacent gap, not just a display bug — closed).

**Note on `claude-security`:** the plan names the `claude-security`
scan-changes workflow for this step. That tool is explicitly user-triggered
and billed (the same as `/code-review ultra`) — this session does not launch
it autonomously. What follows is a direct manual STRIDE pass over
everything Step 12–15 touched, re-checking the final-verification report's
categories rather than re-doing its full scope:

- **Spoofing:** unchanged — actor is still always server-resolved from the
  bearer token; nothing in Step 12–15 introduced a new identity-bearing
  input. `db_sequence_default()`'s `sequence_name` interpolation (the one new
  string-formatted SQL in this pass) takes only hardcoded literals from our
  own model definitions, never request data — confirmed by reading every
  call site (3, all in `models.py` files).
- **Tampering:** the tiebreaker fix directly closes a residual tampering-
  adjacent gap (above). No other client-settable value reaches a guard
  unverified — re-confirmed for the 3 new/changed call sites this pass
  touched (`verify_otp`, `_entries`, `_effective_status`).
- **Repudiation:** re-swept this pass specifically — every `audit.record()`
  call site across `jobs`/`negotiation` is now either `@transaction.atomic`
  itself or provably reachable only from a caller that already is (checked
  by hand for every call site, not just the ones BLOCKER-1 found; codified
  as a direct rollback test for the four that lacked one:
  `transition()`, `create_draft()`, `decide_high_value()`, `propose()`).
- **Information disclosure:** unchanged — no new error path, no new log
  line, no new field on any existing serializer.
- **Denial of service:** unchanged — no new unbounded query or missing rate
  limit introduced; the new append-only sweep test and concurrency tests are
  test-only code, not reachable in production.
- **Elevation of privilege:** the N-3 regression test (§12) is itself an EoP
  closure — a DRIVER-role group member could previously not be shown, by a
  named test, to be blocked from exercising manager-level assignment
  authority over a fellow member; now it is.

No new finding. `grep`-swept `jobs`/`negotiation`/`incidents` for broad
`except Exception`/`except BaseException` (one hit, `jobs/tasks.py` — the
documented, narrow, per-candidate sweep-isolation catch, not a silent
security-relevant swallow) and for any raw SQL with untrusted string
interpolation (none, beyond the already-reviewed sequence-name literals).

## 15. Deviations / ADRs

[`phase-2d-decisions.md`](phase-2d-decisions.md) — 30 ADRs (2D-01–2D-30,
plus 2D-14a), 4 of which are genuine deviations from a Phase 0/1 doc (all
either a Founder Gate confirmation or a Founder-selected reconciliation of
two conflicting approved docs, never a silent decision): ADR-2D-10 (plain
lat/lng, no PostGIS), ADR-2D-11 (`negotiation_entry` fully immutable, status
derived), ADR-2D-16 (`RecipientOtpChallenge.link` nullable), ADR-2D-20
(`Dispute`'s partial-unique index, not a hard `UNIQUE(job_id)`). Plus 3
self-caught defects fixed during the increments themselves, and 2
post-implementation corrective passes (BLOCKER-1, the tiebreaker fix) fixed
after a dedicated final-verification review. No approved **product**
decision was changed anywhere in Phase 2D.

## 16. Explicitly NOT Implemented

A real Trust & Reputation engine (only the interim deterministic rule) ·
ratings/reputation · `DISPUTED → RESUME`/`RESUME_PRIOR` (still an open
Phase-0 item) · any wired SMS/WhatsApp/M-Pesa/eTIMS provider ·
wallets/escrow/fare custody · payroll, shift scheduling, driver transfers,
or other complex fleet management · continuous GPS/live-tracking/route
optimisation/AI dispatch · native mobile apps. No placeholder
implementations of any of these were created.

## 17. Known Limitations

- Licence-*class* matching is not implemented — `LICENCE` verification is a
  binary fact; heavy-vehicle compliance is carried by the vehicle's own
  domain instead. A pre-existing Phase 2C schema gap, correctly left
  unaddressed rather than invented.
- `If-Match`/`job.version` optimistic concurrency is fully built at the
  domain layer but not yet wired to any HTTP request header — see
  `phase-2d-api.md` §1. A real, honestly-documented gap, not a designed
  limitation.
- `intake_recipient_report()` exists as a domain function with no HTTP route
  (plan §19 Step 8 built it as a plain callable, still true after Step 10).
- OpenAPI schema generation carries pre-existing, cosmetic warnings (104
  warnings / 372 errors — "unable to guess serializer" for plain `APIView`s,
  `operationId` collisions) — not a runtime disclosure issue.
- Reusing a saved `BusinessLocation` at job-creation time is deferred — only
  ad-hoc pickup/destination locations are supported.
- RLS still not enabled (Phase 1 OD-10); row scoping is application-layer.

## 18. Phase 2E / next-phase handoff — clean inputs only

- The full API boundary (`phase-2d-api.md`) and the 13 already-built,
  tested frontend domain primitives from Design Phase 5B (JobStatusChip,
  JobCard, JobTimeline, NextActionCard, TrustLevel, Modal, etc.) — ready to
  compose the Jobs frontend screens Design Phase 5C escalated as blocked.
- `Resolution.actions`'s stored-but-unexecuted intent flags (ADR-2D-21) and
  `Dispute.pre_dispute_status` (ADR-2D-07) — clean seams for a future Trust
  & Reputation / `RESUME_PRIOR` phase to read, once approved.
- Provider-neutral outbox events for every OTP/notification/recipient-link
  path (ADR-2D-09/18) — ready for whichever SMS/WhatsApp/M-Pesa/eTIMS
  provider decision comes next.

**Do not start the next phase, deploy, or merge further work to `main`
without explicit founder instruction.**

---

## Exact commands

```bash
# ── Backend ───────────────────────────────────────────────────────────
cd backend
export DJANGO_SETTINGS_MODULE=config.settings.test
export POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=fikisha \
       POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev

python manage.py migrate
python manage.py makemigrations --check --dry-run   # -> "No changes detected"
ruff check fikisha config
ruff format --check fikisha config
mypy fikisha                                        # -> 0 errors, 183 files
pytest --cov --cov-report=term-missing               # 904 passed, 90% coverage

# ── Docker / smoke ───────────────────────────────────────────────────
cp .env.example .env
./scripts/smoke-test.sh                              # -> SMOKE TEST PASSED
docker compose down
```

---

## Phase 2D Status

IMPLEMENTATION + VERIFICATION COMPLETE — AWAITING FOUNDER APPROVAL (second gate)
