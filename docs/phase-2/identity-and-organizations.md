# Identity & Organization Domain (Phase 2B)

The actors and organizational structures a future **Job** depends on:

```
User (Phase 2A)
 ├── BusinessAccount ──< BusinessMembership >── User
 │        └──< BusinessLocation
 └── OperatorProfile (1:1 User)
          ├──< GroupMembership >── OperatorGroup
          └──< BaseMembership  >── OperatingBase
OperatorGroup ──< BaseMembership >── OperatingBase
```

Nothing about Jobs, negotiation, assignment, vehicles, verification, trust,
custody, commission, disputes, ratings, or provider integrations is implemented.
Relationships are shaped so those can be added later without a rewrite.

---

## 1. Modules

| Django app | Owns | Public surface |
| --- | --- | --- |
| `fikisha.business` | `BusinessAccount`, `BusinessMembership`, `BusinessLocation` | `business.services`, `business.authz`, `business.policies` |
| `fikisha.operators` | `OperatorProfile`, `OperatingBase`, `BaseMembership` | `operators.services`, `operators.authz`, `operators.policies` |
| `fikisha.groups` | `OperatorGroup`, `GroupMembership` | `groups.services`, `groups.authz`, `groups.policies` |
| `fikisha.platform_config` (extended) | `Zone` | `platform_config` (config) |

Module rule (unchanged from Phase 1 / 2A): a module uses another module only
through its `services` / `authz` surface or via domain events. Cross‑module
foreign keys use **string references** (`"operators.OperatorProfile"`), so no
module imports another's model class.

---

## 2. Data model

