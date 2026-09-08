# Authentication & Authorization

Implements Phase 0 `FR-A-1..A-10`, `NFR-SEC-2/3/7`, `trust-and-safety.md` §5,
`users-and-roles.md`, `D-ADM-1`.

**Authorization is enforced server-side on every state-changing action.** The
PWA hides controls the user cannot use, for UX only — it enforces nothing
(NFR-SEC-2, brief §19).

---

## 1. Authentication

### 1.1 Account holders (Business, Operator, Group contact) — phone + OTP

```mermaid
sequenceDiagram
    participant C as Client
    participant API
    participant OTP as OTP store (Redis + otp_challenge)
    participant SMS as SMS gateway
    participant S as session / refresh_token

    C->>API: POST /auth/otp/request { phone, purpose: LOGIN }
    API->>API: rate-limit (per phone, per IP); do NOT reveal if phone is registered
    API->>OTP: create challenge (6-digit, code_hash, TTL 5m, max_attempts 5)
    API->>SMS: send code (primary channel; WhatsApp only if configured)
    API-->>C: 202 { challenge_id }  (no indication of registration status)

    C->>API: POST /auth/otp/verify { challenge_id, code }
    API->>OTP: check hash, attempts, TTL; consume on success; lockout on 5 fails
    alt phone not registered
        API->>API: create User (status ACTIVE, locale from Accept-Language, default 'sw' for operator flows)
    end
    API->>S: create session + refresh_token (rotation family)
    API-->>C: 200 { access_token (15m, in memory), refresh via httpOnly cookie }
```

- OTP: 6 digits, **hashed** at rest (`code_hash`), 5-minute TTL, **5 attempts**
  then the challenge is locked (NFR-SEC-7).
- **Rate limits** (Redis token buckets): OTP request — per phone (e.g. 1 / 30 s,
  5 / hour) and per IP; verify — per challenge and per IP. Exceeding →
  `429 Retry-After`.
- **Enumeration-safe**: `POST /auth/otp/request` always returns `202` with a
  `challenge_id`; registration status is never leaked.
- **Account recovery** (FR-A-9): same phone-OTP flow; there is no password to
  reset for standard users. An optional PIN (`credential`) can gate quick re-entry
  on a trusted device but is never the sole factor.
- **Sessions**: opaque server-side session id (RECOMMENDED over stateless JWT for
  the pilot — instant revocation, no key-rotation choreography, ADR-011).
  Access token TTL ~15 min (a short opaque token or a signed token carrying only
  `session_id`); **refresh token** in an `HttpOnly; Secure; SameSite=Strict`
  cookie, TTL ~30 days, **rotated on every use** with **reuse detection**:
  presenting an already-used refresh token revokes the whole session family and
  forces re-auth (NFR-SEC-7).
- **Device / session list**: `session.device_label`, `last_seen_at`; the user can
  see and revoke sessions; logout revokes the current session + its refresh
  family.

### 1.2 Administrators — phone + OTP **+ mandatory TOTP MFA** (NFR-SEC-3)

- Admin accounts are **provisioned internally** (`admin_profile` +
  `role_assignment` created by a Platform Admin), never self-service (FR-A-3).
- First login: phone-OTP **then** forced **TOTP enrolment** (`totp_device`,
  secret envelope-encrypted, backup codes hashed). No admin action is possible
  until `totp_device.confirmed_at` is set.
- Every admin login = phone-OTP **+** a valid TOTP code.
- **Admin session** TTL ≤ 8 h; `is_admin_session = true`.
- **Step-up re-auth** (a fresh TOTP) is required for: platform-config change,
  account suspension/offboarding, binding dispute resolution, high-value
  approval, and **viewing a HIGH-PII document** (the `evidence_access_log` row
  records the step-up). See [security-architecture.md](security-architecture.md).

### 1.3 Recipient (link) — no authentication, link-scoped session

Covered in [recipient-access.md](recipient-access.md): the raw token is exchanged
once for a short-lived, link-scoped bearer bound to `link_id` + `job_id` +
`allowed_actions`; a per-job OTP gates confirm-receipt.

### 1.4 Provider webhooks — signature, not a user

Inbound SMS/WhatsApp delivery receipts and the optional M-Pesa C2B confirmation
authenticate by **HMAC signature / shared secret**, plus an **IP allowlist**
where the provider publishes ranges. Processing is idempotent
([events-and-background-jobs.md](events-and-background-jobs.md)).

---

## 2. Authorization model

