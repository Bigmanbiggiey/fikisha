# PHASE 2B — IDENTITY & ORGANIZATION DOMAIN REPORT

> **PHASE 2B — COMPLETE — AWAITING FOUNDER REVIEW**
> Identity, organization, and operating-location foundations are implemented.
> No Phase 2C vehicle/verification implementation has been started.

---

## 1. Status

The first Fikisha business-domain phase. Builds the actors and organisational
structures a future **Job** depends on — Business, its members and locations;
Transport Operator profiles; minimal Operator Groups and their membership;
first-class Operating Locations (stage / base / yard) — on top of the Phase 2A
foundation, reusing its authentication, authorization engine, audit, outbox,
API conventions, CI, and test infrastructure unchanged.

## 2. What was implemented

- **Business:** `BusinessAccount`, `BusinessMembership` (OWNER / DISPATCHER /
  VIEWER; ACTIVE / SUSPENDED / REMOVED; last-owner invariant),
  `BusinessLocation` (5 types, one-active-MAIN invariant, soft delete).
- **Operators:** `OperatorProfile` (1:1 User, one per user), `OperatingBase`
  (STAGE / BASE / YARD / WAITING_AREA), `BaseMembership` (operator **or** group
  presence claim, DB CHECK).
- **Groups:** `OperatorGroup` (4 types, `assignment_mode`, `standing`),
  `GroupMembership` (OWNER / MANAGER / DRIVER; one active group per operator;
  last-owner invariant).
- **Config:** `Zone` lookup + a seeded `KITENGELA` pilot zone (D-PIL-5).
- **Authorization:** organisation-level policies extending the Phase 2A engine
  (default deny; platform-level ≠ organisation-level; object-level checks before
  the handler).
- **APIs:** ~30 versioned endpoints under `/api/v1/` (RFC 9457 problem+json,
  `{data, page}` cursor pagination, `Idempotency-Key` on creates).
- **Audit:** every organisation mutation writes an `audit_log_entry` in the same
  transaction (founder included). No second audit system.
- **Outbox:** `business.member.added` / `group.member.added` event contracts for
  future notification delivery — no provider integration.
- **Frontend:** functional (not elaborate) role-aware screens for businesses,
  members, locations, operator profile, operating locations, groups, group
  members; English + Swahili; existing design-system + problem+json client.
- **Tests:** 79 new backend tests (193 total), 2 new frontend tests (11 total).
- **Docs:** this report + `identity-and-organizations.md`,
  `organization-authorization.md`, `operating-locations.md`,
  `phase-2b-decisions.md`.

## 3. Domain model

Full field-level detail: [`identity-and-organizations.md`](identity-and-organizations.md) §2.

```
User (2A)
 ├── BusinessAccount ──< BusinessMembership >── User        (business_account, business_membership)
 │        └──< BusinessLocation                              (business_location; 1 active MAIN)
 └── OperatorProfile (1:1 User)                              (operator_profile)
          ├──< GroupMembership >── OperatorGroup             (group_membership; ≤1 active group)
          └──< BaseMembership  >── OperatingBase             (base_membership; operator XOR group)
OperatorGroup ──< BaseMembership >── OperatingBase           (operator_group)
Zone (config_zone)  ←  BusinessLocation.zone, OperatingBase.zone
```

## 4. Business model

`BusinessAccount`: `owner_user` (PROTECT), `trading_name`, free-text `category`,
contact fields, `standing` (GOOD | RESTRICTED | **SUSPENDED**, admin-only,
authz-checked), inert `verification_status`. Registration ids (KRA PIN etc.)
deliberately **not** collected in 2B (legal-scope §7). Services: `create_business`
(creates the account + an OWNER membership atomically, both audited),
`update_business`, `businesses_for`.

## 5. Business membership

