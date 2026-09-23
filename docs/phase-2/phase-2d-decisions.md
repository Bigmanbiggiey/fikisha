# Phase 2D — Implementation Decisions

Decisions taken while implementing Jobs & Core Coordination (the Job
lifecycle, negotiation, assignment, custody, recipient access, incidents &
disputes, commission, the API boundary, and scheduled sweeps), and every
place the implementation fills a gap in or deviates from the approved Phase
0/1 design. Extracted from `docs/phase-2/phase-2d-plan.md` §14 (where these
were originally recorded, ADR-2D-01 through ADR-2D-30 plus 2D-14a) as part of
closing out Phase 2D (plan §19 Step 15). **No approved product decision was
changed. No contradiction with the approved architecture was found that
wasn't already resolved, deliberately and non-silently, below.**

Status: **CONFIRMED** (follows the approved design, or a permitted technical
refinement in its spirit) · **DEVIATION** (differs from a Phase 0/1 doc, with
rationale — several of these were explicit Founder Gate confirmations, see
plan §21) · **PROVISIONAL** (revisit in a later phase — currently only the
interim Trust ceiling, ADR-2D-05, pending the Trust & Reputation phase).

---

## ADR-2D-01 — Module layout: `jobs` owns the lifecycle writer; siblings depend inward — CONFIRMED

`jobs` owns `JobLifecycleService.transition()` and the guards; `negotiation`
and `incidents` are sibling apps that depend inward on `jobs` (read via
`jobs.selectors`, write only through `transition()`); custody has no
dedicated app — it is `job_event` rows written by `jobs` itself, continuing
the single append-only-table consolidation Phase 1's own ADR-009 already
established.

## ADR-2D-02 — Optimistic concurrency + idempotency reuse existing primitives — CONFIRMED

`job.version` is the `If-Match` optimistic-concurrency token (a new `common`
helper parses `If-Match` and raises `412 stale_job`); `Idempotency-Key`
support reuses `common/idempotency.py`, scoped `(actor_id, job_id, key)`. No
new concurrency-control mechanism invented.

## ADR-2D-03 — DB trigger backstop + seed table mirror the 2A/2C append-only pattern — CONFIRMED

The transition-table backstop (a `BEFORE UPDATE` trigger + an
`allowed_job_transition` seed table, added via a reversible `RunSQL`
migration) rejects any `job.status` write outside the approved edge set,
even a raw SQL `UPDATE`. The `app.lifecycle_service` session flag is set only
*inside* `transition()`, after every guard has passed — the same pattern
already used for the audit/outbox append-only triggers in Phase 2A/2C.

## ADR-2D-04 — `job_event` is one append-only table; timeline views are SQL views, not duplicated data — CONFIRMED

`job_event` carries `category`/`type`/`is_custody` on a single table;
`chain_of_custody` / `job_status_event` / `job_timeline` are SQL **views**
over it, not separate tables. This is not full event sourcing — `job.status`
remains the authoritative current-state column (brief §26); the events are
the permanent history alongside it.

## ADR-2D-05 — Driver trust ceiling: interim conservative deterministic rule — PROVISIONAL

