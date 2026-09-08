# Domain Model

**Conceptual model only.** This is not a database schema, an ORM design, or a
migration plan. It names the entities, their relationships, and the key
enumerations so Phase 1 can design the actual data layer. Field lists are
indicative.

The **JOB** is the fundamental transaction and the aggregate around which most of
the model is organised.

---

## 1. Entity map (text)

```
User ──< BusinessAccount ──< BusinessLocation
User ──< OperatorProfile ──< Vehicle
                         └──< OperatingBase (many-to-many via BaseMembership)
                         └──< ServiceArea
                         └──  TrustLevelState
OperatorGroup ──< GroupMembership >── OperatorProfile   (role: OWNER|MANAGER|DRIVER)
OperatorGroup ──< Vehicle            (group-owned; Vehicle.owner = OperatorProfile | OperatorGroup)
OperatorGroup ──< OperatingBase (via BaseMembership) ──  GroupStandingState
User ──  AdminProfile (with AdminRole)

BusinessAccount ──< Job
Job ── pickup: JobLocation        (from a BusinessLocation or ad-hoc)
Job ── destination: JobLocation   (+ recipient contact)
Job ── CargoDetails
Job ── VehicleRequirement
Job ──< NegotiationThread ──< NegotiationEntry
Job ──  Agreement (0..1, created on CONFIRMED)
Job ──  Assignment (0..1)  ── (OperatorProfile | OperatorGroup+assigned OperatorProfile) + Vehicle
Job ──< ChainOfCustodyEntry
Job ──  ProofOfPickup (0..1)
Job ──  ProofOfDelivery (0..1)
Job ──  RecipientAccessLink (0..1, scoped, time-limited, no account)
Job ──< Incident ──< Evidence        (Incident.reported_by may be RECIPIENT_LINK)
                 └──< Statement
Job ──  Dispute (0..1) ──  Resolution (0..1)
Job ──< Rating (0..3)   (business→operator/driver, operator→business, +group aggregate)
Job ──  CommissionRecord (0..1, created on COMPLETED; payee = OperatorProfile | OperatorGroup)
Job ──< JobStatusEvent   (audit of every transition)

VerificationRecord ── subject: (OperatorProfile | Vehicle | OperatingBase | BusinessAccount | OperatorGroup) + domain
AuditLogEntry ── actor + action + entity (covers ALL entities)
PlatformConfig ── singleton, versioned
Notification ── recipient + job/event + channel (IN_APP | SMS | WHATSAPP)
```

---

## 2. Core entities

### 2.1 User
Base account holder.
`id, phone (unique, primary identifier), email?, display_name, created_at,
status (ACTIVE | SUSPENDED | OFFBOARDED), auth_method, last_login_at`.
A User may have one or more of: `BusinessAccount`, `OperatorProfile`,
`AdminProfile`. A single job may never have the same User as both requester and
assigned operator.

### 2.2 BusinessAccount
`id, user_id (owner), trading_name, category, contact_persons[], registration_ids?
(e.g. KRA PIN — collection subject to validated privacy basis),
verification_status (UNVERIFIED | VERIFIED), standing (GOOD | RESTRICTED),
created_at`.
Members: `BusinessMembership(user_id, role: OWNER | DISPATCHER | VIEWER)` —
SHOULD for MVP, MAY be single-user.

### 2.3 BusinessLocation
`id, business_id, label, type (MAIN | BRANCH | WAREHOUSE | STORE | PICKUP_POINT),
address_text, geo (lat,lng), zone, contact_person, contact_phone, hours,
access_notes, active, created_at`.
Exactly one `MAIN` per business.

### 2.4 OperatorProfile
`id, user_id, full_name, photo_ref, phones[], payout_number (access-controlled),
trust_level (see 2.13), availability (AVAILABLE | BUSY | UNAVAILABLE),
reputation_summary (avg_rating, completed_jobs, incident_counts),
good_conduct_cert (ref + expiry), group_id? (if a member of an OperatorGroup),
status (PENDING | ACTIVE | RESTRICTED | SUSPENDED | OFFBOARDED), created_at`.

