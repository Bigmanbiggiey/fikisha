# Design Phase 6 — Jobs Frontend: Architecture & Build Plan

**Status:** APPROVED 2026-09-15 — founder confirmed, including the proposed
defaults for all 6 open questions in §9. Implementation proceeds per §7's
increment sequence.

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

### Increment 2 — Business: create & monitor a Job (P2 Flow Family A, P3 §6)

Business Home (§6.1) · Create Job wizard (§6.2, 8-step) · Review & Submit
(§6.3) · Business Job Detail (§6.4, all 14 states' action table) · Jobs list
segmented Active/Requests/Completed/Cancelled (§6.5) · Business Pickup
Confirmation (§6.6, founder-approved O-P2 addition — one of two always-valid
pickup proofs).

### Increment 3 — Negotiation (shared, P3 §8)

Negotiation Thread screen; wired into both Business (from Job Detail) and
Operator (Increment 4) once both exist. Built here since it's on Business's
own critical path to `CONFIRMED`.

### Increment 4 — Operator: discover, negotiate, assign (P2 Flow Family B, P3 §7, §9)

Operator Home (§7.1) · Work discovery (§7.2) · Job Opportunity (§7.3) ·
Operator Job Detail (§7.4) · My Jobs (§7.5) · Confirmed Job view (§9.1) ·
Assign driver & vehicle (§9.2, server-authoritative eligibility, never a
client-side bypass).

### Increment 5 — Driver: the physical delivery (P2 Flow Family C, P3 §10–§13)

Current Job home (§10.1, 56px action-dominant) · Go to pickup (§10.2) ·
Pickup proof, STANDARD and ELEVATED+ variants (§11.1–§11.3, exact band
matrix) · Custody confirmation (§12.1) · In transit (§13.1) · At destination
(§13.2) · Delivery proof, both band variants (mirrors §11's pattern).

### Increment 6 — Recipient (P2 Flow Family D, P3 §20)

Scoped-link shell (§20.1, minimum-necessary-disclosure per the exact §20.0
field table) · Confirm receipt (§20.2, band-appropriate) · Report a problem
(§20.3).

### Increment 7 — Incidents & Disputes (P3 §17)

Incident entry (§17.1, shared across roles) · Ops Officer incident/dispute
review workspace (§17.2, amicable-first; Platform-Admin-only actions
*hidden*, not disabled, with a route to escalate) · Platform Admin dispute
resolution + the `DISPUTED → RESUME` action shell (§17.3 — reason + fresh
MFA + confirm + audit, **no `RESUME_PRIOR` precondition logic**, per O-P1) ·
Dispute timeline overlay (§17.4).

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
