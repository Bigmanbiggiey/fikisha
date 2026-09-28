# Design Phase 7 — UI/UX Pass: Phase Brief

**Status:** APPROVED 2026-09-23. The founder approved all §10 recommendations
("approved as recommended"), with one amendment to D-6 (see §10).

**Kind of phase:** a **findings and proposals** phase. It produces
documents, screenshots and mockups only. **No application code, tokens,
config or backend changes.** Implementing the approved proposals is a
separate, later build step with its own approval, the same way Design
Phases 3–4 (spec) came before 5B/5C (build).

**Lineage:** `design-brief.md` (P0) → IA (P1) → user flows (P2) →
wireframes (P3) → visual system (P4) → palette (P5A) → tokens and
primitives (P5B) → screen migration (P5C) → Jobs frontend build (P6,
Increments 1–8 done) → **this brief (P7)**.

---

## 1. Why now

The Jobs frontend was built one increment at a time (Design Phase 6,
Increments 1–8), each screen against its own slice of the wireframes. No one
has looked at the product **as a whole**: whether the ~38 screens read as one
consistent product across six roles, two languages and three screen classes.
Two concrete signals:

- **Increment 8's screens have never been seen in a real browser.** The
  founder declared the increment done after verification over HTTP only; the
  browser extension was unavailable.
- **Every increment's live check found real UI defects the test suite
  couldn't see.** Examples: raw error codes shown to users, a hanging
  geolocation prompt, and the Increment 8 `Modal` focus bug, which silently
  broke Increment 4's counter-offer sheet. A dedicated pass is likely to find
  more.

## 2. Objective

Produce an evidence-backed picture of where the current frontend falls short
of the **approved** design baseline and of good practice, and a prioritised
set of concrete proposals, with mockups for the most important ones, that the
founder can approve, reject or defer one by one.

## 3. Scope

**In scope:** every screen currently in `frontend/src/app/router.tsx`, grouped
by role:

| Role / area | Screens |
| --- | --- |
| Public / auth | Landing, Login |
| Business | Home, Jobs list, Create Job (8 steps), Job Detail, Pickup confirmation, Negotiation |
| Operator / Group Manager | Home, Work list, Job Opportunity, My Jobs, Assign driver & vehicle, Negotiation, Job Detail |
| Driver | Job Detail (driver actions), Pickup proof, Custody confirmation, Delivery proof |
| Recipient (no account) | `/r/:token`, Confirm receipt, Report a problem |
| Incidents & disputes | Report an issue, Incident detail, Dispute detail |
| Operations Officer | Overview, Monitor, High-value review, Audit, Job Detail staff panel |
| Org / account (Phase 2B/2C, migrated in P5C) | Businesses, Operator profile, Groups, Operating locations, Vehicles, Verification queue and record |

