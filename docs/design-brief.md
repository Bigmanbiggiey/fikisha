# Fikisha — Brand & Design Brief

**Audience:** the design team engaged to develop platform branding and product
aesthetics.
**Status:** context package for design kick-off. Product decisions below are
founder-approved (Phase 0) unless marked otherwise. Nothing here is a visual
decision — that is the design team's to make.
**Source material:** `docs/phase-0/` (product discovery, approved) and
`docs/phase-1/` (architecture, approved). Key references are cited inline.

---

## 1. What Fikisha is

Fikisha is a **local logistics marketplace** for **Kitengela, Kajiado County and
its environs** (Namanga-road corridor, Athi River / Mavoko boundary, Isinya,
Kisaju, Kaputiei, and links to Nairobi's Industrial Area / CBD). It connects
businesses and individuals who need goods moved with **verified local transport
operators** — every vehicle class from a **motorcycle parcel to a semi-trailer
haul**.

The product **digitises how this network already works** rather than replacing
it: operators work from physical **stages, bases and yards**; work is found by
**phone and WhatsApp**; **price is negotiated** before a job is "on"; disputes
are **settled amicably** first. Fikisha makes that network *addressable,
accountable and trustworthy* — structured discovery, a preserved negotiation
record, an **auditable chain of custody** from pickup to delivery, and a
**progressive trust** model where new operators earn access to high-value work.

It is a **coordination layer over capacity it does not own.**

### What Fikisha is NOT (important for tone and imagery)

- Not an owned-fleet carrier or a courier brand with its own last-mile staff.
- Not a fixed-tariff service (no enforced pricing — the parties negotiate).
- Not a payments / wallet business (money moves directly between the parties;
  the platform only records and invoices commission).
- Not a bank, insurer, or freight forwarder.
- Not a slick Silicon-Valley "disruptor" positioned *against* the existing
  operators — it is *with* them. Riders and yard owners are the heroes, not the
  problem.

---

## 2. The brand name

**`Fikisha`** — founder-decided 2026-09-08 (`docs/phase-0/brand-name.md`,
decision `D-BRAND-1`).

| Attribute | Detail |
|---|---|
| Meaning | Swahili verb: **"deliver / cause to arrive / get it there."** The actual delivery verb, not a noun. Outcome-focused — *the goods arrive.* |
| Pronunciation | fee-KEE-sha (3 syllables), stress on the second. |
| Register | Everyday Swahili, understood by every operator and business in the pilot area. Works as a verb in a sentence: *"tunafikisha mzigo wako"* ("we deliver your load"). |
| Why this name | More ownable as a trade mark than a bare common noun; not tied to any vehicle class; warm and local, not corporate. |
| Tagline directions (not final) | SW: *"Fikisha — mzigo wako, mikono salama"* ("your load, safe hands"). EN: *"Delivered, tracked and trusted."* Design may propose alternatives. |
| Legal entity vs brand | The company may incorporate under a neutral name (e.g. "Fikisha Technologies Limited" or a holding name); the **app/consumer brand is `Fikisha`**. "Logistix" is only an internal working/repo name — never user-facing. |

### Clearance status — affects how far to take final lockups now

Name reservation and trade-mark registration are **in progress, not complete**:
BRS name reservation; KIPI trade-mark search + application in **Nice classes 39
(transport/logistics), 42 (software), 35 (marketplace/business services)**;
`.co.ke` / `.com` domains, WhatsApp Business, social handles; an informal-use
check in Kajiado (no local SACCO/cooperative already trading as "Fikisha").

**Design implication:** brand *exploration and system design can proceed now.*
Hold final production of the definitive wordmark/lockup and any printed
collateral until KIPI clearance comes back, in case a spelling variant or
descriptor is required.

---

## 3. Who sees the brand, and where

Three account-holding roles plus one no-account actor. The brand and UI must
serve all four, on the surfaces listed in §7.

| Audience | Context of use | Design consequence |
|---|---|---|
| **Transport operators** (riders, drivers, small owner-operators, yard/SACCO groups) | Outdoors, on a **low-end Android phone**, often **one-handed**, in **sunlight**, on **patchy data**, between jobs at a stage or yard. May be **low-literacy**. Swahili-first. | This is the **primary** design target. Big tap targets, minimal typing, icons that carry meaning next to text, very high contrast, fast. Swahili prominent. |
| **Businesses / shippers** (retailers, wholesalers, hardware & construction suppliers, agri-traders, market vendors, individuals with an occasional load) | Phone or desktop, in a shop or office, creating and tracking jobs. English or Swahili. | Efficient, legible, trustworthy. Can carry a little more density than operator screens. |
| **Platform administrators** (founder + ops staff) | Desktop, verification queue, monitoring, dispute handling, configuration. Every action is audit-logged. | A functional **admin console** aesthetic — dense tables, status, evidence viewers. Same design language, tuned for information density. Not a marketing surface. |
| **Recipients / consignees** (the person goods are delivered to) | **No account.** One tap on an SMS/WhatsApp link, at the doorstep, on any phone. Confirms receipt (name + OTP / signature / photo) or raises an incident. | A single, self-contained, unbranded-login page. Must be instantly obvious and trustworthy to someone who has never seen Fikisha before. Bilingual one-tap EN | SW toggle. |

Pilot geography is **Maasai-majority Kajiado** — imagery and illustration should
reflect the real local context (stages, yards, boda-to-trailer range, Kitengela
/ Namanga-road setting), not generic Western logistics stock or a Nairobi-CBD
gloss.

---

## 4. Brand personality

The product principle is **"design around discovered practice, not assumed
practice."** The brand should feel like it belongs at the stage and the yard.

**Attributes to express**

| Attribute | What it means here |
|---|---|
| **Trustworthy / accountable** | Every job has a record. The brand should feel like a reliable witness — calm, clear, evidence-minded. This is the single most important attribute (the product's reason to exist is recourse and a shared record). |
| **Local & grounded** | Kenyan, Kajiado, Swahili-first. Familiar, not imported. Warm, not cold-corporate. |
| **Practical / no-nonsense** | Operators and traders are busy. Plain language, obvious actions, nothing decorative that costs a tap or a second. |
| **Respectful of the operator** | The rider and the yard owner are professionals with a track record worth carrying. The brand elevates them; it never talks down. |
| **Fast & light** | Reflects a product engineered for cheap phones and thin data. Visual restraint reads as competence here. |

**Anti-patterns — avoid**

- Aggressive "disruption" energy; anything that frames existing operators as
  obsolete.
- Heavy gradients, glassmorphism, dense illustration, large hero imagery,
  animation flourishes — all cost performance budget (see §8) and read as
  frivolous to this audience.
- Fintech-neon or crypto aesthetics.
- Over-formal corporate-logistics blue-grey that feels like a multinational
  freight forwarder (Fikisha is explicitly *not* that).
- Text-only interfaces — low-literacy users need icons + colour + shape doing
  work alongside words.

---

## 5. Language & voice

**English and Swahili from day one**, per-user selectable, **Swahili prominent
on operator-facing screens** (`docs/phase-1/localization.md`; decisions `D-PIL-4`,
`NFR-ACC-1`). New operator accounts default to Swahili; business accounts default
from the browser then English. A **language switcher is always visible** in the
app bar. The recipient link page has a one-tap **EN | SW** toggle.

Voice guidance for both languages:

- **Short, plain, concrete.** Especially operator critical flows (discover,
  negotiate, custody steps, earnings). Must read clearly on a small screen and
  translate cleanly between EN and SW.
- **Verb-first calls to action** ("Send a load" / "Tuma mzigo", "Confirm
  pickup" / "Thibitisha kupokea").
- Swahili is a **first-class catalogue**, professionally translated and
  reviewed — not machine-translated. Extra care on custody/OTP wording (must be
  unambiguous at a doorstep) and incident/dispute wording (evidentiary).
- No hardcoded strings anywhere; design mock-ups should be delivered with
  **both** EN and SW copy so layout is tested against the longer language
  (Swahili strings are typically ~15–30 % longer).
- Currency is always **Kenyan shillings**, whole numbers, shown as **`KSh 4,000`**
  (`Intl` `KES`, no decimals). Dates/times in **EAT (Africa/Nairobi)**. Distances
  and weights **metric** (km, kg / tonnes).

---

## 6. Visual identity — what we need

### 6.1 Logo / wordmark

- **Primary wordmark** — "Fikisha", horizontal.
- **App / avatar mark** — a compact symbol that works at 16 px (favicon) up to a
  512 px PWA icon and as a social avatar. Must be recognisable in a phone's home
  screen grid.
- **Maskable variant** of the app mark (safe-area padding) for Android adaptive
  icons.
- **Monochrome / single-colour** versions (for the eTIMS invoice, SMS-adjacent
  contexts, stamps, low-ink printing, embroidery on operator vests if that
  happens later).
- **Clear-space and minimum-size** rules.
- Motif ideas the product suggests (not prescriptive): *arrival* (a point
  reached), *hand-to-hand relay / chain of custody*, *the route/path* ("njia"),
  the **stage/yard** as a place. Avoid a literal single vehicle (the platform
  spans motorcycle to trailer).

### 6.2 Colour

Deliver a **token palette** (hex, plus a suggested numeric scale like 50–900 so
it maps onto Tailwind — see §10). Functional requirements the palette must
satisfy:

- **High contrast, sunlight-legible on cheap LCD panels.** Target WCAG AA for
  body text and interactive elements; aim higher on operator critical flows.
  Do not rely on subtle tonal differences that vanish on a $60 phone.
- A **primary brand colour** plus a small set of **semantic colours** that must
  stay distinct for colour-blind users and in bright light:
  - success / delivered / verified
  - warning / attention / expiring
  - danger / dispute / rejected / failed
  - info / neutral / in-progress
- **Status palettes** for the domain state machines in §9 — job lifecycle,
  trust levels, verification states, and the offline/syncing/synced indicator.
  These need enough distinct, legible steps.
- **Light theme must be flawless**; dark theme is *not* required for the MVP but
  the token structure should not preclude it later.
- Provisional in code today: teal `#0f766e` as primary (`theme_color` and a
  `brand` 50–800 scale). **Treat this as a placeholder to replace**, not a
  constraint — though a saturated, grounded, non-corporate hue that survives
  sunlight is the kind of thing that's working.

### 6.3 Typography

- **System font stack only — no web-font download** (performance budget, §8).
  Recommend a concrete cross-platform system stack (the code currently uses
  `system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif`);
  refine it, and confirm it renders Swahili diacritics and the `KSh` glyph
  cleanly on Android.
- A **type scale** tuned for small screens and text-scaling (`NFR-ACC-3`):
  legible minimum body size, clear hierarchy with few steps, generous line
  height for dense bilingual content.
- Tabular/lining figures for money, weights, distances, OTP codes.

### 6.4 Iconography

- A **coherent icon set** — outline or filled, one style — sized for **≥ 44 px
  tap targets**.
- Icons **carry meaning alongside text** for low-literacy users; they are not
  decoration. Priority sets:
  - **Vehicle classes** (see §11) — must be distinguishable at a glance and at
    small size: motorcycle, pickup, canter, tipper, lorry, semi-truck, trailer,
    other.
  - **Custody / job steps** — request, negotiate, confirm, assign, arrive at
    pickup, custody confirmed, in transit, arrive at destination, proof of
    delivery, completed, cancelled, disputed.
  - **Trust levels** — a progression device (tier badges / pips) that reads as
    "earned standing", not a rating of the person.
  - **Verification** — submitted, in review, verified, rejected, expired.
  - **Connectivity** — offline / syncing / synced, always visible in the app bar.
  - General UI — camera, signature, OTP, phone, location/pin, filter, statement.
- A licensed open icon library as a base is fine; the **domain-specific icons
  (vehicles, custody, trust) are bespoke**.

### 6.5 Illustration & imagery

- **Spot illustration** for empty states, onboarding, the recipient link page,
  and error/sync-issue screens. Keep it **light-weight** (SVG, few nodes) and
  **locally grounded** — stages, yards, a boda and a lorry side by side, the
  Kitengela / Namanga-road setting, Maasai-majority Kajiado.
- **Photography direction** for marketing and any in-product hero: real
  operators and real vehicles across the class range, real handover moments,
  daylight, unstaged. No generic warehouse/robot-arm logistics stock. People
  first.
- If a mascot or character is proposed, it must not undercut the "serious
  witness / accountable record" attribute.

### 6.6 Motion

- **Minimal.** Micro-feedback on tap, state transitions, the sync indicator, a
  non-intrusive "new version — reload" toast. Everything must respect
  `prefers-reduced-motion` and the performance budget. No decorative animation.

---

## 7. Surfaces the design system must cover

| Surface | Notes |
|---|---|
| **Operator PWA** | The core. Discovery list, job detail, negotiation, the custody flow (its own tightly-scoped screen set), earnings/statement view, profile/verification/vehicles/base. Mobile-first, one-handed, Swahili-prominent. |
| **Business PWA** | Job creation (cargo, category, weight, value, vehicle type/capacity, price), tracking, negotiation, completed jobs + proof of delivery, ratings, locations, incidents. |
| **Admin console** | Verification queue, active-job monitoring + chain-of-custody drill-down, intervention actions, dispute/incident handling, evidence viewers, platform configuration, operational dashboards. Desktop, dense, same design language. |
| **Recipient link page** | No-account, single-job, time-limited. Status view, confirm-receipt (name + OTP / signature / photo), raise-incident (type + photos + statement), short terms. One-tap EN | SW. Must feel safe to a first-time viewer. |
| **PWA chrome** | App icon set (favicon 16/32, 192, 512, maskable, apple-touch), splash/launch screen, `theme_color` / `background_color`, install prompt, the always-visible offline/syncing/synced indicator, the update toast. |
| **Notifications** | SMS (very short, segment-cost-aware, plain text), WhatsApp (BSP-approved templates, EN and SW), in-app notification copy + icons. Server-rendered in the recipient's language. |
| **Documents** | Weekly **commission statement** (to operator / group), and the **eTIMS / KRA tax invoice** for commission. The tax/legal artefact is **English** with a Swahili summary block (exact requirement pending a tax advisor). These need a clean, printable, monochrome-capable layout with the logo. |
| **Proof-of-delivery artefact** | The captured POD (recipient name + OTP/signature/photo, timestamp, job ref) as shown in-app and in any exported/printed form. |
| **Marketing / recruitment** | Operator-recruitment and business-recruitment materials for the pilot (the founder onboards cohorts by hand). Landing page, one-pager, WhatsApp-shareable cards. |

---

## 8. Hard engineering constraints (non-negotiable — from `docs/phase-1/`)

| Constraint | Why | Design consequence |
|---|---|---|
| App-shell first load **< 200 KB gzipped JS**; route chunks small | low-end Android, thin data (`NFR-PERF-4`) | No web fonts. SVG/WebP only. Restraint in illustration. No heavy component libraries. |
| **System fonts only** | bundle budget | Type system built on a system stack. |
| Images **WebP**, client-compressed before upload | poor networks (`NFR-PERF-5`) | Art direction that survives compression; no fine detail that mushes. |
| **Tap targets ≥ 44 px**, usable **one-handed**, reasonable **contrast & text scaling** | `NFR-ACC-1/3` | Spacing scale, control sizes, thumb-reach layout for primary actions. |
| Interactive actions respond **< 2 s p95** on a typical pilot-area connection | `NFR-PERF-2` | Perceived-performance patterns: skeletons, optimistic UI only where the product allows it (see §9 — many actions are *not* safe to fake). |
| **Stale data is badged** "as of HH:MM"; **offline/syncing/synced** indicator always visible; **conflicts are surfaced, never auto-merged** | offline model (`pwa-architecture.md` §3–4) | Need a clear visual vocabulary for "this is cached", "this is queued", "this needs your attention (sync issue tray)". |
| Some actions are **blocked when offline** with a specific localized message | security / money / custody moments must be server-confirmed | Design explicit "you need a connection to confirm pickup" states — not a generic error — while still letting the safe part happen (e.g. capture the goods photo into the queue). |
| **RTL not required**; no additional languages in MVP | scope | Layouts only need to flex for EN ↔ SW length. |
| Every admin action (incl. the founder's) is **audit-logged**; **MFA mandatory** on admin accounts | governance | Admin console needs clear "reason for action" capture UI and an MFA enrolment/challenge flow. |

---

## 9. Domain state vocabularies to design around

The design system must give each of these a **consistent, legible, colour-blind-
safe visual treatment** (badge / chip / colour / icon). Exact enumerations are in
`docs/phase-0/job-lifecycle.md`, `trust-and-safety.md`, and `mvp-scope.md`.

**Job lifecycle** (indicative): `DRAFT` → `REQUESTED` → *(negotiating: offer /
counter)* → `CONFIRMED` → `ASSIGNED` → `AT_PICKUP` → `PICKED_UP` (pickup OTP) →
`IN_TRANSIT` → `AT_DESTINATION` → `DELIVERED` (recipient OTP / POD) →
`COMPLETED`; plus `CANCELLED` and `DISPUTED` as off-happy-path states. Transitions
are **enforced**; the UI shows only the legal next steps.

**Trust levels** — at least **three progressive tiers**, each with a job-value
ceiling. Visual device must read as *earned standing that grows*, applied to an
operator (and, for a group job, driven by the **assigned driver's** level).

**Verification states** (per domain: identity, licence, vehicle, association,
base, document): `not submitted` / `submitted` / `in review` / `verified` /
`rejected` / `expired`.

**Connectivity**: `online` / `offline` / `syncing` / `synced`, plus a **"sync
issues" tray** state for surfaced conflicts.

**Money**: always `KSh` + whole number; commission shown as *agreed price −
commission = net* on operator earnings.

---

## 10. What already exists in code (all provisional — replace freely)

The Phase 2A foundation build ships placeholder styling so the app runs. None of
it is a brand decision; it is there to be overwritten.

| Item | Current placeholder | Note |
|---|---|---|
| Primary colour | teal `#0f766e`, with a `brand` 50–800 numeric scale | placeholder; `theme_color` and `background_color` in the PWA manifest also use it |
| Font | `system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif` | keep the *system-font* approach; refine the stack |
| CSS framework | **Tailwind CSS 3.4** (utility classes, purged) | design tokens should be delivered as values that map to `tailwind.config` (`colors`, `fontSize`, `spacing`, `borderRadius`) |
| App icon | a stub `favicon.svg` (a plain "F" in a rounded teal square) | needs the full real icon set: favicon 16/32, `192`, `512`, **maskable**, apple-touch |
| Components | unstyled-ish primitives exist: Button (primary/secondary/ghost), Input, Field, Card, Alert (info/success/warning/error), Spinner, StatusBadge (neutral/positive/negative), PageLoader, EmptyState, ErrorState | these are the seams the design system plugs into; expect the set to grow |
| Layout | simple centered `max-w-3xl` shell, top bar with language switcher | placeholder |

**Deliverable format that lands cleanly on this stack:** colour + type + spacing
+ radius **tokens as plain values** (hex, px/rem), a **Figma library** of the
components above plus the domain patterns in §9, **SVG source** for logo and
icons, and **PNG exports** at the icon sizes in §7. A short **usage doc**
(clear-space, do/don't, status-colour semantics) rounds it out.

---

## 11. Vehicle-class icon set (bespoke)

From `docs/phase-0/users-and-roles.md` §3.2. Must be distinguishable at ~24 px:

`MOTORCYCLE` · `PICKUP` · `CANTER` · `TIPPER` · `LORRY` · `SEMI_TRUCK` ·
`TRAILER` · `OTHER`

These appear in discovery filters, job requirements, assignment, and the
operator's vehicle list — high-frequency, small, often glanced at outdoors.

---

## 12. Open questions for design + founder

1. **Wordmark treatment while the trade mark is pending** — how far to finalise
   before KIPI clearance (§2). Recommend: full system + exploratory lockups now,
   lock the definitive wordmark after clearance.
2. **Symbol direction** — arrival point vs. hand-to-hand relay vs. route vs.
   stage/yard (§6.1). Needs a founder steer early.
3. **Tagline** — adopt one of the directions in §2 or propose alternatives, in
   both languages.
4. **Trust-level visual metaphor** — badges, pips, a track? Must not read as a
   star-rating of the person.
5. **Recipient link page** — how much Fikisha branding vs. deliberate
   plainness, given the viewer has never seen the brand and is at a doorstep.
6. **Admin console** — same visual language at higher density, or a distinct
   "back-office" skin? (Recommendation: same language, tuned density.)
7. **Illustration vs. photography** balance for pilot recruitment materials.
8. **eTIMS invoice / statement** layout — needs the tax advisor's input on
   mandatory fields before final design; design the frame now.

---

## 13. Reference documents (in this repo)

| Topic | File |
|---|---|
| Brand name, rationale, clearance steps | `docs/phase-0/brand-name.md` |
| Product vision, principle, what it is/isn't | `docs/phase-0/product-vision.md` |
| The problem being solved | `docs/phase-0/problem-statement.md` |
| Users, roles, permissions, the recipient actor | `docs/phase-0/users-and-roles.md` |
| MVP scope (feature list) | `docs/phase-0/mvp-scope.md` |
| Pilot area, cohorts, learning agenda | `docs/phase-0/pilot-strategy.md` |
| Job lifecycle / state machine | `docs/phase-0/job-lifecycle.md`, `docs/phase-1/job-state-machine.md` |
| Trust levels & safety | `docs/phase-0/trust-and-safety.md`, `docs/phase-1/trust-architecture.md` |
| Localization (EN + SW) rules | `docs/phase-1/localization.md` |
| PWA constraints, offline model, performance budget | `docs/phase-1/pwa-architecture.md` |
| Non-functional requirements (accessibility, performance) | `docs/phase-0/non-functional-requirements.md` |
| Notifications (SMS / WhatsApp / in-app) | `docs/phase-1/notification-architecture.md` |
| Foundation build (current placeholder UI, component seams) | `docs/phase-2/` |
