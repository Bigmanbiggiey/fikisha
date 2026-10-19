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

## ADR-2D-37 — Messages inbox: a read-only composition app with read markers, no new messages — CONFIRMED (Design Phase 7 sub-increment 10g; founder scope 2026-09-23)

**Decision.** A new module, `fikisha.inbox`, lists the conversations that
**already exist** on a person's jobs, newest first, with unread markers:

- offer threads, via a new public read `negotiation.services.inbox_threads`
  (same sealed-thread scoping as `list_threads`);
- "Updates from Fikisha" notes, via `jobs.ops.notes_for` on the jobs from
  `jobs.job_authz.jobs_visible_to` (the `job.read` party rule the notes
  endpoint already uses);
- incidents and disputes, via a new public read
  `incidents.services.inbox_items_for_job` (the incidents module's own party
  rule; an operator that has only negotiated is not an incident party).

It never reads another module's models directly (module boundary rule), and
it **creates no messages**: negotiation stays the authoritative record of
offers, WhatsApp stays a notification channel, and there is no new chat.

**The only state it owns** is `InboxReadMarker(user, conversation_key,
last_read_at)` (table `inbox_read_marker`, unique per user and key, new
migration `inbox.0001`). A conversation is unread when its latest activity
was written by someone else after the person's marker. Keys are
`offer:<thread>`, `notes:<job>` (one conversation per job, not per note),
`incident:<id>`, `dispute:<id>`. Markers are mutable and not audited: they
record what a person has looked at, not a sensitive change. Marking only ever
touches the caller's own row, and a key the caller can't see never matches
one of their items, so nothing is revealed either way.

**Endpoints.** `GET /messages` (`inbox.read`) and `POST /messages/read`
(`inbox.mark_read`); see `phase-2d-api.md` §4b.

**Choices recorded here:**
- **Staff get an empty inbox**, including a staff member who is also a
  business party. They already work from the Ops queues, and their admin
  visibility of every job must not become an inbox of every job.
- **Items carry structured fields, not sentences** (kind, counterparty,
  amount, whose entry, status, preview), so the frontend writes each row in
  the reader's language. The offer's stored note is not shown, since it can
  be system text ("Posted price at publication.").
- **The newest 200 jobs** per person are scanned per request (`MAX_JOBS`).
  Enough for the pilot; older jobs' conversations drop off the inbox, their
  screens are unaffected. The composition is done in memory, per job.
- **Paging is forward-only** with an opaque cursor (the last item's time and
  key); `prev_cursor` is always null. `unread_count` in the response covers
  the whole inbox, for the navigation badge.
- **What marks a conversation read**: opening it from the inbox. Reaching the
  same screen another way does not mark it (known gap; a later increment can
  mark on the screens themselves).

**Why it's safe.** Read-only apart from the caller's own markers; every
source applies its module's existing party check server-side; IDOR/BOLA
tests cover a stranger business, a sibling operator's sealed thread, a
negotiating operator versus incidents, staff, and a business VIEWER.

**Code-review corrections (2026-09-29).** (1) Notes are gated per job on
`job_authz.is_job_party`: `jobs_visible_to` is wider than `job.read` (it lists
a business VIEWER's jobs and a non-managing group member's), and the inbox
must not show notes the notes endpoint refuses. (2) An offer entry posted by
staff (the negotiation `ADMIN` side) carries `from_fikisha` and is worded
"Fikisha offered …", never credited to the counterparty. (3) The frontend's
messages queries are keyed by user id, since sign-out does not clear the
query cache.

**Request cost: batched (founder choice 2026-09-29).** The first build cost
about 9–13 queries per job (63–78 on the seeded accounts, thousands near
`MAX_JOBS`). The founder chose batching over scanning fewer jobs, so what
people see is unchanged:
- each source is one read across all the jobs:
  `negotiation.services.inbox_threads_for_jobs` (threads, then each thread's
  latest entry in one `DISTINCT ON` query), `jobs.ops.notes_for_jobs` and
  `incidents.services.inbox_items_for_jobs`. They replace the per-job
  functions of the first build.
- `jobs.job_authz.recent_jobs_visible_to` loads the jobs with the agreement,
  the assignment and its driver, and the negotiation threads that the party
  checks read. `job_authz.operator_is_party` now walks
  `job.negotiation_threads.all()`, which uses those prefetched threads (the
  same rows as the query it replaces).
- the party checks still run per job and per thread, unchanged. The
  membership lookups under them (`business.authz.active_membership`,
  `groups.authz.active_membership`, `operators.authz.owns_profile`) are
  memoized per user and resource id, but only inside `common.authz_memo`,
  which only this read-only request opens. Everywhere else, writes included,
  they query every time as before.

Result: a fixed 12 queries per request on the seeded accounts. A test adds
three jobs and asserts that the count stays the same for both the business
and the operator.

---

## ADR-2D-38 — Platform Admin console: directory, interventions, config and commission ledger behind a step-up gate that refuses until admin MFA exists — CONFIRMED (Design Phase 6 Increment 9; founder approval 2026-10-13, D-1 deferred)

