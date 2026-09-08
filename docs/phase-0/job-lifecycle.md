# Job Lifecycle

The JOB is the fundamental transaction. Its status must move only through
**explicitly permitted transitions**. Arbitrary status changes are not allowed;
every transition is guarded by role, precondition, and — where relevant — trust
level and verification state, and every transition is written to the audit log
and (where it concerns the goods) to the chain of custody.

---

## 1. States

### 1.1 Primary (happy path) states

| State | Meaning | Goods in operator custody? |
|-------|---------|----------------------------|
| `DRAFT` | Business is preparing the job; not visible to operators | No |
| `REQUESTED` | Published; visible to eligible operators; awaiting offers/acceptance | No |
| `NEGOTIATING` | At least one price offer/counter exists; parties are agreeing terms | No |
| `CONFIRMED` | Both parties agreed a price; job is committed; operator not yet attached (or attached in same step) | No |
| `ASSIGNED` | A specific operator **and** vehicle are attached to the job | No |
| `AT_PICKUP` | Operator has arrived at the pickup location | No (arrived, not yet handed over) |
| `PICKED_UP` | Goods handed over; operator has confirmed custody; proof-of-pickup recorded | **Yes** |
| `IN_TRANSIT` | Operator is moving the goods to the destination | **Yes** |
| `AT_DESTINATION` | Operator has arrived at the destination | **Yes** |
| `DELIVERED` | Goods handed to recipient; recipient verification + proof of delivery recorded | No (handed over) |
| `COMPLETED` | Delivery accepted; ratings window open; commission becomes due; job closed | No |

### 1.2 Interruption / terminal states

| State | Meaning |
|-------|---------|
| `CANCELLED` | Job ended before custody by an allowed party or admin; reason recorded; no commission (cancellation-fee policy is an open question — see business-model.md) |
| `FAILED` | Job could not be completed (e.g. no operator found before expiry, operator abandoned before custody, pickup impossible); reason recorded |
| `DISPUTED` | An incident/dispute has been raised that blocks normal progression; job is frozen pending resolution; resolution routes it to a terminal state |

---

## 2. Allowed transitions

`→` = allowed. Anything not listed is **forbidden** and must be rejected by the
state machine.

### 2.1 Pre-custody

| From | To | Trigger / actor | Key preconditions |
|------|----|-----------------|-------------------|
| `DRAFT` | `REQUESTED` | Business publishes | Required fields complete; pickup + destination + vehicle requirement + proposed price set |
| `DRAFT` | `CANCELLED` | Business / admin | — |
| `REQUESTED` | `NEGOTIATING` | Business or operator places an offer/counter | Operator is eligible (vehicle, area, trust) |
| `REQUESTED` | `CONFIRMED` | Operator accepts the business's proposed price, **or** business accepts an operator's proposal at posted price | Mutual agreement recorded; operator eligible |
| `REQUESTED` | `CANCELLED` | Business / admin | — |
| `REQUESTED` | `FAILED` | System / admin | Job expired with no acceptable offer |
| `NEGOTIATING` | `NEGOTIATING` | Either party counters | Offer recorded, appended to history |
| `NEGOTIATING` | `CONFIRMED` | Either party accepts the other's current offer | Both-sides agreement recorded; agreed price frozen |
| `NEGOTIATING` | `CANCELLED` | Business / admin | — |
| `NEGOTIATING` | `FAILED` | System / admin / either party walks away | Negotiation expired or explicitly ended without agreement |
| `CONFIRMED` | `ASSIGNED` | Operator attaches a specific vehicle (or admin assigns) | Vehicle verified + capacity/type match; operator trust level ≥ job requirement; may be the same action as the accept that produced CONFIRMED |
| `CONFIRMED` | `CANCELLED` | Business / operator / admin | Cancellation policy applies |
| `ASSIGNED` | `AT_PICKUP` | Operator marks arrival | Location capture attempted; timestamp + actor recorded |
| `ASSIGNED` | `CANCELLED` | Business / operator / admin | Cancellation policy applies |
| `ASSIGNED` | `FAILED` | Admin | Operator abandoned; no replacement |
| `ASSIGNED` | `DISPUTED` | Any party / admin | Incident raised pre-pickup (e.g. wrong vehicle sent) |

