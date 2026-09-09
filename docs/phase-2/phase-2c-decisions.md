# Phase 2C — Implementation Decisions

Decisions taken while implementing Vehicles & Verification, and every place the
implementation fills a gap in or deviates from the approved Phase 1 design.
**No approved product decision was changed. No contradiction with the approved
architecture was found.**

Status: **CONFIRMED** · **DEVIATION** (differs from a Phase 1 doc, with
rationale) · **PROVISIONAL** (revisit in a later phase).

---

## ADR-2C-01 — Vehicle classes are a lookup table, not a config JSON list — DEVIATION from Phase 2A / faithful to Phase 1

Phase 2A's `platform_config.defaults` carried `vehicle_types` as a bare string
list. Phase 1 database-design §4.15 actually specifies `vehicle_type` as an
**admin-extensible lookup table** (`id · code · name_en · name_sw · active ·
sort_order`). Phase 2C makes it that table (`config_vehicle_class`), adds a
`heavy` boolean (needed to drive HEAVY_CLASS_COMPLIANCE), seeds the 8 approved
classes, and removes `config.data["vehicle_types"]`.
`ConfigService.vehicle_class_codes()` and `ConfigPublicView` expose the codes so
the `/api/v1/reference` payload is unchanged for clients. One source of truth
(brief §33).

## ADR-2C-02 — `Vehicle.status` gains `SUSPENDED` — DEVIATION (extension)

