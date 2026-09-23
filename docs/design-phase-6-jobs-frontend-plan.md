# Design Phase 6 — Jobs Frontend: Architecture & Build Plan

**Status:** APPROVED 2026-09-15 — founder confirmed, including the proposed
defaults for all 6 open questions in §9. Implementation proceeds per §7's
increment sequence. **Progress (2026-09-23): Increments 1–7 DONE; Increment
8 (Operations Officer console) next, pending founder review.**

**Continues the design track:** `design-brief.md` (P0) → `design-phase-1-ia.md`
(P1, IA/nav) → `design-phase-2-user-flows.md` (P2, journeys) →
`design-phase-3-wireframes.md` (P3, screen-by-screen wireframes) →
`design-phase-4-visual-system.md` (P4, tokens/components spec) →
`design-phase-5-brand-palette.md` (P5A) → `design-phase-5-implementation.md`
(P5B, tokens + 13 primitives **built**) → `design-phase-5c-screen-migration.md`
(P5C, 15 existing screens migrated; **Job/workspace screens escalated as
blocked — no backend**) → **this doc (P6, the backend now exists and is
approved — Phase 2D, `docs/phase-2/phase-2d-summary.md`)**.

**Also authoritative:** `docs/phase-2/phase-2d-api.md` (the exact endpoints
this phase calls), `docs/phase-2/phase-2d-decisions.md` (backend ADRs this
must not contradict), `CLAUDE.md` §4 (invariants — 14 Job states, band-
dependent proof, no wallet/escrow, `RESUME_PRIOR` open, rating deferred).

> **This is a plan for founder review, not implementation.** Nothing in this
> doc has been built. On confirmation, implementation proceeds increment by
> increment (mirroring Phase 2D's own review cadence — each increment lands,
> is reviewed, then the next starts); on any change, this doc is revised and
> re-presented.

---

## 1. What already exists (do not rebuild)

- **Design specs** — full wireframes (P3), user flows + the 5 approved
  corrections (P2), IA/navigation (P1), visual system (P4) for every screen
  this phase builds. This plan cites section numbers throughout rather than
  re-deriving anything design-level.
- **Tokens + 13 domain primitives** (P5B, `frontend/src/design/tokens.ts` +
  `frontend/src/components/`): JobStatusChip, JobStatusHeader,
  NextActionCard, JobCard, JobTimeline, VerificationPill, TrustLevel,
  TrustFacts, VehicleCard, IdentityCard, ConnectivityIndicator, Modal,
  BottomSheet — presentational, prop-driven, already tested (81 tests, 27/27
  WCAG AA pairs). Plus the retoned Phase 2A shared primitives (Button,
  Input/Field, Alert, StatusBadge, Spinner, EmptyState/ErrorState/
  PageLoader).
- **15 existing screens**, already migrated onto semantic tokens (P5C):
  auth, home, diagnostics, businesses/business-detail, groups/group-detail,
  operator-profile, operating-locations, vehicles/vehicle-detail,
  verification (queue + record). **Not touched by this phase** except where
  a role's "More" menu needs to link to one (e.g. Operator → Vehicles).
- **The full Jobs/Negotiation/Incidents backend API** (`phase-2d-api.md`) —
  every screen below calls an already-existing, already-tested endpoint. No
  backend change is in scope here.
- **Frontend conventions to reuse, not reinvent:** `src/services/apiClient.ts`
  (bearer-token-in-memory, RFC 9457 `ApiError` parsing, transparent 401
  refresh) — needs one addition, an `Idempotency-Key` header option (§5);
  the per-feature `xApi.ts` object pattern (`src/features/org/orgApi.ts` is
  the model); `RequireAuth`/`useAuth` for route guarding (needs a role-aware
  variant, §4); React Router v6 (`src/app/router.tsx`).

## 2. What does not exist yet (this phase's scope)

Per the Design 5C escalation (§7) and the three source docs' own screen
inventories: **zero** Job, Negotiation, Incident, or Dispute screens exist
in the frontend today, for any role. Nothing under `src/features/jobs/`,
`negotiation/`, `incidents/`, or role-specific workspace shells exists. This
phase builds all of it.

---

