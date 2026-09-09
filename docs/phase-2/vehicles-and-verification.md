# Vehicles & Verification (Phase 2C)

Establishes **who operates which vehicle**, and **which verification facts have
been independently checked** about an operator / vehicle / operating base.

Nothing here computes trust, value bands, or job / assignment eligibility —
those consume these facts in a later phase.

```
OperatorProfile / OperatorGroup ──< Vehicle >── VehicleClass (config)
        │                              │
        └── VerificationRecord ────────┘   one per (subject, domain)
                 │
                 ├──< VerificationDecision   (append-only history)
                 └──< VerificationEvidence >── evidence.EvidenceObject ──< EvidenceAccessLog
```

---

## 1. Modules

| Django app | Owns | Notes |
| --- | --- | --- |
| `fikisha.evidence` | `EvidenceObject`, `EvidenceAccessLog` | pure dependency — stores bytes via the Phase 2A `storage` abstraction, logs HIGH-PII access. No API of its own. |
| `fikisha.vehicles` | `Vehicle` | one controller (operator XOR group); `VehicleClass` FK. |
| `fikisha.verification` | `VerificationRecord`, `VerificationDecision`, `VerificationEvidence` | the per-domain records + append-only decision log. |
| `fikisha.platform_config` (extended) | `VehicleClass` | admin-extensible lookup; `heavy` flag drives HEAVY_CLASS_COMPLIANCE. |

Cross-module FKs are **string references**; behaviour crosses modules only
through `services` / `authz`.

---

## 2. Vehicle model — `vehicle`

| Field | Type | Notes |
| --- | --- | --- |
| `owner_operator` / `owner_group` | FK `PROTECT`, nullable | **exactly one** set — DB `CHECK` `vehicle_exactly_one_controller`. Fixed at registration in 2C (deactivate + re-register to change — §7). |
| `vehicle_class` | FK → `platform_config.VehicleClass` `PROTECT` | |
| `registration` / `registration_normalized` | text | normalized = `[^A-Z0-9]` stripped, upper-cased. Partial unique on `registration_normalized WHERE deactivated_at IS NULL` — a plate can be reused after a vehicle is deactivated (brief §6). |
| `make` / `model` / `year` | text / smallint | optional |
| `capacity_value` / `capacity_unit` | decimal / enum `KG \| TONNES` | numeric + unit, never free text (brief §10). Leaves room for later cargo matching (not built). |
| `volume_m3` / `tare_kg` / `feature_tags` | optional | |
| `ownership` | enum `OWNED \| AUTHORISED_DRIVER` | Phase 1 `vehicle_ownership` |
| `speed_limiter_fitted` / `telematics_installed` | nullable bool | **operator-declared claims only** — the *verified* facts live in the HEAVY_CLASS_COMPLIANCE verification domain (brief §11). |
| `status` | enum `ACTIVE \| INACTIVE \| UNDER_REPAIR \| SUSPENDED` | operator sets the first three; **`SUSPENDED` is admin-only** (ADR-2C-02). `is_active` = `status == ACTIVE`. |
| `deactivated_at` | nullable | soft delete |

Indexes: `(owner_operator, status)`, `(owner_group, status)`, `vehicle_class`.

### Services (`vehicles.services`)
`register_vehicle` · `update_vehicle` · `set_status` (SUSPENDED / un-suspend
guarded to platform admin) · `deactivate_vehicle` · `vehicles_for_operator` /
`vehicles_for_group`. Each atomic with `vehicle.registered` / `.updated` /
`.status_changed` / `.deactivated` audit rows.

### Authorization
| Action | Allowed for |
| --- | --- |
| `vehicle.list` | any authenticated user (view scopes to vehicles the caller controls) |
| `vehicle.create` | any authed user; the view checks the caller **owns the named operator profile** or is an OWNER/MANAGER of the named group |
| `vehicle.read` | the controlling operator, an active member of the controlling group (**a group DRIVER may read**), or `vehicle.read` permission |
| `vehicle.manage` | the controlling operator, a group OWNER/MANAGER, or a platform admin. `SUSPENDED` transitions: platform admin only |

