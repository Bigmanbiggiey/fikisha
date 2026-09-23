# Increment 10 — Build the approved UI/UX proposals: Implementation Plan

**Status:** APPROVED 2026-09-23. The founder approved the plan and added a
**Messages inbox** (§2, sub-increment 10g; scope chosen by the founder).
Defaults taken for the two unanswered questions: new Swahili strings are
flagged in each PR for founder review, and 10a–10c are built before
Increment 9.

**Source:** `design-phase-7-ui-ux-findings.md` (all 16 proposals approved
2026-09-23) and the mockups (https://claude.ai/artifact/Acqpw9Knkebi3G8fUhsALf).
**Replaces:** the old Increment 10 "cross-cutting verification pass" (Design
Phase 6 plan §7, re-scoped by brief D-2). Its final lint, test, build and
multi-width smoke checks are kept as the last sub-increment.

---

## 1. Shape of the work

**Frontend only, no backend changes, except 10g** (the inbox needs one
read-only endpoint and a small read-marker table). Every other proposal is a
presentation change. One data check confirmed this:
- **Driver contacts (P-03):** the job payload already returns the pickup
  contact name and phone and the recipient's name and phone to every job
  party, including the assigned driver. The founder's ruling (an assigned
  driver sees the sender's and the receiver's contacts) is met without any
  API change.
- **Before assignment (ADR-2D-36 open item):** the same payload also reaches
  operators who are only negotiating. Deciding what they may see stays a
  separate open item and is **not** touched here.

**Six sub-increments**, each on its own branch stacked on the last, each
with its own PR and live check, landed in order. This follows the "land
reviewably, not one giant diff" rule in `CLAUDE.md` §7.

| Sub-increment | Proposals | Findings | Size |
| --- | --- | --- | --- |
| **10a** Blockers, small and contained | P-01, P-02, P-10 | F-01, F-02, F-10 | S–M |
| **10b** Driver journey | P-03, P-12 | F-03, F-12 | M |
| **10c** Role navigation shell | P-04 | F-04, F-16 | L |
| **10d** Language, sync label, dates | P-05, P-06, P-14 | F-05, F-06, F-14, F-15 | M |
| **10e** Consistency and copy | P-07, P-08, P-09, P-11, P-13, P-15, P-16 | F-07, F-08, F-09, F-11, F-13, F-17, F-18 | M |
| **10g** Messages inbox | new (founder, 2026-09-23) | IA §26 Business "Messages" | M |
| **10f** Verification close-out (runs last) | — | the report's coverage gaps | S |

**The same checks for every sub-increment:**
- `npm run typecheck`, `lint`, `vitest` and `vite build` (within the 200 kB
  gzip budget)
- new or updated unit tests for every behaviour change
- re-run the Phase 7 headless capture for the affected screens at 360 / 768
  / 1280 × EN / SW, confirming no horizontal overflow and no new axe
  violations
- stop for review before the next sub-increment

The founder signs in and explores after the revamps (brief D-6).

---

## 2. Sub-increments

### 10a — Blockers (P-01, P-02, P-10)

**P-01 Single-column phone layouts**
- In these 15 files, `sm:` multi-column and row layouts move to `md:` (600 px)
  or `lg:` (900 px). Card grids and `flex-row` action bars: `md:`. Dense
  filter grids: `lg:`. Padding-only tweaks (`sm:p-5` in `Card`) may stay.
  - `features/jobs/{BusinessHomePage,JobsListPage,MyJobsPage,WorkListPage}.tsx`
  - `features/landing/LandingPage.tsx`
  - `features/ops/{AuditLogPage,HighValueReviewPage,OpsJobsPage}.tsx`
  - `features/org/{BusinessDetailPage,BusinessesPage,GroupDetailPage,GroupsPage}.tsx`
  - `features/vehicles/VehiclesPage.tsx`
  - `features/verification/VerificationPanel.tsx`
  - `components/Card.tsx`
- `components/JobCard.tsx`: put the reference and state chip on the top row
  and let the route wrap below them, so the chip never truncates.
- **Guard:** an ESLint `no-restricted-syntax` rule (or a vitest source scan)
  that fails on `sm:grid-cols-` and `sm:flex-row` in `src/`, with a comment
  pointing to the 360 px token.
- **Tests:** `JobCard` renders the chip unclipped (label text present, no
  `truncate`), plus the guard itself.

**P-02 Business cancel safeguard**
- New `features/jobs/CancelJobSheet.tsx`, following the Increment 8
  `StaffJobPanel` cancel modal:
  - a reason radio list over `CANCELLATION_REASONS` (excluding
    `ADMIN_ACTION`), with plain-language labels
  - optional note (`reason_text`)
  - a consequence line computed from `job.status`:
    - before `ASSIGNED`: "doesn't count against you"
    - `ASSIGNED`: late cancellation
    - `AT_PICKUP`: wasted trip