`DriverTrustCeilingCoversValue` (the guard gating a value band against the
assigned driver's trust) derives its answer from verification facts plus
`config.value_bands[].min_trust_level`, deterministically and
conservatively — **not** a Trust score/level engine and **not** any form of
rating. This is Founder-approved Option (b) from plan §21 E-2, explicitly
provisional pending the standalone Trust & Reputation phase; nothing here
should be read as that phase having already happened.

## ADR-2D-06 — Recipient principal is a first-class non-`User` auth subject — CONFIRMED

`RecipientPrincipal` is resolved from a link's `token_lookup`, accepted
directly by `authorize()` alongside ordinary `User`-backed actors, and every
access — resolved, denied, or acted-on — is audited. The minimal-disclosure
serializer (`recipient.view()`) is the only read path a recipient ever
reaches; there is no broader recipient API surface to accidentally expand
later.

## ADR-2D-07 — `DISPUTED → RESUME` is not implemented — CONFIRMED (Founder Gate E-1)

Only `Dispute.pre_dispute_status` is persisted, so a future, separately
founder-approved `RESUME_PRIOR` rule has a deterministic value to read. No
resume operation, endpoint, or algorithm exists anywhere in Phase 2D; the
`JobEventType.RESUMED` enum value exists as a reserved placeholder only and
is never emitted. This item remains an **open Phase-0 product decision**, not
something Phase 2D silently closed.

## ADR-2D-08 — All three time-dependent sweeps are beat-wired, not command-only — CONFIRMED (Founder Gate Q-5)

`request_expiry`, `delivery_acceptance` auto-complete, and (originally
planned, later found unnecessary — see ADR-2D-30) a post-completion-window
close were all intended as beat-wired management commands, unlike Phase 2C's
optional verification-expiry command — because `DELIVERED → COMPLETED` by
`SCHEDULER` is itself part of the already-approved lifecycle, not an optional
hygiene task.

## ADR-2D-09 — Provider-neutral outbox events only; no SMS/WhatsApp wired — CONFIRMED (Founder Gate E-3)

OTP issuance emits `otp.pickup.requested` / `otp.recipient.requested`
outbox events; no SMS or WhatsApp provider is selected or wired anywhere in
Phase 2D. A later phase (or the still-pending provider decision) wires
delivery against these same events — no rework of the domain layer needed
when that happens.

## ADR-2D-10 — Plain `lat`/`lng` decimals, no PostGIS — DEVIATION from `database-design.md` (Founder Gate E-4/Q-4)

`database-design.md` specifies `GEOGRAPHY(POINT,4326)` for pickup/
destination/event locations; the stack has no PostGIS. Phase 2D stores plain
`DecimalField` `lat`/`lng` + a `geo_state` enum instead, mirroring ADR-2B-04
(business/operator locations already made the identical choice in Phase 2B).
Distance is informational only — no routing, no geospatial querying is lost
because none was built on top of the PostGIS column anywhere.

## ADR-2D-11 — `negotiation_entry` is truly immutable; status is derived, not stored — DEVIATION from `database-design.md` §4.8 / `negotiation-architecture.md` §4 (Increment 2)

The plan and `negotiation-architecture.md §7.1` both mandate
`negotiation_entry` as a hard `AppendOnlyModel` + `BEFORE UPDATE/DELETE`
trigger — but `database-design.md §4.8` and `negotiation-architecture.md §4`
separately describe a mutable `status` column updated by the confirm
transaction and an `expire_stale_offers` sweep, which is flatly incompatible
with "INSERT, SELECT only." Reconciled in favour of the **stronger**
immutability statement (CLAUDE.md §4's own append-only rule): an entry row
is never written after `INSERT`; `selectors.effective_entry_status` folds in
thread status, `expires_at`, and later same-side offers at read time — the
exact `VerificationRecord.effective_state()` precedent. The stored `status`
column and its sweep index are dropped; no `expire_stale_offers` beat job was
ever part of the approved Q-5 sweep set either, so nothing is lost. No
product behaviour changes: an expired offer still cannot be accepted, and a
superseded offer still stays visible in the history with its real timestamp.

## ADR-2D-12 — Thread bookkeeping on confirm lives in the Negotiation Service, in the confirming transaction — CONFIRMED (Increment 2)

`job-state-machine.md §3.1` and ADR-007 require "close winning thread;
supersede siblings" *inside* the `CONFIRMED` transaction, but `jobs.apply_fns`
may never import `negotiation` models (module-boundary rule). Resolved by
having `NegotiationService.accept()` wrap
`JobLifecycleService.transition(job, CONFIRMED, …)` in its own
`transaction.atomic()` and, in that same transaction, set the winning thread
`CLOSED` and its siblings `SUPERSEDED` — entries themselves are never
touched; their effective status flips purely by derivation (ADR-2D-11). If
the transition raises (e.g. a racing confirm → 409), the whole thing rolls
back and no thread is altered.

## ADR-2D-13 — Read boundary: siblings read a Job only through `jobs.selectors` — CONFIRMED (Increment 2)

`jobs.selectors.{get_job, job_for_update}` is the only way another app reads
a `Job`; no sibling app ever writes `job.status` except via
`JobLifecycleService.transition()`. This is the concrete implementation of
the module-layout read/write boundary rule.

## ADR-2D-14 — Assignment eligibility is evaluated against the specific driver + vehicle, never the operator/group alone — CONFIRMED (Increment 3)

The new `DriverAssignmentAllowed` guard (added to `CONFIRMED → ASSIGNED`)
requires the driver be the confirmed solo operator, or an **active** member
of the confirmed group whose standing is not `SUSPENDED` — a group's standing
can only *reduce* what it may do, never substitute for the driver's own
required trust eligibility (trust-architecture.md §2). `VehicleEligible`
checks the vehicle is controlled by the confirmed party, meets
`min_payload_kg`/`min_volume_m3`/`required_features`, and passes
`verification.required_domains_for_subject` (VEHICLE + ASSOCIATION, plus
HEAVY_CLASS_COMPLIANCE when heavy). `DriverVerificationCurrent` uses the same
config-driven mandatory-domain set for the driver (IDENTITY + LICENCE +
GOOD_CONDUCT) — group membership never substitutes for it either.
`admin_override_reason` relaxes **only** `DriverTrustCeilingCoversValue`;
every other gate (verification, vehicle, membership, high-value) still runs
unconditionally. High-value approval (`jobs.high_value.decide_high_value`) is
a real pre-assignment mechanism: an Ops Officer may decide a HIGH job, only a
Platform Admin may decide a VERY_HIGH job, one immutable decision per job;
`HighValueApproved` independently re-checks the VERY_HIGH/Platform-Admin
condition rather than trusting the stored decision's face value, so there is
no assignment path around it.

## ADR-2D-14a — Self-caught correctness fix: mistype-warning comparison no longer orders by `created_at` — CONFIRMED (Increment 3 review)

`negotiation._mistype_warning` previously ordered `negotiation_entry` rows by
`created_at` to find "the standing figure" — unreliable at real clock
granularity for entries written in the same transaction (the same underlying
timestamp-tie class of issue the Phase 2D final-verification report later
found and fixed more broadly, see "Post-implementation corrective passes"
below). Fixed during Increment 3's own review by comparing the new figure
against the standing offer / posted price the caller already passed in,
instead of re-deriving order from a timestamp. No behaviour change; removed
a latent flaky path before it was ever observed failing.

## ADR-2D-15 — Method-specific custody events are written by the apply fns, not a static rule — CONFIRMED (Increment 4)

`PICKUP_OTP_CONFIRMED` / `PICKUP_BUSINESS_CONFIRMED` /
`PICKUP_OPERATOR_ATTESTED` / `RECIPIENT_VERIFIED` are written by the
`confirm_pickup`/`confirm_delivery` apply fns, since the method is only known
once the proof is actually being written — `JobLifecycleService._write_events`
still assigns the same gapless, hash-chain-audited per-job `seq` immediately
after. `_write_events` also takes the transition `ctx` so a single geo
reading (lat/lng/accuracy, or `NOT_CAPTURED`) lands on the correct custody
row — chain-of-custody.md §5's "no continuous GPS, one reading per step"
rule, `NOT_CAPTURED` being an acceptable recorded value rather than an error.
`PICKUP_OTP_ISSUED`/`RECIPIENT_OTP_ISSUED` timeline events are written only
when a code is actually issued, so a missing contact phone no longer
produces a misleading "issued" row.

## ADR-2D-16 — `RecipientOtpChallenge.link` is nullable — DEVIATION (schema relaxation, Increment 4)

The recipient OTP is issued to `job.recipient_phone` on
`IN_TRANSIT → AT_DESTINATION`, independent of — and chronologically before —
the recipient access link (Increment 5). OTP verification is split
`verify_otp(consume=False)` (validated and committed in its own transaction,
so a wrong-code attempt's counter survives a later, unrelated guard failure)
plus `consume_otp()` (called by the apply fn only once every other guard has
passed) — so a driver who enters the correct code but forgets a required
photo does not have to ask for a fresh one.

## ADR-2D-17 — `RecipientReportedIssue` is the issue-report boundary, not the `incident` model — CONFIRMED (Increment 5)

Append-only (`AppendOnlyModel` + DB trigger), recording the curated category,
description, and photos, and never moving `job.status`. The Incidents app
(Step 8) is what triages/promotes a report into a full incident and decides
severity. `reported_via_link_id` is a plain `UUIDField`, not a FK to
`recipient_access_link`: the amended link lifecycle *deletes* a superseded
link row, which a FK would either block (`PROTECT`) or crash on
(`SET_NULL`'s delete-collector calls `.update()`, which `AppendOnlyQuerySet`
refuses even for Django's own cascade machinery) — `job` is the real,
permanent correlation key; the link id is forensic-only.

## ADR-2D-18 — Recipient link issuance is inside `arrive_destination`'s own transaction and row lock — CONFIRMED (Increment 5)

The link is issued/refreshed by the `IN_TRANSIT → AT_DESTINATION` apply fn,
under the same job-row `FOR UPDATE` lock as the transition itself — the
amended revoke-then-delete-then-insert sequence never needs a lock of its
own when triggered by arrival (recipient-access.md §8: "consumes
`JobAtDestination`"). `jobs.recipient.reissue_link()` is the standalone,
equally-atomic entry point for any other caller (tested independently,
including two genuinely concurrent threads). The raw token exists in memory
only at mint time, surfaced only behind the same `OTP_DEV_EXPOSE` gate the
OTP dev-code already uses — production delivery is the same provider-neutral
outbox-event seam as the rest of 2D (ADR-2D-09): `RecipientLinkIssued`
carries `link_id`, never the token.

## ADR-2D-19 — Token hashing reuses two existing house conventions — CONFIRMED (Increment 5)

`token_hash` uses Django's configured password hasher (`make_password`/
`check_password`, identical to OTP's `code_hash`); `token_lookup` is
`HMAC-SHA256(settings.SECRET_KEY, token)`, reusing the already-present
`SECRET_KEY` as the "server-held key" `recipient-access.md §2` calls for,
rather than standing up new secret-management/KMS infrastructure that is out
of scope for Phase 2D.

## ADR-2D-20 — Dispute uses a partial-unique index, not a hard `UNIQUE(job_id)` — DEVIATION from `database-design.md` §4.10 (Founder-selected, Step 8)

A literal hard-unique would permanently block the already-approved
`COMPLETED → DISPUTED` post-completion path on any job whose *first* dispute
already resolved it to `COMPLETED` — a second, later dispute could never be
recorded at all. Reconciled, as a Founder-selected option rather than a
silent decision, as
`UniqueConstraint(fields=["job"], condition=Q(status__in=[OPEN, UNDER_REVIEW, AMICABLE_PENDING, ESCALATED]), name="uq_dispute_one_open_per_job")`
— the predicate is on static status values only, never `now()` (the standing
rule from the Increment 5 Founder Gate amendment). One job may have more than
one `Dispute` episode over its lifetime; at most one may be open at a time —
this index doubles as the concurrency backstop for
`incidents.services.open_dispute()` (a second concurrent `INSERT` hits the
index and fails cleanly, not a race-prone check-then-write).

## ADR-2D-21 — `Resolution.actions` records admin-declared intent flags only; nothing executes them — CONFIRMED (Step 8)

`dispute-and-liability.md §6` describes confirmed-fault incidents feeding a
rating summary and operator trust-level assessment; the Step 8 brief
explicitly forbids introducing ratings, trust scoring, or any automatic
trust-level change in this increment. Resolved in favour of the more
specific, more recent instruction: `ResolutionAction` (`NONE` /
`RATING_IMPACT` / `TRUST_CHANGE` / `SUSPENSION`) is stored as data on the
append-only `Resolution` row for a **future**, separately-approved
trust/rating phase to read — no rating computation, no trust-engine call, no
operator/vehicle suspension side effect happens anywhere in Phase 2D. The
already-approved cancellation-reputation rule (3 late cancellations/wasted
trips, rolling 30-day window → admin-review flag) is unchanged and untouched.

## ADR-2D-22 — `jobs.apply_fns`'s dispute paths stay the pre-existing `noop`; Incidents writes its own rows around `transition()` — CONFIRMED (Step 8)

The module-boundary rule (sibling apps depend inward on `jobs`, never the
reverse) means `jobs.apply_fns` must not import or write `fikisha.incidents`
models. `incidents.services.open_dispute()`/`resolve_dispute()` create/
update the `Dispute`/`Resolution` rows themselves, before/around the call to
`JobLifecycleService.transition()`, inside the *same* outer
`transaction.atomic()` that also holds the Job row lock — so
`Dispute.pre_dispute_status` is stamped from the identical locked
`job.status` the transition itself reads, with no risk of the two
disagreeing. The three dispute guards (`BlockingIncidentExists`,
`ResolutionRecorded`, `NoOpenBlockingDispute` — scaffolded in Increment 1
with a lazy cross-app import, the one deliberate, narrower exception to the
module-boundary rule: a **guard** may read across the boundary to protect the
Job lifecycle's own invariants, it never writes there) now verify a real,
persisted, same-job Incident/Resolution row, not a truthy `ctx` claim —
closing a request-forgery gap the Increment-1 placeholder stubs had left
open.

## ADR-2D-23 — Commission lives in `fikisha.jobs`, not a separate app; `complete` is a real apply fn — CONFIRMED (Step 9)

`CommissionRecord`/`CommissionAdjustment` live in a new `jobs/commission.py`
domain-surface module (mirroring `jobs.otp`/`jobs.recipient`/
`jobs.assignment`), the opposite placement from Incidents (ADR-2D-22) and
deliberately so: the brief requires commission creation to be *literally*
inside the `DELIVERED → COMPLETED` transition's own transaction ("if
commission creation fails, the completion transaction must not partially
succeed"), and Commission — unlike Incidents/Disputes — has no workflow of
its own; it is the same shape of thing as `Agreement`/`Assignment`/`ProofOf*`,
already created inline by their apply fns in `jobs.models`. A failure inside
`create_commission_record_locked` aborts the whole transition (including the
`job.status` write) by ordinary transaction rollback — no savepoint-wrapping
needed. `resolve_completed` (`DISPUTED → COMPLETED`) is a plain, idempotent
alias of `complete`: a job can reach `COMPLETED` more than once (an ordinary
completion, then later a post-completion dispute resolved back to
`COMPLETED`, ADR-2D-20), and `create_commission_record_locked` simply returns
the existing row rather than creating a second (`UNIQUE(job_id)` is the DB
backstop either way). `incidents.services.resolve_dispute()` is the *only*
caller of `jobs.commission.create_adjustment()` — the allowed inward
direction, exactly as ADR-2D-22 established for Dispute/Resolution; `jobs`
still never imports `fikisha.incidents` (`source_dispute_id`/
`source_resolution_id` are plain `UUIDField`s, not FKs, same pattern as
`Incident.source_report_id`).

## ADR-2D-24 — Commission-adjustment authority is Platform-Admin-only, checked separately from dispute-resolution authority — CONFIRMED (Step 9)

`jobs.commission.can_adjust_commission()` checks for `PLATFORM_ADMIN`
directly; no `role_permissions` entry grants any other role this (brief §12:
broadening `role_permissions.OPERATIONS_OFFICER` to cover commission
adjustment was explicitly out of scope). An Operations Officer may still
resolve a Standard-band dispute with `commission_treatment=APPLY`, but
`resolve_dispute()` raises `NotAuthorisedForCommissionAdjustment` before any
write if that same Ops Officer asks for `REDUCE`/`WAIVE` — two genuinely
different authorities exercised through one call, checked independently.

## ADR-2D-25 — `jobs.creation.create_draft()` is a new domain function, not new business logic — CONFIRMED (Step 10)

No prior increment built a "create the `DRAFT` row" entry point — every
domain test since Increment 1 constructed a `Job` directly, which is fine for
a fixture but not something an HTTP view may call (views must call domain
services, never write models directly). `DRAFT` is not reached via
`transition()` (no `(_, DRAFT)` row exists — a job is *born* there), so
`create_draft()` is a plain create mirroring the fields the existing
fixtures already used; `submit_job()` immediately hands off to the real
first transition. Only ad-hoc pickup/destination locations are supported —
reusing a saved `BusinessLocation` is deliberately deferred (known
limitation, not a defect: nothing in the approved schema is missing for it,
there is simply no caller that needs it yet).

## ADR-2D-26 — `jobs.job_authz` duplicates the sibling-app party-resolution pattern rather than importing it — CONFIRMED (Step 10)

For the same reason `jobs.apply_fns` never imports `fikisha.incidents`
(ADR-2D-01/22/23): the module-boundary rule runs one way. `job_authz.
is_job_party()` is the real object-level check behind the `job.read`
policy (list views scope their queryset via `job_authz.jobs_visible_to()`;
detail views resolve the actual `Job` and run `is_job_party()` against it).
`incidents.policies`'s new `incident.read` policy follows the identical
pattern via `incidents.authz.is_job_party()` — the allowed inward-import
direction.

## ADR-2D-27 — The commission read endpoint is Platform-Admin-only — CONFIRMED (Step 10)

Not extended to the business or operator, even though the config's
`party_liable: "OPERATOR"` could argue an operator has a stake in seeing it.
No approved functional requirement names a non-admin party with a right to
read platform commission figures — the brief explicitly frames commission as
commercially sensitive, so this stays conservative. Broadening it to a
specific party is a product decision for whoever eventually builds the
weekly M-Pesa statement feature, not assumed here.

## ADR-2D-28 — Idempotency reuses the two existing mechanisms as-is — CONFIRMED (Step 10)

Plain creates with no domain-level idempotency key (job creation, incident
report, dispute open) use the existing cache-based
`common.idempotency.idempotent()` (Phase 2B, already used by every
business/operators/groups create endpoint); lifecycle actions that already
accepted an `idempotency_key` parameter since Increment 1 (submit, assign,
custody confirms, negotiation accept, dispute resolve) simply forward the
HTTP `Idempotency-Key` header into that parameter, reusing
`JobTransitionIdempotency` (the DB-row store built in Increment 1) — no
second idempotency store. One accepted, tested consequence: a retried
`resolve_dispute()` call does not replay a cached response byte-for-byte (no
`peek_idempotent()` short-circuit was added there) — it instead hits
`dispute.status == RESOLVED` under the row lock and cleanly returns `409
dispute_already_resolved`. No duplicate `Resolution`/`CommissionAdjustment`
row is possible either way — a safe, if not byte-identical, retry.

## ADR-2D-29 — A sweep is candidate selection plus one `transition()` call per candidate, nothing else — CONFIRMED (Step 11)

`jobs.tasks.expire_requests`/`autocomplete_delivered` compute their own
cutoff from `platform_config` and hand each candidate to the identical
`transition()` every API view already calls, as
`identity.authz.actors.SystemActor` (`audit_role == "SYSTEM"` — the exact
token already granted `SCHEDULER` since Increment 1; this sweep is simply
the first caller that reaches it). No guard, apply fn, or lifecycle rule
changed. Candidates are queried in bounded batches, then driven one at a
time — each `transition()` call keeps its own row lock and transaction, so a
candidate another actor already moved is a clean, expected `skipped`, never
a `failed`; a genuinely unexpected exception on one candidate is caught and
counted without aborting the rest of the batch. Only the two
lifecycle-critical sweeps are beat-wired (300s); `verification.tasks.
expire_due` exists so it *can* be scheduled later without duplicating
`services.expire_due()`, but stays command-only, matching Q-5. Management
commands call the Celery task function directly for synchronous manual
runs — the existing `drain_outbox` precedent, no new pattern invented.

## ADR-2D-30 — `jobs_close_post_completion_window` was not built — there is nothing left for it to do — CONFIRMED (Step 11)

The plan's original module layout named this sweep, assuming a commission
*hold* state a window-close sweep would later release. Step 9 (ADR-2D-23/24)
deliberately built `CommissionRecord` append-only with no `status`/HELD
field at all — commission is created unconditionally and atomically at
`COMPLETED`, with the only correction path being an explicit, authorized,
reasoned `CommissionAdjustment`. Separately, the `COMPLETED → DISPUTED`
window is already fully self-enforcing at request time
(`WithinPostCompletionWindow`, checked against `completed_at` + config on
every attempt) — once the window closes, the guard alone makes a fresh
dispute impossible; there is no separate piece of state left for a sweep to
flip. Documented as a verified plan-vs-implementation drift, not a silently
dropped requirement.

## ADR-2D-31 — Negotiation thread payload gains `operator_display_name` + `counterparty_offer` — CONFIRMED (Design Phase 6, Increment 3)

Found while building the Negotiation Thread frontend screen
(`design-phase-6-jobs-frontend-plan.md` §7 Increment 3), against
`design-phase-3-wireframes.md` §8.1's explicit offer-card spec (proposer
*name* on every card; a single-tap "Accept KSh X" primary action) — the
existing `_thread_payload()` (Step 10) didn't carry either:

1. **`operator_display_name`** — the wireframe names the proposer ("Athi
   Movers"), but the payload only ever carried `operator_id`/`group_id`, and
   `operator.read`/`group.read` stay closed to everyone but the profile's own
   owner (Phase 2B/2C policy, unchanged) — a business negotiating with an
   operator has no way to resolve that id to a name. Resolved via one new
   public function per sibling module — `operators.services.
   display_name_for(operator_id)` / `groups.services.display_name_for
   (group_id)` — called from `negotiation.services._operator_display_name()`,
   not a direct model import (module boundary rule). This doesn't reopen
   `operator.read`/`group.read`: the thread's own `operator`/`group` FK
   already scopes it to a party of *that* thread, no arbitrary-id lookup is
   added anywhere.
2. **`counterparty_offer`** — `standing_offer` (Step 8) is viewer-agnostic
   (whoever posted last, either side); it is **not** "what the current
   viewer can accept" — if the viewer's own offer is the most recent, there
   is nothing of the *counterparty's* to accept yet. The service layer
   already had this exact logic (`selectors.counterparty_figure_to_accept()`,
   used internally by `accept()`) but never exposed it in the read payload,
   which would have forced the frontend to re-derive an authoritative
   negotiation-state computation itself — directly against this module's own
   "derived, never stored" selectors.py convention. `_thread_payload()` now
   takes an optional `viewer_side` (every call site already computes the
   caller's side for its own authz/business-logic purposes) and includes
   `counterparty_offer: {entry_id, amount_kes} | null`.

Both are read-only additions to an already-approved response shape — no new
endpoint, no relaxed authorization, no negotiation business rule changed.
Regression tests: two businesses/operators with *different* resolved names
(not a same-value-everywhere false pass), and a same-thread two-sided check
that `counterparty_offer` is genuinely viewer-relative (right after an
operator opens a thread, both the operator's and the business's seeded
figures are simultaneously live, so each side's `counterparty_offer` must be
the *other* side's entry, not their own).

## ADR-2D-32 — `_effective_status()`'s blanket-supersede only applies to a SUPERSEDED thread, not CLOSED — CONFIRMED (Design Phase 6, Increment 3)

Found via the same Increment 3 live-browser verification as ADR-2D-31, on the
very next step: after a business accepted an operator's offer and the
operator accepted back (mutual acceptance, job → `CONFIRMED`), reloading the
Negotiation Thread screen showed "This thread was declined" instead of the
wireframe's pinned "Agreed: KSh X" banner — even though the deal had
genuinely gone through.

Root cause: `selectors._effective_status()`'s first check was
`if thread_status != ThreadStatus.ACTIVE: return SUPERSEDED` — true for
**both** `SUPERSEDED` (a sibling thread that lost — the case
`test_confirming_one_thread_supersedes_the_siblings` correctly covers) and
`CLOSED` (a thread that *won*, or was declined). Since `mutual_acceptance()`
only counts entries whose `effective_status` is `ACTIVE`, once
`_close_threads_on_confirm()` flipped the winning thread's own status to
`CLOSED` — inside the very same `accept()` call that just computed
`reached=True` — every *subsequent* read (a page reload, `view_thread()`
called later) recomputed `reached=False` forever after. The bug was invisible
throughout Phase 2D Step 10's own tests because none of them re-read a thread
*after* it closed to check `mutual_acceptance`/`entries` again — every
assertion was made using the same call's own return value, before the
status flip that (silently) invalidated the next read.

Fix: the blanket rule now checks `thread_status == ThreadStatus.SUPERSEDED`
specifically, not `!= ACTIVE`. A `CLOSED` thread's entries now fall through
to the normal per-entry rules — which already correctly resolve historical
ACCEPT/PROPOSE/COUNTER entries — instead of every entry reading as
`SUPERSEDED` regardless of what actually happened. `annotate_entries()` and
`standing_offer()`/`counterparty_figure_to_accept()` inherit the same fix
since they all key off `_effective_status()`; none of their own call sites
gate on `ACTIVE` specifically, so the fix flows through correctly (the
frontend separately gates *composing a new offer* on `thread.status ===
'ACTIVE'`, which is unaffected — the bug was only ever about *reading back*
what already happened). No change to any accept/counter/decline write path,
no new negotiation business rule. Regression test:
`test_mutual_acceptance_stays_readable_after_the_thread_closes` re-reads a
just-confirmed thread via a fresh `view_thread()` call, as a page reload
would. All 33 existing negotiation tests (including the SUPERSEDED-sibling
one) still pass unchanged — the fix narrows an over-broad rule rather than
removing it.

---

## ADR-2D-33 — Staff cancel is band-limited: an Ops Officer cancels ≤ STANDARD, above that only a Platform Admin — CONFIRMED (Design Phase 6, Increment 8; founder decision 2026-09-23)

The lifecycle engine gave every staff actor (Ops Officer or Platform Admin)
the same `ADMIN` initiator token on all six ordinary `* → CANCELLED` rules,
with no guard. So `POST /jobs/<id>/cancel` already let an Ops Officer cancel a
HIGH or VERY_HIGH job. That contradicted P3 §18.2 ("binding lifecycle moves
above Standard route to Platform Admin"), and it was inconsistent with the
dispute rule (D-ADM-1 / `AdminBandAuthorised`). The founder ruled that cancel
**should** be band-limited.

New guard `AdminCancelBandAuthorised` on the six ordinary cancel rules
(`DRAFT`, `REQUESTED`, `NEGOTIATING`, `CONFIRMED`, `ASSIGNED` and `AT_PICKUP →
CANCELLED`). `DISPUTED → CANCELLED` already has `AdminBandAuthorised`. The
guard:
- returns immediately if the caller asserted a **party** token
  (`BUSINESS_PARTY` / `BUSINESS_OWNER_OR_DISPATCHER` / `OPERATOR_PARTY` /
  `GROUP_MANAGER` in `initiator_tokens`, which server code sets, e.g.
  `cancel_job`'s `BUSINESS_PARTY`). **A business cancelling its own job is
  never affected, at any band.**
- on the staff path, requires a non-empty `reason_text`
  (`admin_reason_required`, FR-ADM-2 "each logged with … reason").
- above STANDARD, requires the `PLATFORM_ADMIN` role (`platform_admin_required`,
  the same code `AdminBandAuthorised` uses).
- skips the band check for `DRAFT`. The band isn't frozen yet (the cancel
  apply fn freezes it), and a draft isn't live work.

`AdminBandAuthorised` itself couldn't be reused, because it has no notion of
initiator kind and would have blocked business parties on ELEVATED+ jobs. No
transition was added or removed; only a guard was added.

## ADR-2D-34 — Operational note = an append-only `JobEvent(NOTE, ADMIN_ACTION)`, visible to the job's parties — CONFIRMED (Design Phase 6, Increment 8; founder decisions 2026-09-23)

P3 §18.2's "nudge" is not a system-sent message (that would need an
SMS/WhatsApp provider, which is outside the STOP line). It is the P4 §18
"operational note": `jobs.ops.add_note()` appends a
`JobEvent(type=NOTE, category=ADMIN_ACTION, note=text)` under the job-row
lock (the same lock `transition()` holds, so `seq` stays gapless) and writes
`audit.record("job.note.added")`. It **never** changes `job.status` or
`version`, and it is allowed in any state. Filtering on
`category=ADMIN_ACTION` matters because `(REQUESTED, NEGOTIATING)` also
writes `type=NOTE` events.

Visibility (founder decision): notes are visible to the job's parties through
`GET /jobs/<id>/notes` (`job.read` + `is_job_party`). Parties see the author
only as "Fikisha Operations" (minimum disclosure). The staff member's
user id and role are returned to staff only. Writing requires `job.intervene`.

The contact reveal (`POST /jobs/<id>/contacts/reveal`, also `job.intervene`)
returns each party's name and phone for a staff member to call or WhatsApp,
which digitises existing practice rather than adding an in-app channel.
Every call writes one `job.contacts.revealed` audit row that names the
parties revealed and **never** includes a phone number. The new Ops monitor
rows (`GET /ops/jobs`) carry no contacts, so the audited reveal is the only
staff path to a phone.

## ADR-2D-35 — `audit.view.scoped` = the Ops remit, an allowlist of entity types — CONFIRMED (Design Phase 6, Increment 8; founder decision 2026-09-23)

`platform_config.role_permissions` granted the Operations Officer
`audit.view.scoped`, but no document defined "scoped". The founder chose the
Ops remit. `fikisha.audit.scopes.OPS_AUDIT_ENTITY_TYPES` covers: `job,
negotiation_entry, high_value_approval, recipient_access_link,
recipient_reported_issue, incident, incident_statement, incident_evidence,
dispute, resolution, escalation, verification_record, vehicle`. A Platform
Admin (`"*"`) sees everything. It is an **allowlist**, so a new entity type
added later stays Platform-Admin-only until someone deliberately adds it.
Commission, platform config, identity, session and membership entries are
excluded. `GET /audit/entries` never returns `source_ip` or `source_device`.

## ADR-2D-36 — The Ops Officer's config permissions are now enforced, config-driven, with no `is_admin` shortcut — CONFIRMED (Design Phase 6, Increment 8)

`job.monitor.view`, `job.intervene`, `audit.view.scoped` and `incident.intake`
were named in the approved `role_permissions` config but enforced nowhere.
They are now `@policy` functions that call
`identity.authz.policies.actor_has_permission` (roles-based, deny by default),
for the same reason `incidents.services._require_review_permission` gives:
an active AdminProfile **with no role** gets nothing. Two
`actor_has_permission` implementations exist (identity's is roles-only;
incidents' also counts `audit_role`). This increment uses the identity one
and records the divergence as an open item rather than silently merging
them.

Endpoints: `GET /ops/jobs` (monitor: status / band / attention / stale_hours
filters, plus the job-reference quick jump. `ref` matches the id suffix, so
both the 6-character UI reference and the recipient page's 8-character
`delivery_reference` resolve), `GET /ops/high-value` +
`POST /jobs/<id>/high-value-decision` (over the existing `decide_high_value()`,
which is unchanged; the serializer makes `rationale` required),
`GET /jobs/<id>/events` (the staff event log), `GET /ops/incidents` +
`GET /ops/disputes` (overview queues), and `GET /audit/entries`. See
`phase-2d-api.md`.

**Open items found, not fixed (recorded for the founder):**
- `GET /jobs` and job detail return contact and recipient phones unmasked to
  any party that can see the job, including an operator who has only opened a
  negotiation thread. What an operator should see before assignment is a
  product decision.
- A high-value REJECT is permanent. There is no correction path.
- The reference formats disagree: the recipient page shows 8 characters, the
  UI shows 6.

---

## Self-caught defects fixed during implementation

Every one of these was found by the implementation's own review or test
suite — none was reported externally — and each is recorded here rather than
folded silently into an ADR, per the "no silent decisions" rule.

- **Step 10 API testing:** `(DRAFT, CANCELLED)` — an already-approved row in
  `ALLOWED_TRANSITIONS` since Increment 1 — had never been exercised
  end-to-end. `apply_fns.cancel()` never computed `value_band`, so cancelling
  directly from `DRAFT` violated `ck_job_band_set_once_published`. Fixed by
  having `cancel()` run the identical band computation `publish()` uses, only
  when the job is still `DRAFT` at cancel time; a domain-level regression test
  was added (not only an API-level one).
- **Step 10 security self-review, pre-existing since Phase 2C:**
  `evidence.services.EvidenceValidationError` subclassed plain `ValueError`,
  which `common.exceptions.problem_detail_exception_handler` does not
  recognise — an upload-validation failure surfaced as an unhandled 500, not
  RFC 9457 `problem+json`. Predates Step 10 (the pre-existing Verification
  upload path had the identical latent gap; Step 10's new upload endpoints
  simply made it newly reachable). Fixed at the shared-infrastructure level —
  `EvidenceValidationError` now subclasses `common.exceptions.DomainError`
  (422) — fixing both the pre-existing path and every new one at once.
- **Step 11 concurrency testing:** `jobs.creation.submit_job()`/
  `cancel_job()` called `select_for_update()` with no enclosing
  `@transaction.atomic` — invisible under every prior test (the implicit
  `pytest.mark.django_db` wrapper), and equally broken over real HTTP (no
  `ATOMIC_REQUESTS` configured). Fixed by switching both to the unlocked
  `get_job()` — the lock was never load-bearing, since `transition()` re-locks
  the row itself immediately after.

### Post-implementation corrective passes (`docs/phase-2/phase-2d-final-verification.md`)

Two further real defects were found and fixed *after* the increment sequence
above, during the dedicated final-verification pass — the same class of gap
as the Step 11 item just above, found independently rather than by
extrapolation:

- **BLOCKER-1 (2026-09-11):** 7 of 9 `incidents.services` functions
  (`report_incident`, `intake_recipient_report`, `attach_evidence`,
  `add_statement`, `start_review`, `start_amicable_window`, `escalate`) wrote
  a domain row and called `audit.record()` with no enclosing transaction —
  identical in shape to the Step 11 item above, in a different app. Fixed by
  adding `@transaction.atomic` to all 7, plus `jobs.recipient.confirm_receipt`
  (a related, lower-severity non-atomicity between the `DELIVERED` transition
  and `RecipientAccessLink.used_at`, folded in as N-6). 32 new regression
  tests, including a live reproduction inside a running Docker container.
- **Tiebreaker defects (2026-09-15):** `jobs.otp.verify_otp()` and
  `negotiation.selectors._entries()` both ordered "the newest row" by
  `created_at`/`id`, which can tie under `auto_now_add`'s clock resolution
  (UUIDv7 is only millisecond-ordered) — measured ~3%/~18% real misorder
  rates. Fixed by adding a real Postgres sequence (`seq`, via Django's
  `db_default`) to `PickupOtpChallenge`, `RecipientOtpChallenge`, and
  `NegotiationEntry`, and switching both ordering call sites to it. Two new
  deterministic tests force the exact tie a probabilistic reproduction could
  previously only hit some of the time.

---

## Deviations summary

| # | Phase 0/1 reference | Deviation | Why it is safe |
| --- | --- | --- | --- |
| ADR-2D-10 | `database-design.md`: `GEOGRAPHY(POINT,4326)` | plain `lat`/`lng` decimals, no PostGIS | mirrors ADR-2B-04 (already the same choice for org locations); distance stays informational, nothing was built expecting geospatial querying |
| ADR-2D-11 | `database-design.md §4.8` / `negotiation-architecture.md §4`: stored, mutable `entry.status` + sweep | `negotiation_entry` fully immutable; status derived at read time | the stronger of two conflicting approved docs (CLAUDE.md §4's own append-only rule); no product behaviour changes |
| ADR-2D-16 | Original schema: `RecipientOtpChallenge.link` non-nullable | made nullable | the recipient OTP is issued before the recipient link exists in the approved increment ordering; a schema relaxation, not a behaviour change |
| ADR-2D-20 | `database-design.md §4.10`: hard `UNIQUE(job_id)` on `Dispute` | partial-unique (`status IN {OPEN, UNDER_REVIEW, AMICABLE_PENDING, ESCALATED}`) | a hard unique would permanently block the already-approved `COMPLETED → DISPUTED` path after any prior dispute; Founder-selected, not silently decided; predicate never uses `now()` |

None changes an approved **product** decision (commission model, trust
thresholds, value bands, cancellation policy, the 14-state Job lifecycle,
proof-of-pickup/delivery responsibility, admin role structure, verification
domains, languages, pilot area). Those remain untouched.

---

## Explicitly NOT implemented (extension points left clean)

A real Trust & Reputation engine (only the interim deterministic rule,
ADR-2D-05) · ratings/reputation (Q8, deferred since Design Phase 2) ·
`DISPUTED → RESUME`/`RESUME_PRIOR` (E-1, still an open Phase-0 item) · any
wired SMS/WhatsApp/M-Pesa/eTIMS provider (ADR-2D-09) · wallets/escrow/fare
custody · payroll, shift scheduling, driver transfers, or any other complex
fleet-management feature · continuous GPS/live-tracking, route optimisation,
AI dispatch · native mobile apps · a second lifecycle/event-sourcing engine ·
a second idempotency store · a second module for commission (ADR-2D-23) or
for the dispute-report boundary (ADR-2D-17).

The clean seams later phases consume: the provider-neutral outbox events
listed above (ADR-2D-09/18), `Resolution.actions`'s stored-but-unexecuted
intent flags (ADR-2D-21) for a future trust/rating phase, `Dispute.
pre_dispute_status` (ADR-2D-07) for a future `RESUME_PRIOR` rule, and the
full API boundary (`docs/phase-2/phase-2d-api.md`) for the still-unbuilt
Jobs frontend (Design Phase 5C's escalated workspace screens).