Phase 1 database-design gives `vehicle_state` the values
`ACTIVE | INACTIVE | UNDER_REPAIR` (all operator-set). `users-and-roles.md` §4
and FR-ADM-4 give administrators the power to suspend. 2C adds `SUSPENDED`
(same rationale as ADR-2B-02's business `SUSPENDED`): an operator sets the first
three; only a platform admin sets or lifts `SUSPENDED`; `Vehicle.is_active` is
`status == ACTIVE`, so a suspended vehicle never reads as operational (brief
§9). No behavioural change to the existing three values.

## ADR-2C-03 — One `VerificationEvidence` table, not `vehicle_document` + `heavy_class_compliance` — DEVIATION (consolidation)

Phase 1 has separate `vehicle_document` (kind + evidence + expiry) and
`heavy_class_compliance` (five evidence refs + expiries) tables. 2C stores every
verification document — for any subject and domain — as a `VerificationEvidence`
row (`record`, `evidence_object`, `kind`, `issued_at`, `expires_at`,
`submitted_by`, `superseded_at`). This captures the same facts and per-item
expiry, keyed by `(record, kind)`, with one table instead of three near-
identical concepts — the same kind of permitted technical refinement Phase 1
itself made in ADR-009 (the unified `job_event`), and it satisfies brief §33
("no second source of truth"). The `kind` enum covers `LOGBOOK`,
`INSPECTION_CERT`, `INSURANCE_CERT`, `NTSA_OPERATOR_LICENCE`,
`SPEED_LIMITER_CERT`, `TELEMATICS_CERT`, etc.

## ADR-2C-04 — Heavy-class requirement keyed off `VehicleClass.heavy`, not a per-vehicle tare comparison — DEVIATION (determinism)

Phase 1 keys "heavy" off `vehicle.tare_kg > config.heavy_class_tare_kg`.
`tare_kg` is a nullable, operator-entered per-vehicle field. 2C uses a
config-owned `heavy` boolean on `VehicleClass` instead: deterministic, not
dependent on an operator filling in an accurate tare, and exactly what
"requirements vary by vehicle class → make them configuration-driven" (brief
§19) asks for. `Vehicle.tare_kg` is still stored as an optional attribute and
`config.heavy_class_tare_kg` is kept as informational.

## ADR-2C-05 — Validity is computed on read; no expiry beat job in 2C — CONFIRMED

`VerificationRecord.effective_state()` folds expiry in deterministically from
`state` + `expires_at`, so read correctness needs no scheduled task (brief §16).
`services.expire_due()` + `manage.py verification_expire` materialise EXPIRED
`VerificationDecision` rows and emit `verification.expired` events — useful for
the append-only history and a later notification phase, but **not** wired to
Celery beat in 2C (brief §31: notifications are out of scope).

## ADR-2C-06 — `fikisha.evidence` is a new cross-cutting module with no API — CONFIRMED

Phase 1 domain-architecture §3.15 has Evidence as a cross-cutting module that
others depend on. 2C creates it minimally (`EvidenceObject`,
`EvidenceAccessLog`, `EvidenceService.store` / `open_stream`). It exposes **no
endpoints** — the consuming module (Verification) owns the authorized
upload/download routes and calls the service. This keeps the dependency
direction clean (Verification → Evidence → storage) and lets Custody / Incidents
reuse it later.

## ADR-2C-07 — Vehicle control is fixed at registration in 2C — PROVISIONAL

Transferring a vehicle between an operator and a group (or between operators)
would need to reset the `ASSOCIATION` verification. Rather than build that
coupling now, 2C sets `owner_operator` / `owner_group` at registration and does
not expose a transfer endpoint — deactivate + re-register to correct a mistake
(the vehicle is "control / availability, not a legal vehicle-title registry",
brief §8). `services.invalidate_association` exists for the future transfer path
and is tested. Recorded as a known limitation + a Phase 2D handoff item.

## ADR-2C-08 — Evidence stream is the HIGH-PII path; full production hardening deferred — CONFIRMED

Evidence bytes stream through the API (never a signed bucket URL), authorized
per-fetch, with a HIGH-PII access-log row. ClamAV scanning, EXIF/GPS stripping +
image re-encode, and application-level envelope encryption of HIGH-PII objects
are **documented production hardening** (evidence-storage.md §3/§5), deferred —
consistent with the Phase 2A storage foundation. See
[`phase-2c-privacy-security.md`](phase-2c-privacy-security.md).

## ADR-2C-09 — `OPERATIONS_OFFICER` gains read-only `vehicle.read` — CONFIRMED

`platform_config.defaults.role_permissions["OPERATIONS_OFFICER"]` already had
`verification.queue.view` and `verification.decide`; 2C adds `vehicle.read`
(FR-ADM-1: "administrators can review businesses, operators, and vehicles"). No
mutation permission. A code-default change; an already-deployed config picks it
up via `ConfigService.apply_change`.

---

## Deviations summary

| # | Phase 1 reference | Deviation | Why it is safe |
| --- | --- | --- | --- |
| ADR-2C-01 | `config.vehicle_types` JSON list (Phase 2A) | lookup table | it is the table Phase 1 §4.15 specified; `/reference` unchanged for clients |
| ADR-2C-02 | `vehicle_state` enum | added `SUSPENDED` | approved admin capability (FR-ADM-4); admin-only; `is_active` unchanged |
| ADR-2C-03 | `vehicle_document` + `heavy_class_compliance` tables | one `VerificationEvidence` table | same facts + per-item expiry, one source of truth; mirrors Phase 1's own ADR-009 |
| ADR-2C-04 | heavy = `tare_kg > threshold` | heavy = `VehicleClass.heavy` (config) | deterministic; exactly what brief §19 asks; tare still stored |

None changes an approved **product** decision (commission model, trust
thresholds, value bands, cancellation policy, dispute window, proof-of-pickup
responsibility, admin role structure, verification domains, languages, pilot
area). Those remain untouched.

---

## Explicitly NOT implemented (extension points left clean)

Jobs · job lifecycle · negotiation · pricing · assignment · dispatch · trust
score / level / value-band eligibility engine · ratings · incidents · disputes ·
custody · pickup OTP · delivery · recipient links · commission · payments ·
M-Pesa · eTIMS · SMS · WhatsApp · GPS · route optimisation · AI matching · fleet
scheduling · payroll · driver transfers · wallets · escrow · insurance claims ·
native mobile apps.

The clean facts Phase 2D consumes: `verification.subject_meets(subject,
domains)` / `eligibility(subject)` (per-domain effective state), the
`verification.decided` / `.expired` events, `Vehicle` control + class + `heavy`
flag + status, and `requirements_status(subject)` for the required-domain set.