- `JobDetailPage.tsx`: the Business cancel button opens the sheet instead of
  calling `cancel.mutate('BUSINESS_CHANGED_MIND')`. The idempotency key is
  generated once per sheet open.
- i18n: `jobs:cancel.*` in en and sw. The consequence sentences are **copy
  only**; the rule stays server-side (3 late cancellations or wasted trips in
  30 days, per side).
- **Tests:** there is no immediate cancel on click. The reason is required.
  The consequence text changes by state. The chosen reason code is sent.

**P-10 Recipient code entry**
- `features/recipient/RecipientConfirmPage.tsx`: a visible label and helper
  line above `OtpInput`.
- `components/OtpInput.tsx`: add `aria-label` "Digit n of 6" per cell
  (i18n), keeping the existing group label.
- `components/RecipientHeader.tsx`: the wordmark reads "Fikisha".
- **Tests:** axe-style label assertions (every OTP input has an accessible
  name), and the visible helper is present.

### 10b — Driver journey (P-03, P-12)

**P-03 Driver "Current job"**
- `useJobViewerRole.ts`: add `isAssignedDriver`
  (`job.assigned_driver_id === operatorId`) so the page can pick the driver
  rendering.
- New `features/jobs/DriverJobView.tsx`, rendered by `JobDetailPage` when
  the viewer is the assigned driver in `ASSIGNED`…`DELIVERED`. Following P3
  §10.1, in order:
  1. header: reference + state line
  2. one 56 px action (reusing `operatorNextAction` and the existing
     mutations)
  3. **pickup (sender)** and **drop-off (receiver)** contact cards, each with
     name, phone as selectable text, `tel:` Call and `https://wa.me/` WhatsApp
     links. The current step's card comes first.
  4. cargo and vehicle
  5. a compact 3-step progress (Pickup → Transit → Delivery)
  6. "Report an issue"
  7. "Full job detail" disclosure, which renders the existing cards and
     timeline
- **Disputed:** if the job is `DISPUTED`, the action area becomes "on hold"
  (P3 §10.1 state).
- **Driver-voiced state lines:** new `jobs:statusLine.<STATE>_DRIVER` keys
  for `ASSIGNED`…`DELIVERED` and `DISPUTED`. `JobStatusHeader` gets them
  through the page.
- **"Go to pickup / destination":** an external map hand-off link
  (`https://www.google.com/maps/search/?api=1&query=`) using the address
  text, or lat/lng when present. Links only: no map embed, no GPS (not in
  MVP).
- **Tests:**
  - an assigned-driver viewer sees the driver view
  - a non-assigned operator doesn't
  - both contact phones render with `tel:` hrefs
  - the driver state line doesn't use the business wording

**P-12 Proof method rows**
- `features/jobs/PickupProofPage.tsx` and `DeliveryProofPage.tsx`:
  - replace the pill segment with full-width 64 px radio rows (new
    `components/OptionRow.tsx`), each with a one-line explanation
  - pre-select the code method
  - one 56 px "Continue"
  - the band matrix logic is **unchanged**: the fallback row renders only on
    STANDARD, and the ELEVATED+ explainer stays
- **Tests:**
  - STANDARD shows 3 rows
  - ELEVATED shows 2 rows plus the explainer
  - there is a default selection
  - the targets meet the size rule

### 10c — Role navigation shell (P-04)

- New `shell/navConfig.ts`: the P1 §26 matrix as data (role → primary items
  → secondary items), limited to screens that exist:
  - Business: Home · Jobs, with "Request transport" as the tab or sidebar
    action
  - Operator: Home · Work · My Jobs
  - Driver: Current job · Jobs
  - Group Manager: Home · Jobs
  - Ops: Operations · Monitor · Verification, with High-value, Audit and
    Incidents secondary
  - Platform Admin: same as Ops until Increment 9

  **Messages is left out** (no screen exists). Recorded as an open item for
  the founder.
- New `shell/RoleTabBar.tsx` (phones, below `md`): fixed to the bottom with
  the safe-area inset, 56 px items, and "More".
- New `shell/RoleSidebar.tsx` (from `lg`): persistent, with a secondary group.
- New `features/more/MorePage.tsx`: secondary items, the language switcher and
  sign out.
- **Active role:** chosen with the existing `useWorkspaces`. For multi-role
  users there's a simple role switch (Design Phase 6 plan Q3: "a simple
  role-switch control") in More or the sidebar.
- `shell/TopBar.tsx`: slims down to wordmark, connectivity and language (on
  phones) and stops listing every link.
