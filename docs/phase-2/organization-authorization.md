# Organization Authorization (Phase 2B)

Extends the Phase 2A authorization engine
(`authorize(actor, action, resource) -> Decision`, default deny) with
**organisation‑level** policies. Platform‑level and organisation‑level
permissions are kept distinct: being an `OWNER` of Business A grants nothing on
Business B, and a group `OWNER` is not a platform admin.

---

## 1. How it plugs in

- Each new module registers its policies in `apps.py::ready()`
  (`business.policies`, `operators.policies`, `groups.policies`).
- Views extend `fikisha.common.api.OrgApiView`: each HTTP method names an authz
  **action** (`action_get` / `action_post` / …); a detail view also implements
  `resolve_target(self)` whose (cached) return value is handed to the policy, so
  the **object‑level check runs before the handler body** — not after a mutation
  has begun.
- `ActionPermission` (Phase 2A) still distinguishes **401** (unauthenticated)
  from **403** (authenticated but not permitted).
- The policy functions resolve the caller's relationship to the specific
  resource **server‑side** (`business.authz.active_membership`,
  `groups.authz.active_membership`, `operators.authz.owns_profile`). A
  client‑supplied role or id is never trusted.

## 2. Platform admins

A policy first asks `actor_has_permission(actor, "<action>")`. `PLATFORM_ADMIN`
has `role_permissions = ["*"]`, so it passes every organisation action (with an
audit row, always). `OPERATIONS_OFFICER` was granted **read‑only**
`business.read` / `operator.read` / `group.read` (FR‑ADM‑1 — "review businesses,
operators"); it cannot mutate organisations.

## 3. Actions and rules

| Action | Allowed for |
| --- | --- |
| `business.list` | any authenticated user (the view returns only *your* businesses) |
| `business.create` | any authenticated user (creator becomes `OWNER`) |
| `business.read` | an `ACTIVE` member of that business (any role), or `business.read` permission |
| `business.update` | an `ACTIVE` `OWNER` of that business, or `*`. `standing` changes: platform admin only (service‑enforced, `403`) |
| `business.member.list` | an `ACTIVE` member, or `business.read` |
| `business.member.manage` | an `ACTIVE` `OWNER`, or `*` |
| `business.location.read` | an `ACTIVE` member, or `business.read` |
| `business.location.manage` | an `ACTIVE` `OWNER` or `DISPATCHER`, or `*` |
| `operator.create` | any authenticated user (own profile, one per user) |
| `operator.read.me` | any authenticated user (always their own profile; `404` if none) |
| `operator.read` / `operator.update` | the profile's own user, or `*`. `status` changes: platform admin only |
| `operating_location.read` | any authenticated user (a stage is a public place) |
| `operating_location.create` | any authenticated user **who has an `OperatorProfile`**, or `*` |
| `operating_location.manage` | the base's `created_by` user, or `*` |
| `group.list` | any authenticated user (scoped to your groups) |
| `group.create` | any authenticated user **who has an `OperatorProfile`** |
| `group.read` / `group.member.list` | an `ACTIVE` member of that group (any role), or `group.read` |
| `group.update` / `group.member.manage` | an `ACTIVE` `OWNER` or `MANAGER`, or `*`. `standing`: platform admin only |

## 4. Object‑level isolation (IDOR / BOLA — brief §16, §35)

- Every detail endpoint resolves the target object and passes it to the policy
  **before** the handler runs.
- An authenticated non‑member of an organisation gets **403**
  (`authz.forbidden`) — not `404`. (Organisation existence is not a secret on a
  marketplace; per‑user resources like sessions still return `404`.) This is a
  deliberate difference from Phase 2A's session IDOR behaviour — ADR‑2B‑06.
- Public identifiers are UUIDv7 (non‑sequential) — defence in depth, not a
  substitute for the check.
- Row scoping is **application‑layer** (ADR‑004). PostgreSQL RLS remains a
  RECOMMENDED later hardening (Phase 1 OD‑10); it is not added in 2B.

### Tested

| Attack | Expected | Test |
| --- | --- | --- |
| Business A member → `GET`/`PATCH` Business B | 403 | `business/tests/test_business_security.py::TestCrossBusiness` |
| Business A member → list / add member on Business B | 403 | same |
| Business A member → read Business B locations | 403 | same |
| Business Staff (`DISPATCHER`) → member administration | 403 | `test_business.py::test_add_staff_and_staff_gets_scoped_access` |
| Suspended member → any business resource | 403 | `test_business.py::test_suspended_member_loses_access` |
| Group A member → read / manage / list members / add member on Group B | 403 | `groups/tests/test_groups_security.py::TestCrossGroup` |
| Group `DRIVER` → add a member | 403 | `test_groups.py::test_manager_adds_a_driver` |
| Non‑operator → create a group / operating location | 403 | `test_groups.py`, `test_operators.py` |
| Operator A → associate Operator B's profile with a base | 403 | `test_operators.py::test_cannot_associate_another_operators_profile` |
| Non‑creator operator → edit an operating base | 403 (but `GET` still 200) | `test_operators.py::test_only_the_creator_can_edit_a_base` |
| Unauthenticated → any list/create/detail | 401 problem+json | `*_security.py::TestUnauthenticated` |
| Unknown / malformed id | 403 or 404, always problem+json | `test_business_security.py::TestInvalidIds` |
| Non‑admin → change `standing` / operator `status` | 403 | `test_business.py`, `test_operators.py` |

## 5. Invariants enforced in the service layer

| Invariant | Where | Failure |
| --- | --- | --- |
| A business keeps ≥ 1 active `OWNER` | `business.services` (`_active_owner_count`) | `409 last_owner` |
| A group keeps ≥ 1 active `OWNER` | `groups.services` | `409 last_owner` |
| One operator profile per user | `operators.services.create_profile` + O2O constraint | `409 conflict` |
| An operator is an active member of ≤ 1 group | `groups.services` + partial unique index | `409 already_in_group` |
| Exactly one active `MAIN` business location | partial unique index + `_demote_existing_main` | promotes/demotes atomically |
| A base membership names exactly one party | DB `CHECK` `base_membership_exactly_one_party` | `IntegrityError` |

## 6. Frontend

The PWA hides controls the current role cannot use (`my_role` from the API), but
this is **UX only** — every boundary above is re‑enforced by the API and covered
by the tests in §4. A `DISPATCHER` sees "read business" and "manage locations"; an
`OWNER` also sees "edit business" and "manage members".