### 2.4a OperatorGroup  *(CONFIRMED in MVP — D-OPR-GRP-1)*
`id, name, type (YARD_OWNER | FLEET | SACCO | PARTNERSHIP), primary_contact_user_id,
payout_number (access-controlled), base_ids[] (via BaseMembership),
standing (GOOD | RESTRICTED | SUSPENDED), aggregate_reputation
(avg_rating, completed_jobs, incident_counts), assignment_mode
(MANAGER_ASSIGNS | DRIVER_ACCEPTS), verification_status, created_at`.

`GroupMembership(group_id, operator_profile_id, role (OWNER | MANAGER | DRIVER),
since, status (ACTIVE | INACTIVE))`.

Rules: every member `DRIVER` is a fully verified `OperatorProfile` in their own
right (identity, licence class, Certificate of Good Conduct); every group vehicle
is individually verified. A group `Job` `Assignment` names a specific member
driver + a specific group vehicle. Value-band gating (2.13 / job) uses the
**assigned driver's** `trust_level`; the group's `standing` is an independent
restrict/suspend lever. `CommissionRecord.payee` = the group. Out of MVP:
payroll, scheduling, inter-group transfers.

### 2.5 Vehicle
`id, owner_kind (OPERATOR | GROUP), owner_id (OperatorProfile.id | OperatorGroup.id),
type (see 2.15), sub_descriptor?, plate, payload_kg,
volume_m3? / dims_lwh?, feature_tags[] (TAIL_LIFT, REFRIGERATED, COVERED, OPEN,
CRANE_HIAB, CATTLE_BODY, ...), documents[] (ref + kind + expiry),
heavy_class_compliance? (ntsa_operator_licence, speed_limiter, telematics,
inspection, insurance — refs + expiry, for tare > ~3,048 kg),
ownership (OWNED | AUTHORISED_DRIVER), association_evidence_ref?,
verification_status, state (ACTIVE | INACTIVE | UNDER_REPAIR), created_at`.

### 2.6 OperatingBase
`id, name, type (STAGE | BASE | YARD | WAITING_AREA), geo, zone, landmark?,
photo_ref?, verification_status, created_at`.
`BaseMembership(base_id, operator_id, role?, since)` — many operators per base
(a stage), many bases per operator.

### 2.7 ServiceArea
`id, operator_id, zone_name (from PlatformConfig zones), max_distance_km_from_base?,
corridor? (origin_zone, destination_zone for long-haul), active`.

### 2.8 Job  *(aggregate root)*
Indicative fields, aligned to the founder brief:

| Field | Notes |
|-------|-------|
| `id` | |
| `business_id`, `created_by_user_id` | Requester |
| `status` | One of the lifecycle states (see [job-lifecycle.md](job-lifecycle.md)) |
| `pickup` → JobLocation | From a BusinessLocation or ad-hoc; geo + contact |
| `destination` → JobLocation | Address + geo + `recipient_name` + `recipient_phone` |
| `cargo` → CargoDetails | description, category, est_weight_kg, dims?, declared_value, handling_flags[] |
| `vehicle_requirement` → VehicleRequirement | required_type(s), min_payload_kg, min_volume?, required_features[] |
| `pickup_datetime` | Requested pickup window/time |
| `delivery_requirements` | Free text + flags (e.g. must-deliver-by, fragile, cold-chain) |
| `proposed_price` | Business's opening price (KES minor units) |
| `is_high_value` | Derived from `declared_value` / agreed price vs. PlatformConfig threshold |
| `required_trust_level` | Derived from `is_high_value` / value band |
| `agreement_id?` | Set on CONFIRMED |
| `assignment_id?` | Set on ASSIGNED |
| `distance_km?` | Computed pickup→destination for metrics |
| `created_at`, `published_at?`, `confirmed_at?`, `completed_at?` | |
| `cancellation` / `failure` reason refs | When terminal via those states |
| `dispute_id?` | When a dispute exists |

Derived collections: negotiation threads, chain-of-custody entries, incidents,
ratings, status events, commission record.

### 2.9 JobLocation
`type (PICKUP | DESTINATION), source (BUSINESS_LOCATION:<id> | AD_HOC),
address_text, geo, contact_name, contact_phone, notes`.