**Decision.** A new module, `fikisha.admin_console`, serves the Platform
Admin console (P3 §19) under `/admin/*`. The founder approved the Increment 9
scope (`docs/design-phase-6-increment-9-scope.md`) with its recommendations
for D-2 to D-6, and deferred D-1 (admin MFA). It reads and changes other
modules only through new public surfaces in each module (module boundary
rule):
- `business.admin_directory`, `operators.admin_directory` and
  `groups.admin_directory`: queryset, row, detail, contact, and `set_state`;
- `identity.services.admin_accounts`: `status_of` and `set_state`;
- `platform_config.services`: `preview_change` and `versions`;
- `jobs.admin_ledger`: the commission ledger read;
- `jobs.ops.in_flight_jobs_for`: an account's jobs that are still running.

**The step-up gate.** Phase 1 (`authentication-authorization.md` §1.2)
requires a fresh TOTP step-up for config change and for
suspension/offboarding. Admin TOTP doesn't exist yet, and the founder
deferred it (D-1). So `identity.authz.step_up.require_step_up` checks
`Actor.is_step_up_fresh`, which is always `False` today, and refuses with 403
`step_up_required`. Interventions and config changes are built and tested
behind it (tests use a stepped-up actor), but no request can run them until
9a lands. Nothing else needs changing when it does. This keeps the approved
security architecture intact: deferring MFA defers the actions, it doesn't
remove the check.

**Permissions** (config-driven, `admin_console/policies.py`):
- `admin.directory.read`, `admin.directory.contact_reveal`,
  `admin.account.intervene`;
- `admin.config.read`, `admin.config.change`;
- `admin.commission.read`.

Only the Platform Admin (`"*"`) holds them (D-6). Granting one to the
Operations Officer later is a config change; the step-up still applies.

**Directory (§19.5, D-6).** Businesses, operators and groups, newest first,
filtered by name and by standing or status. Phones are masked
(`+2547•••••678`). The full number is a separate POST that writes an audit row
without the number, the same as Increment 8's contact reveal. The detail page
shows members, the account's in-flight jobs, and the intervention history of
the account and of its person.

**Interventions (§19.2, FR-ADM-4, D-2).** `AdminIntervention` (table
`admin_intervention`, append-only at all three layers, migrations
`admin_console.0001`/`0002`) is the account-level half of Phase 1's
`admin_intervention` table: account type and id, action, admin, reason,
duration (recorded only), and the state before and after. Rules:
- **Suspend:** user ACTIVE; operator PENDING, ACTIVE or RESTRICTED; business
  or group GOOD or RESTRICTED.
- **Reinstate:** restores the state the latest suspension recorded, falling
  back to ACTIVE or GOOD.
- **Offboard:** users and operators only, and terminal. Businesses and groups
  have no offboarded state.
- **Input:** the reason is at least 10 characters; a duration is 1 to 365
  days and only on a suspension.
- **Never:** RESTRICTED is never set; an admin can't act on their own user
  account.
- **Each one writes:** the state change, the intervention row and an audit
  entry (`admin.account.<action>`, with the reason) in one transaction.

**Deviation from Phase 1's table:**
- `REINSTATE` is added to the action enum; Phase 1 listed only
  SUSPEND/RESTRICT/OFFBOARD and had no way to record undoing one.
- Job-level interventions are not copied in, because `job_event` and
  `high_value_approval` already record them.

Why it's safe: it only adds history; nothing is lost.

**Suspension blocks new work (D-2), enforcement gaps closed.** The scope
doc said the existing guards already enforced this. Checking the code showed
they didn't fully:
- a suspended business could still create and publish jobs;
- an offboarded operator was not refused at negotiation;
- a suspended group could still negotiate (only assignment refused it).

Now:
- `jobs.creation.create_draft` raises `business_suspended`;
- the `BusinessVerifiedWithLocation` guard on DRAFT → REQUESTED fails with
  `business_suspended`;
- `OperatorEligibleForJob` refuses SUSPENDED, RESTRICTED and OFFBOARDED
  operators and a suspended group (negotiation now passes `group_id` on the
  NEGOTIATING transition too);
- work discovery returns nothing to a suspended, restricted or offboarded
  operator.

A suspended or offboarded user can't use a session; that was already
enforced in `identity.services.auth`. In-flight jobs carry on. Instead of
D-2's "Ops note", the directory lists them: notes are visible to the job's
parties (ADR-2D-34), so a note would tell a business that its operator was
suspended.

**Configuration (§19.3, D-3).** `GET /admin/config` returns the live config,
its version, the version history and the editable keys.
`POST /admin/config/preview` returns the leaf-by-leaf diff and the commission
on four sample prices before and after; it changes nothing.
`POST /admin/config` applies through the existing `apply_change`, which
versions, validates, audits and emits. It needs a reason of at least 10
characters and a step-up.

Editable keys: `commission.rate`, `commission.min_fee_kes`,
`commission.cap_kes` and the seven `timeouts.*` values. Anything else is
refused with `config_key_not_editable`, including value bands, the high-value
threshold, `role_permissions`, vehicle classes and verification requirements.
Values must be numbers; everything but the rate must be a whole number of at
least 0. A change identical to the live values is refused.

**Commission (§19.4, D-4).** `GET /admin/commission` lists every
`commission_record` with its adjustments and the effective amount, filtered by
time or payee, plus `totals` over the whole filtered ledger and
`statements_available: false`. It is read-only, with no manual adjustments.
Weekly statements, settlement and eTIMS are a separate increment.

