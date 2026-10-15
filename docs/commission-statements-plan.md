# Commission & Statements: plan

**Status:** APPROVED 2026-10-15. Decisions D-1 to D-8 answered the same day, all as recommended (see §7); paybill number to follow. S-1 in progress.
**Founder decision:** 2026-10-14 item 5, "weekly statements + manual
settlement recording; eTIMS later", planned before it is built
(`founder-decisions-2026-10-14.md`). Item 6 also applies: manual commission
adjustments stay dispute-only.
**Sources:**
- Product: `phase-0/decisions.md` D-BIZ-4, D-BIZ-6, D-BIZ-7;
  `functional-requirements.md` FR-M-1 to FR-M-5 and FR-O-8;
  `legal-scope.md` §3.2 (eTIMS) and the paybill row.
- Architecture: `phase-1/commission-ledger.md` §3.3 to §3.5 and §7;
  `database-design.md` §4.11; `notification-architecture.md`
  (`StatementGenerated`).
- Wireframes: `design-phase-3-wireframes.md` §6.5 (Statements), §7.4
  ("Earnings for this Job"), §7.5 (More → Earnings / Statements), §19.4
  (admin view).
- What exists today: `main` @ `e2e4abc`, plus ADR-2D-23, 2D-24, 2D-27,
  2D-30 and 2D-38.

---

## 1. What exists today

| Piece | State |
|---|---|
| `commission_record` | **Built** (ADR-2D-23). Written once per job at `COMPLETED`, in the transition's transaction. Rate, min and cap are pinned on the row. Append-only at model, queryset and DB-trigger level. **No `status`, no `payee_kind`/`payee_id`, no `statement_id`** (unlike `database-design.md` §4.11). The payee is implied by the job's `Agreement` (operator or group). |
| `commission_adjustment` | **Built**. Only `REDUCTION` and `WAIVER`, always negative, created only by a dispute resolution, Platform Admin only (ADR-2D-24). |
| Commission hold for disputes | **Not built by design** (ADR-2D-30). The record is created straight away. The dispute window (`timeouts.post_completion_window`: 72 h, or 7 days for HIGH and latent-risk jobs) is enforced by a guard at request time. |
| Admin ledger read | **Built** (Increment 9, `jobs.admin_ledger`, `GET /admin/commission`). Platform Admin only. |
| Payee reads their own commission | **Not built**. `commission.read` is Platform Admin only (ADR-2D-27), which defers payee visibility to "the weekly statement feature", meaning this one. |
| Statements, statement lines, settlements | **Not built**. |
| eTIMS invoice | **Not built**, and out of scope (decision 5). |
| Notification dispatcher (SMS / WhatsApp / in-app table) | **Not built**. Only the outbox exists. |

## 2. What this increment delivers

1. **A weekly statement run.** For each payee (a solo operator or a group)
   with commission ready to bill, it writes a frozen statement: one line per
   commission record and one line per adjustment, with gross, adjustments
   and net due. It is idempotent per payee and period, and runs on a
   schedule or on demand by a Platform Admin.
2. **Manual settlement recording.** A Platform Admin records an M-Pesa
   payment (amount, M-Pesa reference, date) against a statement. The
   statement's paid / part-paid / unpaid state is computed from those rows,
   never stored and edited.
3. **Payee screens.**
   - Operator: More → Earnings / Statements.
   - Group Owner/Manager: Statements.
   - On a completed job: "Earnings for this Job" (agreed price − commission
     = net).
4. **Admin screens.** Commission → Statements: list, detail, record a
   settlement, and the overview figure "invoiced vs settled" (pilot metric,
   `pilot-strategy.md` §4.7).
5. **A nightly reconciliation check** (`commission-ledger.md` §7). Per
   statement it asserts `net_due == Σ lines` and `settled ≤ net_due`, and
   logs a CRITICAL alert on any mismatch.

**No money moves through Fikisha.** No wallet, no balance and no pay button.
The payee pays Fikisha's own paybill outside the app, and an admin records
that the payment happened.

## 3. Proposed design

### 3.1 Module

A new backend module, **`fikisha.statements`**. It depends inward on `jobs`
through a new read function in `jobs.commission` (records and adjustments
ready to bill), never by importing job models. Commission stays in `jobs`
(ADR-2D-23). Statements have a workflow of their own (the scheduled run and
settlements), which ADR-2D-23 gave as the reason commission did *not* need
a separate app.

### 3.2 Data (all append-only: model guard, queryset guard and Postgres trigger, like `commission_record`)