- `shell/AppShell.tsx`:
  - drops the "Phase 2A foundation" footer (F-16)
  - puts the header in the same width container as the content, fixing the
    `/ops` misalignment
  - lays out sidebar + content from `lg`
- Diagnostics leaves user navigation. It stays reachable at `/diagnostics`
  for staff and dev.
- **Tests:**
  - each role's tab bar lists exactly its items
  - a business never sees Diagnostics, Operator or Groups
  - the tab bar hides from `md` and up, and the sidebar shows from `lg`
  - More includes the language switcher

  UX only: authorization stays server-side.
- **Risk:** this is the biggest change. It touches every page's chrome, so
  it gets a full re-capture of all 38 screens.

### 10d — Language, sync label, dates (P-05, P-06, P-14)

**P-05 Translation-driven shared components**
- **Strings to move into translations:**
  - `Field` `requiredText` gets its default from `common:form.required`. All
    9 callers get it for free: `LoginPage`, `CreateJobPage`,
    `DeliveryProofPage`, `PickupProofPage`, `BusinessesPage`, `GroupsPage`,
    `OperatingLocationsPage`, `OperatorProfilePage`, `RecipientConfirmPage`.
  - `Modal` close button `aria-label` → `common:actions.close`.
  - "Skip to content", the `ErrorBoundary` copy, the `NextActionCard`
    default label, "· as of" in `JobStatusHeader`, and the workspace labels
    in `useWorkspaces` all move to `common:*` keys.
- **Mechanism:** shared components call `useTranslation` themselves, or take
  required props with no English default. Pick one pattern per component,
  preferring `useTranslation` in shell and base components.
- **Login switcher:** `LoginPage` gets the `LanguageSwitcher` in its header
  (P3 §24.3).
- **Guard:** an ESLint rule (`react/jsx-no-literals`, scoped to
  `src/components` and `src/shell`) so English can't creep back in.

**P-06 Online / Offline label**
- `design/tokens.ts` `CONNECTIVITY_VISUAL`:
  - `online` becomes "Online", with an i18n key and no "Synced"
  - `syncing` and `sync_issue` are kept, but unused until a real sync engine
    exists
- `ConnectivityIndicator` gets a translated label from `TopBar`.

**P-14 Date/time helper**
- New `services/datetime.ts`:
  - `formatTime`, `formatDateTime`, `formatRelative` (`Intl.DateTimeFormat` /
    `Intl.RelativeTimeFormat`)
  - locale = the i18n language (`sw-KE` / `en-KE`), `timeZone:
    'Africa/Nairobi'`
- Replace the ad-hoc `toLocale*` calls in:
  - `features/jobs/JobDetailPage.tsx`
  - `features/negotiation/NegotiationPage.tsx`
  - `features/ops/{AuditLogPage,JobNotesSection,OpsHomePage,OpsJobsPage,StaffJobPanel}.tsx`
  - `features/verification/VerificationRecordPage.tsx`
- **Timeline:** rows older than today show the date as well as the time.
- **Ops queue rows (F-15):** a reason chip derived from `status` and the
  attention filter used ("Under dispute" / "Couldn't complete" /
  "High-value review" / "No change"), relative age, and sorting by urgency
  and then age. Only the input value is uppercased, not the placeholder.
- **Tests:**
  - the helper formats in EAT whatever the machine's timezone (mocked `TZ`)
  - Swahili output for the `sw` locale
  - queue rows show the reason chip

### 10e — Consistency and copy (P-07, P-08, P-09, P-11, P-13, P-15, P-16)

- **P-07 targets:** audit the 15 files using `size="compact"`. Keep `compact`
  only for row actions inside dense desktop tables (`lg`+). Everything else
  gets the default 44 px, or `driver` 56 px on driver screens. Add a note in
  `Button.tsx` restating the P4 §475 rule.
- **P-08 job header:**
  - `components/JobStatusHeader.tsx` renders an `<h1>` with the reference,
    plus an optional route summary and "as of" (P-14 helper)
  - `JobDetailPage`, `CreateJobPage` and `PickupConfirmPage` each get
    exactly one `<h1>`
  - the staff variant adds the business name, a value-band chip and a
    "high-value review pending" note when `is_high_value && status ===
    'CONFIRMED'` and no decision yet. That needs a small read:
    `/ops/high-value` already lists pending jobs, so check membership, with
    no API change.
- **P-09:** in `jobHelpers.businessNextAction`, `DELIVERED` returns a status
  instead of an action. `BusinessHomePage` drops it from "Needs your action"
  and shows "Delivered — completes automatically". The date is added only if
  the delivery-acceptance window is already exposed to the client; otherwise
  no date. No new API.
- **P-11:** in `negotiationHelpers.entryStatusLabel`, SUPERSEDED reads
  "Replaced by a newer offer" (en and sw) with a quieter visual weight.
  EXPIRED stays for genuinely expired entries.
