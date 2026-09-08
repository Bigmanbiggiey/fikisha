# Trust and Safety

Trust, safety, security, authorization, and auditability are **first-class MVP
requirements**. They shape the job lifecycle and user model and are not deferred.

---

## 1. VERIFIED vs TRUSTED

The platform draws a clear line between two concepts:

| | **VERIFIED** | **TRUSTED** |
|---|---|---|
| Question it answers | "Is this party who they claim to be, and are they eligible?" | "Has this party demonstrated reliable behaviour on the platform?" |
| Established by | Documents + checks, reviewed by administrators (optionally assisted by automated checks) | Accumulated successful platform activity over time |
| Nature | Mostly binary per domain, with expiry | Progressive levels |
| Changes when | Documents submitted / approved / rejected / expire | Jobs completed, incidents recorded, ratings received, time elapsed |
| Gates | Whether an operator can be active at all; which vehicle they can use | Which **value band** of jobs an operator may take; extra safeguards |

An operator can be **VERIFIED but low-TRUST** (new joiner) — allowed to work, but
only on lower-value jobs. An operator cannot be **TRUSTED without being
VERIFIED**.

---

## 2. Verification domains

Each is a separate `VerificationRecord` with its own state and, where relevant,
expiry.

| Domain | What it establishes | Evidence (MVP WORKING ASSUMPTION) | Expiry |
|--------|--------------------|----------------------------------|--------|
| **Identity** | The operator is a real, identifiable person | National ID / passport image + selfie/photo match; name + DOB | On document expiry |
| **Licence** | The operator may legally drive the relevant class | Driving licence image; class(es); endorsements | On licence expiry |
| **Vehicle** | The vehicle exists and is roadworthy/registered | Registration/logbook, inspection certificate, insurance certificate, photos of vehicle + plate | On earliest document expiry (esp. insurance) |
| **Vehicle ↔ operator association** | This operator is entitled to use this vehicle | Ownership match, or owner-consent evidence for an authorised driver | Reviewed on change |
| **Operating base / stage / location** | The operator genuinely works from a real base/stage | Founder/administrator local knowledge for the pilot; optional photo / co-sign by base peers | Periodic re-check |
| **Supporting documentation** | Any additional docs a job/vehicle class needs (e.g. goods-in-transit paperwork) | Case-by-case | Case-by-case |
| **Platform history** | Track record on the platform | Derived from completed jobs, incidents, ratings — feeds TRUST, not a document | Continuous |

**Which specific licences, endorsements, certificates, and insurances are
legally required per vehicle class REQUIRES KENYAN PROFESSIONAL VALIDATION.**
Phase 0 does not assert the legal list.

### 2.1 Verification states
`NOT_SUBMITTED → SUBMITTED → IN_REVIEW → VERIFIED | REJECTED`, plus `EXPIRED`
(from VERIFIED when a document lapses) and `INFO_REQUESTED` (reviewer needs more).

### 2.2 Business verification
Lighter: confirm the business is real (trading name, contact person, at least one
confirmed physical location; optional registration identifiers). Higher-value or
higher-risk businesses may get enhanced checks — **OPEN QUESTION** whether MVP
needs business trust tiers; recommend a single verified/unverified flag plus
admin discretion for the pilot.

---

## 3. Progressive operator trust levels

**CONFIRMED DECISION:** new operators do **not** automatically get unrestricted
access to high-value jobs. Access widens progressively.

### 3.1 Level model — CONFIRMED 2026-09-08 (founder-approved; values configurable in `PlatformConfig`; see [decisions.md](decisions.md) D-TRU-6)

| Level | Name | Entry criteria (pilot starting values) | Job value ceiling | Extra |
|-------|------|----------------------------------------|-------------------|-------|
| L0 | Pending | Registered, verification incomplete | Cannot accept jobs | — |
| L1 | Verified | Identity + correct-class licence + ≥1 verified vehicle + verified base. **0 completed jobs is fine.** | **Standard** (≤ KES 50,000) | — |
| L2 | Established | L1 + **≥ 8** completed jobs + **≥ 14 days** active + avg rating **≥ 4.2/5** + **no unresolved** incident + **≤ 1** at-fault incident in last 20 jobs + admin confirms | **Elevated** (≤ KES 250,000) | **DCI Certificate of Good Conduct required** (D-TRU-7) |
| L3 | Trusted | L2 + **≥ 30** completed jobs + **≥ 60 days** active + avg rating **≥ 4.5/5** + **0** unresolved/unremediated at-fault *serious* incidents (loss/damage/misconduct) + **≥ 3** clean Elevated-band jobs + admin confirms | **High** (≤ KES 1,000,000); **Very high** (> KES 1,000,000) only with per-job founder/admin approval | Enhanced verification refresh; current goods-in-transit/carrier's cover |
| — | Restricted | Admin-imposed after an at-fault serious incident, or avg rating **< 3.5** over last 10 jobs | Standard or zero | Remediation plan to exit |

- **Progression is auto-proposed, admin-confirmed** for MVP (guards against
  gaming a thin early dataset).
- **Regression:** serious incidents or a rating drop can lower a level or move
  the operator to Restricted, always with a recorded reason.

### 3.2 Value bands and high-value jobs — CONFIRMED 2026-09-08 (D-TRU-5)

| Band | Declared cargo value (KES) | Min trust | Mandatory safeguards |
|------|---------------------------|-----------|----------------------|
| Standard | ≤ 50,000 | L1 | Standard proof of pickup/delivery |
| Elevated | 50,001 – 250,000 | L2 | Recipient **OTP** + **photo POD** + pickup-side **OTP** (no operator-attested fallback) |
| High | 250,001 – 1,000,000 | L3 | **Admin pre-assignment review**; operator goods-in-transit / carrier's cover re-checked current; two contacts on file |
| Very high | > 1,000,000 | L3 + **per-job founder/admin approval** | Case-by-case; consider requiring the business to arrange its own cover; possible in-transit check-in |

