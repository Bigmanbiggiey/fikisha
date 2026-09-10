# FIKISHA — Design Phase 5C — Screen Migration & Responsive Workspace

**Status:** PARTIAL — existing screens migrated; the Phase 3 workspace screens are **BLOCKED** (no backend). Founder decision required (§7).
**Design track:** Phase 5C (screen-by-screen visual migration onto the approved system)
**Builds on:** `docs/design-phase-5-implementation.md` (5B token foundation, commits `125f275`…`4aed71d`); Founder-approved Stage & Yard palette.
**Authoritative sources:** `CLAUDE.md` · `docs/team-skills-policy.md` · `docs/design-phase-1-ia.md` · `docs/design-phase-2-user-flows.md` · `docs/design-phase-3-wireframes.md` · `docs/design-phase-4-visual-system.md` · `docs/design-phase-5-brand-palette.md` · `docs/design-phase-5-implementation.md`

> **No product behaviour, API, model, migration, auth, verification, trust,
> custody, negotiation, commission, or notification logic was changed.** No new
> runtime dependency. No IA / navigation change. Not merged to `main`.
> `RESUME_PRIOR` remains OPEN; rating/reputation remains DEFERRED.

---

## 1. What this phase did

Migrated **every screen that exists in the application today** off the legacy
Tailwind palette classes (`slate-*`, `brand-*` literals, `positive`/`negative`
badge aliases, `tone="error"`) and onto the Phase 5B semantic token system and
domain primitives.

**Result: zero legacy palette or alias usages remain anywhere in `frontend/src`.**

### Screens migrated (15)

| Screen | Route | Key changes |
| --- | --- | --- |
| `ErrorBoundary` | (global) | token action button, 44 px target |
| `LoginPage` | `/login` | `text-h1`/`text-body-sm` scale, `fg`/`surface` tokens, `Alert tone="danger"` |
| `HomePage` | `/` | token scale + colours; role chips → `tone="brand"` |
| `DiagnosticsPage` | `/diagnostics` | token colours; health badge gains an icon (status ≠ colour-only) |
| `BusinessesPage` | `/businesses` | `Card interactive` list rows; standing badge → `success`/`danger` **+ icon** |
| `BusinessDetailPage` | `/businesses/:id` | token `<select>`s (44 px, `surface-input`); member/standing/MAIN-location badges meaning-mapped + iconed; **Remove** → `destructive` `compact` |
| `OperatorProfilePage` | `/operator` | token colours; operator-status badge → `success`/`neutral` + icon; embeds `VerificationPanel` |
| `GroupsPage` | `/groups` | `Card interactive`; token `<select>` |
| `GroupDetailPage` | `/groups/:id` | token `<select>`; standing/member badges mapped + iconed; **Remove** → `destructive` `compact` |
| `OperatingLocationsPage` | `/operating-locations` | token `<select>`; token list cards |
| `VehiclesPage` | `/vehicles` | `Card interactive`; token `<select>`s; **vehicle status via the shared `vehicleStatusBadge` helper** (ACTIVE→success+check · UNDER_REPAIR→warning · SUSPENDED→danger · INACTIVE→neutral) |
| `VehicleDetailPage` | `/vehicles/:id` | token dl/rows; `vehicleStatusBadge`; embeds `VerificationPanel` |
| `VerificationPanel` (shared) | (in operator/vehicle) | raw state badge → **`VerificationPill`** (7 states → 5 groups); token evidence-kind `<select>` + file input; local `state→tone` map deleted |
| `VerificationQueuePage` | `/verification` | `Card interactive`; state badge → `VerificationPill … hideDomain` |
| `VerificationRecordPage` | `/verification/:id` | `VerificationPill` for `state` and (when different) `effective_state` as "Now: …"; token history list |

### Components touched (in support)

- **`VerificationPill`** — added optional `hideDomain` (for rows that already
  label the domain).
- **`vehicleStatus.ts`** (new) — `vehicleStatusBadge(status)` returns
  `{tone, icon, label}`; extracted from `VehicleCard` so the mapping is reusable
  and `VehicleCard.tsx` stays component-only (react-refresh).
- **`components/index.ts`** — export `vehicleStatusBadge` / `VehicleStatus`.

---

## 2. Migration method (Phase 3 → Phase 4 → Phase 5B → screen)

Per §4 of the brief: no new design layer. For each legacy class the **meaning**
was determined from the surrounding markup before mapping (§13):