### 2.2 Custody and delivery

| From | To | Trigger / actor | Key preconditions |
|------|----|-----------------|-------------------|
| `AT_PICKUP` | `PICKED_UP` | Operator confirms custody | **Proof-of-pickup: mandatory pickup-side OTP** to the person releasing the goods (CONFIRMED, D-CUS-2). *Standard band only* fallback: operator photo of goods + pickup-contact name → custody entry flagged "operator-attested, unverified" and job capped at Standard band unless business later confirms in-app. **Elevated band and above: pickup-side OTP (or in-app business confirmation) required, no fallback.** Cargo-condition note/photos optional. |
| `AT_PICKUP` | `CANCELLED` | Business / operator / admin | Only before custody is confirmed |
| `AT_PICKUP` | `FAILED` | Operator / admin | Goods not available / not as described / pickup impossible; reason + evidence |
| `AT_PICKUP` | `DISPUTED` | Any party / admin | e.g. cargo materially different from job; wrong pickup location |
| `PICKED_UP` | `IN_TRANSIT` | Operator starts moving | — |
| `PICKED_UP` | `DISPUTED` | Any party / admin | e.g. damage noticed at handover |
| `PICKED_UP` | `FAILED` | Admin | Rare; abandoned immediately after custody — routes to incident |
| `IN_TRANSIT` | `AT_DESTINATION` | Operator marks arrival | Location capture attempted |
| `IN_TRANSIT` | `DISPUTED` | Any party / admin | Accident, breakdown with loss, theft, major delay, misconduct |
| `IN_TRANSIT` | `FAILED` | Admin | Delivery became impossible; goods status captured via incident |
| `AT_DESTINATION` | `DELIVERED` | Operator completes handover | Recipient verification + proof of delivery recorded (name + OTP/signature/photo) |
| `AT_DESTINATION` | `DISPUTED` | Any party / admin | Recipient refuses goods; wrong recipient; damage on arrival |
| `AT_DESTINATION` | `FAILED` | Admin | Recipient unreachable/absent and no fallback; goods return handled as incident |
| `DELIVERED` | `COMPLETED` | Business/recipient confirms acceptance, **or** auto-complete after a configurable window with no objection | No open dispute |
| `DELIVERED` | `DISPUTED` | Business / recipient / operator / admin | Objection raised within the acceptance window |

### 2.3 Dispute resolution outcomes

| From | To | Trigger / actor | Notes |
|------|----|-----------------|-------|
| `DISPUTED` | `COMPLETED` | Admin resolution | Job deemed successfully delivered (possibly with adjustments recorded) |
| `DISPUTED` | `FAILED` | Admin resolution | Job deemed not completed |
| `DISPUTED` | `CANCELLED` | Admin resolution | Job unwound by agreement |
| `DISPUTED` | *(prior state)* | Admin resolution | **OPEN QUESTION:** allow resume to the pre-dispute state if the issue is cleared and the job can continue (e.g. breakdown fixed, replacement vehicle). Recommended: yes, admin-only, logged. |

### 2.4 Post-completion disputes

- `COMPLETED` is the lifecycle terminal for the happy path.
- **CONFIRMED 2026-09-08 (D-JOB-5):** the **post-completion dispute window** is
  **72h** for all bands and **7 days** for High/Very-high bands and latent-risk
  cargo categories (electronics, packaged goods, perishables), during which
  `COMPLETED → DISPUTED` is permitted (latent damage, shortage discovered later).
  After the window, an incident may still be recorded for the record and
  reputation but does **not** reopen the job state or commission. Configurable.
- **OPEN QUESTION for founder:** length of the window; whether it applies to all
  job/cargo types or only above a value threshold.

---

## 3. State diagram (textual)