- **`commission_statement`**: payee (`payee_kind` OPERATOR/GROUP +
  `payee_id`), `period_start` / `period_end` (Kenya dates), totals (gross,
  adjustments, net due), `reference` (short, shown to the payee and used as
  the paybill account number), `generated_at`, `generated_by` (null = the
  schedule), `config_version`. Unique per (payee, period_start).
- **`statement_line`**: `kind` COMMISSION or ADJUSTMENT, the record or
  adjustment it bills, `job_id`, `amount_kes`. **Unique per
  commission_record and per adjustment**, so nothing can be billed twice.
  This uniqueness is what "invoiced" means, so `commission_record` needs no
  status column.
- **`statement_settlement`**: `amount_kes`, `method` (MPESA_PAYBILL, BANK,
  OTHER), `payment_ref`, `paid_on`, `recorded_by`, `note`. A correction is a
  new row of kind `REVERSAL` pointing at the original, with a reason (see
  D-5).

**Deviation from `database-design.md` §4.11, documented, not silent:**
- There are no stored `status` columns on records or statements. Both are
  derived: "billed" means a line exists, and "paid / part-paid / unpaid"
  comes from the settlement sum. This keeps every table truly append-only,
  which the stored-status design could not, because it updated
  `DUE → INVOICED → SETTLED`.
- There is no `etims_invoice` table and no C2B webhook (decision 5).
- **Why it's safe:** the product behaviour is identical, and the
  immutability is stronger.

### 3.3 Which commission goes on a statement

A commission record is billed in the first run after **all** of these hold:
- the job is `COMPLETED` and not `DISPUTED`;
- the job's post-completion dispute window has closed;
- no statement line exists for it yet.

Adjustments are billed the same way, on the next statement after they are
created. If an adjustment's record is already on an earlier statement, the
adjustment becomes a credit line on the next one. An issued statement is
never edited.

This is how D-BIZ-7's "commission held until resolution" is met without a
hold status. A job completed late in the week rolls to the following week.
**See D-2.**

### 3.4 The run

- A Celery beat entry on **Monday 06:00 EAT** bills the prior Mon–Sun
  (`statements.period`, config).
- The run is also callable by a Platform Admin for a named period. It is
  idempotent, and a re-run adds nothing already billed.
- Each statement is written in its own transaction with `audit.record()`
  and a `StatementGenerated` outbox event (no sender is wired; see D-6).
- A payee with nothing to bill gets no statement. A payee whose lines net
  to zero (for example, everything waived) still gets one, showing KES 0.

### 3.5 Who sees what (server-side `authorize`, default deny, IDOR tests for each)

| Actor | Statements | Per-job earnings |
|---|---|---|
| Solo operator | Their own | Their own completed jobs |
| Group OWNER / MANAGER | The group's | The group's completed jobs |
| Group DRIVER member | None. Internal settlement is the group's affair (FR-O-8, legal-scope) | None |
| Business | None. The operator pays commission (D-BIZ-4) and the business never sees it. **See D-7** | None |
| Ops Officer | Read only. **See D-4** | Read only |
| Platform Admin | All, plus record a settlement | All |

### 3.6 Screens (EN + SW, 360 / 768 / 1280)

- **Payee statements list → detail**: period, reference, lines (job
  reference, route, agreed price, commission), adjustments, net due, paid so
  far and outstanding, and "Pay to paybill `<number>`, account
  `<reference>`" (D-3). A printable layout per P3 §6.5. No pay button.
- **Job Detail, completed job**: "Earnings for this Job" card (agreed price,
  commission, net to you), linking to the statement once billed.
- **Admin Commission → Statements**: filter by period, payee and
  paid/unpaid. Detail with settlements and **Record a payment** (amount,
  M-Pesa ref, date) through the shared admin action dialog, plus **Run
  statements for a period**. The overview tile shows "invoiced vs settled
  this period".

## 4. Decisions needed from the founder

### D-1: Is a statement without eTIMS acceptable for the pilot? (legal, blocking)
`legal-scope.md` §3.2 says commission invoices must be eTIMS-compliant, and
decision 5 put eTIMS "later".
- **(a)** Issue statements labelled "Commission statement — not a tax
  invoice" until eTIMS lands, and confirm this with the tax advisor before
  the first statement goes to a real operator.
- **(b)** Build statements but don't release them to payees until eTIMS
  exists.

**Recommend (a).** It needs the advisor's sign-off, which is a founder
action, not a build step.

### D-2: When commission becomes billable
- **(a)** After the dispute window closes (§3.3). This honours D-BIZ-7 with
  no hold state, and costs about a week's delay for late-week jobs.
- **(b)** At completion; a later dispute's waiver or reduction becomes a
  credit on the next statement.

