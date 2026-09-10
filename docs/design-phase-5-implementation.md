# FIKISHA — Design Phase 5B — Production Design Tokens & Visual Foundation

**Status:** COMPLETE — AWAITING FOUNDER REVIEW
**Design track:** Phase 5B (first Phase 5 implementation phase — token foundation + primitives)
**Approved palette:** Option A "Stage & Yard" (`docs/design-phase-5-brand-palette.md`, Founder-approved 2026-09-10)
**Authoritative sources:** `CLAUDE.md` · `docs/team-skills-policy.md` · `docs/design-brief.md` ·
`docs/design-phase-1-ia.md` · `docs/design-phase-2-user-flows.md` ·
`docs/design-phase-3-wireframes.md` · `docs/design-phase-4-visual-system.md` ·
`docs/design-phase-5-brand-palette.md`

> **Scope of this phase:** the *visual foundation* only — production design tokens,
> the shared visual primitives, accessibility + contrast validation, and the
> responsive foundation. **No screen-by-screen migration.** No product behaviour,
> API, model, migration, auth, verification, trust, custody, negotiation,
> commission, or notification logic was touched. No new runtime dependency. Not
> merged to `main`.

---

## 1. Approved palette — "Stage & Yard"

Implemented verbatim from Phase 5A (`brand.600 = #0C7A6C`), with the mandatory
Phase 5A accessibility adjustments applied, plus **two further token-level
adjustments surfaced by automated contrast validation** (both neutral-derived —
**not** a brand change):

| Layer | Value (implemented) |
| --- | --- |
| **Brand teal** (`brand.50…900`) | `#ECFBF7 · #CDF3EA · #9CE6D5 · #5FD0BC · #26B49F · #0F9585 · #0C7A6C · #0A6459 · #0B5049 · #0A3F3A` |
| **Kajiado clay** (`accent.50…800`) | `#FBF3EC · #F3E0CC · #EACBA6 · #DDA475 · #CB8A56 · #BC6C3A · #9E561F · #7F4418 · #5F330F` (200/400/800 interpolated to complete the scale) |
| **Warm stone** (`stone.0…900`) | `#FFFFFF · #F7F5F1 · #EEEBE4 · #E0DBD1 · #C9C3B6 · #A69F90 · #7A7365 · #59534A · #3E3931 · #29251F · #1A1712` — **replaces** Tailwind's built-in `stone` |
| **Text** | primary `#1A1712` · secondary `#59534A` · **muted `#6B6458`** (adj. — see below) · disabled `#A69F90` · inverse `#FFFFFF` · link `#0A6459` |
| **Semantic status** (`.fg` / `.solid` / `.bg` / `.border`) | success `#177A33` (Phase-5A adj.) · warning `#8A4A10` deep amber (Phase-5A adj.) · danger fg `#B02017` / solid `#C22B22` · info fg `#245285` / solid `#2A5D93` · neutral = `stone.600` |
| **Surfaces** | page `stone.50` · card / raised / input / nav `#FFFFFF` · nav-console `stone.50` · sunken `stone.100` · brand-tint `brand.50` · overlay `rgba(26,23,18,.55)` |
| **Borders** | subtle `stone.100` · default `stone.200` · **strong `#948C7D`** (adj.) · focus `brand.600` |

### Adjustments beyond the Founder-approved two

Surfaced by `src/design/contrast.test.ts`, both are **neutral-token** refinements
to meet WCAG — not changes to the brand or accent hues:

| Token | Was | Now | Reason |
| --- | --- | --- | --- |
| `text.muted` | `stone.500 #7A7365` | `#6B6458` | `#7A7365` computes to **4.32:1** on `surface.page` — just under AA for normal text. Nudged one step darker → **5.37:1**. |
| `border.strong` (input / selectable-row boundary) | `stone.300 #C9C3B6` | `#948C7D` (stone-350 level) | `#C9C3B6` on white is **1.76:1** — fails WCAG 1.4.11 (3:1 for a boundary that identifies a component). `#948C7D` → **3.33:1** on white, **3.06:1** on the page. Dividers/cards keep `border.default` (they are not the sole state indicator). |