**Left out (D-5).** Trust & Reputation, the resume-request queue, System
health and cross-entity search.

**Why it's safe.**
- Every endpoint is Platform-Admin-only server-side. IDOR/BOLA tests refuse
  an Ops Officer, an ordinary user and an anonymous caller on every endpoint.
- The two powerful writes can't run until step-up exists.
- Every write is audited in its own transaction, and the intervention record
  is append-only at three layers.
- The config allowlist keeps privilege and invariant settings out of reach.
- Nothing moves money.

## ADR-2D-39 — Admin TOTP MFA and step-up — CONFIRMED (Increment 9a; founder decision 2026-10-14, D-1 (a))

**Decision.** Admin MFA is built to Phase 1 `authentication-authorization.md`
§1.2 and `security-architecture.md` item 17.

**Sign-in**
- Phone OTP first, then **forced TOTP enrolment** on an admin's first
  sign-in, and a TOTP code (or a one-time backup code) on every later one.
- **An admin's roles and admin flag apply only on a session that passed
  MFA** (`AuthSession.mfa_verified_at`). Until then `authz.actors` builds an
  ordinary-user actor, so every admin policy refuses.
- Internal callers with no session (services, tests) are unaffected.
- `/me` reports `mfa {required, enrolled, verified, step_up_fresh}`, and the
  app shows the MFA screen instead of anything else until `verified`.

**Step-up**
- A fresh code (`POST /auth/step-up`) sets `AuthSession.step_up_at`.
  `Actor.is_step_up_fresh` is true for `STEP_UP_TTL_SECONDS` (default 300).
  Passing MFA at sign-in also counts as a fresh step-up.
- **Guarded actions:**
  - account suspend / reinstate / offboard and config apply (in their
    services, as ADR-2D-38 wired them);
  - **dispute resolution** and **high-value decisions** (at their API views,
    so existing service tests stay valid);
  - **staff viewing HIGH-PII evidence**, recorded in the
    `evidence_access_log` reason as "(step-up)". A person viewing their own
    document needs no step-up (Phase 1 permission matrix).
- **In the app:** `StepUpProvider` registers one handler with the API
  client. A request refused with `step_up_required` opens the code dialog
  and, once the code is accepted, retries once. Concurrent refusals share one
  dialog.

**Storage and hardening**
- The secret is Fernet-encrypted (`cryptography`), keyed by
  `TOTP_ENCRYPTION_KEY`. Dev and test derive the key from `SECRET_KEY`;
  **production refuses to start without its own key.**
- Ten one-time backup codes are stored as password hashes, shown once, and
  burn on use.
- TOTP accepts one 30-second step either side of now, and the last accepted
  step is remembered, so **a code can't be replayed**.
- **Five wrong codes lock MFA for that user for 15 minutes**
  (`MFA_MAX_ATTEMPTS`, `MFA_LOCK_SECONDS`; counter in the cache).
- Enrolment, verification and step-up are audited; failures are logged (an
  audit row would roll back with the failed transaction).

**New dependencies:** `pyotp` 2.9.0 (RFC 6238), `cryptography` ~43.0.3
(Fernet), and `qrcode-generator` 1.4.4 on the frontend. The QR code is
rendered locally as an image, so the secret never leaves the app.

**Not in this increment:**
- Resetting another admin's lost authenticator. Today it's a manual DB
  operation; a Platform Admin "reset MFA" action is a follow-up.
- Shorter step-up windows per action.

**Why it's safe.** It only narrows access: nothing an admin could do before
is possible without MFA now. Every MFA path is tested, including the
replay, lockout, expiry, roles-wait and non-admin cases, and the
stale-versus-fresh step-up on each guarded action.

## ADR-2D-40 — Follow-ups batch 1: phones until assignment, reversible high-value rejection, 6-character references — CONFIRMED (founder decisions 2026-10-14, items 7–9)

**1. Contact phones are hidden until the job is assigned (closes ADR-2D-36).**
- **Who sees the numbers** (`job_authz.may_see_contact_phones`):
  - staff;
  - any member of the job's business;
  - once the job is **assigned**, the confirmed operator or group manager
    and the assigned driver.
- **Who doesn't:** an operator who has only negotiated, a confirmed operator
  before assignment, and anyone browsing open work. They get blank
  `pickup_location.contact_phone`, `destination_location.contact_phone` and
  `recipient_phone`, plus `contacts_hidden: true`. Contact names stay
  visible.
- **Where:** `creation.job_detail(job, viewer=...)` applies it on job detail,
  the job list and work opportunities. The business's own create response
  has no viewer, so nothing is hidden.

**2. A Platform Admin can reverse a high-value rejection, with a reason.**
- A new append-only `HighValueReversal` (one per decision; model guard,
  queryset guard and DB trigger, migrations `jobs.0009`/`0010`) points at
  the original `HighValueApproval`, which never changes.
- `high_value.effective_decision(job)` reads a reversed rejection as
  APPROVED by a Platform Admin. The `HighValueApproved` guard and the
  assignment-candidates check both use it, so a reversed job can be
  assigned.
