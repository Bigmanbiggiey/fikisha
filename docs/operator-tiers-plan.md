# Operator tiers: plan and decisions

**Source:** founder request 2026-10-20: "operator tiers and progress should be
shown on their pages. admin functionality to promote/demote operator from
tier should be included." **TD-1 to TD-6 approved as recommended,
2026-10-20.** This record is the authoritative copy. Built on the
assessment 2026-10-20 branch.

## Where things stood

- Every operator with current identity, licence and Good Conduct
  verification counted as **L1** (interim rule, ADR-2D-05; founder decision
  12 of 2026-10-14). L2 and L3 could not be reached; only a staff override
  reason at assignment let a driver take a higher band.
- `docs/phase-1/trust-architecture.md` defines L0 to L3 and Restricted, an
  append-only change log, progression proposed by the system and confirmed
  by an admin, and **no "set level" action**. Ratings do not exist
  (founder decision 11).

## Decisions (approved as recommended)

| # | Decision | Approved answer |
| --- | --- | --- |
| TD-1 | How tiers change | **Both.** The system proposes a promotion when the measured criteria are met and a Platform Admin confirms or rejects it; a Platform Admin can also promote or demote directly. Every change needs a reason and a fresh authenticator code, and a direct change shows as "manual" in the history. (Changes trust-architecture §3 "no set level action", by the founder.) |
| TD-2 | Start the tier engine now | **Yes, as scoped here:** no automatic promotion, no ratings. Replaces the interim rule (decision 12). |
| TD-3 | Rating criteria | **Skipped, shown as "not yet measured"**; switched on when ratings are built. |
| TD-4 | Restricted | **Used as a demotion target** (STANDARD jobs only), exit back to L1 with a recorded reason. The operator *account* status stays separate. (Changes decision 13.) |
| TD-5 | Automatic demotion after a serious at-fault incident | **Later, with ratings.** For now a Platform Admin demotes by hand. |
| TD-6 | Who sees an operator's tier | **The operator, their group manager (on the driver-pool screen), and staff.** Businesses keep seeing verification facts only. |

## What is measured

| Criterion | L2 (Established) | L3 (Trusted) | Source |
| --- | --- | --- | --- |
| Completed jobs as driver | ≥ 8 | ≥ 30 | jobs |
| Days active (since first completed job) | ≥ 14 | ≥ 60 | jobs |
| Average rating | not yet measured | not yet measured | ratings deferred |
| No unresolved incident on their jobs | required | — | incidents |
| No unresolved serious incident (loss, damage, missing goods, misconduct) | — | required | incidents |
| At-fault findings | not yet measured | not yet measured | no at-fault finding is recorded yet |
| Good Conduct verified | required | required | verification |
| Clean ELEVATED-or-above jobs (no incident) | — | ≥ 3 | jobs + incidents |
| No late-cancellation flag (3 in 30 days) | required | required | jobs |

Pilot values live in config `trust_tiers` (defaults in code).

## Plan (one branch)

- **T-1 Tier record** — new module `fikisha.trust`: `trust_level_state`
  (one per operator) and append-only `trust_level_change` (from, to,
  trigger, status, reason, who, criteria snapshot, evidence job ids, config
  version). Job eligibility reads the stored tier; verification stays the
  floor (lapsed → L0). No state row means L1, so nobody gains or loses
  access on the day it ships.
- **T-2 Progress** — the criteria above, per operator, MET / NOT MET / NOT
  MEASURED. When every measured criterion for the next tier is met, the
  system writes a PROPOSED change (on job completion and nightly); a
  rejected proposal is not re-proposed for 30 days.
- **T-3 Operator pages** — "Your tier" card on operator Home and the
  Operator profile: tier, the job values it allows, the checklist toward
  the next tier, the history with reasons. Driver pool shows each driver's
  tier.
- **T-4 Admin** — tier card on the applicant page and the directory page:
  progress, history, open proposal (confirm / reject), promote / demote.
  Platform Admin only, reason required, step-up, audited. Ops read only.
- **T-5 Tests** — eligibility follows the tier; L0 floor; promote / demote
  / confirm / reject write history and audit; refusals (non-admin, own
  profile, stale proposal); progress numbers; screens.

Demoting an operator affects new assignments only; jobs already assigned
keep their driver (staff can reassign).