| Legacy | Meaning | Semantic token |
| --- | --- | --- |
| `text-slate-900` / `-800` | primary text / title | `text-fg` |
| `text-slate-700` / `-600` | supporting text | `text-fg-secondary` |
| `text-slate-500` | caption / meta / hint | `text-fg-muted` |
| `border-slate-300` | input / selectable boundary | `border-line-strong` |
| `border-slate-200` / `-100`, `divide-slate-100` | divider / card edge | `border-line` / `divide-line` |
| `bg-slate-50` / `-100` | recessed panel | `bg-surface-sunken` |
| `text-brand-700` (link) | link / secondary-action text | `text-action-secondary-text` |
| `hover:border-brand-300` (list card) | interactive affordance | `Card interactive` |
| `text-xl/lg/sm/xs font-semibold/medium` | ad-hoc sizes | `text-h1/h2/h3/body-sm/label/caption` |
| `tone="positive"` / `"negative"` | status | mapped **by meaning** to `success`/`danger`/`neutral`/`warning` + an icon |
| `tone="error"` | error alert | `tone="danger"` |

**`green` / `red` / `amber` were NOT blind-mapped** — the only such classes were
already in the shared components (migrated in 5B). Feature screens used only
`slate-*` neutrals + a little `brand-*`.

---

## 3. Domain primitives now in use on real screens

- **`VerificationPill`** — VerificationPanel, VerificationQueuePage,
  VerificationRecordPage. Renders the 5 user-facing groups over the 7
  authoritative states; "Needs attention" = `INFO_REQUESTED` + `REJECTED` +
  effective `EXPIRED`. Always names the domain (or is explicitly `hideDomain`);
  never a score, never a blanket "verified operator" badge.
- **`vehicleStatusBadge`** — VehiclesPage, VehicleDetailPage, VehicleCard.
- **`Card interactive`** — all Link-wrapped list rows (Businesses, Groups,
  Vehicles, Verification queue).
- **`StatusBadge` `tone="brand"` / `icon`** — role and standing chips.
- **`Button` `variant="destructive" size="compact"`** — Remove actions.
- **`Alert tone="danger"`** — all error alerts.

`JobStatusChip`, `JobStatusHeader`, `NextActionCard`, `JobCard`, `JobTimeline`,
`TrustLevel`, `TrustFacts`, `IdentityCard`, `Modal`, `BottomSheet` are built and
tested (5B) but **not yet used on a screen** — see §7.

---

## 4. Responsive

- The migrated screens are **org/vehicle/verification management** screens, not
  the Job/coordination workspaces. They keep a focused single-column layout with
  the existing `sm:` form-row / `sm:grid-cols-2` responsive behaviour, which is
  correct for these screens (§9 of the brief forbids adding density just because
  space exists).
- The Phase 4 responsive amendment is intact from 5B: **no hard 480 px cap**;
  `useBreakpoint()` / `atLeast()` available; `Modal` → bottom sheet `< md`.
- The **Operator workspace two-pane layout** and the **Driver focused workflow**
  layout (Phase 4 §21.2–21.3) are **not implemented** because those screens do
  not exist (§7).
- No horizontal body scroll introduced (verified in the build; wide content
  is not present on these screens).

---

## 5. Accessibility

Preserved on every migrated screen:

- Semantic HTML (`<h1>` per screen, `<ul>`/`<li>`, `<dl>`, `<form>`, `<label>`).
- Visible focus — the global `:focus-visible` ring from 5B applies; `Card
  interactive` adds `focus-within` outline for Link-wrapped rows.
- 44 px targets — `<select>`s now carry `min-h-target`; buttons already ≥ 44 px;
  `compact` (36 px) used only for non-primary Remove actions in dense list rows.
- Status is colour + icon + text everywhere (added icons to standing / health /
  membership / vehicle-status / MAIN-location badges).
- Errors — `Alert tone="danger"` is `role="alert"`; `Field` wires
  `aria-describedby` (5B).
- The 27-pair contrast suite (5B) still passes — no new colour pairs introduced.
- Reduced motion, 200 % scaling — unchanged from 5B (rem scale, global media
  rule).

