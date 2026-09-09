# Phase 2B — Implementation Decisions

Decisions taken while implementing the identity & organisation domain, and every
place the implementation fills a gap in or deviates from the approved Phase 1
design. **No approved product decision was changed. No contradiction with the
approved architecture was found.**

Status: **CONFIRMED** (settled for 2B) · **DEVIATION** (differs from a Phase 1
doc, with rationale) · **PROVISIONAL** (revisit in a later phase).

---

## ADR‑2B‑01 — Three new Django apps: `business`, `operators`, `groups` — CONFIRMED

Mirrors Phase 1 domain‑architecture §3.2–3.4 (Business, Operators, Operator
Groups are three separate modules). Cross‑module foreign keys use **string
references** (`"operators.OperatorProfile"`) so no module imports another's
model class; behaviour crosses modules only through `services` / `authz`.
`Zone` was added to the existing `platform_config` app (Phase 1: zones belong to
Platform Configuration).

## ADR‑2B‑02 — `BusinessAccount.standing` gains `SUSPENDED` — DEVIATION (extension)

Phase 1 database‑design §4.2 gave `business_account.standing` the values
`GOOD | RESTRICTED`. `users-and-roles.md` §4 and FR‑ADM‑4 give administrators the
power to **suspend** a business. 2B adds `SUSPENDED` to the enum (the smallest
clean extension), platform‑admin‑only, and checked by the authorization layer
(`BusinessAccount.is_operational`). No behavioural change to `GOOD`/`RESTRICTED`.

## ADR‑2B‑03 — `BusinessMembership` gains a `status` lifecycle — DEVIATION (extension)

Phase 1's `business_membership` table had `role` and a `unique(business, user)`
constraint but **no status column** (the pilot was single‑user). Phase 2B
implements the full membership relationship the phase is about, so a lifecycle
is needed: `status ∈ {ACTIVE, SUSPENDED, REMOVED}` (mirroring
`group_membership`'s status field). `INVITED` from the brief §9 list is **not**
implemented — there is no invite/accept flow in 2B; an `OWNER` adds a known
person directly as `ACTIVE` (pilot practice). `INVITED` is reserved for that
later flow. Removal is a soft state change (`REMOVED`), never a hard delete —
the row is kept for history (brief §32).

## ADR‑2B‑04 — Plain `lat`/`lng`, not PostGIS — DEVIATION from a RECOMMENDATION

Phase 1 database‑design *recommended* PostgreSQL/PostGIS `GEOGRAPHY(POINT)`
columns for `business_location.geo` and `operating_base.geo`, for proximity
ranking in job discovery. Phase 2B stores nullable `lat`/`lng` `DECIMAL(9,6)`
instead, because: proximity ranking is a **discovery** concern that does not
exist in 2B; the brief (§19) explicitly says *do not build a GIS, route
optimisation, or geofencing*; and database‑design §6 itself documents the plain
lat/lng fallback as "workable at pilot scale". Adopting PostGIS later is an
additive migration.

## ADR‑2B‑05 — Group `standing` is a plain field; no `group_standing_change` yet — DEVIATION (deferral)

Phase 1 gives Operator Groups an append‑only `group_standing_change` history
driven by incidents and admin action. In 2B `standing` is a plain field a
platform admin can set (`GOOD | RESTRICTED | SUSPENDED`), with an audit row.
The append‑only standing history belongs with the Trust & Incidents phases that
actually drive it. `payout_number` (HIGH‑PII) and group‑owned vehicles are
likewise deferred to the commission and vehicle phases.

## ADR‑2B‑06 — Cross‑organisation access returns 403, not 404 — CONFIRMED (differs from 2A sessions)

Phase 2A's session IDOR test returns **404** (a user's session list must not
reveal that another user's session exists). Organisation resources return
**403** for an authenticated non‑member: a business/group on a marketplace is not
a secret, and Phase 1's permission matrix marks cross‑org access "—" (denied =
403). Per‑user resources keep the 404 behaviour.

## ADR‑2B‑07 — Minimal `Idempotency-Key` support — CONFIRMED

Phase 1 ADR‑008 calls for idempotency keys on mutations; brief §26 asks for it
on organisation / membership / location creation. `fikisha/common/idempotency.py`
caches a create's response (keyed by `Idempotency-Key` + actor + path) for 24h;
a replay returns the stored response; a concurrent replay gets
`409 idempotency_in_progress`. Requests without the header are unaffected.
Natural keys (`unique(business, user)`, the operator O2O, the base‑membership
partials) already make most retries safe; this covers the create‑with‑no‑natural‑key
cases (a new business, a new base).

## ADR‑2B‑08 — `business.category` is free text; `verification_status` is inert — CONFIRMED

Phase 1 has a `business_category` config lookup table and a verification
workflow. 2B keeps `category` as a free‑text field (no lookup table yet) and
`verification_status` as an inert enum defaulting `UNVERIFIED` — the field exists
so later phases can drive it, but nothing reads it for a decision in 2B. The
same applies to `OperatorGroup.verification_status`.

## ADR‑2B‑09 — `OPERATIONS_OFFICER` granted read‑only org access — CONFIRMED

`platform_config.defaults.role_permissions["OPERATIONS_OFFICER"]` gains
`business.read`, `operator.read`, `group.read` (FR‑ADM‑1: "administrators can
review businesses, operators"). This is a code‑default change; an already‑deployed
config would need an `apply_change` to pick it up. No mutation permission is
granted.

## ADR‑2B‑10 — `django.contrib.postgres` added to `INSTALLED_APPS` — CONFIRMED

Needed for the `ArrayField` on `OperatorProfile.phones` (Phase 1:
`operator_profile.phones TEXT[]`). It is a Django contrib app, not a new
dependency.

---

## Deviations summary

| # | Phase 1 reference | Deviation | Why it is safe |
| --- | --- | --- | --- |
| ADR‑2B‑02 | `business_account.standing` enum | added `SUSPENDED` | approved admin capability (FR‑ADM‑4); authz‑checked; no change to existing values |
| ADR‑2B‑03 | `business_membership` (no status) | added `status` lifecycle | the phase is about membership; mirrors `group_membership`; `INVITED` reserved, not built |
| ADR‑2B‑04 | PostGIS `GEOGRAPHY` (RECOMMENDED) | plain `lat`/`lng` | discovery doesn't exist yet; brief §19 forbids GIS; documented fallback; additive later |
| ADR‑2B‑05 | `group_standing_change` (append‑only) | plain `standing` field + audit | the history is driven by trust/incidents phases; audit row still written |

None of these change an approved **product** decision (commission model, trust
thresholds, value bands, cancellation policy, dispute window, proof‑of‑pickup
responsibility, admin role structure, languages, pilot area). Those remain
untouched and unimplemented.

---

## Explicitly NOT implemented (extension points left clean)

Jobs · job lifecycle · negotiation · assignment · vehicles · driver /
operator verification workflows · trust levels & value‑band gating · chain of
custody · recipient links · delivery confirmation · ratings · incidents ·
disputes · commission · payments · M‑Pesa · SMS · WhatsApp · GPS · AI matching ·
dynamic pricing.

Where a relationship is shaped for the future without implementing it:
`assignment` will name a `GroupMembership(role=DRIVER)` — the partial‑unique
"one active group per operator" and the `(group, role, status)` index make
"assignable drivers for this group" a cheap query; `BaseMembership` +
`ServiceArea` (deferred) will feed discovery; `verification_status` /
`operator.status` / group `standing` fields exist for the verification and trust
phases to drive.