These are flagged for Founder awareness; they do not alter the "Stage & Yard"
character.

---

## 2. Token architecture (two-tier, as approved)

```
PRIMITIVES            SEMANTIC                         COMPONENT / UTILITY
src/design/tokens.ts  src/design/tokens.ts             per-component + tailwind
  primitive.brand.*  →  semantic.action.primary     →  bg-action-primary
  primitive.stone.*  →  semantic.surface.page        →  bg-surface-page
  primitive.green.*  →  semantic.status.success.*    →  bg-status-success-solid …
```

- **Source of truth:** `frontend/src/design/tokens.ts` — typed `primitive` and
  `semantic` objects + the non-colour token families (`typography`, `space`,
  `radius`, `border`, `elevation`, `motion`, `breakpoint`, `target`, `zIndex`,
  `a11y`) + the domain **visual mappings** (`JOB_STATE_VISUAL` for all 14 states,
  `VERIFICATION_GROUP_OF` / `VERIFICATION_GROUP_VISUAL` for the 7 states → 5
  groups, `CONNECTIVITY_VISUAL`).
- **Tailwind theme:** `frontend/tailwind.config.ts` imports from `tokens.ts` and
  exposes **semantic utility classes** — `bg-surface-*`, `text-fg` / `text-fg-*`,
  `border-line` / `border-line-*`, `bg-action-*`, `text-accent-token-*`,
  `bg-status-*` / `text-status-*` (each status has `-fg` / `-bg` / `-border` /
  `-solid`), plus `rounded-{sm,md,lg}`, `shadow-{e1,e2,e3}`, `min-h-target` /
  `min-h-target-driver`, the `sm/md/lg/xl/2xl` screens, `font-{sans,numeric}`,
  the `display/h1/h2/h3/body/body-sm/label/caption/numeric-lg` font sizes, and
  `duration-{fast,base,slow}` / `ease-{standard,exit}` / `z-{sticky…toast}`.
- **CSS custom properties:** `frontend/src/styles/index.css` mirrors the
  key semantic tokens as `--fk-*` variables (for the handful of plain-CSS needs),
  sets `body` to `bg-surface-page text-fg font-sans`, adds a global
  `:focus-visible` ring, a `.fk-numeric` tabular-figures helper, and a global
  `prefers-reduced-motion` rule.
- **Components consume semantic tokens**, never raw hex. Raw `brand-*` / `accent-*`
  / `stone-*` steps remain available for the rare case that needs a specific step.
- **Mode-ready:** semantic tokens are defined for the light theme; a future dark
  theme re-declares only the semantic block. No dark values authored.

### Non-colour tokens

| Family | Values |
| --- | --- |
| Typography | system stack (`font-sans` / `font-numeric` with `tnum`); scale display 28 · h1 22 · h2 18 · h3 16 · body 16 · body-sm 14 · label 14/600 · caption 12 · numeric-lg 24/700 |
| Spacing | 4 px base — `space.0…16` (0/4/8/12/16/20/24/32/40/48/64) |
| Radius | `sm 4` · `md 8` (cards/buttons/inputs/chips base) · `lg 12` (sheets/dialogs) · `full` |
| Border | hairline / control 1 px · emphasis 2 px |
| Elevation | `e1` sticky edge · `e2` dropdowns/toasts · `e3` dialogs/sheets — **borders in flow, shadows only for floating surfaces** |
| Motion | fast 120 ms · base 200 ms · slow 280 ms · `standard` / `exit` easings; all suppressed under `prefers-reduced-motion` |
| Breakpoints | sm 360 · md 600 · lg 900 · xl 1200 · 2xl 1600 |
| Targets | min 44 px · driver 56 px · compact 36 px (dense tables only) |
| z-index | base/sticky/nav/dropdown/overlay/modal/toast |

---

