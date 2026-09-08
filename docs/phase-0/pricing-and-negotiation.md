# Pricing and Negotiation

## 1. Principle

The platform does **not** enforce a fixed delivery price during MVP. Both parties
negotiate, exactly as they do today. The job becomes **CONFIRMED** only after
both sides agree. The system's job is to **facilitate** the negotiation and
**preserve** its full history and the final agreed price.

Recommended price ranges from historical data are a **FUTURE CONSIDERATION** and
must not replace negotiation in the MVP.

---

## 2. Actors and actions

Both the **Business** and the **Operator** can:

| Action | Meaning |
|--------|---------|
| **Propose** | State a price (the business does this when creating the job; either party can open with a figure) |
| **Counter-offer** | Respond to the other party's price with a different figure (optionally with a note) |
| **Accept** | Agree to the other party's current price — this is the mutual-agreement event |
| **Reject** | Decline and end this negotiation thread (does not by itself cancel the job unless the business rejects and withdraws) |

---

## 3. Negotiation flow

```
Business creates job with a PROPOSED price
        │
        ▼
Job REQUESTED  ── eligible operators see it
        │
        ├─ Operator ACCEPTS proposed price ─────────────▶ mutual agreement ▶ CONFIRMED
        │
        └─ Operator COUNTERS (amount + optional note) ──▶ Job NEGOTIATING
                     │
                     ├─ Business ACCEPTS ───────────────▶ mutual agreement ▶ CONFIRMED
                     ├─ Business COUNTERS ──────────────▶ still NEGOTIATING (loop)
                     └─ Business REJECTS ───────────────▶ thread ends; job stays REQUESTED for others,
                                                          or Business CANCELS
```

Notes:
- **Multiple operators may negotiate in parallel** on the same `REQUESTED` /
  `NEGOTIATING` job. Each operator has an independent negotiation **thread** with
  the business.
- The job is **CONFIRMED with exactly one operator** — the first thread to reach
  mutual acceptance (or the one the business chooses to accept). On confirmation,
  all other open threads for that job are automatically closed
  (state: `superseded`).
- **OPEN QUESTION:** if two acceptances race, the server serialises and the
  first wins; the second is told the job is no longer available. Confirmed via
  the concurrency requirement in [job-lifecycle.md](job-lifecycle.md).

---

## 4. What is recorded

### 4.1 Negotiation entry (immutable, append-only)
Every propose / counter / accept / reject creates a `NegotiationEntry`:

| Field | Notes |
|-------|-------|
| `id` | — |
| `job_id` | — |
| `thread_id` | Groups entries for one business↔operator negotiation |
| `actor` | Which party (business user id / operator id) |
| `actor_role` | BUSINESS / OPERATOR / ADMIN |
| `type` | PROPOSE / COUNTER / ACCEPT / REJECT |
| `amount` | Money (KES), required for PROPOSE/COUNTER; for ACCEPT, the amount being accepted is copied in |
| `currency` | KES (single currency for MVP) |
| `note` | Optional free text (e.g. "includes loading help", "excludes tolls") |
| `created_at` | Server timestamp (authoritative) |
| `in_response_to` | Previous entry id, where applicable |
| `status` | ACTIVE / SUPERSEDED / EXPIRED |

Negotiation entries are **never edited or deleted**. Corrections are made by
adding a new entry.

### 4.2 Agreement (created once, on CONFIRMED)
| Field | Notes |
|-------|-------|
| `job_id` | — |
| `agreed_price` | The final figure |
| `currency` | KES |
| `operator_id` | The confirmed operator |
| `accepted_by` | The entry ids from both sides that constitute mutual agreement |
| `agreed_at` | Server timestamp |
| `terms_note` | Snapshot of any note attached to the accepted offer |
| `price_breakdown` | Optional structured extras (see §5) |

The agreed price is **frozen** at confirmation. Any later change (e.g. scope
change agreed between parties) requires an explicit **re-negotiation** that
creates new entries and a new agreement version, all logged. **OPEN QUESTION:**
whether MVP needs in-flight re-negotiation or whether scope changes simply become
a new job / an incident adjustment. Recommend: no in-flight re-negotiation in
MVP; handle via incident/admin adjustment.

---

## 5. Price structure

- **MVP WORKING ASSUMPTION:** a single all-in amount in **KES**. Simple, matches
  practice.
- Optional free-text `note` captures what's included/excluded (loading,
  waiting time, tolls, fuel, return trip).
- **OPEN QUESTION:** whether to support structured line items (base + loading +
  waiting + tolls). Recommendation: **not** for MVP; capture in the note, learn
  from the pilot whether structure is needed.
- Commission is **separate** from the negotiated price and is computed by the
  platform on the agreed price. **CONFIRMED 2026-09-08 (D-BIZ-4):** the
  **operator pays**, so it is shown as a **deduction** in the operator's earnings
  view (`agreed price − commission = payout`). See
  [business-model.md](business-model.md).

---

## 6. Validation and guardrails (non-price-fixing)

These help the negotiation without enforcing a tariff:

| Guardrail | Behaviour | Category |
|-----------|-----------|----------|
| Non-negative, sane amounts | Reject zero/negative; warn on obviously mistyped values (e.g. an extra zero) | WORKING ASSUMPTION |
| Configurable soft ceiling/floor per vehicle class | If set by admin, show a non-blocking warning when an offer is far outside it | FUTURE CONSIDERATION (needs pilot data) |
| Declared cargo value sanity | If agreed price is a tiny fraction of a very high declared value, flag for the operator's awareness (risk) and possibly for trust-level gating | WORKING ASSUMPTION |
| Offer expiry | Offers lapse after a configurable time (1–4h default) to keep threads current | WORKING ASSUMPTION |
| Anti-spam | Rate-limit rapid repeated offers from one party | WORKING ASSUMPTION |

The platform never rejects a negotiated price for being "too low" or "too high";
it only warns.

---

## 7. Transparency requirements

- Both parties can always see the **full history** of their own thread.
- The business can see it has multiple threads and their current standing offers.
- After confirmation, both parties see the frozen agreed price and terms note.
- The operator's **earnings view** shows: agreed price − commission = net (or
  agreed price with commission noted separately, per the business-model
  decision).
- Administrators can see all threads for a job for dispute purposes.
- Operators do **not** see each other's offers on the same job (sealed threads).
  **OPEN QUESTION:** whether a later version shows anonymised "other offers
  exist" signals; not for MVP.

---

## 8. Future: recommended price ranges (DEFERRED)

Once the pilot has produced enough completed jobs with agreed prices, distances,
weights, vehicle classes, and areas, the platform may show a **non-binding
suggested range** ("similar jobs recently: KES X–Y"). This is a
[future-roadmap.md](future-roadmap.md) item and must not be built into the MVP.

---

## 9. Status summary

| Item | Category |
|------|----------|
| No enforced/fixed price in MVP; negotiation is core | CONFIRMED DECISION |
| Job CONFIRMED only on mutual agreement | CONFIRMED DECISION |
| Full negotiation history preserved, immutable, append-only | CONFIRMED DECISION |
| Final agreed price frozen and recorded | CONFIRMED DECISION |
| Parallel sealed threads with multiple operators; one wins | WORKING ASSUMPTION (recommended) |
| Single all-in KES amount + free-text note (no line items) | WORKING ASSUMPTION |
| No in-flight re-negotiation in MVP | WORKING ASSUMPTION (recommended) |
| Soft ceilings/floors, suggested ranges | FUTURE CONSIDERATION |
| Offer expiry / rate-limit defaults | WORKING ASSUMPTION — tune in pilot |