### 2.10 CargoDetails
`description, category (see 2.16), est_weight_kg, dims_lwh?, declared_value_kes,
handling_flags[] (FRAGILE, PERISHABLE, HAZARDOUS?, HIGH_VALUE, LIVESTOCK,
BULK, LIQUID, ...)`.
Note: HAZARDOUS handling and any dangerous-goods rules
**REQUIRE KENYAN PROFESSIONAL VALIDATION**; MVP MAY simply flag and exclude such
cargo from the pilot.

### 2.11 VehicleRequirement
`required_types[] (one or more of the vehicle type enum), min_payload_kg,
min_volume_m3?, required_features[], notes`.

### 2.12 NegotiationThread / NegotiationEntry
- `NegotiationThread(id, job_id, operator_id, status: ACTIVE | SUPERSEDED |
  CLOSED, opened_at)`
- `NegotiationEntry(id, thread_id, job_id, actor_user_id, actor_role
  (BUSINESS | OPERATOR | ADMIN), type (PROPOSE | COUNTER | ACCEPT | REJECT),
  amount_kes?, note?, in_response_to?, created_at (server), status (ACTIVE |
  SUPERSEDED | EXPIRED))`.
- **Append-only. Never updated or deleted.** (FR-N-2)

### 2.13 Agreement
`job_id, operator_party (OPERATOR:<id> | GROUP:<id>), agreed_price_kes,
accepting_entry_ids[] (one from each side), agreed_at, terms_note,
version (for any admin-recorded adjustment)`.
Created once on CONFIRMED; frozen (FR-N-5).

### 2.14 Assignment
`job_id, operator_party (OPERATOR:<id> | GROUP:<id>), assigned_driver_profile_id
(the individual in custody — equals the operator for a solo op; a member DRIVER
for a group), vehicle_id, assigned_by (SELF | GROUP_MANAGER:<id> | ADMIN:<id>),
assigned_at, reassigned_from?`.
Invariant: `assigned_driver_profile_id`'s trust ceiling ≥ job value band;
driver identity/licence + vehicle verification VERIFIED and not EXPIRED.

### 2.15 ChainOfCustodyEntry
`id, job_id, step (ASSIGNED | AT_PICKUP | CUSTODY_CONFIRMED | IN_TRANSIT |
AT_DESTINATION | RECIPIENT_VERIFIED | DELIVERED | COMPLETED | NOTE),
actor_user_id? , actor_role (BUSINESS | OPERATOR | GROUP_DRIVER | BUSINESS_CONTACT
| RECIPIENT | ADMIN), server_time, reported_time?, geo? | "NOT_CAPTURED",
confirmation_method? (OTP | SIGNATURE | PHOTO | NONE), evidence_refs[],
content_hashes[], note?`.
**Append-only, immutable** (FR-C-6). Corrections = new `NOTE` / corrective entry
referencing the original.

### 2.16 ProofOfPickup / ProofOfDelivery
`job_id, kind (PICKUP | DELIVERY), party_name, methods[] (OTP | SIGNATURE |
PHOTO), otp_verified?, signature_ref?, photo_refs[], captured_by
(OPERATOR | BUSINESS_CONTACT | RECIPIENT | ADMIN), captured_at, condition_note?,
attestation (VERIFIED | OPERATOR_ATTESTED_UNVERIFIED)`.
`OPERATOR_ATTESTED_UNVERIFIED` is only allowed for pickup on a Standard-band job
(D-CUS-2) and caps that job at the Standard band.

### 2.16a RecipientAccessLink  *(CONFIRMED in MVP — D-RCP-1)*
`id, job_id, token (opaque, single-use scope), channel_sent (SMS | WHATSAPP),
sent_to_phone, sent_at, expires_at (= COMPLETED + post-completion dispute
window), allowed_actions[] (VIEW_STATUS, CONFIRM_RECEIPT, RAISE_INCIDENT),
used_at?, revoked?`. No account, no login. Exposes only this job's delivery
status. A recipient action via the link is attributed as `actor_role = RECIPIENT`
in the audit log and chain of custody.