`high_value_threshold` (point where admin review begins) = **KES 250,000**
(configurable). The value used is the **declared cargo value**; agreed price may
also be considered.

The platform must **not** invent legal or insurance guarantees for high-value
cargo (see [legal-scope.md](legal-scope.md) §3.7). If the founder wants any cover
or guarantee, that **REQUIRES KENYAN PROFESSIONAL VALIDATION**.

The platform must **not** invent legal or insurance guarantees for high-value
cargo. If the founder wants any cover or guarantee, that
**REQUIRES KENYAN PROFESSIONAL VALIDATION**.

---

## 4. Chain of custody (safety-critical)

Full detail in [job-lifecycle.md](job-lifecycle.md) transitions and
[domain-model.md](domain-model.md). Summary of the minimum auditable chain:

```
Assignment
  → Operator + specific vehicle identified and recorded
  → Arrival at pickup           (timestamp, actor, location attempt)
  → Goods handed over           (description/condition note, optional photos)
  → Pickup / custody confirmation (proof: OTP / signature / photo from pickup side)
  → In transit
  → Arrival at destination      (timestamp, actor, location attempt)
  → Recipient verification      (name + OTP / signature / photo)
  → Delivery confirmation       (proof of delivery captured)
  → Completion
```

### 4.1 Requirements
- Each step records: **who** (actor id + role), **when** (server timestamp;
  any client time stored as "reported"), **where** (device geolocation where
  available and permitted; otherwise the named location / "not captured"),
  **what evidence** (media references + integrity hash), **confirmation method**.
- Chain-of-custody entries are **append-only and immutable**. Errors are
  corrected by a new entry with a reason, not by editing.
- Evidence media is stored access-controlled and encrypted at rest; retention
  follows the configured window (see
  [non-functional-requirements.md](non-functional-requirements.md)).
- The complete chain for a job is viewable by: the business (its own job), the
  assigned operator (its own job), and administrators.

---

## 5. Authorization model

- **Role-based** (Business / Operator / Admin sub-roles) **plus attribute-based**
  gates (verification state, trust level, suspension state, job ownership).
- Every state-changing action checks authorization server-side. Client-side
  hiding of controls is not a security control.
- **Least privilege** for admin sub-roles (see
  [users-and-roles.md](users-and-roles.md)).
- Sensitive personal data (ID numbers, licence images, payout details) is
  accessible only to the verification sub-role and only when needed; access is
  itself audit-logged.

---

## 6. Account safety actions

| Action | Who | Effect | Recorded |
|--------|-----|--------|----------|
| Suspend | Platform admin | Account cannot log in / act | Reason, duration, actor |
| Restrict | Ops / platform admin | Reduced capability (e.g. trust level lowered, no new jobs) | Reason, actor |
| Force-intervene in a job | Ops admin | Reassign / cancel / force allowed transition | Reason, actor, before/after |
| Flag for review | Any admin / auto from incident pattern | Adds to a review queue | Trigger |
| Offboard | Platform admin | Terminate relationship; retain records per retention policy | Reason, actor |

---

## 7. Abuse / risk scenarios to design against (pilot to measure frequency)

- Operator sends a different (unverified) vehicle than the one assigned →
  mitigation: assignment names a specific vehicle; pickup step asks the pickup
  side to confirm the vehicle/plate.
- Identity sharing (verified operator, someone else drives) → mitigation:
  identity check at onboarding + photo on file visible to pickup contact;
  incident path for "not the assigned operator".
- Inflated or deflated declared cargo value → mitigation: value sanity flags;
  high-value gating; declared value is the requester's responsibility and is
  recorded.
- Collusive fake ratings → mitigation: ratings only from completed jobs;
  admin confirmation of trust progression; watch repeat-pair patterns in pilot.
- Off-platform diversion to avoid commission → see
  [business-model.md](business-model.md) §8.
- Data exposure of operator IDs → mitigation: strict access control + audit on
  document access.

---

## 8. Status summary

| Item | Category |
|------|----------|
| VERIFIED vs TRUSTED distinction | CONFIRMED DECISION |
| Per-domain verification records with expiry | CONFIRMED DECISION |
| Progressive trust levels; no auto unrestricted high-value access | CONFIRMED DECISION |
| High-value jobs gated: threshold KES 250k + trust L3 + admin pre-assignment review + cover re-check | CONFIRMED 2026-09-08 (D-TRU-5) |
| Append-only, immutable chain of custody with actor/time/location/evidence | CONFIRMED DECISION |
| Server-side role + attribute authorization on every action | CONFIRMED DECISION |
| Trust levels, thresholds, value bands (L1/L2/L3/Restricted; bands 50k/250k/1M; L2 8 jobs/14d/4.2★; L3 30 jobs/60d/4.5★/3 clean Elevated) | CONFIRMED 2026-09-08 (D-TRU-6) — values configurable, tune in pilot |
| DCI Certificate of Good Conduct mandatory before L2/Elevated | CONFIRMED 2026-09-08 (D-TRU-7) |
| Admin-confirmed (not automatic) trust progression for MVP | CONFIRMED 2026-09-08 (part of D-TRU-6) |
| Business trust tiers | OPEN QUESTION — single verified flag recommended for MVP |
| Base/stage verification method for the pilot | WORKING ASSUMPTION — founder/admin local knowledge |
| Legally required licences / certificates / insurance per vehicle class | REQUIRES KENYAN PROFESSIONAL VALIDATION |
| Any platform-provided guarantee or cover | REQUIRES KENYAN PROFESSIONAL VALIDATION — not assumed |