`BusinessMembership`: `role` (OWNER / DISPATCHER / VIEWER), `status`
(ACTIVE / SUSPENDED / REMOVED — lifecycle; `INVITED` reserved for a later
invite/accept flow, ADR-2B-03), `unique(business, user)`. **Invariant:** always
≥ 1 active OWNER (`409 last_owner`). `add_member` normalises the phone,
`get_or_create`s the user, activates/creates the membership, audits, and emits
`business.member.added`. `update_membership` / `remove_member` (soft — row kept).
An OWNER manages members; a DISPATCHER manages locations; a VIEWER reads.

## 6. Operator model

`OperatorProfile`: 1:1 with `User`, `full_name`, `display_name`, `phones` (text
array), `status` (PENDING | ACTIVE | RESTRICTED | SUSPENDED | OFFBOARDED — the
approved enum; admin-only). **No verification, trust, vehicles, service areas,
availability, or payout details** — those are later phases. Services:
`create_profile` (one per user), `update_profile`, `profile_for`.

## 7. Operator groups

`OperatorGroup`: `name`, `type` (YARD_OWNER | FLEET | SACCO | PARTNERSHIP),
always-set `primary_contact`, `assignment_mode` (MANAGER_ASSIGNS |
DRIVER_ACCEPTS), `standing` (GOOD | RESTRICTED | SUSPENDED — plain admin lever;
the append-only `group_standing_change` history is deferred to the trust phase,
ADR-2B-05), inert `verification_status`. **Not** a fleet-management system — no
payroll, scheduling, dispatch, maintenance, transfers, or group-owned vehicles.
Only a user with an `OperatorProfile` may form a group; the creator becomes
OWNER.

## 8. Group membership

`GroupMembership`: `group` × `operator_profile`, `role` (OWNER / MANAGER /
DRIVER), `status` (ACTIVE / INACTIVE), `since`, `added_by`. Constraints:
`unique(group, operator)` and a partial `unique(operator) WHERE status='ACTIVE'`
(one active group per operator). Index `(group, role, status)` — the future
"assignable drivers for this group" query. **Invariant:** ≥ 1 active OWNER.
`add_member` emits `group.member.added`. Assignment of a specific driver to a Job
is **not** implemented; the model simply does not make it impossible.

## 9. Operating locations

`OperatingBase` is a place, not a possession — see
[`operating-locations.md`](operating-locations.md). Presence is a separate
`BaseMembership` (operator **or** group; DB `CHECK` that exactly one is set).
Creating a base does not require membership, and a base does not require a
membership to exist — so an operator's physical operating location can be
established without formal stage membership (brief §20). `Zone` is a minimal
lookup; one `KITENGELA` zone is seeded; coordinates are plain nullable
`lat`/`lng` (no PostGIS — ADR-2B-04); `"Kitengela"` is configuration, never a
code branch.

## 10. Authorization

`organization-authorization.md` is the full reference. Highlights: the Phase 2A
`authorize(actor, action, resource)` engine is extended with per-module policies
(default deny); platform-level permissions (`PLATFORM_ADMIN` `*`) are distinct
from organisation-level roles; `OPERATIONS_OFFICER` gains **read-only** org
access (FR-ADM-1); every detail endpoint resolves its target and runs the
object-level check **before** the handler; an authenticated non-member gets
**403** (ADR-2B-06); service-layer invariants (last-owner, one-group-per-operator,
one-MAIN-location).

## 11. Audit integration

Every organisation mutation calls Phase 2A `audit.record(...)` **inside the same
`transaction.atomic`** as the change — 20 distinct actions
(`business.created` … `group.member.removed`), a platform admin's actions
included. The Phase 2A hash chain still verifies (`verify_chain()` → `[]` after
the smoke run). No second audit mechanism, no bypass.

## 12. API implementation