## 3. Foundational components (Phase 4 §30 inventory)

All under `frontend/src/components/` (barrel: `components/index.ts`). Presentational,
prop-driven, domain-agnostic — no API coupling. Existing call sites keep working
(back-compatible signatures; `ghost` button variant and `positive/negative`
badge tones retained as aliases).

| Component | Status | Notes |
| --- | --- | --- |
| **App shell** (`shell/AppShell`) | retoned | token colours; adds a skip-to-content link; IA/nav unchanged |
| **Navigation** (`shell/TopBar`, `shell/LanguageSwitcher`) | retoned | token colours; adds the connectivity indicator; links unchanged (§17) |
| **Button** | reworked | `primary / secondary / tertiary / ghost(alias) / destructive / success`; sizes `default 44 / driver 56 / compact 36`; loading = `aria-busy` + spinner; `type="button"` default |
| **Input / Field** | reworked | 44 px min, 16 px text, `border.strong` (WCAG 1.4.11), 2 px focus ring; `Field` wires `aria-describedby` + `aria-required` and renders "Required" as text |
| **Alert / banner** | reworked | info / success / warning / danger (+`error` alias); icon + text; `role="alert"` for danger, `role="status"` otherwise |
| **StatusBadge** | reworked | `soft / solid / outline`; tones incl. `brand`; optional `icon`; legacy `positive/negative` → `success/danger` |
| **Spinner** | reworked | decorative by default (`aria-hidden`); `label` for an announced status |
| **EmptyState / ErrorState / PageLoader** | retoned | token colours; ErrorState uses the `Retry` pattern |
| **JobStatusChip** | new | all 14 authoritative states → approved label + icon + tone + chip style (`JOB_STATE_VISUAL`); `CANCELLED` neutral-outline ≠ `COMPLETED` success-solid; `DISPUTED` deep-amber solid |
| **JobStatusHeader** | new | state chip + plain-language `role="status"` line + optional `as of HH:MM` |
| **NextActionCard** | new | one primary action or an explicit "nothing needed"; `driver` → 56 px dominant |
| **JobCard** | new | route / cargo / meta / price (tabular) / next-action hint / reference; whole-card target when `onClick` given (keyboard-operable) |
| **JobTimeline** | new | `<ol>` with `aria-current="step"`; nodes ✓ done / ● current / ○ upcoming / dashed pending-sync; end-caps **cancelled** ≠ **failed** ≠ **disputed** overlay (prior steps kept); operator-attested marker |
| **VerificationPill** | new | domain · group (7 states → 5 groups; "Needs attention" = INFO_REQUESTED + REJECTED + effective EXPIRED); always names the domain — never a blanket "Verified operator" badge; never a score |
| **TrustLevel / TrustFacts** | new | 3-pip clay ladder + full accessible name ("Level 2 of 3 — Established — cleared for deliveries up to KSh 250,000"); **not** stars, **no** `slider`/`radiogroup` semantics; facts are verification pills; absence is neutral |
| **VehicleCard / IdentityCard** | new | class + plate + status + verification marker; `IdentityCard minimal` = recipient view (name + vehicle + one "identity verified" line only) |
| **ConnectivityIndicator** | new | `online / syncing / offline / sync_issue`; `role="status"` polite; icon + word (never colour-only); count for sync-issue |
| **Modal / BottomSheet** | new | dependency-free focus trap + scrim + Escape (respects `dismissible`) + focus restore; `Modal variant="auto"` = bottom sheet < md, centred dialog ≥ md; `BottomSheet` = sheet at every width |
| **Icon** (`design/Icon`) | new | one outline style, 24 px grid, `currentColor`; ~28 glyphs incl. the status shapes (✓ ● ○ ! ▲ ✕ ⏸ ↻ ⚑) and vehicle/step icons; meaningful icons take a `title`, decorative ones are `aria-hidden` |

