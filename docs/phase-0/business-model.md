# Business Model

## 1. Confirmed model

**Revenue = a transaction fee / commission on successfully facilitated jobs.**

- The fee is **configurable** platform-wide (and potentially per vehicle class,
  per trust level, or per job-value band — see open questions).
- The fee is validated and tuned through the pilot.
- No other revenue model is implemented during MVP without explicit founder
  approval.

> **Update 2026-09-08 — founder-approved (see [decisions.md](decisions.md)
> D-BIZ-4…D-BIZ-7 and [decision-memo-2026-09-08.md](decision-memo-2026-09-08.md)
> §2):**
> - **Operator pays** the commission, shown transparently as a line item
>   (`agreed price − commission = payout`).
> - **Rate (pilot default, configurable):** 10% headline; **KES 40 minimum** per
>   completed job; large-job taper 10% ≤ KES 50k / 5% on 50k–150k / 3% > 150k
>   (equivalently flat 10% capped at KES 5,000); optional **introductory ramp
>   0% weeks 1–4 → 5% weeks 5–8 → 10% thereafter**.
> - **Collection:** weekly per-operator statement via a **merchant M-Pesa
>   paybill**; **eTIMS-compliant** invoices; the platform **never holds the
>   transport fare**.
> - **Disputed jobs:** commission held until resolution. **Cancelled/failed
>   jobs:** no commission.
>
> The sections below record the reasoning that led here; where they previously
> said "OPEN QUESTION — who pays / rate / collection", read the box above.

## 2. What "successfully facilitated" means

A job that reaches **COMPLETED** (delivered and confirmed, no unresolved
dispute that reverses the outcome).

- Jobs that end **CANCELLED** or **FAILED**: no commission (a cancellation fee is
  an OPEN QUESTION — see §6).
- Jobs in **DISPUTED**: commission is **held/pending** until resolution;
  resolution decides whether it applies, is reduced, or is waived.

## 3. Who pays the commission

**OPEN QUESTION — needs founder decision + pilot validation.** Options:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Operator pays | Commission deducted from the operator's agreed earnings | Simple; matches ride-hailing norms operators may recognise | Operators may inflate quotes to compensate; resistance if margins thin |
| B. Business pays | Commission added on top of the agreed transport price | Operator receives full negotiated amount; clean value story ("you pay a small coordination fee") | Businesses may resist a visible add-on; harder if they compare to informal channels |
| C. Split | Shared between both, e.g. 50/50 | Perceived fairness | More to explain; still needs collection from two sides |

**Recommendation:** default to **Option A (operator pays)** for the pilot,
presented transparently in the earnings breakdown, because supply (operators) is
the founder's controlled network and easier to align during a pilot. Revisit
based on pilot feedback. **Requires founder approval.**

## 4. Commission rate

- **CONFIRMED:** rate is configurable, not hard-coded.
- **WORKING ASSUMPTION for pilot default:** a single flat percentage in the
  region of **8–15%** of the agreed price, exact value **set by the founder**.
  This number is illustrative only and is an **OPEN QUESTION**.
- **OPEN QUESTIONS:**
  - Flat % vs. banded (lower % on high-value loads, minimum fee floor on small
    parcels)?
  - Different rates by vehicle class (a motorcycle parcel vs. a trailer haul have
    very different absolute values)?
  - A minimum absolute fee (e.g. so a very small delivery still covers cost)?
  - An introductory reduced/zero rate during early pilot weeks to drive adoption?

## 5. How commission is collected during the pilot

Because MVP does **not** include escrow/wallet/in-app processing
(see [mvp-scope.md](mvp-scope.md)), collection needs a defined mechanism.
**OPEN QUESTION — options:**