~30 endpoints across `fikisha.business.api`, `fikisha.operators.api`,
`fikisha.groups.api`, wired into `fikisha/api/urls.py` before the catch-all 404.
`fikisha.common.api.OrgApiView` maps each HTTP method to an authz action and
exposes a detail view's target to the policy. `fikisha.common.idempotency`
gives `Idempotency-Key` support on creates (ADR-2B-07). Response shape, error
contract (`application/problem+json`), pagination (`{data, page}`),
authentication (Bearer), and 401-vs-403 semantics are unchanged from Phase 2A.
Endpoint list: [`identity-and-organizations.md`](identity-and-organizations.md) §4.

## 13. Frontend implementation

`frontend/src/features/org/`: `orgApi.ts` + `types.ts` (typed client),
`BusinessesPage` / `BusinessDetailPage`, `OperatorProfilePage`,
`OperatingLocationsPage`, `GroupsPage` / `GroupDetailPage`. New routes behind
`<RequireAuth>`, new `TopBar` nav, new `org` i18n namespace (en + sw). Controls
the current role cannot use are hidden (`my_role` from the API) — **UX only**;
the API re-enforces every boundary. Uses the existing design-system components
and the problem+json-aware API client.

## 14. Database migrations

New: `platform_config/0002_zone`, `platform_config/0003_seed_pilot_zone`,
`business/0001_initial`, `operators/0001_initial`, `groups/0001_initial` +
`groups/0002_initial` (Django split — the `operators ↔ groups` FK cycle).
Verified from an **empty** database:

```
empty PostgreSQL 16  →  migrate  →  Phase 2A + 2B schema  →  193 tests pass
python manage.py makemigrations --check --dry-run   ->  "No changes detected"
```

## 15. Tests

**Backend — 193 pass (was 114), ~87% line coverage.** New:

| File | Covers |
| --- | --- |
| `business/tests/test_business.py` | create (owner auto-added), list scoping, profile update, standing (owner 403 / admin 200), add staff + scoped access, outbox event, last-owner guard, suspended member loses access, MAIN uniqueness + demotion, soft delete, unknown zone |
| `business/tests/test_business_services.py` | promote/demote owners, last-owner reject, reactivate a removed member, duplicate-active conflict, unknown role, location update + promote-to-MAIN, no-op update, idempotent deactivate, bad type |
| `business/tests/test_business_security.py` | Business A → read/update/list-members/add-member/read-locations on Business B → 403; unauthenticated → 401; unknown/malformed id → problem+json |
| `operators/tests/test_operators.py` | profile create + `/me`, `/me` 404 without a profile, one-per-user, own update, status (owner 403 / admin 200), base create + list, non-operator cannot create a base, only creator edits (but anyone reads), associate + end, cannot associate another's profile, enum values, CHECK constraint |
| `operators/tests/test_operators_services.py` | phones trimmed, second profile conflict, field/no-op update, non-admin vs admin status, bad status, base create/update/no-op, bad base type, re-associate after INACTIVE |
| `groups/tests/test_groups.py` | creator becomes OWNER, non-operator blocked, list scoping, update (owner) / standing (owner 403 / admin 200), manager adds a driver + scoped access + outbox event, one-active-group-per-operator (409), last-owner guard, soft remove, roles |
| `groups/tests/test_groups_services.py` | create needs operator profile, owner-already-in-a-group, member role/status update, reactivate-after-joined-elsewhere conflict, group↔base associate + end + re-associate |
| `groups/tests/test_groups_security.py` | Group A member → read/manage/list-members/add-member on Group B → 403; unauthenticated → 401 |
| `common/tests/test_idempotency.py` | same key → one row + replay header; different keys → distinct rows; no key → not idempotent |
| `api/tests/test_phase_2b_smoke.py` | the full brief §43 flow end-to-end + Business A ✗ Business B + Group A ✗ Group B |

**Frontend — 11 pass (was 9).** New: `features/org/BusinessesPage.test.tsx`
(renders the list; creates a business and refreshes).

## 16. Security tests