Domain components (JobCard, JobTimeline, VehicleCard, IdentityCard, JobStatusHeader,
NextActionCard) are **presentational shells** — they take plain formatted props.
Wiring them to real API data on real screens is **Phase 5C**.

---

## 4. Responsive foundation (Phase 4 §21.2–21.3, §25 — carried forward, unchanged)

- Breakpoints in the Tailwind theme: `sm 360 · md 600 · lg 900 · xl 1200 · 2xl 1600`.
- `src/design/useBreakpoint.ts` (`useBreakpoint()`, `atLeast()`) for **contextual
  adaptation** — e.g. Operator single-column → workspace layout — **not**
  proportional scaling.
- **No hard 480 px Operator/Driver cap.** The Phase 4 amendment stands:
  - **Driver** stays focused / action-dominant at every width (the 56 px
    `Button size="driver"` + `NextActionCard driver` establish the dominant-action
    treatment); never a desktop dashboard.
  - **Operator** may expand into a workspace layout on larger screens where it
    aids coordination; the primitives are layout-agnostic and compose into either
    a single column or a two-pane/rail arrangement.
- Modal → BottomSheet on `< md`, centred dialog on `≥ md`.
- App content column stays readable-width; wide content scrolls in its own
  container (no horizontal body scroll). The existing feature screens keep their
  Phase 2A layout until 5C.

---

## 5. Accessibility implementation

| Requirement | Implementation |
| --- | --- |
| WCAG 2.2 AA floor | contrast-validated (§6); components ship AA pairs |
| `:focus-visible` ring | global 2 px `brand.600` ring, 2 px offset, in `index.css` on every interactive element; components add their own where the container needs it |
| Keyboard operability | `Button` real `<button>`; `JobCard` (when actionable) is `role="button"` + `tabIndex=0` + Enter/Space; `Modal` traps + restores focus, Escape (when dismissible) |
| Semantic HTML / headings | `JobStatusHeader` → `<header>` + `role="status"` line; `JobTimeline` → `<ol>` + `aria-current="step"`; `Modal` → `role="dialog"` + `aria-modal` + `aria-labelledby`; skip link in `AppShell` |
| Form labels / errors | `Field` label always visible (never placeholder-as-label); error `role="alert"` + `aria-describedby`; "Required" is text; `Input` `aria-invalid` |
| Status never colour-only | every status carries an **icon + text** (`StatusBadge` requires `label`, takes `icon`; `JobTimeline` node glyphs are distinct shapes; `ConnectivityIndicator` icon + word) |
| Accessible icons | `Icon` is `aria-hidden` unless given a `title`; meaningful icons in components are paired with visible text |
| Reduced motion | global `@media (prefers-reduced-motion: reduce)` kills animation/transition; `ConnectivityIndicator` spin is `motion-safe:` only |
| Target size | `min-h-target` (44) default, `min-h-target-driver` (56) for driver-critical; `Modal` close button 44×44 |
| 200 % text scaling | rem-based type scale; no fixed-height text containers in the primitives |
| EN / SW | all component copy is prop-driven / i18n-driven; chips and buttons size to content and wrap rather than truncate; `lang` follows the existing switcher |

---

## 6. Contrast validation

`frontend/src/design/contrast.test.ts` — a vitest suite that computes WCAG 2.x
ratios (`src/design/contrast.ts`) for **27 token pairs** and asserts the AA floor
(and the ≥ 7:1 target for driver / operator-critical). Runs in `npm test`.
Result: **27/27 pass.** Representative ratios (computed):

