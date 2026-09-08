# Chain of Custody

Implements Phase 0 `trust-and-safety.md` §4, `job-lifecycle.md`, and
`FR-C-1..C-9`, `D-CUS-2`. This is a **safety-critical subsystem**: an
append-only, actor-attributed, timestamped record of the goods from assignment
to completion.

---

## 1. What it is (and what it is not)

- **The chain of custody is the `is_custody = true` subset of `job_event`** (see
  [database-design.md](database-design.md) §4.7 and
  [phase-1-decisions.md](phase-1-decisions.md) ADR-009). It is exposed as the
  `chain_of_custody` view, ordered by `job_event.seq`.
- It is **not** a separate table, **not** continuous GPS, and **not** editable.
- The wider `job_timeline` also carries negotiation references, admin actions,
  and system events; the **custody subset** is the legally significant part
  (assignment → completion) that the business, the assigned operator, and admins
  read (FR-J-10).

---

## 2. Custody event types and what each records

| `job_event.type` | Written when | Actor | Location | Evidence / confirmation |
|------------------|--------------|-------|----------|-------------------------|
| `OPERATOR_ASSIGNED` | `CONFIRMED → ASSIGNED` | assigner (operator / group manager / admin) | — | `assignment_id` |
| `DRIVER_CONFIRMED` | same txn as ASSIGNED | system | — | `assigned_driver_profile_id` |
| `VEHICLE_CONFIRMED` | same txn as ASSIGNED | system | — | `vehicle_id` + plate + operator photo ref (so the pickup contact can identify who arrives) |
| `ARRIVED_AT_PICKUP` | `ASSIGNED → AT_PICKUP` | assigned driver | **attempted** (`getCurrentPosition`, one reading) → `geo` + `geo_accuracy_m`, or `geo_state = NOT_CAPTURED` | server time; `reported_time` if the client was offline when it happened |
| `PICKUP_OTP_ISSUED` | on `ARRIVED_AT_PICKUP` | system | — | `pickup_otp_challenge` id; `sent_to_phone` (the pickup contact) |
| `PICKUP_OTP_CONFIRMED` | `AT_PICKUP → PICKED_UP` (verified path) | assigned driver (submits the code the pickup contact reads out) | attempted | `confirmation_method = OTP`; `otp_verified = true` |
| `PICKUP_OPERATOR_ATTESTED` | `AT_PICKUP → PICKED_UP` (Standard-band fallback only) | assigned driver | attempted | `confirmation_method = PHOTO`; goods photo evidence id + pickup-contact name; **`attestation = OPERATOR_ATTESTED_UNVERIFIED`** → job capped at STANDARD |
| `GOODS_RECEIVED` | same txn as PICKED_UP | assigned driver | — | optional cargo-condition note + photos; `ProofOfPickup` row |
| `IN_TRANSIT` | `PICKED_UP → IN_TRANSIT` | assigned driver | — | — |
| `ARRIVED_AT_DESTINATION` | `IN_TRANSIT → AT_DESTINATION` | assigned driver | **attempted** → `geo` | — |
| `RECIPIENT_OTP_ISSUED` | on `ARRIVED_AT_DESTINATION` | system | — | `recipient_otp_challenge` id; sent to `job.recipient_phone` |
| `RECIPIENT_VERIFIED` | `AT_DESTINATION → DELIVERED` | assigned driver **or** recipient (via link) | attempted | `confirmation_method ∈ {OTP, SIGNATURE, PHOTO}`; Elevated+ requires **OTP + photo** (D-TRU-5) |
| `DELIVERY_CONFIRMED` | same txn as DELIVERED | driver / recipient | — | `ProofOfDelivery` row (name + methods + evidence) |
| `COMPLETED` | `DELIVERED → COMPLETED` (explicit or auto) | business / recipient / scheduler | — | — |
| `NOTE` | any time, by an admin or a participant, to **correct** a prior custody row | actor | — | `corrects_event_id` → the row being corrected (the original stays) |

Every custody row also carries `source_meta` (IP, device, channel) and
`config_version_id`. Server timestamps are authoritative; a client-reported time
(e.g. from the PWA offline queue) is stored **separately** in `reported_time`
(NFR-AUD-4).