## 3. Architecture decisions this phase must make

### 3.1 Routing: role-aware, not role-namespaced

The current router (`src/app/router.tsx`) is a single flat route list with
no role branching — every authenticated user sees the same nav. The IA doc
(P1 §26) specifies **six distinct primary-nav sets** (Business, Operator,
Driver, Group Manager, Operations Officer, Platform Admin) keyed off
`AuthUser.roles`/`is_admin` (already present in `authApi` — no backend
change needed).

**Proposed approach:** keep one route tree (not `/business/*` vs
`/operator/*` namespaces — a person can hold more than one role, e.g. an
operator who is also a group driver), and make the **shell** role-aware:
`AppShell` reads the active role context and renders the matching nav set
(P1 §5–§10); a `RoleTabBar` component (net-new, §6 below) replaces the
current flat `TopBar` links on mobile. Job detail at `/jobs/:jobId` is one
route whose *content* (next-action set, visible sections) varies by the
viewer's relationship to that Job — exactly how the backend already scopes
`job_authz.is_job_party()` — not six separate detail routes. This mirrors
the backend's own "one Job, party-scoped view" model (`phase-2d-decisions.md`
ADR-2D-26) instead of inventing a parallel frontend role-partition.

**Open question for the founder gate (§9, Q1).**

### 3.2 Offline / server-confirmed: graceful degradation, not a sync engine

P3 §23 requires every screen to mark each action `[local-ok]` or `[server]`,
with money/custody/identity moments always `[server]`, and P5B's own
deviation note (§11.5) already scoped `ConnectivityIndicator` to
`navigator.onLine` only, explicitly deferring "richer syncing / sync-issue
states" to "the offline/outbox work in a later phase."