**Recommend (a).** It matches the architecture's HELD intent and means
statements rarely need credits.

### D-3: Paybill details
The statement must say where to pay. Needed from the founder: the paybill
number, and confirmation that the statement reference is the account
number. This becomes config (`statements.paybill_number`, read-only to
payees). Until it is set, statements show "payment details to follow".

### D-4: Who records a settlement, and is step-up needed?
- **(a)** Platform Admin only, with fresh MFA step-up.
- **(b)** Platform Admin only, no step-up. This is what the architecture
  says: "a recording action".
- **(c)** Ops Officers too.

**Recommend (a).** It is a money record, and step-up is cheap now that 9a
exists. Ops Officers get read-only access.

### D-5: Fixing a wrongly recorded payment
- **(a)** A reversal row: Platform Admin, a reason, step-up, audited. The
  original stays.
- **(b)** No correction path in the pilot.

**Recommend (a).** Typos in M-Pesa references will happen. Over-payment is
refused (settled can never exceed net due). An actual over-payment is
handled outside the app.

### D-6: Telling the payee a statement is ready
No SMS or WhatsApp sender is wired (CLAUDE.md stop line).
- **(a)** In-app only: a "New statement" card on Home and an unread marker
  in the Statements list. The `StatementGenerated` event is emitted for a
  later sender.
- **(b)** Also add statements to the Messages inbox.

**Recommend (a).**

### D-7: Business "Statements" in the IA
The IA (`design-phase-1-ia.md`) and P3 §6.5 list Statements for a business,
but businesses are never charged commission (D-BIZ-4).
- **(a)** Leave business statements out. The business still sees each
  job's agreed price.
- **(b)** Give businesses a list of the fares they agreed per week. This is
  a different feature, not commission.

**Recommend (a).** Record it as a resolved wireframe ambiguity.

### D-8: Unpaid statements
- **(a)** Show "overdue" to admins after N days (config, default 14). No
  automatic effect on the payee's ability to work.
- **(b)** Also block new work for payees with overdue statements.

**Recommend (a).** (b) is a new business rule with real pilot risk. If
wanted later, it can go through the existing manual suspension.

## 5. Proposed sub-increments (if the recommendations are approved)

| # | Scope | Notes |
|---|---|---|
| S-1 | Backend: `fikisha.statements` models, triggers, run (beat + admin), billing rules, settlement + reversal, reconciliation task, API, audit, IDOR tests | A migration review before merge (append-only triggers) |
| S-2 | Payee screens: statements list/detail/print, Job Detail earnings card, Home card | `commission.read`-style payee policy replaces ADR-2D-27's admin-only read for the payee's own rows |
| S-3 | Admin screens: statements list/detail, record payment, reverse, run for a period, invoiced-vs-settled tile | Uses the shared admin action dialog and step-up |

Each lands as its own PR with a full test run, a Docker smoke run and a live
check in EN and SW. New Swahili strings go on the pre-launch review list
(decision 20).

## 6. Out of scope (unchanged stop lines)

- eTIMS submission or invoice documents; M-Pesa C2B webhook or any wired
  M-Pesa / SMS / WhatsApp provider.
- New adjustment kinds (manual credit or debit). Decision 6 keeps them
  dispute-only.
- Prepaid commission credit (FR-M-6), a wallet, a balance, or collecting at
  completion.
- Any change to the commission rate, the calculation, or when a
  `commission_record` is written.
- Ratings, trust, `RESUME_PRIOR`.

## 7. Decision sheet

| # | Decision | Recommendation | Founder answer |
|---|---|---|---|
| D-1 | Statements before eTIMS | (a) "not a tax invoice" label; tax-advisor confirmation before the first real statement | **(a)**. Founder action: tax-advisor confirmation before the first statement reaches a real operator |
| D-2 | When commission is billable | (a) after the dispute window closes | **(a)** |
| D-3 | Paybill details | Founder supplies the paybill number; the statement reference is the account number | **Statement reference is the account number.** Paybill number not yet given: statements show "payment details to follow" until `statements.paybill_number` is set |
| D-4 | Who records a settlement | (a) Platform Admin + step-up; Ops read-only | **(a)** |
| D-5 | Correcting a recorded payment | (a) reversal row, reasoned, step-up | **(a)** |
| D-6 | Notifying the payee | (a) in-app only; event emitted for later | **(a)** |
| D-7 | Business statements | (a) left out | **(a)** |
| D-8 | Unpaid statements | (a) admin "overdue" marker only | **(a)** |

Answers were collected through the founder's private decision form
(submitted 2026-10-15 08:45 EAT, 8 of 8 answered, no notes). This table is
the authoritative copy.