Mapped to brief §16 / §35 in
[`organization-authorization.md`](organization-authorization.md) §4. All pass:

- Cross-business access (read / update / member list / member add / location
  read) by a Business A member on Business B → **403**.
- Cross-group access (read / manage / member list / member add) by a Group A
  member on Group B → **403**.
- Privilege escalation: Business Staff → member administration → **403**;
  Group DRIVER → group administration → **403**; non-admin → change
  `standing` / operator `status` → **403**.
- Suspended member → any business resource → **403**.
- Deleted / inactive: removed members and soft-deleted locations keep their rows
  (history); a suspended business's `is_operational` is `False`.
- Unauthenticated → any endpoint → **401** problem+json.
- Invalid / malformed ids → **403 or 404**, always `application/problem+json`,
  never a 500 or HTML.
- Every protected mutation produces an audit record (asserted by the smoke test).

## 17. Smoke-test results

`pytest .../test_phase_2b_smoke.py` — **pass**. Also run live against
`docker compose up` (2026-09-09):

```
migrate ran on container start: business/operators/groups [X] applied
1.  POST /businesses                              -> 201, my_role=OWNER
2.  POST /businesses/{id}/members (DISPATCHER)    -> 201
3.  staff GET  /businesses/{id}                   -> 200
4.  staff POST /businesses/{id}/members           -> 403   (owner-only)
5.  POST /operators ; POST /groups               -> 201, group my_role=OWNER
    POST /groups/{id}/members (DRIVER)            -> 201
6.  driver GET  /groups/{id}                      -> 200
7.  driver POST /groups/{id}/members              -> 403   (manage = OWNER/MANAGER)
8.  POST /operating-locations {zone: KITENGELA}   -> 201
9.  owner GET /businesses/{rival_id}              -> 403   (cross-org)
10. verify_chain()                                -> []    (audit chain intact)
    audit actions: business.created, business.member.added, operator.created,
                   group.created, group.member.added, operating_location.created
RESULT: PASS
```

## 18. Files created / modified

**New (backend):** `fikisha/{business,operators,groups}/` (each: `__init__`,
`apps`, `models`, `services`, `authz`, `policies`, `migrations/`, `api/{serializers,
views,urls}`, `tests/`), `fikisha/common/api.py`,
`fikisha/common/idempotency.py`, `fikisha/common/tests/test_idempotency.py`,
`fikisha/api/tests/test_phase_2b_smoke.py`,
`fikisha/platform_config/migrations/0002_zone.py`,
`.../0003_seed_pilot_zone.py`.
**Modified (backend):** `config/settings/base.py` (LOCAL_APPS +
`django.contrib.postgres`), `fikisha/api/urls.py` (include the 3 url modules),
`fikisha/platform_config/models.py` (`Zone`),
`fikisha/platform_config/defaults.py` (OPERATIONS_OFFICER read perms),
`conftest.py` (`make_user`, `client_for`).
**New (frontend):** `src/features/org/*` (7 pages + `orgApi.ts` + `types.ts` +
`BusinessesPage.test.tsx`), `src/i18n/locales/{en,sw}/org.json`.
**Modified (frontend):** `src/app/router.tsx`, `src/shell/TopBar.tsx`,
`src/i18n/index.ts`.
**New (docs):** this file + `identity-and-organizations.md`,
`organization-authorization.md`, `operating-locations.md`,
`phase-2b-decisions.md`.

## 19. Dependencies added

**None.** `django.contrib.postgres` (a Django contrib app, already shipped with
Django) was added to `INSTALLED_APPS` for the `ArrayField`. No new pip or npm
package.

## 20. Deviations from Phase 0 / 1 / 2A

Four, all in [`phase-2b-decisions.md`](phase-2b-decisions.md), none touching an
approved product decision:

| ADR | Deviation |
| --- | --- |
| ADR-2B-02 | `BusinessAccount.standing` gains `SUSPENDED` (approved admin capability) |
| ADR-2B-03 | `BusinessMembership` gains a `status` lifecycle (Phase 1's table had none); `INVITED` reserved, not built |
| ADR-2B-04 | plain `lat`/`lng` instead of PostGIS (documented fallback; brief §19 forbids GIS) |
| ADR-2B-05 | group `standing` is a plain field; the append-only history is deferred to the trust phase |

## 21. Technical decisions

ADR-2B-01 (three new apps, string cross-module FKs) · ADR-2B-06 (403 not 404 for
cross-org) · ADR-2B-07 (minimal `Idempotency-Key`) · ADR-2B-08 (`category` free
text, `verification_status` inert) · ADR-2B-09 (OPERATIONS_OFFICER read-only org
access) · ADR-2B-10 (`django.contrib.postgres`). Details in
[`phase-2b-decisions.md`](phase-2b-decisions.md).

## 22. Known limitations

- Membership `INVITED` state and an invite/accept flow are not built (owner adds
  known staff directly).
- `ServiceArea` (operator work zones/corridors) is deferred to the discovery
  phase; `Zone` is the foundation it will reference.
- No PostGIS / proximity ranking (ADR-2B-04); one seeded zone (D-PIL-5).
- `verification_status` (business, group) and `operator.status` / group
  `standing` are settable but not driven by any workflow in 2B.
- `payout_number`, group-owned vehicles, and `group_standing_change` history are
  deferred to the commission / vehicle / trust phases.
- RLS is still not enabled (Phase 1 OD-10); row scoping is application-layer.
- Idempotency records live in the cache (Redis/locmem), not a durable table.

## 23. Recommended Phase 2C

**Vehicles & verification** — the next dependencies a Job needs:
`Vehicle` (owned by an operator or a group, `owner_kind`), `VehicleDocument`,
`HeavyClassCompliance`; the `Verification` module (`VerificationRecord` per
subject × domain, the reviewer decision flow, expiry sweep, derived
eligibility); then **Trust & Reputation** (trust levels, value ceilings,
admin-confirmed progression). Only after those does a Job's actor graph
(requester, driver, vehicle, eligibility) exist. Keep `ServiceArea` and the
membership invite flow on the list for whichever phase touches discovery /
onboarding.

---

## Exact commands

```bash
# ── Backend ───────────────────────────────────────────────────────────
cd backend
python -m venv .venv && . .venv/Scripts/activate            # or .venv/bin/activate
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.test
export POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=fikisha \
       POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev \
       DJANGO_SECRET_KEY=test-secret \
       REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1

python manage.py migrate                                    # migrations
python manage.py makemigrations --check --dry-run           # -> "No changes detected"
ruff check .                                                # lint
ruff format --check .                                       # formatting
mypy .                                                      # types  -> 0 errors, 110 files
pytest                                                      # 193 passed, ~87% coverage

# ── Frontend ──────────────────────────────────────────────────────────
cd ../frontend
npm ci
npm run lint                                                # eslint
npm run typecheck                                           # tsc --noEmit
npm run test                                                # vitest -> 11 passed
npx vite build                                              # production build -> ok

# ── Docker / smoke ───────────────────────────────────────────────────
cp .env.example .env
docker compose up -d --build                                # full stack
docker compose exec backend python manage.py migrate        # (also runs on container start)
pytest fikisha/api/tests/test_phase_2b_smoke.py             # the §43 flow (in-process)
# or the live curl sequence in §17 against http://localhost:8000
docker compose exec backend python manage.py shell -c \
  "from fikisha.audit.services import verify_chain; print(verify_chain())"   # -> []
docker compose down
```

---

## Status

**PHASE 2B — COMPLETE — AWAITING FOUNDER REVIEW**
Identity, organization, and operating-location foundations are implemented.
No Phase 2C vehicle/verification implementation has been started.