**This phase does not build an offline queue/outbox/IndexedDB sync engine.**
It builds the *UI contract* P3 asks for: `[server]`-marked actions disable
their control and show a clear "you're offline" state when
`navigator.onLine` is false (via the existing `ConnectivityIndicator`), and
`[local-ok]` actions (e.g. typing into the Create Job wizard) keep working
and warn before navigating away with unsaved input — using ordinary React
state / `sessionStorage`, not a durable sync engine. A `SyncIssuesTray`
component is built as a presentational shell only (P3 §23's "surfaced in a
tray, never auto-merged" requirement) with no real queued-mutation replay
behind it yet.

**Open question for the founder gate (§9, Q2).**

### 3.3 Idempotency-Key on the frontend

`phase-2d-api.md` §1 requires `Idempotency-Key` on lifecycle-transition
calls (submit, cancel, assign, every custody confirm, negotiation accept,
dispute resolve). `apiClient.ts` has no such option today. This phase adds
one: a `idempotencyKey?: string` `RequestOptions` field that sets the
header, and each `xApi.ts` transition call generates one (e.g.
`crypto.randomUUID()`) once per user-initiated action attempt (not
per-render) so a retry after a network blip reuses the same key.

### 3.4 What this phase does NOT touch

No backend/API/migration change. No new business rule. No
`RESUME_PRIOR` precondition logic (only the action *shell* — reason + a
disabled/placeholder state, per O-P1, `phase-2d-decisions.md` ADR-2D-07).
No rating/reputation UI beyond nothing at all — Q8 stays deferred, and P2
§83/§20 say don't build ahead of "the later reputation/rating product
phase," so no placeholder button either. No GPS/route/dispatch. No wallet/
escrow/payment UI (statements are read-only, no "pay" control anywhere,
matching `phase-2d-decisions.md` ADR-2D-27's conservative commission-read
scope). No native app.

---

## 4. Role-aware shell & navigation (P1 §5–§10, §26)

New: `src/shell/RoleTabBar.tsx` (mobile bottom nav, role-conditional),
`src/shell/RoleSidebar.tsx` (desktop, for the two desktop-first roles), a
`useActiveRole()` hook resolving which workspace to render when a user
holds multiple roles (e.g. an operator who owns a business account) — P1
doesn't specify a switcher mechanism, **flagged as Q3 below**.

| Role | Primary nav (mobile bottom tabs) | Desktop | IA ref |
| --- | --- | --- | --- |
| Business | Home · Jobs · Messages · More | responsive, not desktop-first | §5 |
| Operator | Home · Work · My Jobs · More | responsive | §6 |
| Driver | Current Job · Jobs · More | mobile-first always (56px targets, never a dashboard) | §7 |
| Group Manager | Home · Jobs · Team · More | responsive | §8 |
| Operations Officer | Operations · Jobs · Verification (+Incidents/Disputes/Businesses/Operators/Vehicles/Search) | **desktop/tablet-first**, sidebar | §9 |
| Platform Admin | Control · Jobs · Verification (+Trust/Incidents/Users/Configuration/Commission/Audit) | **desktop-first**, sidebar | §10 |

---

## 5. New API client modules

Mirroring `src/features/org/orgApi.ts`'s pattern, one `xApi.ts` per backend
app, each call mapped 1:1 to `phase-2d-api.md`:

- `src/features/jobs/jobsApi.ts` — collection/detail/submit/cancel/assign/
  commission + every custody endpoint (arrive-pickup, confirm-pickup ×3,
  fail-at-pickup, start-transit, arrive-destination, confirm-delivery).
- `src/features/jobs/recipientApi.ts` — the three `/r/<token>...` routes
  (no bearer auth — token-in-URL, per `phase-2d-api.md` §2).
- `src/features/negotiation/negotiationApi.ts` — threads collection/detail/
  counter/accept/decline.
- `src/features/incidents/incidentsApi.ts` — incidents + evidence +
  statements + review + amicable + escalate; disputes collection/detail/
  resolve.

Every lifecycle-transition call passes an idempotency key (§3.3). Types
(`Job`, `NegotiationThread`, `NegotiationEntry`, `Incident`, `Dispute`, …)
go in each feature's `types.ts`, mirroring the org feature's convention —
field names taken directly from the backend serializers, not re-guessed.

---

## 6. New shared components (beyond the 13 already built)

Per the wireframes' own component inventory (P3 §29) cross-referenced
against what P5B already delivered — **11 of 13 already exist**; these are
net-new, all presentational/prop-driven like the existing 13, added to
`src/components/`:

| Component | Used by | Notes |
| --- | --- | --- |
| `RoleTabBar` / `RoleSidebar` | shell (§4) | role-conditional nav chrome |
| `NegotiationThread` / `OfferCard` | Business, Operator | offer history + accept/counter/decline |
| `EligibilityRow` | Operator Work/Opportunity, Assign screen | per-candidate eligibility + concrete reason, never a bare "ineligible" |
| `OtpInput` | Driver pickup/delivery proof, Recipient confirm | 6-digit, matches backend OTP shape |
| `PhotoCapture` | Driver attested-fallback, delivery proof, Incident forms | camera/file input, evidence upload |
| `SignaturePad` | Delivery proof (STANDARD signature option) | canvas-based capture |
| `ProofRequirementPanel` / `BandContextLine` | Driver pickup/delivery proof | renders the exact band-dependent matrix (§8 below) — one source, not duplicated per screen |
| `CustodyConfirmation` | Driver | "goods received" confirmation moment |
| `EvidenceViewer` | Ops Officer incident/dispute review | reuses the existing evidence-fetch pattern from `verification` feature |
| `IncidentForm` | Business/Operator/Driver/Recipient (shared, role-varies fields) | 11-category taxonomy from `phase-2d-decisions.md` |
| `RecipientShell` / `RecipientConfirm` | Recipient | no-account, minimal-disclosure chrome |
| `ReasonForActionDialog` / `ConfirmDialog` | Business pickup confirm, Platform Admin action shell, cancel flows | reason-required, audited-action pattern |
| `SyncIssuesTray` | global | presentational shell only, §3.2 |
| `StaleBadge` | Job Detail | `If-Match`-adjacent "this may be out of date, refresh" — **see §9 Q4**, since `If-Match` itself isn't wired server-side yet |
| Skeleton set | every screen | loading placeholders matching each card/list shape |
| `VehicleClassIcon` set | Job/vehicle screens | icon per vehicle class |

---

## 7. Screen inventory & increment sequence

Sequenced by the approved priority order (P2 §85: Core Marketplace → Physical
Delivery → Trust & Safety → Management → Administrative), adapted to ship in
reviewable increments the way Phase 2D's eleven increments did.

### Increment 1 — Frontend infrastructure (no screens) — DONE, 2026-09-15

API client modules (§5) and the `Idempotency-Key` `apiClient.ts` addition
(§3.3): `jobsApi`/`recipientApi`/`negotiationApi`/`incidentsApi` + their
`types.ts`, every field/enum verified directly against the backend
serializers/DTOs rather than re-guessed (this caught and fixed one real
doc error: `phase-2d-api.md` had said the recipient `/r/<token>` routes are
mounted outside `/api/v1/` — they aren't, confirmed against
`config/urls.py`). The workspace-resolution half of the role-aware shell
(§4) — `useWorkspaces()`, built on the codebase's established
`@tanstack/react-query` pattern (not plain `useState`/`useEffect` as
first drafted — corrected after discovering react-query is already the
convention every other feature page uses), resolving Business/Operator/
Group-Manager/Ops-Officer/Platform-Admin workspaces from the existing org
endpoints. 89/89 frontend tests, lint/typecheck/build clean (103.36 kB
gzip).

**Scope refinement from this section's original text:** the 17 new shared
components (§6) are **not** pre-built in isolation here. Building them
against guessed prop shapes before any consuming screen exists risks
rework; they're built just-in-time as each increment's screens need them
instead — still unit-tested, just not batched up front. `RoleTabBar`/
`RoleSidebar` (the presentational half of §4) are deferred the same way,
to Increment 2, since there's nothing to navigate to yet.

### Increment 2 — Business: create & monitor a Job (P2 Flow Family A, P3 §6) — DONE, 2026-09-15

Business Home (§6.1) · Create Job wizard (§6.2, 8-step) · Review & Submit
(§6.3) · Business Job Detail (§6.4, all 14 states' action table) · Jobs list
segmented Active/Requests/Completed/Cancelled (§6.5) · Business Pickup
Confirmation (§6.6, founder-approved O-P2 addition — one of two always-valid
pickup proofs). `RoleTabBar`-equivalent nav (a "Jobs" link) and role-aware
`/home` dispatch (§4) landed here, since Business is the first workspace with
somewhere to go. `jobHelpers.ts` centralizes the 14-state → business-facing
next-action/segment mapping so it isn't re-derived per screen; `money.ts`
handles KES minor-unit formatting/parsing (every `*_kes` field is cents).

**Mandatory live-browser verification (CLAUDE.md: "start the dev server and
use the feature in a browser before reporting complete") caught a real
backend defect**, not a frontend one: a freshly created business never
appeared as a workspace on `/home`. Root cause and fix are recorded as
`ADR‑2B‑11` in `phase-2b-decisions.md` — `GET /businesses` (list) always
returned `my_role: null` because the generic `paginated()` helper never set
the serializer context key the single-object create/detail views did; fixed
by annotating the queryset with a per-row correlated subquery. Verified
end-to-end after the fix: fresh login → `/home` correctly renders
`BusinessHomePage` for an owner. 905/905 backend tests, 100/100 frontend
tests (21 files), lint/typecheck clean on both sides.

**Bug found during this increment's own build, fixed in the same pass (not a
backend issue):** `CreateJobPage.tsx` originally called `navigate()` directly
in the render body once the job was created, instead of inside `useEffect` —
under real user-interaction testing (not static analysis) this produced a
runaway re-render loop that OOM'd a test run. Fixed by moving the navigate
call into `useEffect`; verified no other new screen has the same pattern.

### Increment 3 — Negotiation (shared, P3 §8) — DONE, 2026-09-16

Negotiation Thread screen (`features/negotiation/NegotiationPage.tsx`),
wired from Business Job Detail's "Review offers" (`NEGOTIATING` state).
Shared presentational components `OfferCard`/`NegotiationThread`
(`src/components/`) render the offer/counter history; Operator's own use
of them arrives in Increment 4 (its actions/composer are Business-specific
this increment). Business can counter, accept, or decline; on mutual
acceptance the pinned "Agreed: KSh X" banner + "Open Job" appear, matching
§8.1's exact spec. Composer uses `counter()` uniformly for the business's
outgoing figure (never `propose()`, which requires an existing thread
anyway once a thread exists to view) — "Ask again" vs. "Send counter"
wording distinguishes only whether there's currently something to accept.

**Known simplification:** the wireframe's desktop split-panel (thread list
+ open thread side-by-side) is a single mobile-first flow instead — a
plain list when more than one operator has responded, tap through to the
full-screen thread — consistent with the mobile-first stack; a `lg:`
responsive enhancement can be added later without a data-flow change.

**Three real defects found and fixed during this increment's mandatory
live-browser verification** (none were reachable by the jsdom-based test
suite or caught by static analysis):

1. **CORS gap (all environments, since Increment 1):** the backend never
   allowed the `Idempotency-Key` header for cross-origin requests
   (`django-cors-headers`' own defaults don't include custom headers) — a
   real browser's preflight silently dropped every job-creation/lifecycle
   request before it ever reached Django, surfacing only as a bare
   "Cannot reach Fikisha" network error. Invisible to vitest/jsdom, which
   doesn't enforce real CORS. This had silently blocked *every* Increment 2
   screen's actual submit path in a real browser the whole time — Increment
   2's own live verification happened to stop short of exercising it.
   Fixed in `config/settings/base.py` (`CORS_ALLOW_HEADERS`).
2. **`operator_display_name` + `counterparty_offer` missing from the
   negotiation thread payload** (`ADR-2D-31`) — the wireframe names the
   proposer on every offer card and shows a single "Accept KSh X" action,
   neither of which the existing payload supported for a real (non-test)
   caller.
3. **`_effective_status()`'s blanket-supersede covered `CLOSED` as well as
   `SUPERSEDED`** (`ADR-2D-32`) — a *just-agreed* thread's own re-read (a
   page reload) could never again report `mutual_acceptance.reached: true`,
   so the "Agreed" banner only ever worked in the instant it was created,
   never on revisit. Caught by reloading the negotiation screen after
   confirming, exactly the real user flow the wireframe describes.