- **P-13:**
  - New `components/Textarea.tsx` and `components/Select.tsx` to the P4
    input spec (44 px min, `line.strong`, focus ring, `Field` wiring).
  - Replace the 6 raw `<textarea>`s: `DisputeDetailPage`,
    `IncidentDetailPage`, `IncidentReportPage`, `HighValueReviewPage`,
    `StaffJobPanel`, `RecipientReportIssuePage`.
  - Replace the 8 raw `<select>`s: `DisputeDetailPage`, `OpsJobsPage`,
    `BusinessDetailPage`, `GroupDetailPage`, `GroupsPage`,
    `OperatingLocationsPage`, `VehiclesPage`, `VerificationPanel`. This also
    fixes the axe `select-name` error on Groups.
  - Fix the High-value `<dl>` structure (axe `definition-list`).
- **P-15:**
  - `useWorkspaces` operator query: cache a 404 for the session
    (`staleTime: Infinity`, no refetch on mount).
  - Check the double `/me` + `/auth/refresh` on first load. If it's React
    StrictMode double-invoking in dev only, record that and change nothing.
    Otherwise, de-duplicate in `AuthProvider`.
- **P-16:** remove the literal "· " from the report-issue link copy in en
  and sw.

### 10g — Messages inbox (founder addition, 2026-09-23)

**Founder-chosen scope:** one list of the conversations that **already
exist**, across all of the user's jobs, newest first, with unread markers.
Each item opens its existing screen. **No new chat channel:** negotiation
stays the authoritative record, and WhatsApp stays a notification channel.

- **Backend:** a new read-only composition app, `fikisha.inbox`. It reads
  only through each module's public surface (module boundary rule).
  - **Sources:**
    - negotiation threads the user is party to (latest entry, whose turn it
      is)
    - "Updates from Fikisha" notes on the user's jobs (`jobs.ops.notes_for`)
    - incident and dispute statements on the user's jobs, plus status
      changes where the user is a party
  - **`GET /messages`:** cursor-paginated items `{kind, job_id, job_reference,
    title, preview, at, unread, link}`, scoped by each module's existing
    party checks. Staff see nothing new here; they already have the Ops
    queues.
  - **Read markers:** a small `InboxReadMarker(user, conversation_key,
    last_read_at)` table. `POST /messages/read {conversation_key}` sets it.
    Opening the linked screen marks it read. This is a new migration.
  - **Records:** ADR-2D-37 for the new app, the read-marker table, and
    "aggregates only, no new messages"; plus IDOR/BOLA tests (a user never
    sees another business's or operator's items).
- **Frontend:**
  - `features/messages/MessagesPage.tsx`: list with filters (All · Offers ·
    Fikisha updates · Issues), unread badge, relative age (P-14 helper), EN
    and SW.
  - The Messages item joins the Business primary nav (and the Operator
    one, which also has offer threads) in `navConfig`, with an unread count
    badge on the tab/sidebar item.
- **Tests:**
  - aggregation per source
  - scoping (IDOR)
  - read markers
  - frontend list, filters and unread badge
- **Order:** after 10c (it needs the nav shell), before 10f.

### 10f — Verification close-out

- **Exception states:** extend the capture script to reach and screenshot
  the P3 §22 exception states:
  - offline, via `context.setOffline(true)`
  - error, via a stopped backend or a route to a non-existent job
  - expired recipient link (seed one past expiry)
  - unauthorised (a non-party on a job URL)
  - stale / conflict where reachable
  - the Increment 8 modals open
- **Full pass:** a final full capture of every screen, plus lint,
  typecheck, vitest and build.
- **Report:** update `design-phase-7-ui-ux-findings.md` with a
  "Resolution" column per finding, and record Increment 10 DONE in the
  Design Phase 6 plan and `CLAUDE.md`.

---

## 3. Open items (not decided here)

1. ~~Messages~~ **Resolved 2026-09-23:** build an inbox of existing threads
   (10g).
2. **Swahili copy review:** the new sw strings (cancel consequences, proof
   explanations, driver state lines) need a native-speaker pass before 10b
   and 10d land. Can the founder name a reviewer, or should Claude flag them
   in the PR for the founder?
3. **Unchanged open items:**
   - phones visible before assignment (ADR-2D-36)
   - a high-value rejection can't be reversed
   - references use 6 characters in the app and 8 on the recipient page
   - RESUME_PRIOR
   - ratings

## 4. Order relative to Increment 9

The brief (D-1) ran Phase 7 before Increment 9. **Recommendation:** build
10a–10c before Increment 9, so the Platform Admin console is built on the
new navigation shell and the fixed breakpoints. 10d–10f can follow
Increment 9, or run before it; the founder chooses.