- `POST /jobs/<id>/high-value-decision/reverse {reason}`:
  - Platform Admin only;
  - reason of at least 10 characters;
  - fresh MFA step-up;
  - audited as `job.highvalue.rejection_reversed`;
  - emits `HighValueDecision` with `reversal: true`.
- For staff, job detail now carries `high_value_decision`. The staff header
  shows "High-value review rejected", and a Platform Admin gets "Reverse the
  rejection" through the shared action dialog.

**3. One 6-character reference everywhere.** The recipient page's
`delivery_reference` now uses `jobs.ops.job_reference` (the last 6
characters, as the app shows) instead of 8 hex characters.

**Why it's safe.**
- (1) only removes data from some viewers.
- (2) adds an audited, step-up-guarded Platform Admin action and changes no
  existing record.
- (3) is display only.
- Tests: `jobs/tests/test_followups_batch.py` (9) and
  `StaffJobContext.test.tsx` (2).

## ADR-2D-41 — Group Manager assigns from the driver pool — CONFIRMED (founder decision 2026-10-14, item 19; scope approved as built 2026-10-15)

Closes the deferral recorded on 2026-09-21 (Increment 4: "Group Manager
driver-pool assign deferred"). The assign step itself already handled
group jobs (`assignment._resolve_authority`, `guards.driver_assignment_allowed`,
`guards.vehicle_eligible`). What was missing was the candidates list and the
screen, so a Group Manager had nothing to pick from.

**The pool** (`GET /jobs/<id>/assignment-candidates` on a group job):
- **Group Manager (OWNER/MANAGER) or staff:** every **active** member of the
  confirmed group, each with `group_role`, and the **group's** vehicles.
  A member's own vehicle is not offered, because `vehicle_eligible` would
  refuse it.
- **`DRIVER_ACCEPTS` group, a member who doesn't manage it:** only themselves,
  matching the self-assign path in `_resolve_authority`.
- **`MANAGER_ASSIGNS` group, a member who doesn't manage it, or anyone
  outside the group:** refused (`NotAuthorisedToAssign`), no pool returned.
- **Suspended group:** the pool is shown, but every driver is ineligible with
  the suspension reason, matching `driver_assignment_allowed`.
- The response now has `supports_group_assignment: true` and
  `assignment_mode`. Per-row reasons come from the same guard predicates as
  the assignment, so the preview and the assign step agree.

**Frontend** (`AssignDriverVehiclePage`): each driver row shows the group
role next to the trust level. A group with no active members gets "This
group has no active members to assign yet", and a group with no vehicles
gets "This group has no vehicles registered yet". The old "not available
yet" message is gone. SW strings are added; they go on the Swahili review
list (decision 20).

**Not changed:** value-band gating still uses the chosen driver's and
vehicle's own eligibility (§4 invariant: a group is not a substitute for the
driver's trust level). No new model, migration, endpoint or permission. The
cross-module reads of `fikisha.groups.models` follow the existing jobs
pattern (`guards.py`, `assignment.py`, `job_authz.py`).

**Why it's safe.** It only adds a read-only list to an endpoint that already
existed, under the same authorisation as the assign step. The assign step,
which enforces everything, is unchanged.
- Tests: `jobs/tests/test_assignment_groups.py` (+5: manager pool and assign
  over HTTP, member refused under `MANAGER_ASSIGNS`, member sees only
  themselves under `DRIVER_ACCEPTS`, outsider refused, suspended group) and
  `AssignDriverVehiclePage.test.tsx` (+3).

## ADR-2D-42 — Weekly commission statements and manual settlement (backend) — CONFIRMED (Commission & Statements S-1; plan approved 2026-10-15)

Implements S-1 of `docs/commission-statements-plan.md`, with founder answers
D-1 to D-8 (all as recommended).

**Module.** A new `fikisha.statements` app. It reads commission only through
new `jobs.commission` functions (`billable_commission`,
`unbilled_adjustments`, `commission_for_job`), which return plain rows. It
never imports job models. Commission itself stays in `jobs` (ADR-2D-23).

**Tables** (append-only at model, queryset and Postgres-trigger level;
migrations `statements.0001`/`0002`):
- `commission_statement`: payee (OPERATOR or GROUP + id), Kenya-date
  period Mon–Sun, gross / adjustments / net due, `reference` (`ST-` + 6
  characters, the paybill account number, D-3). Unique per payee and
  period. DB checks: gross ≥ 0, adjustments ≤ 0, net = gross + adjustments.
- `statement_line`: COMMISSION (one record) or ADJUSTMENT (one adjustment).
  **One-to-one on the record and on the adjustment**, so nothing can be
  billed twice. That uniqueness is what "billed" means. The job reference
  and agreed price are frozen on the line.
- `statement_settlement`: PAYMENT (positive) or REVERSAL (the negative of
  the payment it names, one per payment). Paid / part-paid / unpaid,
  outstanding and overdue are derived on read, never stored.

**Billing rule (D-2).** A record is billed in the first run, as of the end
of that week (Monday 00:00 EAT), where its job is `COMPLETED` (so not
`DISPUTED`) and its post-completion dispute window has closed.
`guards.post_completion_window_hours` is now shared by the dispute guard
and the run, so there is one source of truth. Adjustments are billed once
their record is billed and they existed by the end of the week. An
adjustment to an already-billed record is a credit line on a later
statement, so net due can be negative and a payee owes nothing that week.
An adjustment whose record is never billed (a job that ended `FAILED`
after a dispute) is never billed either.

**The run.** It runs from Celery beat every Monday 06:00 EAT for last
week, from `POST /admin/statements/run` (Platform Admin), or from
`manage.py statements_run`. It is serialised by a Postgres advisory lock
and is idempotent:
- a re-run bills nothing already billed;
- a payee who already has that week's statement is skipped, and anything
  newly ready for them rolls to the next week.

Only finished weeks starting on a Monday are accepted. Each statement is
audited as `statement.generated`, with source `SCHEDULER` or `ADMIN_UI`, and
emits `StatementGenerated` with identifiers only. No sender is wired (D-6).

**Payments (D-4, D-5).**
- Who: Platform Admin only (`statements.settle`), with a fresh step-up.
- Recording a payment: the statement row is locked first. Recording more
  than is still owed is refused (409 `settlement_exceeds_due`). Reusing an
  M-Pesa reference that is still in effect is refused (409
  `duplicate_payment_ref`). References are stored upper-case.
- Reversing a payment: needs a reason of at least 10 characters. A payment
  can be reversed only once, and a reversal can't be reversed (409
  `settlement_not_reversible`). Once reversed, its reference can be used
  again.
