# Admin Architecture

Implements Phase 0 `users-and-roles.md` §4, `D-ADM-1`, `FR-ADM-1..9`,
`FR-DASH-1..4`, and Phase 1 brief §20.

**Pilot admin roles: 2** — `PLATFORM_ADMIN` (the founder) and
`OPERATIONS_OFFICER`. The **4-role split** (`VERIFIER`, `OPERATIONS`,
`DISPUTE_OFFICER`, `PLATFORM_ADMIN`) is a **configuration** of
`platform_config.role_permissions`, enabled later without a deploy (FR-ADM-8).

**Every administrative action — including the founder's — is audit-logged with
actor + reason + before/after. There is no admin path that bypasses the audit
subsystem** (FR-ADM-9, brief §20, §34 P11).

---

## 1. Admin surface: two clients, one authorization model

| Surface | What it is | Used for |
|---------|-----------|----------|
| **Fikisha Admin (PWA admin area)** | Purpose-built screens in the same PWA, behind an admin session (phone-OTP + TOTP) | The day-to-day operational workflow: verification queue, job monitor + interventions, dispute console, high-value approvals, trust confirmations, dashboards, exports |
| **Django Admin** | The framework's model admin, hardened | Config editing with the versioned wrapper, audit-log browsing, lookup-table maintenance (zones, vehicle types, cargo categories), template editing, break-glass data inspection |

Both go through the **same `authorize(actor, action, resource)` engine** and the
**same audit + step-up requirements**. Django Admin is not a backdoor: its
`ModelAdmin` classes are read-mostly, write actions route through the domain
services (so the state machine, append-only rules, and audit still apply), and
mutating a `job.status` or an append-only row from Django Admin is **not
possible** (no form, and the DB trigger + table roles would reject it anyway).

---

## 2. Queues & consoles (materialised projections)

Each queue is a filtered/ordered view over a domain module's data plus a small
`admin_task` projection so counts and SLAs are cheap.

### 2.1 Verification queue (FR-V-4, FR-ADM-1)

- Source: `verification_record` in `SUBMITTED / IN_REVIEW / INFO_REQUESTED`.
- Columns: subject (operator / group member / vehicle / base), domain, age,
  `owner_admin_id`, assist-check flags (FR-V-8).
- Actions: `START_REVIEW`, view evidence (**step-up + `evidence_access_log`** for
  HIGH-PII), `REQUEST_INFO`, `APPROVE` (+ `set_expires_at`), `REJECT` (+ reason).
- Bulk: none in the MVP (each decision is deliberate).

### 2.2 Active-job monitor (FR-ADM-2)

- Source: `job` not in a terminal state; filter by status, zone, band, vehicle
  type, age-in-status.
- Drill-in: the full `job_timeline`, `chain_of_custody` view, negotiation threads
  (admin sees all — pricing-and-negotiation §7), assignment, incidents.
- **Interventions** (each writes `admin_intervention` + `audit_log_entry`, always
  with a mandatory `reason` and `before`/`after`):
  | Intervention | Rule |
  |--------------|------|
  | Reassign (driver + vehicle) | new assignment must satisfy the same guards (`VehicleEligible`, driver trust ceiling); `reassigned_from_assignment_id` chained |
  | Cancel | routes through `JobLifecycleService.transition(CANCELLED)`; `cancellation_record(by=ADMIN)` |
  | Force a transition | only to a state reachable in `ALLOWED_TRANSITIONS`; sets the `app.lifecycle_service` flag; still writes status event + custody + audit |
  | Contact parties | triggers a templated notification; logged |

### 2.3 High-value approval queue (D-TRU-5, trust-architecture §4)

- Source: `high_value_approval` with `decision = PENDING`.
- `HIGH` → Operations Officer or Platform Admin may approve; `VERY_HIGH` →
  Platform Admin only.
- The screen shows: assigned/candidate operator's trust level, current
  goods-in-transit / carrier cover status, contacts on file, route/plan, cargo.
- Approve records `conditions[]` (e.g. in-transit check-ins) surfaced to the
  driver.

### 2.4 Trust confirmation queue (FR-T-3, trust-architecture §3)

- Source: `trust_level_change` with `status = PROPOSED`.
- Shows the `criteria_snapshot` and linked evidence jobs/incidents.
- Actions: **confirm** (→ `APPLIED`) or **reject** (→ `REJECTED`, reason). No
  free-text level setting; `impose Restricted` is a separate step-up action.

### 2.5 Dispute console (FR-D-5/6/7/8, FR-ADM-3)

- Source: `incident` not `RESOLVED`, and `dispute` not `RESOLVED`; SLA timers
  from `sla_*_due_at`.
- Panels: incident details, the auto-attached `chain_of_custody` rows, all
  `incident_statement`s (append-only), all `incident_evidence`, the negotiation
  history, the two parties' positions.
- Flow: **amicable-first** prompt → if agreed, record the outcome; else
  **administrative review** → `POST /admin/disputes/{id}/resolution`
  (`outcome_code`, `rationale`, `commission_treatment`, `actions`,
  `routed_job_status`). Binding resolutions **above STANDARD band** require
  `PLATFORM_ADMIN` (D-ADM-1) + step-up.
- **Escalation**: `POST /admin/incidents/{id}/escalate` records the escalation
  and that parties were advised of external options (the platform does not
  adjudicate criminal matters — dispute-and-liability §4).

### 2.6 Account management (FR-ADM-4)