### 2.1 One engine, default deny

```
AuthzService.authorize(actor, action, resource) -> Allow | Deny(code, reason)
```

- Called by **every** DRF viewset (a base permission class) **and** by
  application services for object-level checks. A missing check is a bug caught
  by the authorization test matrix ([testing-strategy.md](testing-strategy.md)).
- **RBAC**: the actor's role(s).
- **ABAC**: resource ownership, job participation, verification state, trust
  level / value band, suspension state, group membership, link scope.
- **Default deny**: an `action` with no matching policy rule → `Deny`.

### 2.2 Actor shapes

| Actor | Carries |
|-------|---------|
| `BusinessActor` | `user_id`, `business_id`, `business_membership.role`, `business.standing` |
| `OperatorActor` | `user_id`, `operator_profile_id`, `trust_level`, `value_ceiling`, `operator.status`, verification eligibility flags, `managed_group_ids`, `member_of_group_id` |
| `RecipientActor` | `link_id`, `job_id`, `allowed_actions` (no `user_id`) |
| `AdminActor` | `user_id`, `roles[]`, `is_step_up_fresh` |
| `SystemActor` | scheduler / event-handler identity (for audit attribution of automated transitions) |

### 2.3 Permissions

- **User-role permissions** (Business, Operator) are a fixed set in code (they
  don't change during the pilot).
- **Admin permissions** come from `platform_config.role_permissions`
  (`{role: [permission...]}`) — so switching the pilot's **2 roles** to the
  **4-role split** (Verifier / Operations / Dispute Officer / Platform Admin) is a
  **config change**, not a deploy (FR-ADM-8, D-ADM-1). `role_assignment` maps
  user→role; the engine resolves `permissions = ⋃ role_permissions[r] for r in
  roles`.
- Changing `role_permissions` is itself a guarded, versioned, step-up action.

---

## 3. Permission matrix (representative — not exhaustive)

`✓` allowed · `✓*` allowed with an attribute condition · `—` denied ·
`A` = audited intervention (always logged with reason)

| Action | Business | Operator (individual) | Group MANAGER | Group DRIVER | Recipient (link) | Operations Officer | Platform Admin |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Register / manage own profile | ✓ | ✓ | ✓ (group) | ✓ (own) | — | — | ✓ |
| Add / edit business locations | ✓* own | — | — | — | — | — | ✓ A |
| Register vehicles / bases | — | ✓* own | ✓* group | — | — | — | ✓ A |
| Submit verification evidence | ✓* (business) | ✓* own | ✓* group + members | ✓* own | — | — | — |
| **Decide** verification (approve/reject) | — | — | — | — | — | ✓ (Verifier perm) | ✓ |
| Set / confirm trust level | — | — | — | — | — | propose only | confirm / impose Restricted |
| Create / publish a job | ✓* verified + location | — | — | — | — | — | ✓ A |
| Discover jobs | — | ✓* eligible | ✓* group eligible | ✓* if `DRIVER_ACCEPTS` | — | view all | view all |
| Place negotiation offer/counter/accept | ✓* own job, any thread | ✓* own thread only | ✓* group threads | ✓* if allowed | — | `ADMIN` entry as intervention A | A |
| Read a negotiation thread | ✓* all threads on own job | ✓* own thread only | ✓* group threads | ✓* own thread | — | ✓ all | ✓ all |
| Confirm a job (accept) | ✓* own job | ✓* own thread | ✓* group thread | ✓* if allowed | — | A | A |
| Assign driver + vehicle | — | ✓* self + own vehicle | ✓* member driver + group vehicle | — | — | reassign A | reassign A |
| **Job status transition** (custody steps) | in-app pickup confirm ✓* own job | ✓* assigned driver | — | ✓* assigned driver | confirm-receipt ✓* (DELIVERED) | force-transition A | force-transition A |
| Mark AT_PICKUP / PICKED_UP / IN_TRANSIT / AT_DESTINATION | — | ✓* assigned driver | — | ✓* assigned driver | — | A | A |
| Cancel a job | ✓* own, allowed states | ✓* assigned, allowed states | ✓* group job | ✓* assigned | — | A | A |
| High-value job approval | — | — | — | — | — | ✓ (HIGH); — (VERY_HIGH) | ✓ (all) |
| Open an incident | ✓* own job | ✓* own job | ✓* group job | ✓* assigned job | ✓* this job | ✓ A | ✓ A |
| Add statement / evidence to an incident | ✓* party | ✓* party | ✓* party | ✓* party | ✓* this job | ✓ | ✓ |
| Facilitate amicable resolution | — | — | — | — | — | ✓ | ✓ |
| **Binding** dispute resolution | — | — | — | — | — | ✓* STANDARD band only | ✓ (all bands) |
| Rate the other party | ✓* completed job | ✓* completed job | ✓* completed job | ✓* completed job | — | — | — |
| View operator reputation summary | ✓ | own | own group | own | — | ✓ | ✓ |
| View raw ID / licence document | — | own (thumbnail of own doc) | — | own | — | ✓ (Verifier perm) + step-up, logged | ✓ + step-up, logged |
| View a job's chain of custody | ✓* own job | ✓* own/assigned job | ✓* group job | ✓* assigned job | milestones only (link view) | ✓ all | ✓ all |
| Commission statement (own) | — | ✓* own | ✓* group | — | — | view | ✓ |
| Record settlement / adjustment | — | — | — | — | — | record settlement A | ✓ A (adjustments) |
| Suspend / restrict / offboard an account | — | — | — | — | — | — | ✓ A + step-up |
| Change platform configuration | — | — | — | — | — | — | ✓ A + step-up + rationale |
| View the audit log | — | — | — | — | — | ✓ (scoped) | ✓ |
| Data-export (CSV) | — | — | — | — | — | ✓ A | ✓ A |

Notes:
- The **4-role split** re-partitions the Operations Officer column: `Verifier`
  keeps verification rows; `Operations` keeps job-monitor/intervention rows;
  `Dispute Officer` keeps incident/dispute rows; `Platform Admin` unchanged.
  This is achieved by editing `role_permissions`, no code change.
- **Every `A` action** writes an `admin_intervention` + `audit_log_entry` with a
  mandatory `reason` and `before`/`after` (FR-ADM-9, brief §34 P11) —
  **including when the actor is the founder** (Platform Admin). There is no
  silent superuser path.

---

## 4. Object-level checks (IDOR / BOLA defence — brief §25)

Every endpoint that names a resource id runs an object-level check **after** the
role check:

| Resource | Ownership predicate |
|----------|---------------------|
| `job` | `job.business_id == actor.business_id` (business) · `assignment.assigned_driver_profile_id == actor.operator_profile_id` OR `job` in a thread owned by `actor` (operator) · `link.job_id == resource.id` (recipient) · role-based (admin) |
| `negotiation_thread` | `thread.operator_id == actor.operator_profile_id OR thread.group_id in actor.managed_group_ids` (operator) · `thread.job.business_id == actor.business_id` (business) |
| `evidence_object` | via `linked_entity` → the same predicate as the linked job/incident/verification; verification docs → Verifier permission only |
| `commission_statement` | `statement.payee_id == actor.operator_profile_id / group_id` |
| `incident` | `actor` is a party to the incident's job, or admin, or the recipient link for that job |

- Public identifiers are **UUIDv7** (non-sequential) so an id cannot be guessed
  or walked (defence in depth; not a substitute for the check).
- **PostgreSQL RLS** on the highest-risk tables is a RECOMMENDED second layer
  (ADR-004): a query that forgets the `WHERE` still returns nothing.

---

## 5. Session & token security summary

| Control | Value |
|---------|-------|
| Transport | TLS 1.2+ only; HSTS; secure cookies |
| Access token | ~15 min; carries `session_id` only (or opaque); sent in `Authorization: Bearer` |
| Refresh token | ~30 days; `HttpOnly; Secure; SameSite=Strict` cookie; **rotated every use**; reuse → family revoke |
| CSRF | Bearer-header API is not CSRF-exposed; the refresh cookie is `SameSite=Strict` and the refresh endpoint also checks an `Origin`/`Sec-Fetch-Site` allowlist |
| XSS token theft | access token in **memory only** (never `localStorage`); strict CSP; refresh cookie is `HttpOnly` so JS can't read it |
| Admin session | ≤ 8 h; TOTP required; step-up for sensitive actions |
| Logout | revokes session + refresh family server-side (instant, because sessions are server-side) |
| Brute force | rate limits + lockout on OTP; account lock + alert on repeated auth failures; recipient-link 404-storm alerting |
| Privilege escalation | role changes are Platform-Admin-only, step-up, audited; no self-grant; `role_permissions` change is guarded + versioned |
| Replay | `Idempotency-Key` on mutations; OTPs single-use; a nonce on step-up confirmations |