### 2.17 Incident
`id, job_id, type (DAMAGE | LOSS | MISSING_GOODS | WRONG_RECIPIENT | WRONG_PICKUP
| MISCONDUCT | BREAKDOWN | ACCIDENT | DELAY | CANCELLATION | OTHER),
other_label?, severity (LOW | MEDIUM | HIGH | CRITICAL),
reported_by (USER:<id> | RECIPIENT_LINK:<link_id>), reported_at, description,
status (OPEN | UNDER_REVIEW | AMICABLE_PENDING | RESOLVED | ESCALATED),
owner_admin_id?, linked_custody_entry_ids[]`.
A `RECIPIENT_LINK` incident notifies the business, the operator/group, and an
administrator, and enters the standard workflow (FR-D-*).

### 2.18 Evidence
`id, incident_id, uploaded_by, uploaded_at, kind (PHOTO | DOCUMENT | NOTE),
ref, content_hash, caption`. Append-only.

### 2.19 Statement
`id, incident_id, party_user_id? | "RECIPIENT", role, text, submitted_at`.
Append-only; multiple allowed per party.

### 2.20 Dispute / Resolution
- `Dispute(id, job_id, incident_ids[], opened_by, opened_at, status (OPEN |
  AMICABLE | UNDER_REVIEW | RESOLVED | ESCALATED), officer_admin_id?)`
- `Resolution(dispute_id, outcome_code, rationale, financial_adjustment?
  {agreed_compensation_kes?, commission_treatment (APPLY | REDUCE | WAIVE),
  reduced_amount_kes?}, actions[] (RATING_IMPACT | TRUST_CHANGE | SUSPENSION |
  NONE), routed_job_state (COMPLETED | FAILED | CANCELLED | RESUME_PRIOR),
  resolved_by, resolved_at)`.

### 2.21 Rating
`id, job_id, rater_role (BUSINESS | OPERATOR | RECIPIENT?), rater_user_id?,
ratee_kind (OPERATOR | GROUP | BUSINESS), ratee_id, score (1–5),
dimensions? {timeliness, care, communication, ...}, comment?, created_at`.
Only for jobs in COMPLETED; within a configurable window. A group job produces a
rating against **both** the assigned driver (`OPERATOR`) and the `GROUP`.

### 2.22 CommissionRecord
`job_id, gross_agreed_price_kes, rate_applied, band_applied?, min_fee_applied?,
amount_kes, payee_kind (OPERATOR | GROUP), payee_id, party_liable = OPERATOR
(D-BIZ-4; for a group job the group is billed), status (PENDING | DUE | SETTLED |
WAIVED | REDUCED), statement_id?, computed_at, settled_at?`.
Created on COMPLETED (FR-M-1). Held while DISPUTED. Rate structure from
`PlatformConfig` (10% headline / KES 40 min / taper / optional intro ramp).

### 2.23 PaymentReport
`job_id, reported_by_role, method (CASH | MOBILE_MONEY | BANK | OTHER),
reported_at, counterparty_confirmed?`. Records that the transport fee was paid
directly between the parties; the platform holds no funds in MVP.

### 2.24 VerificationRecord
`id, subject_type (OPERATOR | VEHICLE | BASE | BUSINESS | GROUP), subject_id,
domain (IDENTITY | LICENCE | GOOD_CONDUCT | VEHICLE | HEAVY_CLASS_COMPLIANCE |
ASSOCIATION | BASE | DOCUMENT | HISTORY),
state (NOT_SUBMITTED | SUBMITTED | IN_REVIEW | INFO_REQUESTED | VERIFIED |
REJECTED | EXPIRED), evidence_refs[], reviewer_admin_id?, reviewed_at?,
expires_at?, notes`.

### 2.25 TrustLevelState & TrustLevelChange
- `TrustLevelState(operator_id, level (0..3 | RESTRICTED), value_ceiling_kes,
  since, last_evaluated_at)`
- `TrustLevelChange(operator_id, from_level, to_level, trigger (AUTO_PROPOSED |
  ADMIN_CONFIRMED | ADMIN_REGRESSION | INCIDENT), reason, actor_admin_id?,
  created_at)`. Append-only.