---

## 3. Sequence — a clean Elevated-band job

```mermaid
sequenceDiagram
    autonumber
    participant D as Driver (PWA)
    participant API
    participant FSM as Job Lifecycle Service
    participant CUS as Custody Service
    participant N as Notifications
    participant PC as Pickup contact (business)
    participant R as Recipient (link)

    Note over API: job is CONFIRMED, then ASSIGNED (driver + vehicle recorded:<br/>OPERATOR_ASSIGNED, DRIVER_CONFIRMED, VEHICLE_CONFIRMED)

    D->>API: POST /jobs/{id}/transitions {to: AT_PICKUP, geo?}
    API->>FSM: transition(AT_PICKUP)
    FSM->>CUS: record ARRIVED_AT_PICKUP (+geo or NOT_CAPTURED)
    FSM->>N: JobArrivedAtPickup -> issue pickup OTP
    N->>PC: SMS/WhatsApp: "Fikisha driver <name>, plate <X>, code 4821"
    N-->>API: PICKUP_OTP_ISSUED custody row

    D->>PC: shows up; PC reads the code aloud
    D->>API: POST /jobs/{id}/transitions {to: PICKED_UP, otp: "4821", condition_note?, photos?}
    API->>FSM: transition(PICKED_UP)
    FSM->>CUS: guard PickupSideOtpVerifiedOrStandardFallback -> OTP valid ✓<br/>(Elevated band: NO fallback allowed)
    FSM->>CUS: write ProofOfPickup, PICKUP_OTP_CONFIRMED, GOODS_RECEIVED (one txn)
    FSM->>N: JobPickedUp -> notify business

    D->>API: POST /jobs/{id}/transitions {to: IN_TRANSIT}
    D->>API: POST /jobs/{id}/transitions {to: AT_DESTINATION, geo?}
    API->>FSM: ... ARRIVED_AT_DESTINATION (+geo)
    FSM->>N: issue recipient OTP + (re)issue recipient link
    N->>R: SMS/WhatsApp: link + "code 7390"

    alt recipient confirms via link
        R->>API: GET /r/{token} -> scoped delivery view
        R->>API: POST /r/{token}/confirm {name, otp: "7390", photo}
        API->>FSM: transition(DELIVERED) as actor_role=RECIPIENT
    else driver records POD on the doorstep
        D->>API: POST /jobs/{id}/transitions {to: DELIVERED, recipient_name, otp: "7390", photo}
    end
    FSM->>CUS: write ProofOfDelivery, RECIPIENT_VERIFIED, DELIVERY_CONFIRMED (one txn)
    FSM->>N: JobDelivered -> notify business; start acceptance timer (24h Elevated)

    Note over FSM: business confirms OR scheduler auto-completes after the window
    FSM->>CUS: write COMPLETED custody row
    FSM->>N: JobCompleted -> ledger accrual, trust re-eval, ratings window
```

---

## 4. The mandatory pickup-side OTP (D-CUS-2)

The single most important custody control. Enforced by the guard
`PickupSideOtpVerifiedOrStandardFallback` on `AT_PICKUP → PICKED_UP`:

| Band | Accepted proof of pickup | Fallback if OTP undeliverable/unusable |
|------|--------------------------|---------------------------------------|
| `STANDARD` | pickup-contact OTP (default) **or** the business user confirming in-app | operator captures **goods photo + pickup-contact name** → `PICKUP_OPERATOR_ATTESTED`, `attestation = OPERATOR_ATTESTED_UNVERIFIED`; **the job is capped at the STANDARD band** and flagged in the timeline as unverified, unless the business later confirms in-app (which flips it to `VERIFIED`) |
| `ELEVATED` / `HIGH` / `VERY_HIGH` | pickup-contact OTP **or** in-app business confirmation — **required, no fallback** | none — the transition is refused (`422 pickup_confirmation_required`) |