```
DRAFT ──▶ REQUESTED ──▶ NEGOTIATING ──▶ CONFIRMED ──▶ ASSIGNED ──▶ AT_PICKUP ──▶ PICKED_UP
  │           │  │  └──────────────┐        │            │            │             │
  │           │  └──▶ CONFIRMED    │        │            │            │             ▼
  ▼           ▼                    ▼        ▼            ▼            ▼         IN_TRANSIT
CANCELLED   FAILED             FAILED   CANCELLED   CANCELLED     FAILED           │
                                                    /FAILED     /CANCELLED         ▼
                                                                /DISPUTED    AT_DESTINATION
                                                                                   │
   PICKED_UP ──▶ IN_TRANSIT ──▶ AT_DESTINATION ──▶ DELIVERED ──▶ COMPLETED         │
       │             │               │                 │             │             ▼
       ▼             ▼               ▼                 ▼             ▼          DELIVERED
   DISPUTED      DISPUTED        DISPUTED          DISPUTED     DISPUTED (window)
       │
       └──▶ (resolution) ──▶ COMPLETED | FAILED | CANCELLED | resume prior state
```

(The ASCII is indicative; the authoritative rules are the tables in §2.)

---

## 4. Enforcement requirements

- **FR:** The system MUST implement job status as a finite state machine.
  A transition request naming a `(from, to)` pair not in the allowed set MUST be
  rejected with a clear error and no side effects.
- **FR:** Each transition MUST check its preconditions (role, eligibility, trust,
  verification, required evidence present) before applying.
- **FR:** Each successful transition MUST append an audit entry
  (actor, timestamp, from, to, reason/notes) and, for custody-relevant
  transitions, a chain-of-custody entry (see
  [trust-and-safety.md](trust-and-safety.md) and
  [domain-model.md](domain-model.md)).
- **FR:** Concurrent transition attempts MUST be serialised so the job cannot
  branch (optimistic locking / version check).
- **FR:** Only an administrator may perform a forced transition outside the
  normal actor rules, and only to states reachable per §2, always with a
  recorded reason.
- **FR:** Timestamps are server-authoritative; client-supplied times are stored
  as "reported" values only.

---

## 5. Timeouts and automation (configurable)

| Timer | Effect | Default (WORKING ASSUMPTION) |
|-------|--------|------------------------------|
| Request expiry | `REQUESTED`/`NEGOTIATING` → `FAILED` if no agreement | Job's pickup time, or 24h, whichever first *(range, tune in pilot)* |
| Offer expiry | An unanswered offer lapses (does not change job state) | 1–4h *(range, tune in pilot)* |
| Delivery acceptance | `DELIVERED` → `COMPLETED` if no objection | **CONFIRMED 2026-09-08 (D-JOB-5): 24h Standard/Elevated · 48h High/Very-high** |
| Post-completion dispute window | `COMPLETED` → `DISPUTED` allowed | **CONFIRMED 2026-09-08 (D-JOB-5): 72h all bands · 7 days High/Very-high & latent-risk cargo (electronics, packaged goods, perishables)** |
| Stale assignment | Alert admin if `ASSIGNED` with no `AT_PICKUP` past pickup time | +30–60 min *(range, tune in pilot)* |

All values are platform configuration. The delivery-acceptance and
post-completion windows are founder-approved (D-JOB-5); the rest remain ranges to
tune in the pilot.

---

## 6. Status summary

| Item | Category |
|------|----------|
| The 11 primary + 3 interruption states from the brief | CONFIRMED DECISION |
| Transitions enforced by a state machine, no arbitrary changes | CONFIRMED DECISION |
| Exact allowed-transition table above | WORKING ASSUMPTION (refined from the brief; needs founder review) |
| Resume-from-DISPUTED to prior state | OPEN QUESTION — recommend allow, admin-only |
| Delivery-acceptance & post-completion dispute windows (24h/48h; 72h/7d) | CONFIRMED 2026-09-08 (D-JOB-5) |
| Other timeout default values | WORKING ASSUMPTION — tune in pilot |
| Proof-of-pickup: mandatory pickup-side OTP; operator-attested photo fallback Standard band only; none at Elevated+ | CONFIRMED 2026-09-08 (D-CUS-2) |