- Both are audited (`statement.payment_recorded` / `.payment_reversed`)
  and emit an event.

**Who sees what (plan §3.5).**
- A solo operator sees their own statements.
- A group's OWNER/MANAGER sees the group's.
- A group DRIVER member and a business see none (FR-O-8, D-7).
- Staff with `statements.read.all` see all: the Platform Admin through
  `"*"`, and the Operations Officer, newly granted read only (D-4).
- `GET /jobs/<id>/earnings` gives the payee their per-job commission. It
  answers 404 to anyone else, so a job's existence doesn't leak. For the
  payee's own rows, this replaces ADR-2D-27's Platform-Admin-only read.
- Statement detail answers 403 to a non-payee.

**Overdue (D-8).** A statement that isn't paid after `statements.overdue_days`
(default 14) is marked overdue in the API. There is no effect on work.

**Reconciliation** (`commission-ledger.md` §7). A nightly task logs
CRITICAL for any statement whose totals, lines or payments disagree.

**Deviations from `database-design.md` §4.11, documented:**
- No stored status columns on records or statements. Status is derived, so
  every table stays truly append-only. The original design updated
  `DUE → INVOICED → SETTLED` on append-only rows, which contradicts itself.
- No `etims_invoice` table and no C2B webhook (decision 5).
- No `payee_kind`/`payee_id` on `commission_record`; the payee comes from
  its agreement.
- **Why it's safe:** the behaviour is the same, the immutability is
  stronger, and nothing about when or how commission is calculated changes.

**Config.**
- New `statements.overdue_days` (14) and `statements.paybill_number`
  (null, D-3).
- `statements.read.all` is added to the Operations Officer defaults.
- The live config is seeded from defaults only once. A fresh database
  gets all three; an existing database reads the two settings from their
  code fallbacks, but **its Ops Officers lack `statements.read.all` until
  `role_permissions` is updated**. Only the local dev database is affected,
  since there is no production yet.

**Also changed.** `GET /admin/commission` now returns
`statements_available: true`. The admin screen's "not produced yet" notice
is updated in S-3.

**Tests:** `fikisha/statements/tests/` (24), covering:
- billing: closed vs open window, disputed held, waiver netting, a later
  credit, solo vs group payees, idempotent re-runs, the skipped payee,
  period validation, the weekly task as SCHEDULER, reconciliation;
- payments: part/full payment, over-payment, duplicate reference,
  reversal rules, step-up and Platform Admin only, overdue, append-only on
  all three tables at ORM and DB level;
- the API: each payee lists only their own, detail IDOR, earnings IDOR,
  Ops read-only, the admin run, payment and reversal over HTTP with a
  stale vs fresh step-up.

### ADR-2D-42 addendum — S-2 payee screens and the "seen" marker (2026-10-15)

**Backend addition.** D-6 asks for an unread marker on the Statements list
and a Home "New statement" card, which S-1 did not provide. S-2 adds:
- `statement_seen` (migration `statements.0003`): one row per person and
  statement, written the first time the **payee** opens it, through
  `POST /statements/<id>/seen`. Staff opening a statement records nothing.
- `GET /statements` now returns `seen` on each row and `unseen_count`.
- The marker records what someone looked at, not a change to the ledger.
  It is therefore mutable-table style and not audited, like
  `inbox_read_marker` (ADR-2D-37).
- Test: `test_new_statements_are_unseen_until_the_payee_opens_them`.

**Screens** (`frontend/src/features/statements`):
- **Statements** (`/statements`): in the operator and Group Manager
  navigation (P3 §7.5). The list shows the unseen dot and the
  paid / part-paid / overdue badge.
- **Statement detail** (`/statements/<id>`):
  - "Commission statement — not a tax invoice" (D-1);
  - the summary, the jobs and any credits;
  - payments, with reversals struck through;
  - "How to pay": the paybill once set, otherwise "details to follow"
    with the account reference (D-3);
  - a printable layout: the navigation hides, the wordmark shows (P3
    §6.5).