- Suspend / restrict / offboard a business, operator, or group — **Platform
  Admin only**, **step-up**, mandatory reason + duration; writes
  `admin_intervention` + `audit_log_entry`; emits `AccountSuspended` (cascades:
  operator loses discovery, active jobs flagged for review, links revoked where
  appropriate).

### 2.7 Audit-log viewer (FR-ADM-5, NFR-AUD-5)

- Filter by actor, entity type + id, action, time range.
- Operations Officer sees a **scoped** view (jobs/incidents they can already
  see); Platform Admin sees all.
- Export (async, itself audited).

---

## 3. Configuration management (FR-ADM-6/7)

- `GET /admin/config` → the current `platform_config.data`.
- `POST /admin/config` `{patch, rationale}` — **Platform Admin only**, **step-up**,
  **rationale required**. The Config Service validates the patch against the
  config schema, applies it, and appends a `platform_config_version` (version,
  changed_by, changed_at, rationale, full snapshot). Emits `PlatformConfigChanged`
  → consumers reload.
- Configurable in the pilot (FR-ADM-6): commission model/rate/min/cap +
  `party_liable`; `high_value_threshold_kes`; `value_bands`; trust-level criteria
  + ceilings; `restricted_rule`; vehicle types; `heavy_class_tare_kg`; cargo
  categories + `latent_risk_categories`; **zones** (the deferred Kitengela
  breakdown — D-PIL-5); cancellation policy (`rolling_window_days`,
  `flag_threshold`, `courtesy_fee_enabled` (default **false**),
  `courtesy_fee_kes`); timeout values (`request_expiry`, `offer_expiry`,
  `delivery_acceptance {standard_h, high_h}`, `post_completion_window
  {default_h, high_and_latent_days}`, `stale_assignment_alert`);
  `retention_windows`; notification channel config; **`role_permissions`**
  (the 2↔4 role switch); `verification_requirements`; `sla_targets`;
  `feature_flags`.
- **Every job / commission / trust decision pins the config version it used**
  (`config_version_id`), so a change is never retroactive and the weekly pilot
  review can read a change's effect in the data (pilot-strategy §6).

---

## 4. Operational dashboard (FR-DASH-1, pilot-strategy §4)

Reads **`metric_daily`** rollups (not live table scans). Panels:

| Panel | Source metrics |
|-------|----------------|
| **Job funnel** | created → published → confirmed → assigned → picked up → delivered → completed (counts + conversion + time-in-stage) |
| **Live jobs** | current active jobs by status/zone/band, with age-in-status and stale-assignment flags |
| **Incident queue + SLA** | open incidents by severity vs `sla_targets`; amicable-vs-admin-vs-escalated split |
| **Reliability** | cancellation rate by state, FAILED rate + reasons, no-show rate, on-time pickup/delivery |
| **Economics** | commission accrued / invoiced / settled; invoiced-vs-settled %; SMS/WhatsApp cost per job; contribution per job |
| **Supply/demand** | active operators/day by vehicle class + base; jobs offered vs accepted; coverage gaps (job requirements with no eligible operator) |
| **Pricing** | proposed-vs-agreed delta; counter-offers to agreement; time REQUESTED→CONFIRMED |
| **Onboarding funnel** | registration → docs submitted → verified → first job (drop-off) |

The full pilot-metric → source-event mapping is in
[observability.md](observability.md) §"Pilot metrics".

---

## 5. Data export (FR-DASH-2/3)

- `POST /admin/exports {scope}` → async `export_job` → a Celery task builds a CSV
  from `analytics_event` / `metric_daily` / job records with **minimum necessary
  personal data** (NFR-PRIV-1) → stored as an `evidence_object` → signed
  short-TTL download → `ExportReady` notification. The request and the download
  are both audited.
- Scopes: jobs, negotiations (amounts + timestamps, no free-text notes by
  default), incidents (types + outcomes + timings), notification costs, the
  weekly metric set.

---

## 6. The founder is not above the audit (brief §20, §34 P11)

- `PLATFORM_ADMIN` (the founder) has the widest permission set but **every one of
  their actions** writes `admin_intervention` + a hash-chained `audit_log_entry`
  with `actor_user_id`, `reason`, `before`, `after`.
- The founder **cannot**: set a trust level to an arbitrary value (only
  confirm/reject/Restricted); edit a negotiation entry, an agreed price, a
  commission record, a custody row, a statement, or an audit row (append-only DB
  roles); disable auditing (no such toggle); mutate `job.status` outside the
  allowed-transition set (state machine + DB trigger).
- Config changes require a **rationale** and are versioned — visible in the
  weekly pilot governance review.
- The audit chain is verified nightly and exported off-box, so tampering by
  anyone with DB access is detectable.

---

## 7. Admin events

| Emits | Consumers |
|-------|-----------|
| `AdminActionPerformed` (generic wrapper) | Reporting (admin-activity metrics), Observability |
| `HighValueApproved` / `HighValueRejected` | Jobs (unblocks/blocks assignment), Notifications |
| `AccountSuspended` / `AccountRestricted` / `AccountOffboarded` | Operators/Groups/Business (capability cascade), Recipients (revoke links), Evidence (schedule deletions), Notifications |
| `PlatformConfigChanged` | every module with cached config; Reporting (annotate the timeline) |

| Consumes | For |
|----------|-----|
| queue-feeding events: `VerificationSubmitted`, `IncidentOpened`, `TrustLevelChangeProposed`, `JobRequested` (HIGH/VERY_HIGH), stale-assignment ticks | keep the `admin_task` projections current |