### 2.26 AdminProfile & AdminRole
`AdminProfile(user_id, roles[] (VERIFIER | OPERATIONS | DISPUTE_OFFICER |
PLATFORM_ADMIN), active)`. Roles MAY be collapsed to a single role for the
earliest pilot.

### 2.27 AuditLogEntry
`id, actor_user_id, actor_role, action, entity_type, entity_id, before?, after?,
server_time (UTC), source_meta {ip?, device?, channel?}`. Immutable, append-only,
covers every entity. (NFR-AUD-1)

### 2.28 JobStatusEvent
`id, job_id, from_state, to_state, actor_user_id, actor_role, reason?,
server_time`. The lifecycle-specific audit trail (subset/mirror of AuditLog for
convenience and metrics).

### 2.29 PlatformConfig  *(singleton, versioned)*
`commission {rate, bands?, floor_kes?, party_liable}, high_value_threshold_kes,
value_bands[], trust_levels[] {level, value_ceiling_kes, criteria}, vehicle_types[],
cargo_categories[], zones[] {name, geo_boundary?}, cancellation_policy,
timeouts {request_expiry, offer_expiry, delivery_acceptance,
post_completion_dispute_window, stale_assignment_alert}, retention_windows{...},
notification_channels[]`.
`PlatformConfigVersion(version, changed_by, changed_at, rationale, snapshot)` —
append-only (FR-ADM-7).

### 2.30 Notification
`id, recipient_user_id? | recipient_phone, channel (IN_APP | SMS | WHATSAPP),
type, job_id?, payload, created_at, sent_at?, status (QUEUED | SENT | FAILED |
FELL_BACK_TO_SMS), retry_count`.
Channels are in-app + SMS + WhatsApp (D-NOTIF-1). OTP is SMS-primary. A failed
WhatsApp send falls back to SMS.

---

## 3. Key enumerations (seed values; all configurable where noted)

| Enum | Seed values |
|------|-------------|
| Job status | DRAFT, REQUESTED, NEGOTIATING, CONFIRMED, ASSIGNED, AT_PICKUP, PICKED_UP, IN_TRANSIT, AT_DESTINATION, DELIVERED, COMPLETED, CANCELLED, FAILED, DISPUTED |
| Vehicle type *(configurable)* | MOTORCYCLE, PICKUP, CANTER, TIPPER, LORRY, SEMI_TRUCK, TRAILER, OTHER |
| Base type | STAGE, BASE, YARD, WAITING_AREA |
| Operator group type | YARD_OWNER, FLEET, SACCO, PARTNERSHIP |
| Group membership role | OWNER, MANAGER, DRIVER |
| Location type | MAIN, BRANCH, WAREHOUSE, STORE, PICKUP_POINT |
| Cargo category *(configurable)* | GENERAL, CONSTRUCTION_MATERIALS, AGRICULTURE_PRODUCE, FOOD_BEVERAGE, FURNITURE_APPLIANCES, ELECTRONICS, DOCUMENTS_PARCELS, LIVESTOCK, LIQUIDS_BULK, OTHER |
| Handling flags | FRAGILE, PERISHABLE, HIGH_VALUE, LIVESTOCK, BULK, LIQUID, OVERSIZE, (HAZARDOUS — validation required, likely excluded from pilot) |
| Verification domain | IDENTITY, LICENCE, GOOD_CONDUCT, VEHICLE, HEAVY_CLASS_COMPLIANCE, ASSOCIATION, BASE, DOCUMENT, HISTORY |
| Notification channel | IN_APP, SMS, WHATSAPP |
| Verification state | NOT_SUBMITTED, SUBMITTED, IN_REVIEW, INFO_REQUESTED, VERIFIED, REJECTED, EXPIRED |
| Trust level | 0 PENDING, 1 VERIFIED, 2 ESTABLISHED, 3 TRUSTED, RESTRICTED |
| Incident type | DAMAGE, LOSS, MISSING_GOODS, WRONG_RECIPIENT, WRONG_PICKUP, MISCONDUCT, BREAKDOWN, ACCIDENT, DELAY, CANCELLATION, OTHER |
| Incident severity | LOW, MEDIUM, HIGH, CRITICAL |
| Negotiation entry type | PROPOSE, COUNTER, ACCEPT, REJECT |
| Admin role | VERIFIER, OPERATIONS, DISPUTE_OFFICER, PLATFORM_ADMIN |
| Currency | KES (single, MVP) |