| Mechanism | Description | Notes |
|-----------|-------------|-------|
| Periodic invoice/statement | Platform generates a weekly statement of commission owed per operator; operator settles by mobile money to a platform account | Lowest build cost; relies on operator compliance; good for a trusted pilot network |
| Prepaid job credits | Operator tops up a balance; each completed job debits commission | Better collection guarantee; adds a balance/ledger feature |
| Deferred to Phase 1 payments | Introduce mobile-money collection at point of completion in Phase 1 once flows are understood | Cleanest long term; **REQUIRES KENYAN PROFESSIONAL VALIDATION** (payment-service and tax obligations) |

**Recommendation:** start with **periodic invoice/statement** during the pilot
(the network is known and trusted), while designing the ledger so that prepaid
credits or point-of-completion collection can be added in Phase 1. **Requires
founder approval.**

## 6. Cancellation / no-show economics

**OPEN QUESTION.** Informal practice sometimes involves a courtesy fee for a
wasted trip. Options to validate in the pilot:

- No fees at all during MVP (simplest; measure how often abuse happens).
- A configurable cancellation fee that applies only after ASSIGNED / AT_PICKUP,
  payable by the cancelling party, recorded like commission.
- Reputation-only consequence (cancellations count against the party's rating /
  trust assessment) with no money.

**Recommendation:** **reputation-only** for the earliest pilot, add a
configurable fee later if data shows abuse. **Requires founder approval.**

## 7. Cost side (for context, not a deliverable commitment)

Indicative operating costs the pilot should track to assess unit economics:

- SMS / WhatsApp messaging per job.
- Map / geocoding API usage.
- Hosting and storage (evidence photos, documents).
- Verification effort (staff time per operator/vehicle).
- Dispute-handling staff time.
- Support/coordination staff time.

Platform economics = commission revenue per completed job − variable cost per
job. The pilot must produce enough data to compute this.

## 8. Disintermediation risk

Because parties can and will contact each other directly (a deliberate design
choice), there is a risk they arrange repeat jobs off-platform to avoid
commission.

- **MVP stance:** accept the risk; do not build anti-circumvention friction that
  would damage the core value proposition.
- **Mitigations to consider:** keep on-platform value high (chain of custody,
  dispute protection, reputation, easy re-booking); make commission low enough
  that avoidance is not worth the effort; measure repeat-pair behaviour in the
  pilot.
- **OPEN QUESTION:** whether loyalty/volume incentives are needed. FUTURE
  CONSIDERATION.

## 9. Future revenue possibilities (DEFERRED — not for MVP)

Recorded, not planned. See [future-roadmap.md](future-roadmap.md).

- Business subscriptions (priority matching, higher limits, analytics).
- Enterprise / contract logistics agreements.
- Fleet-management tooling for larger operators.
- Premium services (dedicated support, insured lanes — legal validation
  required).
- Analytics / market-rate data products.
- API / integration services for business systems.

None of these are to be implemented during MVP without explicit approval.

## 10. Status summary

| Item | Category |
|------|----------|
| Commission on completed jobs is the revenue model | CONFIRMED DECISION |
| Rate is configurable, tuned via pilot | CONFIRMED DECISION |
| Rate/band structure: 10% headline, KES 40 min, taper 10/5/3% (or flat 10% cap KES 5,000), optional 0→5→10% intro ramp | CONFIRMED 2026-09-08 (D-BIZ-5) |
| Who pays: **operator**, shown transparently | CONFIRMED 2026-09-08 (D-BIZ-4) |
| Collection: weekly per-operator statement via merchant M-Pesa paybill + eTIMS invoices; platform never holds the fare | CONFIRMED 2026-09-08 (D-BIZ-6) |
| Cancellation fees: reputation-only for pilot; courtesy fee built but default-off | CONFIRMED 2026-09-08 (D-DIS-3) |
| Escrow / wallet / in-app payments | FUTURE CONSIDERATION |
| Other revenue streams | FUTURE CONSIDERATION — not without approval |
| Payment-service / tax / licensing obligations of collecting money | REQUIRES KENYAN PROFESSIONAL VALIDATION |