- **Home** "New statement" card on the operator Home.
- **Job Detail**: a completed job's "Earnings for this job" card, showing
  agreed price − commission = net and linking the statement (P3 §7.4).
  The payee's server answer decides; a group's driver gets 404 and no
  card.
- **Fixed on the way:** a completed job's operator action card said "will
  be marked complete automatically" and "coming in a later update". It now
  says "Nothing needed from you right now."

**Why it's safe.** It only adds reads, plus one per-person seen marker on a
statement the person is the payee of. The ledger tables are unchanged.

### ADR-2D-42 addendum — S-3 staff screens (2026-10-15)

Frontend only; no backend change.
- **Where:** `/ops/statements` and `/ops/statements/<id>`, behind
  `RequireStaff`, so Operations Officers get their read access (D-4).
  "Statements" is in the staff navigation, which the Platform Admin
  shares.
- **List:**
  - filters by week (the last 12 finished weeks, Kenya time) and payee
    kind;
  - invoiced / paid / still-owed totals for the filter (pilot-strategy
    §4.7);
  - a Platform Admin also gets **Run a week** (finished weeks only; the
    server is idempotent).
- **Detail:** the payee's breakdown (shared parts), with every payment and
  its note. A Platform Admin gets:
  - **Record a payment**: amount (refused above what's still owed),
    M-Pesa/bank reference, date (not in the future), method, then a
    confirm step that restates it;
  - **Reverse**: through the shared admin action dialog, reason at least
    10 characters.
  - Both trigger the existing step-up prompt (`StepUpProvider`).
  - Operations Officers see no action controls. Server-side policy is the
    enforcement either way.
- **Control:** last week's invoiced / paid / still owed.
- **Commission:** the "not produced yet" notice is replaced by a link to
  Statements.
- New error messages: `invalid_statement_period`, `invalid_settlement`,
  `settlement_exceeds_due`, `duplicate_payment_ref`,
  `settlement_not_reversible`.

**Why it's safe.** These are screens over the S-1 endpoints, whose
authorization, step-up and limits are unchanged and already tested.

## ADR-2D-43 — PR #5 review follow-ups and the last "coming later" placeholders — CONFIRMED (founder approval 2026-10-16)

The four non-blocking follow-ups from the PR #5 re-review (2026-10-13),
plus the Job Detail placeholders still saying "coming in a later update".

1. **Per-user cache keys.** The businesses, groups and vehicles lists were
   cached as `['businesses']`, `['groups']`, `['vehicles']` in the
   navigation (`useWorkspaces`, `useNavRoles`) and their pages. Sign-out
   doesn't clear the cache, so a second person on the same tab could
   briefly get the first person's navigation. Each is now keyed by user id,
   like `['operator', 'me', …]` since 10c. Invalidation by prefix still
   refreshes them. UX only; the server authorises every action.
2. **Current job reads past page 1.**
   - `GET /jobs` gains two optional filters: `status=A,B` and
     `assigned=me`, meaning jobs whose assigned driver is the caller's own
     operator profile. Both only narrow `jobs_visible_to`. An unknown
     status or any other `assigned` value is 400.
   - The driver's Current job asks for exactly their active jobs, instead
     of filtering the first page of everything.
3. **Messages filters cover the whole inbox.**
   - `GET /messages` gains `kind=OFFER,FIKISHA_UPDATE,INCIDENT,DISPUTE`,
     applied before paging. `unread_count` still covers everything. An
     unknown kind is 400.
   - The filter chips now ask the server, and keep the last result on
     screen while the next loads.
4. **"Written by you" on incidents is recorded, not guessed.**
   - The inbox treated an incident as the reporter's own when it was
     "updated within 2 s of creation", so a quick staff review read as
     untouched. `Incident.last_changed_by` (migration `incidents.0003`) is
     now set on create (the reporter; null for a recipient-link report) and
     on review, facilitation, escalation and resolution (the staff member).
     The inbox compares it to the viewer.
   - The migration fills existing rows with the old rule, so nothing
     changes for them.
   - Test: a staff review within 2 s of the report is now unread for the
     reporter.
5. **Placeholders.** On a disputed job with no dispute the viewer can link
   to, both the business and the operator action cards said "coming in a
   later update". They now say "Fikisha is reviewing this job. You'll be
   told when there's an update", or show loading while the dispute record
   loads. The `jobs.detail.comingSoon` string is gone; `disputeUnderReview`
   is new (EN + SW, added to the Swahili review list).

**Why it's safe.** The new API filters only narrow existing visibility. The
new incident field is a recorded fact used only for an unread marker, and
the authorization paths are untouched. Tests:
- `jobs/tests/test_job_list_filters.py` (2);
- `inbox/tests/test_inbox.py` (+2: kind filter before paging, staff review
  unread);
- `CurrentJobPage.test.tsx`, `MessagesPage.test.tsx` and
  `JobDetailPage.test.tsx` updated.

## ADR-2D-44 — Edit-conflict protection: `If-Match` wired at the HTTP layer — CONFIRMED (founder approval 2026-10-16)

Closes the gap `phase-2d-api.md` recorded in Step 10. The domain check
(`TransitionContext.if_match_version` → `StaleJob` 412, ADR-2D-02) has
existed since Increment 1, but no view read the header. It also settles
Design Phase 6 Q4, where `StaleBadge` was presentational only until this
gap closed.

**Backend.**
- `GET /jobs/<id>` returns `ETag: "<version>"`. The version is already in
  the body.
- `fikisha.common.if_match.IfMatchMiddleware` notes an `If-Match` header on
  any unsafe request whose URL names a `job_id`.
  `JobLifecycleService.transition()`, the single writer of job status,
  takes it for that job only, once. This covers every job action (submit,
  cancel, assign, custody steps, staff actions, opening a dispute) without
  changing a dozen service signatures.
  - **Only that job:** a transition on any other job is unaffected.
  - **Only once:** an action that makes two transitions on the same job
    doesn't trip over its own first write.
  - An explicit `if_match_version` from a caller still wins.
- `"7"`, `W/"7"` and `7` are accepted, and `*` means any version. Anything
  else is 400 `invalid_if_match`.
- `if-match` is added to `CORS_ALLOW_HEADERS`. Without it, browsers would
  block every request carrying it: the same trap as `Idempotency-Key` in
  Increment 3.

**Frontend.**
- `features/jobs/jobVersions.ts` remembers the last version this tab saw
  for each job: from job detail, from every job action's response, and from
  opening a dispute. `jobsApi` actions and dispute opening send it as
  `If-Match`.
- A `412 stale_job` triggers the query client to refresh every job and
  dispute view, and the action's error message says "Someone else changed
  this job while you had it open. It has been refreshed: check it and try
  again. Nothing was changed."
- Versions are forgotten on sign-out.
- **Fixed on the way:** the business "Continue request" action never
  showed its error at all. It now does.

**Deviation from `api-architecture.md`, documented:** the architecture says
job mutations *require* `If-Match`. This build enforces it when sent, but
does not yet reject a request without it.
- **Why:** some flows don't hold a job version, such as negotiation
  acceptance (thread URLs), the recipient's link page (token URLs) and
  scheduled sweeps.
- **Why it's safe:** every screen that shows a job and acts on it now sends
  the header, so the conflicts this protects against are caught. Requests
  without it behave exactly as before.
- **Making it mandatory later:** one check in
  `take_expected_version`/`transition()` (428 when absent on a job URL),
  once every client sends it.

**Tests:**
- `jobs/tests/test_if_match.py` (9): ETag; a stale header is refused and
  changes nothing; current, weak, bare, `*` and missing all go through;
  malformed is 400; CORS allows it.
- `jobVersions.test.ts` (3): version sent and then advanced, none for an
  unknown job, refresh on `stale_job`.
- `apiClient.test.ts` (+1): the header.
- **Live check:** the business opened a draft, it was submitted elsewhere,
  and the business's click sent `If-Match: "0"`, got 412, showed the
  message and refreshed to Requested.

## ADR-2D-45 — Business and group verification — CONFIRMED (founder approval 2026-10-19, D-1 / D-6)

From the founder's assessment (`docs/assessment-2026-10-19-plan.md`,
finding F-1): `DRAFT → REQUESTED` has always required a VERIFIED business
(`BusinessVerifiedWithLocation`), but nothing set the flag, so no real
business could send a job. Groups had the same unused flag.

