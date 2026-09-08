# Negotiation Architecture

Implements Phase 0 `pricing-and-negotiation.md` and `FR-N-1..N-10`:

- Business **and** operator can **propose**, **counter**, **accept**, **reject**.
- Negotiation history is **immutable / append-only** (FR-N-2).
- Every entry has a server timestamp and an actor (FR-N-2).
- A job is **CONFIRMED only on mutual agreement** (D-NEG-2).
- The agreed price is **frozen** at confirmation (D-NEG-3).
- The MVP does **not** set or recommend prices (D-NEG-4, brief §34 P4).

---

## 1. On "sealed threads" — the Phase 1 brief's challenge

The Phase 1 brief §11 says: *"Do NOT introduce unnecessary 'sealed thread'
complexity unless you can demonstrate a concrete security or business requirement
for it."* Phase 0 `FR-N-3` and `pricing-and-negotiation.md` §7 say operators do
**not** see each other's offers.

**Resolution (RECOMMENDED — see [phase-1-decisions.md](phase-1-decisions.md)
ADR-006):** keep a **per-(job × operator) negotiation thread with read
scoping**. This is *not* heavyweight — there is no encryption, no isolation
infrastructure, no separate storage. "Sealed" here means only: **the default
authorization rule scopes thread reads to the thread's operator/group, the job's
business, and admins.** That is one `WHERE` clause and one policy rule.

Three concrete requirements make it necessary, not decorative:

1. **NFR-PRIV-6** (Phase 0) — "operators see only the business/job data a job
   requires". A rival operator's price is not job data the operator requires.
2. **Preserving the negotiation the founder explicitly wants** — if operator B
   can see operator A's KES 4,000 offer, B rationally offers KES 3,999 and the
   two-sided negotiation the founder is digitising collapses into a
   race-to-the-bottom the platform would be seen to orchestrate.
3. **Competition-law prudence** (Phase 0 `legal-scope.md` §8) — the platform must
   not "set or recommend prices" and should avoid *facilitating independent
   operators observing each other's prices*. Per-thread scoping keeps the
   platform clearly a neutral intermediary (posture A).

Cost of the design: negligible. Benefit: real. It stays.

---

## 2. Data model

From [database-design.md](database-design.md) §4.8:

- **`negotiation_thread`** — one per `(job, operator_party)`. `status ∈
  {ACTIVE, SUPERSEDED, CLOSED}`. `U(job_id, operator_id, group_id)`.
- **`negotiation_entry`** — append-only. `type ∈ {PROPOSE, COUNTER, ACCEPT,
  REJECT}`, `amount_kes` (KES minor units), `note`, `in_response_to_id`,
  `status ∈ {ACTIVE, SUPERSEDED, EXPIRED}`, `expires_at`, `created_at` (server).
  **Never updated or deleted** — a correction is a new entry (FR-N-2). Table role
  has `INSERT, SELECT` only.

There is **no** `Agreement` row until CONFIRMED; the agreement is created by the
Job Lifecycle Service inside the confirming transaction (see
[job-state-machine.md](job-state-machine.md) §3.1).

---

## 3. Flow

```mermaid
sequenceDiagram
    participant B as Business
    participant NS as Negotiation Service
    participant DB as PostgreSQL
    participant FSM as Job Lifecycle Service
    participant O1 as Operator A
    participant O2 as Operator B

    B->>NS: create job with proposed_price P0  (job REQUESTED)
    Note over O1,O2: both discover the job (FR-J-6 filters)

    O1->>NS: COUNTER P1 (thread A)
    NS->>DB: INSERT negotiation_entry(A, OPERATOR, COUNTER, P1)
    NS->>FSM: transition(job, NEGOTIATING)  [no-op if already NEGOTIATING]
    O2->>NS: ACCEPT P0 (thread B) -- accepts the posted price
    NS->>DB: INSERT negotiation_entry(B, OPERATOR, ACCEPT, P0)
    NS->>NS: mutual acceptance? need a matching business-side ACCEPT

    B->>NS: COUNTER P2 on thread A
    B->>NS: ACCEPT P0 on thread B   -- business picks operator B
    NS->>DB: SELECT job FOR UPDATE
    NS->>NS: NoRacingConfirm: job.status in {REQUESTED,NEGOTIATING} ✓
    NS->>NS: MutualAcceptanceExists on thread B ✓ (B ACCEPT P0 + O2 ACCEPT P0)
    NS->>FSM: transition(job, CONFIRMED, {thread_id: B, accepting_entry_ids})
    FSM->>DB: within one txn: create Agreement(price=P0, operator=O2);<br/>thread B -> CLOSED; thread A -> SUPERSEDED;<br/>all ACTIVE entries in A -> SUPERSEDED; job.status=CONFIRMED
    FSM-->>NS: confirmed
    NS-->>O1: thread A superseded (notification)
    NS-->>O2: job confirmed (notification)
```

### 3.1 Who can open with a figure

- The **business** always opens with `job.proposed_price` at publish (a `PROPOSE`
  entry is written implicitly per thread the first time an operator engages, or
  the `proposed_price` is treated as a standing offer on every thread — **RECOMMENDED:**
  materialise it as the first `negotiation_entry(actor_role=BUSINESS,
  type=PROPOSE, amount=proposed_price)` when a thread is opened, so every thread
  has a complete history).
- Either party may then `COUNTER` (a new amount) or `ACCEPT` the other's current
  standing amount or `REJECT`.

### 3.2 Mutual acceptance

`CONFIRMED` requires, in **one** thread:

- an `ACCEPT` entry from the **operator/group side** referencing amount X, and
- an `ACCEPT` entry from the **business side** referencing amount X,
- both `ACTIVE` (not `EXPIRED`), X being the same value.