Each screen is looked at in **English and Swahili**, at **360px (phone),
768px (tablet) and 1280px (desktop)**, and in its exception states (P3 §22:
loading, empty, offline, error, unauthorised, expired, conflicting/stale,
cancelled, couldn't-complete, under-dispute).

**Out of scope:**
- The Platform Admin console (Increment 9). It isn't built yet.
- Any backend or API change.
- New features or new business rules.
- Anything touching the 14-state lifecycle, band-dependent proof,
  commission, or the trust/verification invariants (`CLAUDE.md` §4).

## 4. The baseline (what "right" means)

Findings are measured **against the approved docs**, not against taste:

1. **Wireframes and interaction structure:** `design-phase-3-wireframes.md`,
   including exception states (§22), offline vs server-confirmed (§23),
   per-role responsive rules (§24.1, with the P4 amendment: Driver always
   focused and action-dominant; Operator may expand on large screens) and
   accessibility (§25).
2. **Visual system:** `design-phase-4-visual-system.md` and the approved
   "Stage & Yard" palette (`design-phase-5-brand-palette.md`), as
   implemented in `frontend/src/design/tokens.ts` and the 13 P5B primitives.
3. **User flows:** `design-phase-2-user-flows.md`.
4. **Voice:** `design-brief.md`. English and Swahili are both first-class,
   and Swahili is prominent on operator and driver screens.
5. **Accessibility:** WCAG 2.2 AA; 56px targets on driver actions; status
   never shown by colour alone.

A finding that says the **approved baseline itself** should change (e.g. "the
palette fails in bright sunlight") is allowed. It is marked **baseline change**
and goes to the founder as a separate decision; it is never folded silently
into a fix.

## 5. Method

| Step | What happens | Skills / tools |
| --- | --- | --- |
| 1. Capture | Launch the app (dev stack on :5173 / :8010) and screenshot every in-scope screen at 3 widths × 2 languages, plus the reachable exception states, using seeded demo data. A headless Playwright script (scratch, not committed) signs in as each seeded role with the dev-only code (D-6 as amended). | `run`, `webapp-testing` (Playwright) |
| 2. Map | Inventory components, token usage, one-off styles, duplicated patterns (e.g. page-local tables, raw `<textarea>`s, ad-hoc selects) | Read/Grep (no agent fan-out unless approved) |
| 3. Critique | Visual hierarchy, consistency across roles, clarity of the "one primary next action" principle (P1 IA), density per role | `frontend-design`, `design:design-critique`* |
| 4. Accessibility | WCAG 2.2 AA: contrast of composed screens (not just tokens), focus order and traps, target size, ARIA, reduced motion, screen-reader naming | `accessibility-compliance` (`wcag-audit-patterns`, `ui-visual-validator`, `screen-reader-testing`), `design:accessibility-review`* |
| 5. Copy | EN and SW microcopy: labels, empty states, errors, confirmation dialogs, length and overflow in Swahili | `design:ux-copy`* |
| 6. Consistency | Token drift, spacing and type scale, component reuse; candidates for new shared primitives (e.g. Table, Textarea, FilterBar) | `design:design-system`*, `tailwind-design-system` (optional) |
| 7. Report | Findings report, one entry per finding (see §6) | `doc-coauthoring` |
| 8. Propose | Before/after mockups for the top-priority proposals, inside the approved tokens | `frontend-design`, `artifact-design` + `web-artifacts-builder` / `playground` (approved for this phase, D-3) |
| 9. Plan | For the approved proposals only: a file-by-file implementation plan for a later build step | `superpowers:writing-plans` (as a plan writer only, not the `using-superpowers` preamble, which stays rejected) |

\* The `design:*` skills (`design-critique`, `accessibility-review`,
`ux-copy`, `design-system`) are **not classified** in
`docs/team-skills-policy.md`. **Approved 2026-09-23 (D-3)** and added to the
policy's §5.4 as STANDARD (design phases).

## 6. Deliverables

1. **`docs/design-phase-7-ui-ux-findings.md`:** the findings report. Every
   finding has:
   - ID and title
   - screen(s), role, width and language
   - evidence: a screenshot reference, and a file:line reference where the
     cause is in code
   - the baseline it breaks (doc and section), or "best practice" with source
   - severity: **Blocker** (a user can't complete a flow, or it breaks an
     accessibility requirement), **Major**, **Minor** or **Polish**
   - proposed fix, and whether it is **within baseline** or a **baseline
     change**
2. **A screenshot set** (committed under `docs/design-phase-7/screens/` or
   attached to the artifact).
3. **Mockups:** interactive before/after pages for the top proposals
   (proposed: up to 8), published as a private artifact the founder can
   share. They use the real Stage & Yard tokens.
4. **A decision sheet:** each proposal with Approve / Reject / Defer, plus the
   baseline-change decisions listed separately.
5. **After the decision sheet comes back:** an implementation plan for the
   approved proposals, sequenced into reviewable increments.

## 7. Constraints (non-negotiable)

- **No code in this phase.** No edits to `frontend/src`, tokens, Tailwind
  config or the backend. The only exception is reading the code.
- **The 14 Job states are never renamed, collapsed or re-mapped**, even in
  mockups. Human-friendly labels only (`CLAUDE.md` §4).
- **Band-dependent proof, value-band gating, the no-wallet/no-escrow model
  and "WhatsApp is not the system of record" stay as approved.** Mockups
  must not imply otherwise (e.g. no "Pay now" button, no live GPS map).
- **Recipient screens keep minimum-necessary disclosure** (P3 §20.0).
- **Not-in-MVP items stay out:** live tracking, AI dispatch, route
  optimisation, native-app patterns.
- **RESUME_PRIOR and ratings stay open.** Mockups show at most the existing
  placeholders.
- **Server-side authorization is the enforcement.** A proposal to hide or
  show controls is UX only and must say so.
- **Seeded data only.** No real personal data in screenshots or artifacts.

## 8. Relationship to Increments 9 and 10

- **Increment 10 ("cross-cutting verification pass")** already plans a sweep
  of exception states, offline marking, responsive behaviour, WCAG and target
  size across every screen. This phase is essentially that sweep done
  **before the fixes**, with proposals and mockups instead of direct edits.
  **Recommendation:** this phase replaces the *audit* half of Increment 10.
  Increment 10 becomes the build step that implements the approved
  proposals.
- **Increment 9 (Platform Admin console)** isn't built, so it can't be
  audited. Two orderings are possible (§10, D-1).

## 9. Exit criteria

This phase is done when:
- every in-scope screen has been captured at 3 widths × 2 languages, with any
  screen that couldn't be captured listed with the reason
- the findings report and decision sheet are complete
- mockups exist for the agreed top proposals
- the founder has returned the decision sheet

Then Claude **stops**. Implementation needs its own approval.

## 10. Founder decisions needed before starting

| # | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| D-1 | When to run it | (a) **now**, before Increment 9, then audit Increment 9's screens as a small follow-up; (b) after Increment 9, so everything is audited at once | **(a)**. Most screens exist, Increment 8 has never been seen in a browser, and findings can shape Increment 9's screens before they are built |
| D-2 | Merge with Increment 10 | Make this phase Increment 10's audit half (§8), or keep them separate | **Merge** |
| D-3 | Skills | Approve the four unclassified `design:*` skills for this phase and add them to `team-skills-policy.md` §5.4 as STANDARD (design phases). Approve `web-artifacts-builder` / `playground` for the mockups (currently OPTIONAL, founder request) | **Approve both** |
| D-4 | Mockup count and form | Up to 8 interactive before/after mockups as a private artifact page, or static images in the repo only | **Artifact**, up to 8 |
| D-5 | Baseline changes | May the report propose changes to approved docs (palette, wireframes), clearly marked for separate decision, or must it stay strictly within baseline? | **Allow, clearly marked** |
| D-6 | Sign-in for screenshots | ~~The founder signs in for each role~~ **Amended by the founder:** capture runs automatically. It uses a headless Playwright script, outside the repo, against the local dev stack, signing in with the seeded test accounts and the dev-only `dev_code`. It never uses the founder's own browser or credentials. The founder signs in and explores each section after the revamps | Approved (amended) |

## 11. Effort and cadence

Roughly: capture (1 session, needs the founder for sign-ins) → map and
critique (1–2 sessions) → report and decision sheet (1 session) → mockups
(1–2 sessions). Claude stops for review after the findings report, before
starting mockups, so the founder can reprioritise.