Also fixed the same pass: `jobs.guards`' `business_not_verified` /
`business_no_active_location` / `cargo_prohibited` / `required_fields_
incomplete` codes had no `errors:` translation, showing the raw snake_case
code to the user (hit while setting up test data for this increment — the
same pre-existing gap Increment 2 never happened to trigger live).

905 → 907 backend tests (2 new: `ADR-2D-31`'s counterparty-offer-is-
viewer-relative test, `ADR-2D-32`'s reload-after-close regression), 100 →
110 frontend tests (`NegotiationPage`, `NegotiationThread`, plus a
`JobDetailPage` navigation regression), all green; lint/typecheck/build
clean. Live-verified the full happy path end-to-end: create a job → open a
thread as an operator (no Operator UI yet, driven directly) → counter →
accept → operator accepts back → Agreed banner → Open Job → Job Detail
shows `CONFIRMED` at the agreed price.

Stopped here for review, per the plan's per-increment discipline —
Increment 4 (Operator) not started.

### Increment 3 code-review fixes — DONE, 2026-09-17

Three fix commits from the code review of Increment 3, landed before
Increment 4: `GET /groups` never populated `my_role` (the same defect as
`ADR-2B-11`, found on the business list in Increment 2); negotiation
`accept()` replayed a saved response for a reused idempotency key before
checking that the caller was a party to the thread, so an actor could
reuse a key from their own thread on the same job to read another thread's
payload (the party check now runs first); a thread closed by `decline()`
kept its last offer ACTIVE after `ADR-2D-32` (it is now superseded); a
superseded ACCEPT still showed an "Accepted" badge; the Job Detail
timeline lost every earlier checkmark once a job was CANCELLED, FAILED or
DISPUTED (progress is now derived from the last populated timestamp).

### Increment 4 — Operator: discover, negotiate, assign (P2 Flow Family B, P3 §7, §9) — DONE, 2026-09-21

Operator Home (§7.1) · Work discovery (§7.2) · Job Opportunity (§7.3) ·
Operator Job Detail (§7.4) · My Jobs (§7.5) · Confirmed Job view (§9.1) ·
Assign driver & vehicle (§9.2, server-authoritative eligibility, never a
client-side bypass).

**Founder scope decision:** individual operators only. The Group Manager's
driver-pool assignment flow is deferred to a later increment.

**Backend (a gap this increment could not be built without):**
`job.read` deliberately hides `REQUESTED`/`NEGOTIATING` jobs an operator
has not yet touched, so there was no way to discover work. Added
`GET /jobs/opportunities`, `GET /jobs/<id>/opportunity` (`job.discover`,
scoped to the operator's own vehicle classes, never the whole marketplace)
and `GET /jobs/<id>/assignment-candidates` (`job.assign.candidates`). The
eligibility-reason predicates were moved out of `jobs/guards.py` so the
preview and the real `CONFIRMED → ASSIGNED` guard use one source of truth.
See `docs/phase-2/phase-2d-api.md` §2.

Frontend: `OperatorHomePage`, `WorkListPage`, `JobOpportunityPage`,
`AssignDriverVehiclePage`, `MyJobsPage`; new `EligibilityRow` (ineligible
options are shown with their reason, not hidden) and a `useJobViewerRole`
hook, so `JobDetailPage` and `NegotiationPage` branch per job instead of
being forked. "Accept the posted price" is `propose()` then `accept()`,
and the job still needs the business's own ACCEPT to confirm. `TopBar`
shows Work/My Jobs only for a workspace holding an Operator profile; the
full RoleTabBar/RoleSidebar redesign stays deferred.

**Defects found in live-browser verification:** `localizeError()` compared
a namespaced key with i18next's un-namespaced fallback, so every error code
missing from `errors.json` showed its raw machine string; the NEGOTIATING
status line on Job Detail was written from the business's side only.

13 new backend tests (441 existing jobs tests unchanged), 131 frontend
tests. Live-verified: discovery → opportunity → accept → negotiating →
confirmed → assign (ineligible vehicle shown disabled with reasons) →
ASSIGNED.

### Increment 5 — Driver: the physical delivery (P2 Flow Family C, P3 §10–§13) — DONE, 2026-09-22

Current Job home (§10.1, 56px action-dominant) · Go to pickup (§10.2) ·
Pickup proof, STANDARD and ELEVATED+ variants (§11.1–§11.3, exact band
matrix) · Custody confirmation (§12.1) · In transit (§13.1) · At destination
(§13.2) · Delivery proof, both band variants (mirrors §11's pattern).

Frontend only; the custody endpoints already existed from Phase 2D. New
components `OtpInput`, `PhotoCapture` (no client-side WebP compression; a
documented simplification) and `SignaturePad`. New screens
`PickupProofPage` (STANDARD shows the operator-attested fallback; ELEVATED+
shows only the two verified paths and a blocking explainer),
`CustodyConfirmationPage`, `DeliveryProofPage` (STANDARD: one of
OTP/signature/photo; ELEVATED+: OTP **and** photo). The driver's per-status
actions extend `JobDetailPage`'s `OperatorNextActionSection` rather than a
separate screen. "Go to pickup" and "I'm at pickup" are one screen: there
is no geofence, and chain-of-custody.md §5 takes one reading per event.

**Defects fixed in `jobsApi.ts`** (this increment was the first real
caller): arrival geo was sent at the top level instead of under `geo`, so
the server always dropped it; `startTransit` sent a body the view never
reads; attested-pickup and delivery proof only sent JSON, so photo and
signature uploads were impossible (now `FormData`). **Found live:** the
Geolocation API's `timeout` does not cover an unanswered permission
prompt, so an arrival tap could hang forever. `geo.ts` now races it
against a 5s limit.

Live-verified on both bands: the STANDARD attested fallback through to
DELIVERED with a full timeline; on ELEVATED+ no fallback is offered, and
the explainer appears after a failed OTP.

### Increment 6 — Recipient (P2 Flow Family D, P3 §20) — DONE, 2026-09-22

Scoped-link shell (§20.1, minimum-necessary-disclosure per the exact §20.0
field table) · Confirm receipt (§20.2, band-appropriate) · Report a problem
(§20.3).

The first unauthenticated Jobs routes: `/r/:token` and its two
sub-screens sit outside `AppShell`/`RequireAuth`, like `/login`, and
`AuthProvider` skips its `/auth/me` call on `/r/` routes.

**Founder scope decisions made before implementation:**
- The recipient's confirm-receipt OTP is always mandatory. The backend
  requires it, so the wireframe's STANDARD "one of OTP/signature/photo"
  line is out of date. `RecipientView` has no `value_band` (§20.0), so the
  screen doesn't branch on band. It always offers an optional photo or
  signature. If an ELEVATED+ job then fails with `delivery_proof_incomplete`,
  the photo control opens and the name and OTP already entered are kept
  (the `ADR-2D-16` pattern).
- Photo evidence on "report a problem" was built rather than deferred:
  `RecipientReportIssueView` now accepts multipart `photos`, using the
  service's existing `photo_evidence_ids` support.

Live-verified, fully logged out: STANDARD confirm with OTP only; ELEVATED
`delivery_proof_incomplete` retry with a photo; report with photo
(verified in the DB as `INCIDENT_EVIDENCE`, `uploaded_by_kind=RECIPIENT`);
unknown token (404) and expired link (410), each with its own copy. 455
jobs-app backend tests, 166 frontend tests.

### Increment 7 — Incidents & Disputes (P3 §17) — DONE, 2026-09-22

Incident entry (§17.1, shared across roles) · Ops Officer incident/dispute
review workspace (§17.2, amicable-first; Platform-Admin-only actions
*hidden*, not disabled, with a route to escalate) · Platform Admin dispute
resolution + the `DISPUTED → RESUME` action shell (§17.3 — reason + fresh
MFA + confirm + audit, **no `RESUME_PRIOR` precondition logic**, per O-P1) ·
Dispute timeline overlay (§17.4).

**Backend gap closed:** incident detail never included its evidence or
statements, and neither had a GET endpoint, so the Ops Officer's "review
evidence" and "communication log" (§17.2) couldn't be built. Incident
detail now embeds both, and `GET /incidents/evidence/<id>/content` streams
evidence through the existing `incident.read` policy.

**Scope decisions recorded here (not silently made):**
- **Resume is a permanently disabled shell.** `RESUME_PRIOR` has no backend
  at all (a DB CHECK constraint excludes it; `JobEventType.RESUMED` is
  never emitted), and it is still an open Phase-0 decision (O-P1). The
  shell shows the reason field and the wireframe copy, and makes no API
  call.
- **No MFA UI.** Nothing made functional here needs it, and the backend
  has no MFA enforcement to call (`is_step_up_fresh` is an unused stub).
  §17.3's "fresh MFA" therefore isn't met yet. It has to be revisited with
  Increment 9 (suspend/config).
- **Opening a dispute** is an Ops Officer / Platform Admin action from
  Incident Detail, not a self-service control for ordinary roles. The
  backend's ability for a job party to open one is unchanged, just not
  exposed.
- **No cross-job incident/dispute queue.** The backend has no list-all
  endpoint for incidents or disputes; that is Increment 8's triage work.
  Reachability is via Job Detail's "Report an issue" and "View dispute"
  links.

Frontend: `features/incidents/`: `IncidentReportPage`,
`IncidentDetailPage` and `DisputeDetailPage`. Resolve controls are
read-only for non-admins. An Ops Officer can resolve STANDARD band only,
with commission fixed to APPLY. A Platform Admin gets REDUCE/WAIVE plus the
disabled Resume shell.

**Found live:** opening a dispute didn't invalidate the
`['disputes', jobId]` cache, so "View dispute" showed "no dispute" for 30s.
Fixed. Live-verified with three real logins (business owner, Ops Officer,
Platform Admin): report with photo → evidence opens → dispute opened →
above-STANDARD "needs a Platform Administrator" state → REDUCE resolution
(a `CommissionAdjustment` row in the DB, Job → COMPLETED). 136
incidents-app backend tests, 169 frontend tests.

Stopped here for review. Increment 8 (Operations Officer console) is not
started.

### Increment 8 — Operations Officer console (P3 §18)

Operations overview/triage (§18.1) · Job monitoring table (§18.2) ·
High-value review (§18.3, HIGH/VERY_HIGH bands) · Search (§18.4) ·
Audit/activity read (§18.5).

### Increment 9 — Platform Admin console (P3 §19)

Control overview (§19.1) · the Platform-Admin-only action-shell pattern
(§19.2, shared by RESUME/binding-resolution/suspend/config) ·
Configuration, read-mostly with a propose-change flow (§19.3) · Commission &
statements, admin read (§19.4, no wallet/balance/pay control anywhere) ·
Users & organizations (§19.5).

### Increment 10 — Cross-cutting verification pass

Sweep every screen against: the exception-state catalogue (P3 §22 — Loading/
Empty/Offline/Error/Unauthorized/Expired/Already-done/Conflicting-stale/
Missing-proof/Cancelled/Couldn't-complete/Under-dispute/Sync-issue);
offline-vs-server marking (§23); the per-role responsive strategy (§24.1);
WCAG 2.2 AA + target-size audit (§25) — the same discipline P5B's
`contrast.test.ts` already applies to tokens, extended to the composed
screens; a full `npm run lint` / `typecheck` / `vitest` / `vite build` pass
+ a manual multi-width smoke pass (mirroring the backend's Docker smoke
discipline).

**Secondary/lower-priority screens intentionally sequenced last or
deferred — see Q5:** Business Staff/Locations/Statements/Account, Operator
Group/Earnings, Group Manager's Team screen. These are all "More" menu items
behind the primary flow, not on the P1 (Core Marketplace) or P2 (Physical
Delivery) critical path.

---

## 8. Band-dependent proof matrices (exact — do not approximate)

Pinned from `phase-2d-decisions.md` / `phase-2d-plan.md`, restated here
because `ProofRequirementPanel` must render them exactly:

| | STANDARD (≤ KES 50,000) | ELEVATED/HIGH/VERY_HIGH (> KES 50,000) |
| --- | --- | --- |
| **Pickup** | OTP, or in-app business confirmation, or operator-attested fallback (photo + contact name) → caps the Job at STANDARD, marked unverified until a later business confirmation | OTP or in-app business confirmation only — no fallback, transition refused if neither obtainable |
| **Delivery** | one of OTP / signature / photo | OTP **and** photo, both required |

---

## 9. Founder gate — decisions requested

**Please confirm before implementation begins:**

1. **Q1 (§3.1)** — accept the role-aware-single-route-tree approach (one
   `/jobs/:jobId`, shell renders per-role nav) over per-role route
   namespaces. *(Or direct otherwise.)*
2. **Q2 (§3.2)** — accept that this phase builds only the `[server]`/
   `[local-ok]` UI contract and a presentational `SyncIssuesTray`, not a
   real offline queue/sync engine (deferred, per P5B's own prior framing).
3. **Q3 (§4)** — a person holding more than one role (e.g. operator + group
   manager) needs a workspace switcher; P1 doesn't specify one. Propose a
   simple role-switch control in the "More" menu — confirm, or direct
   otherwise.
4. **Q4 (§6, `StaleBadge`)** — `phase-2d-api.md` flagged that `If-Match`
   optimistic concurrency exists at the domain layer but isn't wired to any
   HTTP header yet. Build `StaleBadge` as a presentational-only "may be
   stale, refresh" hint (polling/refetch-based), not real `If-Match`
   enforcement, until that backend gap is closed separately? *(Or treat
   closing the `If-Match` gap as a prerequisite increment — your call.)*
5. **Q5 (§7)** — confirm the increment order (Business → Negotiation →
   Operator → Driver → Recipient → Incidents/Disputes → Ops → Admin → QA),
   and that Business/Operator/Group-Manager secondary screens (Staff,
   Locations, Statements, Team, Earnings) can ship last or in a later
   phase without blocking the primary flow.
6. Confirm no change is wanted to the two non-negotiables already carried
   through every design phase unchanged: `RESUME_PRIOR` preconditions stay
   unimplemented (shell only), and no rating/reputation UI of any kind ships
   in this phase.

On confirmation, implementation proceeds per §7's increment sequence; on any
change, this plan is revised and re-presented.