An `ACCEPT` of the other party's *current standing offer* is the normal path;
the service resolves "current standing offer" as the latest `ACTIVE`
`PROPOSE`/`COUNTER` from the counterparty in that thread.

### 3.3 Confirmation is one atomic transaction

`NegotiationService.accept(entry, actor)`:

```
BEGIN
  job = SELECT ... FROM job WHERE id = entry.job_id FOR UPDATE
  guard NoRacingConfirm          -- job.status in {REQUESTED, NEGOTIATING}
  guard MutualAcceptanceExists   -- on entry.thread_id
  guard OperatorEligibleForJob   -- re-check the winning operator NOW
  call JobLifecycleService.transition(job, CONFIRMED, actor,
        context={thread_id, accepting_entry_ids=[op_accept.id, biz_accept.id]},
        idempotency_key)
    -> creates Agreement(agreed_price, operator_party), sets confirmed_at,
       thread -> CLOSED, siblings -> SUPERSEDED, entries -> SUPERSEDED
COMMIT
```

Everything in one commit; notifications afterward via the outbox.

---

## 4. Concurrency & edge cases (FR-N-6, FR-N-7, FR-N-8)

| Case | Handling |
|------|----------|
| **Two ACCEPTs race** (business accepts thread B while operator C's ACCEPT lands on thread C) | The `SELECT job FOR UPDATE` serialises. The first to commit sets `status = CONFIRMED`. The second's `NoRacingConfirm` guard fails → `409 job_no_longer_available`. Operator C's thread is `SUPERSEDED` by the first transaction. (FR-N-6.) |
| **Duplicate offer submission** (client retry) | `Idempotency-Key` on `POST .../entries`; the stored entry id is returned; no duplicate row. |
| **Offer expiry** | A beat job (`expire_stale_offers`, every 5 min) sets `status = EXPIRED` on `ACTIVE` entries whose `expires_at < now()`. **This does not change `job.status`** (FR-N-7). An `EXPIRED` entry cannot be accepted (`MutualAcceptanceExists` requires `ACTIVE`). Default `offer_expiry` from config (1–4h range — Phase 0). |
| **Business rejects a thread** | `REJECT` entry; thread → `CLOSED`; the job stays `REQUESTED`/`NEGOTIATING` for other operators (pricing-and-negotiation §3). |
| **Business cancels the job mid-negotiation** | `JobLifecycleService.transition(job, CANCELLED)`; a consumer of `JobCancelled` closes all `ACTIVE` threads/entries as `SUPERSEDED`. |
| **Sanity validation** (FR-N-8) | `amount_kes > 0` (reject non-positive); a **non-blocking warning** returned in the response when the amount is an obvious mistype (e.g. ≥ 10× or ≤ 1/10 of the last entry) or is a tiny fraction of a very high `declared_value`. The platform **never rejects** a price for being "too low/high" (pricing-and-negotiation §6). |
| **Anti-spam** (FR-N-8) | Per-`(actor, thread)` rate limit on `POST .../entries` (Redis token bucket). |
| **Re-negotiation after CONFIRMED** | **Not in MVP** (D-A-NEG-3). Scope changes → a new job or an admin/incident adjustment. The `agreement` table role has no `UPDATE`, so the frozen price is enforced by the database, not just convention. |

---

## 5. Authorization (read/write scoping)

From [authentication-authorization.md](authentication-authorization.md):

| Actor | Can read | Can write |
|-------|----------|-----------|
| Business (job owner) | **all** threads on its job + standing offers | `PROPOSE`/`COUNTER`/`ACCEPT`/`REJECT` on any thread of its job |
| Operator / Group manager | **only** threads where `thread.operator_id = self` or `thread.group_id ∈ self.managed_groups` | offers on its own thread only |
| Group DRIVER (not manager) | own thread if `assignment_mode = DRIVER_ACCEPTS` | offers on own thread if the group allows |
| Recipient (link) | nothing | nothing |
| Operations Officer / Platform Admin | **all** threads on a job (dispute + monitoring — pricing-and-negotiation §7) | may place an `ADMIN` entry only as part of a recorded intervention |

The "sealed" property is exactly the operator row: `WHERE thread.operator_id =
:actor_operator_id OR thread.group_id = ANY(:actor_managed_groups)`.

---

## 6. What the negotiation subsystem emits / consumes

| Emits (outbox) | Consumes |
|----------------|----------|
| `OfferPlaced` → notify counterparty; metrics (counter count, time-to-first-offer) | `JobCancelled` / `JobFailed` → close open threads |
| `OfferAccepted` (one side) | beat tick → `expire_stale_offers` |
| `AgreementReached` → the Job Lifecycle Service already did the CONFIRM inside the same txn; this event is for notifications + metrics (`REQUESTED→CONFIRMED` time, proposed-vs-agreed delta — pilot-strategy §4.3) | |
| `ThreadClosed` / `ThreadSuperseded` → notify the losing operator | |

---

## 7. Immutability guarantees (how FR-N-2 / D-NEG-3 are actually enforced)

1. **`negotiation_entry`**: the table is granted `INSERT, SELECT` only to the app
   role; the service exposes no update/delete; a test asserts an attempted
   `UPDATE`/`DELETE` raises.
2. **`agreement`**: same table-role restriction; `U(job_id)`; created once inside
   the confirming transaction; the agreed price column is never written again.
3. **Corrections**: a mistaken offer is fixed by placing a new
   `COUNTER`/`REJECT` entry — the wrong one stays visible in the history with its
   timestamp, exactly as Phase 0 requires.
4. **Audit**: every entry insert and the confirmation also write an
   `audit_log_entry` (hash-chained), so the negotiation record is independently
   corroborated.