**Backend.**
- `verification` gains two subjects, `BUSINESS` and `GROUP`
  (`subject_business` / `subject_group`), with domains `BUSINESS` /
  `GROUP` (plus `DOCUMENT`) and two document kinds
  (`BUSINESS_REGISTRATION_CERT`, `KRA_PIN_CERT`). Migration
  `verification/0002` widens the exactly-one-subject check and adds the
  per-subject unique constraints.
- **Documents are optional** for those two domains: the details record may
  be submitted with none (`EVIDENCE_OPTIONAL_DOMAINS`).
- **Registering is submitting.** `business.create_business` and
  `groups.create_group` submit the details record in the same transaction,
  as the creator, so a reviewer can never approve their own organisation
  (`reviewer_is_submitter`).
- **A reviewer's decision sets the flag.** Approving the details record
  sets `verification_status = VERIFIED`; rejecting it sets `UNVERIFIED`.
  The verification module calls `business.services.set_verification_status`
  / `groups.services.set_verification_status`; only the owning module
  writes its flag, audited (`business.verification_status.changed` /
  `group.verification_status.changed`), in the decision's transaction.
- Approving a business with **no active location** is refused
  (`422 business_has_no_location`), the "≥ 1 confirmed location" of
  `verification-architecture.md` §7.
- Subject owner: the business **OWNER**; a group **OWNER or MANAGER**.
  Dispatchers, viewers and drivers neither read nor submit.
- Config: two mandatory rules in `verification_requirements`. A live config
  that predates them takes the shipped default rules for any subject type
  it does not name, until an admin applies one that does.

**Frontend.** After registering, a pop-up says the profile was submitted for
verification. Business Home, the create-job page and the business page show
where verification stands; an unverified business sees why on the create-job
page instead of the form. The business page (owner) and group page
(owner/manager) carry the verification panel, with documents optional.

**Deviation from `verification-architecture.md` §7, documented:** §7
describes "a single flag set by an admin, no per-domain records". This
build keeps the single flag as the thing the job guard checks, but sets it
through a verification record.
- **Why:** the founder asked for the business's submitted data, documents
  and decision history in the verification queue, next to operators (D-1).