| Pair | Ratio | Floor |
| --- | --- | --- |
| `text.primary` on `surface.page` | **16.41:1** | 4.5 (and ≥ 7 target) |
| `text.secondary` on page | **6.99:1** | 4.5 |
| `text.muted` (adjusted) on page | **5.37:1** | 4.5 |
| `link` on card | **7.05:1** | 4.5 |
| white on `action.primary` (standard CTA) | **5.23:1** | 4.5 |
| white on `action.primaryStrong` (**driver / safety CTA**) | **7.05:1** | **7.0** |
| `accent.text` on card (trust label) | **5.52:1** | 4.5 |
| white on `status.danger.solid` | **5.73:1** | 4.5 |
| white on `status.info.solid` | **6.81:1** | 4.5 |
| white on `status.success.solid` (adjusted) | **5.43:1** | 4.5 |
| white on `status.warning.solid` (DISPUTED, deep amber) | **6.85:1** | 4.5 |
| success / warning / danger / info / neutral `.fg` on their `.bg` (chips) | **4.88 – 7.03:1** | 4.5 |
| focus ring vs card / page / brand-tint | **5.23 / 4.80 / 4.91:1** | 3.0 |
| `border.strong` (adjusted) vs card / page (WCAG 1.4.11) | **3.33 / 3.06:1** | 3.0 |

The suite also asserts **`status.success` is a distinct hue from the brand
colour** (green–blue channel spread check) — enforcing "brand colour must not
become the meaning of success".

**Physical low-cost-display check:** performed a live render via `vite preview`
in Chrome — the sign-in screen renders with the Stage & Yard tokens (warm stone
`#F7F5F1` ground, white hairline-bordered card, grounded-teal primary CTA with
white text, near-black title, visible input border). Foundation confirmed
end-to-end. A full multi-width / on-device sweep of migrated screens is a **5C**
task (there are no token-migrated feature screens yet).

---

## 7. Existing-frontend inspection & migration strategy

**What existed (Phase 2A):** Tailwind 3.4 with a 5-step placeholder `brand` teal
(`#0f766e`), `bg-slate-50 text-slate-900` on `body`, system-font stack, ~11 shared
primitives using **raw Tailwind palette classes** (`bg-brand-700`, `text-slate-*`,
`bg-green-50`, `bg-amber-*`, `bg-red-*` …). No semantic layer, no token file.
~145 raw palette class literals across the feature screens.

**Conflict:** components invented visual values directly. **Resolution
(smallest safe path):**

1. Add the two-tier token system (`tokens.ts` + Tailwind semantic keys + CSS vars).
2. `theme.extend` is used, so Tailwind's built-in `slate / green / amber / red`
   palettes **remain available** — un-migrated feature screens keep rendering
   unchanged (they inherit the new warm `body` ground and near-black text, which
   is the intended brand shift).
3. Migrate the **shared primitives** + the **app shell** onto semantic tokens now.
4. Add the new foundational primitives.
5. Feature-screen migration is **deferred to Phase 5C** (see below).

`stone` deliberately **overrides** Tailwind's built-in `stone` (nothing in the
codebase used `stone-*`; the codebase uses `slate-*`).

Radius: `rounded-{sm,md,lg}` are overridden to the Phase 4 scale (4 / 8 / 12).
Existing `rounded-lg` usages on un-migrated screens shift 8 → 12 px — cosmetic,
documented, resolved during 5C migration.

---

## 8. Known legacy styling (to migrate in Phase 5C)

The following still use raw Tailwind palette classes and will move to semantic
tokens screen-by-screen in 5C (each a small, reviewable diff):

```
src/features/auth/LoginPage.tsx
src/features/home/HomePage.tsx
src/features/diagnostics/DiagnosticsPage.tsx
src/features/org/*.tsx            (Businesses, BusinessDetail, Groups, GroupDetail,
                                   OperatingLocations, OperatorProfile)
src/features/vehicles/*.tsx       (VehiclesPage, VehicleDetailPage)
src/features/verification/*.tsx   (VerificationPanel, VerificationQueuePage,
                                   VerificationRecordPage)
src/app/ErrorBoundary.tsx
```

They render correctly today (they inherit the token `body` styles and use the
retoned primitives); the remaining literals are `slate-*` / `green-*` / `amber-*`
/ `red-*` utility classes that should become `fg-*` / `status-*` / `surface-*`.

---

## 9. Product invariants — UNCHANGED