- The OTP is generated server-side, 6 digits, hashed at rest, 5-min TTL, sent to
  `job.pickup_location.contact_phone` (or the business's on-site contact). The
  **driver** enters the code the contact reads out — so a driver cannot
  self-confirm, and the contact does not need the app.
- A fresh OTP can be re-issued (rate-limited) if the first is not received.
- Every issuance and every verification attempt is a custody row +
  `audit_log_entry`.

---

## 5. Location privacy (brief §16, NFR-PRIV-4)

**Event-based location evidence only. No continuous GPS. No tracking.**

| Question | Answer |
|----------|--------|
| **What is collected** | A **single** `getCurrentPosition` reading (`lat`, `lng`, `accuracy_m`) at four moments: `ARRIVED_AT_PICKUP`, `PICKED_UP` (implicit, same place), `ARRIVED_AT_DESTINATION`, `DELIVERED`. Optionally one reading per prompted in-transit check-in for `HIGH`/`VERY_HIGH` jobs (FR-C-9). Nothing between events. |
| **When** | Only at the moment the driver marks the custody step, and only if the browser grants permission for that call. |
| **Why** | To corroborate that the operator was where the job says, for dispute evidence and pilot metrics (on-time-at-pickup, coverage). It is **not** used to surveil the operator's day. |
| **If permission is denied / no signal** | `geo_state = NOT_CAPTURED` — an **acceptable recorded value** (NFR-PRIV-4). The custody step still succeeds; the OTP, not the location, is the gating proof. |
| **Who can see it** | The job's business, the assigned operator/driver, and administrators (FR-J-10). **Never** the recipient. Never other operators or businesses. |
| **How it is protected** | `MEDIUM`-PII; DB at rest; row scoping + RLS candidate table. |
| **Retention** | Raw `lat`/`lng` on custody rows are **coarsened to the zone centroid after 12 months** (`geo_state = COARSENED`) by the retention sweep; the event summary ("arrived at pickup 14:05, near <zone>") is kept with the job record for 7 years (legal-scope §7 — REQUIRES VALIDATION). |
| **Consent** | The Privacy Notice and onboarding consent cover custody-event location capture (NFR-PRIV-3 — REQUIRES VALIDATION). The browser permission prompt is a second, per-use gate. |

The PWA requests geolocation **lazily** — only when the driver taps a custody
action — never on app load, and never in the background.

---

## 6. Append-only guarantees (FR-C-6)

1. `job_event` table role has `INSERT, SELECT` only.
2. The Custody Service has no update/delete path.
3. A correction is a new `NOTE` row with `corrects_event_id` pointing at the
   original; the original remains visible in the `chain_of_custody` view with a
   "superseded by note" marker in the UI.
4. Each custody row's `evidence_ids` reference `evidence_object`s whose `sha256`
   is stored on the row (`content_hashes`) — a swapped file is detectable
   (NFR-INT-4).
5. Every custody write also writes a hash-chained `audit_log_entry`.
6. The per-job `seq` is assigned inside the job's `FOR UPDATE` transaction, so the
   order is total and gap-analysis reveals a missing step.

---

## 7. Completeness indicator (FR-C-8, SHOULD)

`CustodyService.completeness(job)` returns, for the job's band, which expected
custody rows are present and which are missing (e.g. "arrived at pickup ✓,
pickup OTP ✓, in transit ✓, arrived at destination ✗"). The business and admin
job views render it; the pilot metrics record per-job custody completeness
(pilot-strategy §4.8).

---

## 8. Events

| Emits | Consumers |
|-------|-----------|
| `ArrivedAtPickup` | Notifications (issue pickup OTP to the pickup contact); metrics (CONFIRMED→AT_PICKUP time) |
| `CustodyConfirmed` (PICKED_UP) | Notifications (business); metrics (on-time-at-pickup); if `OPERATOR_ATTESTED_UNVERIFIED` → flag for the business to confirm |
| `InTransit` | metrics |
| `ArrivedAtDestination` | Recipients (issue/refresh the delivery link + OTP); Notifications; metrics |
| `ProofOfDeliveryRecorded` | Jobs (feeds `DELIVERED`); metrics (POD method chosen) |

| Consumes | For |
|----------|-----|
| `JobAssigned` | pre-create the custody context; write `OPERATOR_ASSIGNED` / `DRIVER_CONFIRMED` / `VEHICLE_CONFIRMED` rows |
| `JobDisputed` | freeze — reject further custody transitions until resolved |