- **Why it's safe:** the job guard, the flag's two values and the absence
  of business trust tiers are unchanged; the record only adds the history
  and the reviewer rules every other subject already has.

**Not done here:** existing businesses keep their current flag and have no
record until the owner presses "Submit for verification". Documents can be
added to a record already awaiting review only after a reviewer asks for
more information (evidence stays frozen during review).

**Tests:** `verification/tests/test_organisation_verification.py` (9):
registration submits; the owner sees it as mandatory; approval sets the
flag and is audited; no-location approval refused; reject after approval
unverifies; documents frozen during review; a stranger can neither read nor
submit (IDOR); the owner cannot review their own business; group create →
approve. Frontend: the pop-up, and the unverified create-job state.

## ADR-2D-46 — Operator approval and the pending lock-out — CONFIRMED (founder approval 2026-10-19, D-2 / D-3)

From the founder's assessment (finding F-2): operators start `PENDING` and
nothing ever moved them to `ACTIVE`, while `PENDING` already counted as
operational, so a brand-new operator saw Work.

**Backend.**
- `POST /admin/operators/<id>/approve {note?}` →
  `admin_console.services.approve_operator`: `PENDING → ACTIVE`, one
  append-only `admin_intervention` row (new action `APPROVE`, migration
  `admin_console/0003`) and an `admin.account.approve` audit entry, in one
  transaction with the row locked.
- **Who:** the verification reviewers (`verification.decide`: Operations
  Officer and Platform Admin), since they read the operator's records. No
  step-up: like a verification decision, it is routine review work.
- A reviewer cannot approve their own operator profile. Only a `PENDING`
  operator can be approved (409 otherwise). `APPROVE` cannot be sent
  through `/admin/interventions`.
- **Never automatic.** Approval does not require or follow from records
  reaching `VERIFIED`; the reviewer decides (verification records facts).
  Job eligibility still applies its own verification and trust checks.
- **Lock-out (D-3):** work discovery returns nothing to a `PENDING`
  operator; `OperatorEligibleForJob` refuses their offers
  (`operator_not_approved`); `DriverAssignmentAllowed` refuses a `PENDING`
  group member as the driver, so a group cannot hand work to someone
  Fikisha has not approved.

**Frontend.** A `PENDING` operator, while working as Operator, Driver or
Group Manager, sees Home, Operator, Vehicles and Operating locations only.
Home is a checklist (profile, each mandatory verification and its state, a
vehicle, Fikisha's review). Work, jobs, messages, groups and statements
redirect Home (`RequireApprovedOperator`). The same person working as a
Business keeps their business screens. The Approve button is on the
applicant page of the verification queue (ADR-2D-47).

**Tests:** `admin_console/tests/test_operator_approval.py` (8): approve
with intervention row and audit; only `PENDING`; non-reviewer 403; no
self-approval; no back door via interventions; no work while pending
(then visible once approved); offers refused; assignment refused. Frontend:
the pending tab bars (`RoleNav.test`), the route guard (3).

## ADR-2D-47 — The verification queue by applicant — CONFIRMED (founder approval 2026-10-19, D-6)

From the founder's assessment (finding F-7): the queue was a flat list of
records ("OPERATOR · IDENTITY"), so a reviewer could not see one applicant's
submissions together, and businesses were not in it.

**Backend (read-only).** `fikisha.verification.applicants` and two
endpoints, both behind the existing `verification.queue` policy (reviewers
and queue viewers only; the applicant themselves gets 403):
- `GET /verification/applicants?kind=OPERATOR|BUSINESS|GROUP`: one row per
  applicant with an open record (`SUBMITTED`, `IN_REVIEW`,
  `INFO_REQUESTED`) on themselves or on what they own, plus every operator
  still awaiting approval. Oldest waiting first. Rows carry status, open
  count and, for operators, mandatory checks verified out of how many.
  Pilot-sized, so not cursor-paginated; the response has the one-page shape.
- `GET /verification/applicants/<kind>/<id>`: the applicant's details and
  every record with its evidence and decision history, grouped: the
  operator's own records, each vehicle they own, each operating location
  they created; a business's record and its locations; a group's record and
  its vehicles.
- Nothing about deciding changed: actions still go through the per-record
  endpoints (append-only decisions, `reviewer_is_submitter`), and evidence
  bytes are still fetched one document at a time, authorised and logged.
  Phones are not included (the admin directory's audited reveal stays the
  only way to see them).

**Frontend.** `/verification` has tabs Operators · Businesses · Groups and
lists applicants. `/verification/applicants/<kind>/<id>` shows the
applicant, their required checks, every record as a review card (documents,
actions, history; `RecordReview`, shared with the single-record page), and
for a pending operator the Approve action (ADR-2D-46), with a warning when
not every required check is verified yet. The single-record page's
hard-coded English is now translated.

**Tests:** `verification/tests/test_applicants.py` (7): one row per
operator counting their vehicle's record; business and group tabs; a pending
operator with nothing submitted still listed; reviewers only; records
grouped under operator and vehicle; business locations; unknown → 404.
Frontend `ApplicantQueue.test.tsx` (2): tabs and rows; the grouped
applicant page and Approve.

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