### API
```
GET    /api/v1/vehicles                      -> {data, page}  (controlled by the caller)
POST   /api/v1/vehicles                      {owner_operator_id | owner_group_id, vehicle_class,
                                              registration, capacity_value, capacity_unit, ...}
GET    /api/v1/vehicles/{id}
PATCH  /api/v1/vehicles/{id}
POST   /api/v1/vehicles/{id}/status          {status, reason?}
DELETE /api/v1/vehicles/{id}                 {reason?}   -> 204 (soft)
```

---

## 3. Verification model

### `verification_record` — one per (subject, domain)

`subject_type` (`OPERATOR | VEHICLE | BASE`) + exactly one of
`subject_operator` / `subject_vehicle` / `subject_base` (DB `CHECK` + three
partial uniques `uniq_{operator,vehicle,base}_domain`). `domain` ∈
`IDENTITY | LICENCE | GOOD_CONDUCT | VEHICLE | HEAVY_CLASS_COMPLIANCE |
ASSOCIATION | BASE | DOCUMENT | HISTORY` (Phase 1). `HISTORY` is defined but
**not submittable** in 2C (it is derived and feeds trust).

`state` (`NOT_SUBMITTED | SUBMITTED | IN_REVIEW | INFO_REQUESTED | VERIFIED |
REJECTED | EXPIRED`) is a **cache** of the latest decision + expiry.
`effective_state()` folds expiry in deterministically:
`state == VERIFIED and expires_at and expires_at <= now → EXPIRED`. Read paths
use `effective_state()`; no sweep is needed for correctness (brief §16).

Also: `issuing_authority`, `reviewer` (who approved/rejected), `owner_admin`
(who claimed it via START_REVIEW), `verified_at`, `expires_at`, `last_decision`.

### `verification_decision` — append-only

`record` · `action` (`SUBMIT | START_REVIEW | REQUEST_INFO | APPROVE | REJECT |
EXPIRE | RENEW`) · `actor` `PROTECT` (identity retained — brief §18) ·
`actor_role` · `reason` (mandatory for REJECT) · `note` (for REQUEST_INFO) ·
`set_expires_at` · `created_at`. Enforced append-only at the service, model
(`AppendOnlyModel`) and DB-role layers — a later reviewer can always answer
*what was submitted, by whom, when, what was reviewed, who reviewed it, what was
decided, when it expired, whether it was replaced* (brief §21).

### `verification_evidence`

`record` · `evidence_object` FK `PROTECT` → `evidence.EvidenceObject` · `kind`
(document type enum) · `issued_at` / `expires_at` (document dates) ·
`submitted_by` · `submitted_at` · `superseded_at` (set — row **kept** — when a
newer item of the same `kind` is attached). "Current" evidence = `superseded_at
IS NULL`. This one table subsumes Phase 1's `vehicle_document` /
`heavy_class_compliance` structures (ADR-2C-03) — one source of truth (brief §33).

### Lifecycle (verification-architecture §2)

```
NOT_SUBMITTED ──add evidence──▶ (still NOT_SUBMITTED) ──submit──▶ SUBMITTED
SUBMITTED ──START_REVIEW──▶ IN_REVIEW
IN_REVIEW ──REQUEST_INFO──▶ INFO_REQUESTED ──resubmit──▶ SUBMITTED
IN_REVIEW ──APPROVE (+expires_at?)──▶ VERIFIED ──(expiry passes)──▶ EXPIRED
IN_REVIEW ──REJECT (+reason)──▶ REJECTED ──resubmit──▶ SUBMITTED
```

`APPROVE` sets `expires_at` from the reviewer's input, else the earliest current
evidence `expires_at`, else (GOOD_CONDUCT) `now + good_conduct_recheck_months`.

