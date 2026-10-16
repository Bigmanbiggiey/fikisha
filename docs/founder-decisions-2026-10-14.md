# Founder decisions — 2026-10-14

**Source:** the founder's answers to the open-decisions form (private
artifact, 20 of 20 answered and submitted 2026-10-14 09:25 EAT). No notes were
added; every answer is one of the options offered. This record is the
authoritative copy; the form was only the means of collecting it.

## Decided

| # | Decision | Answer | What it sets in motion |
| --- | --- | --- | --- |
| 1 | Admin MFA and step-up (Increment 9 D-1) | **Build it now** (TOTP enrolment, MFA at admin login, hashed backup codes, step-up before sensitive actions, including dispute resolution and high-value approval, which already shipped without it) | Increment 9a, next. Unlocks suspend/offboard and config apply (ADR-2D-38) |
| 2 | What Claude builds next | **Admin MFA (9a)** | — |
| 3 | Docker Desktop | **Installed** | The standard `docker compose` stack (Postgres, Redis, Celery) is available again for full-stack smoke runs |
| 4 | Branch protection on `main` | **Apply now** | Applied 2026-10-14: PRs required (0 approvals, so the founder can merge their own), admins included, force-pushes and deletion blocked. Closes the 2026-09-11 process-exception hardening item |
| 5 | Commission & Statements scope | **Weekly statements + manual settlement recording; eTIMS later** | A Commission & Statements increment, planned before it is built. eTIMS waits for legal validation and a provider |
| 6 | Manual commission adjustments | **Keep dispute-only** | No change |
| 7 | Phones visible to operators who are only negotiating (ADR-2D-36) | **Hide phones until the job is assigned to them** | A backend change to the job payload (contact phones masked for non-assigned operator parties), with tests. Closes the ADR-2D-36 open item |
| 8 | High-value rejection | **A Platform Admin can reverse it, with a reason** | A reversal action: Platform Admin only, reasoned, audited, step-up (after 9a) |
| 9 | Job reference length | **6 characters everywhere** | The recipient page moves from 8 to 6 |
| 10 | Resuming a disputed job (`RESUME_PRIOR`, O-P1) | **Keep it disabled for now** | No change; O-P1 stays open |
| 11 | Ratings | **Keep deferred** | — |
| 12 | Trust & Reputation engine | **Keep the interim rule for the pilot** (ADR-2D-05) | — |
| 13 | Operator "Restricted" status | **Leave it unused** | — |
| 14 | Ending a suspension | **Keep reinstatement manual** | — |
| 15 | Config change approval | **One Platform Admin is enough** (reviewed at the weekly pilot meeting) | — |
| 16 | Users & organizations for Ops Officers | **Keep it Platform-Admin-only** | — |
| 17 | Deferred Ops interventions (reassign, force-fail, flag-for-review) | **Keep deferred** | — |
| 18 | Cross-entity search | **Keep deferred** | — |
| 19 | Group Manager assigns from the driver pool | **Schedule it** | A scoped increment for group assignment |
| 20 | Swahili review | **Review everything before the pilot launch** | Claude compiles every Swahili string (with its English source and screen) into one review list before launch |

## Proposed order of the work this creates

1. **Increment 9a — Admin MFA + step-up** (decisions 1–2). **Done, PR #12.**
2. **Small follow-ups batch:**
   - mask phones before assignment (7);
   - reversible high-value rejection (8);
   - 6-character references (9).

   **Built 2026-10-14 (ADR-2D-40).**
3. **Group driver-pool assignment** (19), scoped first.
4. **Commission & Statements** (5), with its own plan first.
5. **Swahili review list** (20), before the pilot launch.

   **Compiled 2026-10-15** (`docs/swahili-review/`): 1,096 strings with
   English source and screen, ready for a native-speaker review.

The order is a proposal; the founder sets it.
