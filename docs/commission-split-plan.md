# Commission split (5% business + 5% operator): plan

**Status:** APPROVED 2026-10-26, D-1 to D-7 all as recommended (§8).
C-1 to C-3 BUILT 2026-10-26 on `feat/commission-split` (stacked on PR #27),
recorded as ADR-2D-55; awaiting founder review.
**Founder decision:** 2026-10-22. Commission stays at 10% of each completed
job, but it is split: **5% paid by the sender (business) and 5% paid by the
operator**, with **no minimum and no maximum** ("we take what we get";
commission pays for running the platform).
**Replaces:** D-BIZ-4 (the operator pays all of it) and the rate part of
D-BIZ-5 (10%, KES 40 minimum, KES 5,000 cap) in `phase-0/decisions.md`, and
CLAUDE.md §4 "Payments / revenue". **Unchanged:** D-BIZ-1, D-BIZ-6 (weekly
statements paid by M-Pesa to the paybill; eTIMS later; Fikisha never holds
the fare) and D-BIZ-7 (disputed jobs wait for resolution; cancelled and
failed jobs pay no commission).
**Sources:** `commission-statements-plan.md` (ADR-2D-42),
`phase-1/commission-ledger.md`, ADR-2D-23 / 2D-24 / 2D-30 / 2D-51, code on
`main` @ `bdfad69`.
**ADR (when approved):** ADR-2D-55. ADR-2D-53 and 2D-54 are taken by the
open trust PRs #26 and #27.

---

## 1. What exists today

| Piece | State on `main` |
|---|---|
| Config `commission` | `model: FLAT_WITH_MIN_CAP`, `rate: 0.10`, `min_fee_kes: 4000`, `cap_kes: 500000`, `party_liable: OPERATOR`. Only that model is implemented (`jobs/commission.py`). |
| `commission_record` | **One row per job** (`OneToOneField(job)`), written when the job reaches `COMPLETED`. It pins the price, rate, min, cap and config version. Append-only (model, queryset and Postgres trigger). It has no "who pays" column, because the operator side always paid. |
| `commission_adjustment` | `REDUCTION` / `WAIVER`, negative, written only by a dispute resolution, Platform Admin only. A resolution chooses **one** treatment (`APPLY` / `REDUCE` / `WAIVE`) for the job's one record. |
| Statements | `commission_statement` per **payee**. `PayeeKind` is only `OPERATOR` or `GROUP`. A weekly run bills records once the dispute window has closed. Statement plan D-7 deliberately **left businesses out** because they were never charged. |
| Screens | Operator: "Earnings for this job" (price − commission = what you keep), Statements, Home card. Admin: Commission ledger, Statements, Configuration (editable allowlist includes `commission.min_fee_kes` and `commission.cap_kes`). **Business: no fee shown anywhere**, while negotiating, on the job or at close-off. |
| Paying the operator | At close-off the sender records paying the operator the agreed price (`job_payment_record`, ADR-2D-51). Fikisha moves no money. |

## 2. What the change means

For a job with an agreed price **P**:

| | Today | After |
|---|---|---|
| Business pays the operator | P | P (unchanged) |
| Business pays Fikisha | nothing | **5% of P** |
| Operator pays Fikisha | 10% of P, at least KES 40, at most KES 5,000 | **5% of P** |
| Operator keeps | P − that | **95% of P** |
| Fikisha receives | 10% (with min and cap) | **10% of P**, with no min or cap |

Worked examples (each side rounded on its own, to the nearest whole cent,
half up):

| Agreed price | Business fee | Operator fee | Fikisha total | Today's fee (operator only) |
|---|---|---|---|---|
| KES 300 | KES 15 | KES 15 | KES 30 | KES 40 (minimum) |
| KES 2,500 | KES 125 | KES 125 | KES 250 | KES 250 |
| KES 80,000 | KES 4,000 | KES 4,000 | KES 8,000 | KES 5,000 (cap) |
| KES 1,200,000 | KES 60,000 | KES 60,000 | KES 120,000 | KES 5,000 (cap) |

Note on the last two rows: with no cap, large jobs pay much more than today.
For a VERY_HIGH job the business now owes KES 60,000+ to Fikisha. This is
what the decision says, so the plan does not add a cap back. It is listed
here so the effect is seen before launch.

## 3. Proposed design

### 3.1 Config

A new model, **`SPLIT_FLAT`**, which becomes the default and the only one
the calculator accepts:

```
"commission": {
    "model": "SPLIT_FLAT",
    "business_rate": 0.05,
    "operator_rate": 0.05,
}
```

`min_fee_kes`, `cap_kes` and `party_liable` are removed. The admin
Configuration allowlist swaps the old keys for `business_rate` and
`operator_rate` (preview, step-up and audit as today). Each rate is validated
as a number from 0 to 1. A rate of 0 means no fee and no record for that side
(useful for an introductory offer later, without new code).

### 3.2 Data: two commission records per job, one per side

- `commission_record` gains **`party`** (`BUSINESS` / `OPERATOR`). The
  one-per-job rule becomes **one per (job, party)**: `OneToOneField(job)`
  becomes a `ForeignKey` plus `UNIQUE(job_id, party)`.
- `min_fee_kes` and `cap_kes` become **nullable**. New rows leave them empty;
  old rows keep their values, so every old row still explains itself.
- Existing rows get `party = OPERATOR`. In Postgres, adding a column with a
  default is a catalog change, not a row update, so the append-only
  `BEFORE UPDATE` trigger does not fire and no historical row is rewritten.
  This migration still gets the migration review and rollback check
  (CLAUDE.md §6) before it merges.
- `create_commission_record_locked` writes **both** sides in the same
  `COMPLETED` transition, with one `audit.record()` and one
  `CommissionRecorded` event per row. It stays idempotent per side.
- `commission_adjustment` is unchanged: an adjustment already points at one
  record, so it applies to one side.

**Why two rows, not one row with two amounts:** statements, adjustments and
the "billed once" rule (`UNIQUE` on `statement_line.commission_record`) all
work per record today. Two records let each side be billed, adjusted and
reconciled on its own without changing those rules.

### 3.3 Which jobs use the new rule

As today, the rule in force **when the job completes** is used, and pinned on
the record. Jobs already completed keep their old rows. The pilot has not
launched, so no real job is caught between the two rules. See **D-4** for
whether to pin the fee earlier, when the price is agreed.

### 3.4 Statements for businesses

- `PayeeKind` gains **`BUSINESS`**. The weekly run bills `BUSINESS` records
  to the business (the organisation, not one person), and `OPERATOR` records
  to the solo operator or group, as today.
- The same rules apply: billed after the dispute window closes, frozen once
  issued, adjustments become credit lines, Platform Admin records payments
  and reversals behind step-up, overdue marker only (statement plan D-8).
- The same paybill and reference scheme (the statement reference is the
  account number). "Not a tax invoice" stays until eTIMS.
- Who in a business sees its statements: see **D-3**.
- This reverses statement plan **D-7** ("business statements left out").
  That was decided because businesses were never charged; the new decision
  changes that fact.

### 3.5 Disputes

A dispute resolution chooses a commission treatment for **each side**
(see **D-5**). A waiver or reduction writes an adjustment against that side's
record only. Cancelled and failed jobs still write no record for either side.

### 3.6 What each person sees (EN + SW, 360 / 768 / 1280)

| Who | Where | What |
|---|---|---|
| Business | Offer and agree screens | "Fikisha fee (5%): KES X. You pay the operator KES P and Fikisha KES X." Shown before they accept, so the fee is never a surprise. |
| Business | Job detail, close-off | "Cost for this job": operator KES P + Fikisha fee KES X. Close-off still records only the operator payment; the fee comes on the weekly statement. |
| Business | New: Statements (list, detail, print), Home "New statement" card | Same screens as the operator's, reused, with business wording. |
| Operator / group | Opportunity and offer screens | "You keep KES 0.95·P after Fikisha's 5%." |
| Operator / group | Earnings for this job, Statements | Unchanged screens; the fee is now 5% with no minimum. |
| Ops / Platform Admin | Commission ledger, Statements, Configuration | A "Side" column and filter; business statements in the list; the two new rate settings. |

The fee shown before agreement is computed by the server from live config
(one read endpoint), never by the browser.

## 4. Docs that change (on approval, in the build PR)

- `phase-0/decisions.md`: D-BIZ-4 and D-BIZ-5 marked superseded by the
  2026-10-22 decision, pointing at ADR-2D-55. Old text kept, struck through.
- CLAUDE.md §4 "Payments / revenue": the new split and config.
- `phase-1/commission-ledger.md`: two records per job, `party`, business
  statements.
- `commission-statements-plan.md` D-7: note that the split reverses it.
- `phase-2d-api.md`: new fields and the fee-preview endpoint.
- ADR-2D-55, with the deviation and "why it's safe" notes.
- New Swahili strings go on the pre-launch review list (decision 20).

## 5. Proposed sub-increments (if the recommendations are approved)

| # | Scope | Notes |
|---|---|---|
| C-1 | Backend: `SPLIT_FLAT` config + validation, `party` column and uniqueness migration, two records per completion, per-side dispute treatment, business statements in the weekly run, business statement reads with authz + IDOR tests, fee-preview endpoint, admin ledger side filter, config allowlist | Migration review before merge (append-only table) |
| C-2 | Screens: business fee at offer/agree, job detail and close-off; business Statements + Home card; operator "you keep" wording; admin side column, business statements, new config fields; dispute resolution per-side treatment | Live check in EN and SW |
| C-3 | Doc updates in §4 and ADR-2D-55 | Can ride with C-1 |

Each lands as its own PR with a full test run and a Docker smoke run. They
go after PRs #26 and #27 so the dispute-resolution change in C-1/C-2 builds
on the trust work, not beside it.

## 6. Decisions needed from the founder

### D-1: How the business pays its 5%
- **(a)** A weekly business statement, paid to the same Fikisha paybill,
  exactly like the operator's. No money moves through the app.
- **(b)** The business adds 5% to what it pays the operator, and the
  operator passes it on. This makes the operator collect money for Fikisha,
  which is close to fare handling and needs legal review.
- **(c)** Pay at close-off in the app. Needs a wired M-Pesa provider, which is
  outside the current stop line.

**Recommend (a).**

### D-2: Rounding
- **(a)** Each side is rounded on its own (half up, to the cent). On odd
  amounts the total can differ from exactly 10% by one cent.
- **(b)** Compute 10%, then split it, with any odd cent going to one side.

**Recommend (a).** Each side's fee is then simply "5% of the price", which is
easier to explain on both statements.

### D-3: Who in a business sees statements
- **(a)** The business Owner only.
- **(b)** Owner and Dispatcher; Viewer sees nothing.
- **(c)** Every member.

**Recommend (a).** It is a bill, and the Owner is the one who pays it.
Dispatchers still see the fee on each job they send.

### D-4: When the fee is fixed
- **(a)** At completion, from the config in force then (as today). If an
  admin changes a rate while jobs are running, those jobs get the new rate.
- **(b)** At agreement: the rates are pinned when the price is agreed, so
  the fee the business saw before accepting is the fee it pays.

**Recommend (b)** for fairness, since businesses now see the fee before
they agree. It adds a small change in negotiation (the agreement stores the
config version). If you'd rather keep the change smaller, (a) is safe before
launch because no real jobs are in flight.

### D-5: Commission in a dispute resolution
- **(a)** One choice (apply / reduce / waive) that applies to both sides.
- **(b)** A choice per side, with "same for both" pre-selected. For example,
  waive the business's fee when the operator was at fault.

**Recommend (b).**

### D-6: Unpaid business statements
- **(a)** Same as operators: an admin "overdue" marker after 14 days, no
  automatic effect on the business's ability to post jobs.
- **(b)** Block new jobs while a statement is overdue.

**Recommend (a)**, for the same reason as statement plan D-8. Manual
suspension stays available.

### D-7: Tax and legal (founder action, not a design choice)
The fee to the business is a service charge to a new kind of customer. The
tax-advisor confirmation (statement plan D-1) needs to cover business
statements too, including VAT and eTIMS treatment and the wording "not a tax
invoice", before the first business statement reaches a real business. The
business terms of service also need to state the fee.

## 7. Out of scope

- Any wired M-Pesa, SMS, WhatsApp or eTIMS provider; collection at
  completion; a wallet or balance.
- A minimum, cap, taper or introductory ramp (a rate of 0 is possible through
  config, nothing more).
- Rewriting or re-billing commission already recorded or billed.
- New adjustment kinds (adjustments stay dispute-only, decision 6).

## 8. Decision sheet

| # | Decision | Recommendation | Founder answer |
|---|---|---|---|
| D-1 | How the business pays | (a) weekly business statement, same paybill | **(a)** |
| D-2 | Rounding | (a) each side rounded on its own | **(a)** |
| D-3 | Who sees business statements | (a) Owner only | **(a)** |
| D-4 | When the fee is fixed | (b) at agreement | **(b)** |
| D-5 | Commission in disputes | (b) per side, "same for both" pre-selected | **(b)** |
| D-6 | Unpaid business statements | (a) overdue marker only | **(a)** |
| D-7 | Tax-advisor confirmation covers business statements | Founder action before the first real business statement | **Agreed.** Founder action before the first real business statement |

Answered by the founder in session, 2026-10-26: "all as recommended, build".
D-5 detail, ruled 2026-10-26 after the first build: with "same for both", a
reduction is the job's **total**, split half and half between the two fees
(an odd cent to the operator side), not the amount off each side.
This table is the authoritative copy.