### Reviewer rules (brief §17, §18)

- Review actions require the **`verification.decide`** permission (pilot:
  `OPERATIONS_OFFICER` or `PLATFORM_ADMIN`). An operator or business user never
  holds it → 403.
- Even a permitted reviewer **may not act on a record they submitted** —
  `_assert_reviewer_not_submitter` raises `422 reviewer_is_submitter` at
  `start_review` / `approve` / `reject`.
- Every decision records `actor` + `actor_role`.

### Derived read helpers (facts only)

`eligibility(subject) -> {domain: effective_state}` ·
`subject_meets(subject, [domains]) -> bool` ·
`requirements_status(subject) -> [{domain, mandatory, state}]`. **No**
`operator_active` / `vehicle_eligible` / band eligibility — deferred to Trust
(brief §5, §19).

### Requirements (config-driven — `requirements.py`)

`required_domains(subject_type, vehicle_is_heavy=…)` reads
`platform_config.verification_requirements`. `HEAVY_CLASS_COMPLIANCE` is required
iff the vehicle's `VehicleClass.heavy` is true — **no vehicle-class literal in
application code** (brief §19). Falls back to the shipped default when a pre-2C
config snapshot lacks the key.

### Events (real async side effects — brief §32)

`verification.submitted` · `verification.decided` · `verification.expired`, each
emitted in the deciding transaction. Consumers are later phases (Trust,
Notifications); none in 2C.

### API
```
GET    /api/v1/verification/records                         -> {data, page}  (caller's own subjects)
POST   /api/v1/verification/records                         {subject_type, subject_id, domain}
GET    /api/v1/verification/records/{id}                     record + evidence + decisions
POST   /api/v1/verification/records/{id}/evidence           multipart: file, kind, issued_at?, expires_at?
POST   /api/v1/verification/records/{id}/submit             {issuing_authority?}
POST   /api/v1/verification/records/{id}/review/start        (verification.decide)
POST   /api/v1/verification/records/{id}/review/request-info {note}
POST   /api/v1/verification/records/{id}/review/approve      {expires_at?, reason?}
POST   /api/v1/verification/records/{id}/review/reject       {reason}
GET    /api/v1/verification/queue                            (verification.queue)  pending records
GET    /api/v1/verification/subjects/{type}/{id}/status      eligibility + requirements
GET    /api/v1/verification/evidence/{id}/content            streams bytes (authorized + logged)
```

`manage.py verification_expire` materialises EXPIRED decisions + events (not
needed for read correctness).

---

## 4. Configuration

- `VehicleClass` (`config_vehicle_class`): `code`, `name_en`, `name_sw`,
  `heavy`, `active`, `sort_order`. Seeded: MOTORCYCLE, PICKUP, CANTER†, TIPPER†,
  LORRY†, SEMI_TRUCK†, TRAILER†, OTHER († = `heavy`). Admin-extensible (a row,
  not a migration).
- `config.verification` — `good_conduct_recheck_months` (12),
  `expiry_lead_days` (30).
- `config.verification_requirements` — `[{subject_type, domain, mandatory,
  heavy_only?}]`. Seeded: OPERATOR → IDENTITY, LICENCE, GOOD_CONDUCT; VEHICLE →
  VEHICLE, ASSOCIATION, HEAVY_CLASS_COMPLIANCE (heavy only); BASE → BASE.
- `config.data["vehicle_types"]` was **removed** (ADR-2C-01); `ConfigPublicView`
  builds `vehicle_types` from the table.

Kitengela remains configuration — no geographic logic was added.

---

## 5. Audit

Every vehicle and verification mutation writes an `audit_log_entry` in the same
transaction (a founder's actions included). Actions: `vehicle.registered` /
`.updated` / `.status_changed` / `.deactivated`; `verification.submitted` /
`.evidence.added` / `.start_review` / `.request_info` / `.approve` / `.reject` /
`.expire`. No second audit system; `verify_chain()` → `[]`.