---

## 4. Invariants (must always hold)

1. A Job has at most one `Agreement`, one `Assignment`, one `CommissionRecord`,
   one `Dispute` at a time.
2. `Agreement` exists ⇔ Job has passed through CONFIRMED.
3. `Assignment` exists ⇔ Job is in ASSIGNED or any later non-terminal-by-failure
   state (or a terminal state it reached after assignment).
4. `Assignment.vehicle` type+capacity satisfies `Job.vehicle_requirement`, and
   the vehicle's verification + the **assigned driver's** IDENTITY / LICENCE /
   GOOD_CONDUCT (and HEAVY_CLASS_COMPLIANCE where applicable) are VERIFIED and not
   EXPIRED at assignment time.
5. `Assignment.assigned_driver.trust_level.value_ceiling_kes` ≥ Job value
   (declared/agreed per config) unless an admin override with recorded reason
   exists. (For a group job this is the **driver's** ceiling, not the group's.)
6. A group `Assignment` (`operator_party = GROUP`) always has a non-null
   `assigned_driver_profile_id` that is an ACTIVE `GroupMembership(role=DRIVER)`
   of that group; the group's `standing` is not SUSPENDED.
7. `NegotiationEntry`, `ChainOfCustodyEntry`, `Evidence`, `Statement`,
   `AuditLogEntry`, `JobStatusEvent`, `TrustLevelChange`,
   `PlatformConfigVersion` are append-only: no update, no delete via application
   roles.
8. Job requester User ≠ the assigned operator/driver User (and ≠ a group the
   requester controls).
9. Money fields are non-negative integers in KES minor units.
10. Every Job status change has a corresponding `JobStatusEvent` and
    `AuditLogEntry`.
11. A Job in COMPLETED has a `ProofOfDelivery` (unless reached COMPLETED via a
    dispute Resolution that explicitly records why not).
12. A `RecipientAccessLink` grants no capability beyond `allowed_actions` and is
    unusable after `expires_at` or `revoked`.

---

## 5. Relationship notes

- **User ↔ roles:** one User, up to one BusinessAccount + one OperatorProfile +
  one AdminProfile. Verification is per profile/subject, never shared.
- **Job ↔ negotiation:** one Job, many threads, one thread per operator; exactly
  one thread reaches agreement.
- **Job ↔ custody:** one Job, ordered append-only custody entries; the entry
  sequence must be consistent with the status transitions that produced them.
- **Operator ↔ base:** many-to-many; base proximity to a job's pickup is a
  discovery ranking signal.
- **Config:** a single evolving `PlatformConfig` with an append-only version
  history; every job/commission/trust decision should be interpretable against
  the config version in force at the time.

---

## 6. Status summary

| Item | Category |
|------|----------|
| JOB as aggregate root with the brief's field set | CONFIRMED DECISION |
| Append-only negotiation, custody, evidence, audit, config history | CONFIRMED DECISION |
| Entity set and relationships above | WORKING ASSUMPTION (conceptual; Phase 1 designs the schema) |
| Single currency KES, money as integer minor units | WORKING ASSUMPTION (recommended) |
| Operator groups (`OperatorGroup` + `GroupMembership` + group-owned `Vehicle` + driver-named `Assignment`) | CONFIRMED 2026-09-08 (D-OPR-GRP-1) — minimal scope |
| Recipient link (`RecipientAccessLink`, no account) | CONFIRMED 2026-09-08 (D-RCP-1) |
| Notification channels incl. WHATSAPP | CONFIRMED 2026-09-08 (D-NOTIF-1) |
| Hazardous / dangerous goods handling | REQUIRES KENYAN PROFESSIONAL VALIDATION — likely excluded from pilot |