**Known a11y gap (pre-existing, not introduced here):** `VerificationRecordPage`
reviewer panel has 2 hardcoded English strings ("Review", "No review action
available in this state.") — missing i18n keys from before 5C. Listed in §6.

---

## 6. EN / SW

- All migrated copy is `t()`-driven except the two pre-existing hardcoded strings
  above and one pre-existing inline bilingual string in `VehicleDetailPage`
  (`"This vehicle is suspended… / Gari hili limezimwa…"`).
- Chips and buttons size to content and wrap (`flex-wrap` added to the badge
  rows in the detail headers) rather than truncate — SW labels for
  `standing` / `status` / `role` are backend enum values (`GOOD`, `ACTIVE`,
  `OWNER`, …), not translated UI strings, so length is bounded.
- Recommend adding the 2 missing i18n keys + moving the inline bilingual string
  into the locale files in a follow-up (small, isolated).

---

## 7. Blocking finding — the Phase 3 workspace screens do not exist (escalate)

**The brief's Groups 3–8 (Business Home/Jobs/Create-Job/Review/Job-Detail/
Messages/Statements; all Operator Work/Job-Opportunity/Job-Detail/Earnings; all
Driver screens; all Operations; all Platform Admin; the Recipient scoped view)
cannot be migrated because they are not implemented, and cannot be built in a
visual phase because the backend they require does not exist.**

- The current app has **14 screens**: auth, home, diagnostics, and the
  identity/organisation surfaces (businesses, groups, operator profile,
  operating locations, vehicles, verification). These are the **Phase 2A–2C**
  surfaces.
- **Jobs, negotiation, custody, dispatch, incidents, disputes, recipient links,
  and the operations/admin consoles have no backend** — Phase 2C's STOP line
  (see `CLAUDE.md`) explicitly defers all of that to **Phase 2D** (Trust &
  Reputation, then Jobs), which the Founder has not authorised.
- Building those screens now would mean **inventing product UI against
  non-existent APIs / models / lifecycle** — which §21, §22, §28, and §35 of the
  5C brief prohibit ("Do not introduce new product behaviour unless … the
  implementation already has the necessary backend support").

**What is ready for them:** the Phase 5B domain primitives (`JobStatusChip`,
`JobStatusHeader`, `NextActionCard`, `JobCard`, `JobTimeline`, `TrustLevel`,
`TrustFacts`, `IdentityCard`, `Modal`, `BottomSheet`) are implemented, tested,
and token-driven — they can compose those screens the moment the backend exists.

**Founder decision needed:** the Job/workspace screen implementation belongs to
the phase that builds the Jobs backend (Phase 2D+ / a later frontend phase), not
to 5C. 5C as scoped is **complete for the screens that exist**.

---

## 8. Verification results

| Check | Result |
| --- | --- |
| `npm run typecheck` | pass (0 errors) |
| `npm run lint` | pass (0 errors, 0 warnings) |
| `npm test` | pass — 13 files, **81 tests** (unchanged; the 27-pair contrast suite still green) |
| `npm run build` | pass — JS **102.08 kB gzip** (< 200 kB budget; +0.35 kB vs 5B), CSS **5.10 kB gzip** |
| Legacy palette / alias scan of `frontend/src` | **NONE** — 0 occurrences |
| New dependencies | none |
| Backend / API / migrations | untouched |
| IA / navigation | unchanged |
| Live render | login screen renders with Stage & Yard tokens; authed screens need the backend running (not available in this session) — build success confirms every semantic utility on the migrated screens resolves |

---

## 9. Known deviations & follow-ups

1. **Groups 3–8 not done** — blocked (§7); requires backend. Escalated.
2. **2 hardcoded English strings** + **1 inline bilingual string** predate 5C
   (VerificationRecordPage reviewer panel, VehicleDetailPage suspended notice) —
   move to i18n in a small follow-up.
3. **Multi-width on-device visual QA of authed screens** not performed — no
   backend to log in against in this session. Build + typecheck + lint + tests +
   the 5B contrast suite stand in; a device sweep should run once a backend
   environment is available.
4. **`rounded-lg` cosmetic shift (8→12 px)** from the 5B radius override is now
   fully resolved on the migrated screens (they use `rounded-md`).
5. **Bottom-nav / role-specific navigation** still not built (brief §6/§17 — no
   nav redesign; and the roles that need distinct bottom nav are the
   Driver/Operator/Business *workspaces* from §7).

## 10. Open decisions preserved

- **`RESUME_PRIOR` preconditions** — OPEN. No resume UI exists or was added.
- **Rating / reputation** — DEFERRED. No stars / scores / ranking /
  recommendation. `TrustLevel` remains an earned-standing ladder.

## 11. Changelog

| Date | Change |
| --- | --- |
| 2026-09-10 | Phase 5C — migrated all 15 existing screens off legacy palette classes onto Stage & Yard semantic tokens + domain primitives (`VerificationPill`, `vehicleStatusBadge`, `Card interactive`). Zero legacy classes remain. typecheck/lint/81 tests/build green. Phase 3 workspace screens (Jobs/Driver/Operations/Admin/Recipient) blocked — no backend; escalated to Founder (§7). |