No change to: Job lifecycle or the 14 states · verification lifecycle or the 7
states · trust rules · value bands · pickup / delivery proof · custody · recipient
access model · authorization · negotiation rules · agreed-price freeze ·
commission · payment architecture · dispute behaviour · cancellation reputation ·
notification rules · legal positioning · MVP exclusions. The domain **visual
mappings** in `tokens.ts` (`JOB_STATE_VISUAL` etc.) are presentation-only; the
enum names and semantics are the approved ones. No API contract, Django model,
migration, or backend file was touched.

### Open decisions preserved

- **`RESUME_PRIOR` preconditions** — OPEN. No component defines or implies the
  conditions for `DISPUTED → RESUME`; there is no resume-flow component.
- **Rating / reputation** — DEFERRED. No star rating, public score, ranking, or
  recommendation component. `TrustLevel` is an earned-standing ladder with no
  rating semantics (test-enforced).

---

## 10. Verification results

| Check | Result |
| --- | --- |
| `npm run typecheck` | **pass** (0 errors) |
| `npm run lint` | **pass** (0 errors, 0 warnings) |
| `npm test` | **pass** — 13 test files, **81 tests** (was 13; +68: contrast 27, JobStatusChip 18, JobTimeline 5, Modal 4, VerificationPill 4, TrustLevel 3, ConnectivityIndicator 3, Button +4) |
| `npm run build` | **pass** — 161 modules; JS **101.73 kB gzip** (< 200 kB shell budget), CSS **5.20 kB gzip** |
| Contrast validation | **27/27 AA pairs pass**; driver CTA 7.05:1 |
| Production CSS spot-check | semantic utilities resolve to the approved hexes (`#0c7a6c`, `#f7f5f1`, `#1a1712`, `#177a33`, `#8a4a10`, `#0a6459`); `theme-color` = `#0C7A6C` |
| Live render (`vite preview`, Chrome) | Stage & Yard tokens applied end-to-end on the sign-in screen |
| New dependencies | **none** |
| Backend / API / migrations | **untouched** |

---

## 11. Deviations & notes

1. **Two neutral-token a11y adjustments** beyond the Founder's pre-approved two
   (`text.muted` and `border.strong`) — see §1. Neutral-derived, WCAG-driven, not
   a brand change; flagged for Founder awareness.
2. **`stone` overrides Tailwind's built-in `stone`** — deliberate; documented.
3. **`rounded-{sm,md,lg}` overridden** to the Phase 4 scale — minor cosmetic
   shift on un-migrated screens (`rounded-lg` 8 → 12 px); resolved in 5C.
4. **Feature screens not migrated** — deliberate per the brief (§4, §24, §31):
   foundation first, then a gated screen-by-screen migration. Legacy styling
   inventory in §8.
5. **`ConnectivityIndicator` wired to `navigator.onLine`** only — a real browser
   signal; the richer syncing / sync-issue states belong to the offline/outbox
   work in a later phase. Not a product-behaviour change.
6. **No `BottomNav` / role-specific navigation** built — Phase 3/4 define it, but
   the brief (§17) says "do not redesign navigation during this phase". The
   `AppShell` retone keeps the Phase 2A top-bar nav.

---

## 12. Phase 5C — NOT STARTED

The next step (a **separate Founder gate**) is the controlled screen-by-screen
migration: replace the legacy palette classes in §8 with semantic tokens, compose
the domain primitives (§3) into the real screens per the Phase 3 wireframes, add
the role-specific navigation and the Operator workspace / Driver focus layouts
(Phase 4 §21), and run a full multi-width on-device visual QA.

**Do not begin Phase 5C without explicit Founder instruction.**

---

## 13. Changelog

| Date | Change |
| --- | --- |
| 2026-09-10 | Phase 5B — production Stage & Yard tokens (two-tier), Tailwind theme, CSS vars, retoned 11 shared primitives + app shell, 13 new foundational primitives, contrast validation (27 pairs), responsive hooks. typecheck / lint / 81 tests / build all green. No product/architecture change; no new deps; not merged. |