### 2.1 `BusinessAccount` — `business_account`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUIDv7 PK | |
| `owner_user` | FK → `identity.User` `PROTECT` | the registering user; never orphaned |
| `trading_name` | text | required |
| `category` | text | free text (Phase 1's `business_category` lookup table is deferred) |
| `contact_name` / `contact_phone` / `contact_email` | text | optional |
| `standing` | enum `GOOD \| RESTRICTED \| SUSPENDED` | Phase 1 had `GOOD \| RESTRICTED`; `SUSPENDED` added (ADR‑2B‑02). Only a platform admin changes it. `SUSPENDED` is checked by authorization. |
| `verification_status` | enum `UNVERIFIED \| VERIFIED` | **inert** — no verification workflow in 2B; the field exists for the future |
| `created_at` / `updated_at` | timestamptz | |

Indexes: `owner_user`, `standing`.

**Deliberately omitted in 2B:** `registration_ids` (KRA PIN / registration number
— collection & handling *requires Kenyan professional validation*, legal‑scope
§7; added with the verification phase).

### 2.2 `BusinessMembership` — `business_membership`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUIDv7 PK | |
| `business` | FK → `BusinessAccount` `CASCADE` | |
| `user` | FK → `identity.User` `CASCADE` | |
| `role` | enum `OWNER \| DISPATCHER \| VIEWER` | Phase 1 domain‑architecture §3.2 |
| `status` | enum `ACTIVE \| SUSPENDED \| REMOVED` | lifecycle (ADR‑2B‑03) — Phase 1's table had no status; `INVITED` is reserved for a later invite/accept flow |
| `invited_by` | FK → `identity.User` `SET_NULL` | |

Constraints: `unique(business, user)`. Indexes: `(business, status)`,
`(user, status)`.

**Invariant:** a business always keeps **at least one `ACTIVE` `OWNER`**.
Demoting, suspending, or removing the last active owner returns
`409 last_owner`. Enforced in the service layer (`_active_owner_count`).

### 2.3 `BusinessLocation` — `business_location`

| Field | Type | Notes |
| --- | --- | --- |
| `label` | text | |
| `type` | enum `MAIN \| BRANCH \| WAREHOUSE \| STORE \| PICKUP_POINT` | FR‑B‑1 |
| `address_text` | text | |
| `lat` / `lng` | decimal(9,6) nullable | **plain lat/lng, no PostGIS** (ADR‑2B‑04) |
| `zone` | FK → `platform_config.Zone` `SET_NULL` | |
| `contact_name` / `contact_phone` | text | |
| `hours` | jsonb | operating hours |
| `access_notes` | text | |
| `deactivated_at` | timestamptz nullable | **soft delete** (FR‑B‑3) |

Constraints: a **partial unique index** enforces exactly one active `MAIN` per
business (`unique(business) WHERE type='MAIN' AND deactivated_at IS NULL`).
Promoting a location to `MAIN` demotes the previous `MAIN` to `BRANCH` in the
same transaction. Index: active locations per business.

### 2.4 `OperatorProfile` — `operator_profile`

| Field | Type | Notes |
| --- | --- | --- |
| `user` | O2O → `identity.User` `CASCADE` | one profile per user |
| `full_name` | text | required |
| `display_name` | text | optional |
| `phones` | `text[]` (Postgres `ArrayField`) | extra numbers; the login phone stays on `User` |
| `status` | enum `PENDING \| ACTIVE \| RESTRICTED \| SUSPENDED \| OFFBOARDED` | Phase 1's exact enum; only a platform admin changes it. **No verification drives it in 2B.** |

Index: `status`. **Omitted in 2B:** `payout_number` (HIGH‑PII, commission domain
— added with commission, alongside real envelope encryption).

### 2.5 `OperatingBase` — `operating_base`

| Field | Type | Notes |
| --- | --- | --- |
| `name` | text | as known locally |
| `type` | enum `STAGE \| BASE \| YARD \| WAITING_AREA` | Phase 1 exact |
| `lat` / `lng` | decimal(9,6) nullable | plain lat/lng (ADR‑2B‑04) |
| `zone` | FK → `Zone` `SET_NULL` | |
| `landmark` | text | |
| `created_by` | FK → `identity.User` `SET_NULL` | who added the place |

A base is **a place, not a possession** — see
[`operating-locations.md`](operating-locations.md).

### 2.6 `BaseMembership` — `base_membership`

An operator **or** a group declares operating presence at a base.

| Field | Type | Notes |
| --- | --- | --- |
| `base` | FK → `OperatingBase` `CASCADE` | |
| `operator` | FK → `OperatorProfile` nullable `CASCADE` | |
| `group` | FK → `OperatorGroup` nullable `CASCADE` | |
| `role` | text | free text (`owner` / `member`) — a claim of presence, not formal ownership |
| `status` | enum `ACTIVE \| INACTIVE` | leaving a base sets `INACTIVE` |

Constraints: a `CHECK` that **exactly one** of `operator` / `group` is set (two
nullable typed FKs, per Phase 1 database‑design §4.3's recommendation over a raw
polymorphic column); `unique(base, operator)` and `unique(base, group)` partials.

### 2.7 `OperatorGroup` — `operator_group`

| Field | Type | Notes |
| --- | --- | --- |
| `name` | text | |
| `type` | enum `YARD_OWNER \| FLEET \| SACCO \| PARTNERSHIP` | Phase 1 exact |
| `primary_contact` | FK → `identity.User` `PROTECT` | always set |
| `standing` | enum `GOOD \| RESTRICTED \| SUSPENDED` | plain admin lever (the append‑only `group_standing_change` history is a trust‑phase concern — ADR‑2B‑05) |
| `assignment_mode` | enum `MANAGER_ASSIGNS \| DRIVER_ACCEPTS` | default `MANAGER_ASSIGNS` |
| `verification_status` | enum `UNVERIFIED \| VERIFIED` | inert |

Index: `standing`. **Omitted:** `payout_number`, `group_standing_change`.

### 2.8 `GroupMembership` — `group_membership`

| Field | Type | Notes |
| --- | --- | --- |
| `group` | FK → `OperatorGroup` `CASCADE` | |
| `operator` | FK → `operators.OperatorProfile` `CASCADE` | membership is by operator profile, not raw user |
| `role` | enum `OWNER \| MANAGER \| DRIVER` | Phase 1 exact |
| `status` | enum `ACTIVE \| INACTIVE` | Phase 1 ER diagram |
| `added_by` | FK → `identity.User` `SET_NULL` | |
| `since` | timestamptz | |

Constraints: `unique(group, operator)`; a **partial unique**
`unique(operator) WHERE status='ACTIVE'` — an operator is an active member of at
most one group (MVP simplification). Index: `(group, role, status)` ("assignable
drivers"). **Invariant:** a group keeps at least one `ACTIVE` `OWNER`
(`409 last_owner` otherwise).

### 2.9 `Zone` — `config_zone`

`code` (unique) · `name_en` · `name_sw` · `active` · `sort_order`. Seeded with a
single `KITENGELA` row (D‑PIL‑5). No polygon geometry — see
[`operating-locations.md`](operating-locations.md) §4.

---

## 3. Services (the only write paths)

Every mutation is one `transaction.atomic` with its audit row written in the
same transaction (Phase 1 NFR‑AUD‑1). Signatures (selected):

```
business.services
  create_business(*, actor, trading_name, ...) -> BusinessAccount
  update_business(*, actor, business, patch, is_platform_admin=False)
  add_member(*, actor, business, phone, role) -> BusinessMembership     # emits business.member.added
  update_membership(*, actor, business, membership, role=None, status=None)
  remove_member(*, actor, business, membership)
  create_location / update_location / deactivate_location
  businesses_for(user) / membership_for(user, business_id)

operators.services
  create_profile(*, actor, full_name, display_name="", phones=None)
  update_profile(*, actor, profile, patch, is_platform_admin=False)
  create_base / update_base
  associate_operator / associate_group / end_association
  profile_for(user) / bases(base_type=None, zone_id=None)

groups.services
  create_group(*, actor, name, type, assignment_mode=...) -> OperatorGroup
  update_group(*, actor, group, patch, is_platform_admin=False)
  add_member(*, actor, group, operator, role) -> GroupMembership        # emits group.member.added
  update_member / remove_member
  groups_for(user)
```

---

## 4. API

All under `/api/v1/`, using the Phase 2A conventions (Bearer auth, RFC 9457
problem+json, `{data, page}` cursor pagination, `Idempotency-Key` on creates).

### Businesses
| Method + path | Action | Who |
| --- | --- | --- |
| `GET /businesses` | `business.list` | any authed (scoped to your memberships) |
| `POST /businesses` | `business.create` | any authed (you become `OWNER`) |
| `GET /businesses/{id}` | `business.read` | member, or admin |
| `PATCH /businesses/{id}` | `business.update` | `OWNER`, or platform admin (standing only) |
| `GET /businesses/{id}/members` | `business.member.list` | member, or admin |
| `POST /businesses/{id}/members` | `business.member.manage` | `OWNER`, or platform admin |
| `PATCH \| DELETE /businesses/{id}/members/{mid}` | `business.member.manage` | `OWNER`, or platform admin |
| `GET \| POST /businesses/{id}/locations` | `business.location.read` / `.manage` | read: member; manage: `OWNER`/`DISPATCHER` |
| `GET \| PATCH \| DELETE /businesses/{id}/locations/{lid}` | as above | |

### Operators & operating locations
| Method + path | Action | Who |
| --- | --- | --- |
| `POST /operators` | `operator.create` | any authed (own profile, one per user) |
| `GET /operators/me` | `operator.read.me` | any authed (404 if none) |
| `GET \| PATCH /operators/{id}` | `operator.read` / `.update` | own profile, or admin (status: admin only) |
| `GET \| POST /operators/{id}/bases` | `operator.read` / `.update` | own profile, or admin |
| `DELETE /operators/{id}/bases/{mid}` | `operator.update` | own profile, or admin |
| `GET /operating-locations` `?type=&zone=` | `operating_location.read` | any authed |
| `POST /operating-locations` | `operating_location.create` | any authed **with an operator profile**, or admin |
| `GET \| PATCH /operating-locations/{id}` | `operating_location.read` / `.manage` | read: any authed; manage: creator or admin |

### Groups
| Method + path | Action | Who |
| --- | --- | --- |
| `GET /groups` | `group.list` | any authed (scoped) |
| `POST /groups` | `group.create` | any authed **with an operator profile** |
| `GET /groups/{id}` | `group.read` | active member, or admin |
| `PATCH /groups/{id}` | `group.update` | `OWNER`/`MANAGER`, or platform admin (standing only) |
| `GET /groups/{id}/members` | `group.member.list` | active member, or admin |
| `POST \| PATCH \| DELETE /groups/{id}/members[/{mid}]` | `group.member.manage` | `OWNER`/`MANAGER`, or platform admin |
| `GET \| POST /groups/{id}/bases` , `DELETE /groups/{id}/bases/{mid}` | `group.read` / `group.update` | read: member; manage: `OWNER`/`MANAGER` or admin |

Full authorization rules: [`organization-authorization.md`](organization-authorization.md).

---

## 5. Events

The outbox is used **only** where 2B has a real future async side effect:

| Event | Emitted by | Payload | Consumer (2B) |
| --- | --- | --- | --- |
| `business.member.added` | `business.services.add_member` | `{business_id, user_id, role, added_by}` | none — the contract for a future "you were added" notification |
| `group.member.added` | `groups.services.add_member` | `{group_id, operator_id, role, added_by}` | none — same |

No SMS/WhatsApp/e‑mail integration is wired (brief §40).

---

## 6. Audit

Every organisation mutation writes an `audit_log_entry` (Phase 2A `audit.record`)
**in the same transaction** as the change, including a platform admin's actions.
Actions recorded: `business.created`, `business.updated`, `business.member.added`,
`business.member.updated`, `business.member.removed`, `business.location.added`,
`business.location.updated`, `business.location.deactivated`, `operator.created`,
`operator.updated`, `operating_location.created`, `operating_location.updated`,
`operating_location.operator_associated`, `operating_location.group_associated`,
`operating_location.association_ended`, `group.created`, `group.updated`,
`group.member.added`, `group.member.updated`, `group.member.removed`. No second
audit system; the Phase 2A hash chain still verifies (`verify_chain()` → `[]`).
