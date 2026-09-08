# Security Baseline

The security properties the Phase 2A foundation guarantees, and exactly where
each is enforced. Everything here is covered by automated tests
(`testing-foundation.md` §4).

---

## 1. Authentication — phone + one‑time code, opaque server‑side sessions

**Model (Phase 1 ADR‑011).** There is no stateless JWT. A login produces:

- a row in `identity_authsession` (the real session; server‑side, revocable);
- a **short signed access token** (`ACCESS_TOKEN_TTL_SECONDS`, default 900s) that
  carries only `{sid, uid, nonce}` — signed with `django.core.signing`, not a
  bearer of claims. `resolve_session()` loads the `AuthSession` and re‑checks it
  on every request;
- a **rotating refresh token**, delivered as an `HttpOnly` cookie scoped to
  `/api/v1/auth/`, stored only as a SHA‑256 hash (`identity_refreshtoken`).

**OTP handling** (`identity/services/otp.py`):

| Property | Enforcement |
| --- | --- |
| Codes never stored in clear | `make_password` (Argon2) hash in `OtpChallenge.code_hash`; verified with `check_password` |
| Short TTL | `OTP_TTL_SECONDS` (300s); `is_expired` checked before comparison |
| Attempt cap | `OTP_MAX_ATTEMPTS` (5); the failed‑attempt increment is committed **before** the error is raised (the whole verify is not rolled back) |
| Single use | `consumed_at` set on success; a second verify returns `otp.already_used` |
| Request flooding | `RateLimiter` — per‑phone/minute, per‑phone/hour, per‑IP; **fail‑closed** (a cache error denies) |
| Enumeration resistance | unknown challenge and wrong code both return `otp.invalid` with the same shape |

**Session lifecycle** (`identity/services/auth.py`):

- `refresh()` rotates the refresh token every use. If a **spent** token is
  presented again, the whole session is revoked, an
  `auth.refresh_reuse_detected` audit row is written (in its own transaction so
  it survives), and the caller gets `auth.refresh_reuse`.
- `logout()` revokes the session; the access token stops resolving immediately
  (the session is re‑checked per request, not just per token expiry).

---

## 2. Authorization — central engine, default deny

`authorize(actor, action, resource) -> Decision` (`identity/authz/engine.py`).

- **Default deny.** An action with no registered policy returns
  `authz.no_policy`. Nothing is permitted implicitly.
- **Actor**, not `request.user`, is the subject: `AnonymousActor`,
  authenticated `Actor` (carries roles + session + `is_step_up_fresh`), or
  `SystemActor` for schedulers/handlers.
- **Admin permissions come from `platform_config.role_permissions`**, not from
  code. `PLATFORM_ADMIN` has `["*"]`; `"*"` short‑circuits to allow. Changing an
  admin's capability is a config change (audited + versioned), not a deploy.
- **Row‑level checks** live in the policy functions (e.g.
  `auth.session.revoke` requires `resource.user_id == actor.user.id`) —
  application‑layer authorization per ADR‑004. Postgres RLS is left as an
  optional later hardening; the app layer is the enforcement point in 2A.
- **DRF integration:** `ActionPermission` reads `view.required_action`, calls the
  engine, and distinguishes **401** (`NotAuthenticated`, for an unauthenticated
  caller) from **403** (`AuthorizationError`, for an authenticated caller who is
  not allowed). `BearerSessionAuthentication` returns `None` (anonymous) when no
  header is present and raises `auth.header_invalid` on a malformed one.

### Tested attack shapes (all pass)

| Attack | Expected | Test |
| --- | --- | --- |
| Invalid / wrong OTP | 401 `otp.invalid` | `test_otp.py::test_verify_wrong_code`, `test_api.py::test_bad_otp_returns_problem_json` |
| Expired OTP | 401 `otp.expired` | `test_otp.py::test_verify_expired` |
| OTP reused after success | 401 `otp.already_used` | `test_otp.py::test_verify_already_used` |
| > 5 OTP attempts | 401 `otp.too_many_attempts`, even for the right code | `test_otp.py::test_verify_too_many_attempts_locks` |
| Refresh‑token replay | session revoked + audited | `test_sessions.py` (reuse detection) |
| No `Authorization` header on a protected route | 401 problem+json | `test_api.py::test_me_requires_auth` |
| Malformed / over‑long bearer | 401 | `test_api.py::test_malformed_bearer_rejected`, `test_bearer_with_extra_parts_rejected` |
| Ordinary user → admin route (`/api/v1/admin/ping`) | 403 `authz.forbidden` | `test_api.py::test_plain_user_cannot_hit_admin_route` |
| Anonymous → admin route | 401 | `test_api.py::test_anonymous_cannot_hit_admin_route` |
| User A revokes User B's session (IDOR/BOLA) | 404 (existence not revealed) + B's session untouched | `test_api.py::test_user_cannot_revoke_another_users_session` |
| User A lists sessions | only A's own | `test_api.py::test_user_lists_only_own_sessions` |
| Unknown `/api/v1/*` path | 404 problem+json (not HTML) | `test_health_and_errors.py` |
| Malformed JSON body / bad UUID | 400 problem+json | `test_health_and_errors.py` |
| Rate‑limit exceeded | 429 with `Retry-After` | `test_common.py` (RateLimiter), `test_otp.py::test_request_rate_limited_per_minute` |

---

## 3. The dev OTP mechanism is not a fake production auth system

Two switches, both **off by default** in `config/settings/base.py`:

| Switch | Dev | Test | **Prod** | Effect when on |
| --- | --- | --- | --- | --- |
| `OTP_DEV_EXPOSE` | `true` | `true` | **`false` — forced** | the OTP request response includes `dev_code`; the code is logged at DEBUG |
| `OTP_DEV_FIXED_CODE` | `""` | `"000000"` | **`"" ` — forced** | every challenge also accepts this constant |

`config/settings/prod.py` sets both to their safe values **unconditionally**
(not from the environment) — there is no env var that can re‑enable them in
production:

```python
AUTH_CONFIG["OTP_DEV_EXPOSE"] = False
AUTH_CONFIG["OTP_DEV_FIXED_CODE"] = ""
```

The real code path is identical in every environment: generate → Argon2‑hash →
store → compare → consume. Dev mode only changes **what is generated** and
**whether it is echoed back**; it does not bypass hashing, TTL, attempt caps,
rate limiting, or single‑use. Delivery (`_deliver`) is a logging stub — no SMS
provider exists yet, and that is stated plainly, not faked.

---

## 4. MFA — foundation only, not claimed as implemented

Present:

- `identity.TotpDevice` model (`secret_encrypted`, `confirmed_at`);
- `Actor.is_step_up_fresh` flag and an `OtpPurpose.STEP_UP` value;
- policy hooks can already read `actor.is_step_up_fresh`.

**Not present in 2A:** no TOTP secret is generated, provisioned, or verified; no
step‑up challenge is issued; `is_step_up_fresh` is always `False`. See
ADR‑2A‑07. Do not describe Fikisha as having MFA until Phase 2B implements it.

---

## 5. Audit — append‑only, hash‑chained, covers administrative actions

### The founder/admin is audited too

`audit.record(...)` resolves the actor to `(user, role)` for **everyone** —
`PLATFORM_ADMIN` included (`_resolve_actor`). `ConfigService.apply_change`
(the founder's main lever) writes an `platform_config.changed` audit row and an
outbox event in the same transaction. There is **no code path that mutates
sensitive state without an audit row**, and no "admin bypass" flag.

### Nothing can quietly rewrite history — three layers

1. **Service layer.** `audit/services.py` exposes `record()` and `verify_chain()`
   only. There is no update or delete function.
2. **Model layer.** `AuditLogEntry` extends `AppendOnlyModel`: a non‑adding
   `save()` or any `delete()` raises `AppendOnlyModelError`; the manager is an
   `AppendOnlyQuerySet` whose `.update()` / `.delete()` raise as well.
3. **Database layer.** Migration `audit/0003_append_only_db_guard.py` installs a
   `fikisha_forbid_mutation()` PL/pgSQL function and `BEFORE UPDATE` /
   `BEFORE DELETE` triggers on `audit_log_entry` and `platform_config_version`.
   A raw `UPDATE`/`DELETE` (bypassing the ORM entirely) is rejected by Postgres.
   Tested: `test_audit.py::test_db_trigger_blocks_raw_update` / `_delete`.

**Production note.** The triggers are defence‑in‑depth. The intended production
posture is that the application's DB role (`app_rw`) is granted
`SELECT, INSERT` only on these tables:

```sql
REVOKE UPDATE, DELETE ON audit_log_entry, platform_config_version FROM app_rw;
```

This is documented in the migration's docstring. It is not applied automatically
in local dev (the compose Postgres uses a superuser), so the triggers are what
make the guarantee real in every environment today.

### The hash chain

Each row: `row_hash = sha256("{seq}\n{prev_hash}\n{canonical_json(payload)}")`.
`seq` and `prev_hash` come from the `AuditChainHead` singleton (pk=1), taken
under `SELECT … FOR UPDATE`, so the chain is gapless and serialised.
`verify_chain()` walks it and reports `row_hash_mismatch`, `gap_or_reorder`, and
`prev_hash_mismatch`. Tested: `test_audit.py::test_verify_chain_detects_a_bad_row_hash`,
`test_verify_chain_detects_a_seq_gap`.

Audit writes are **not** wrapped in their own transaction — `record()` asserts it
is already inside one (`transaction.get_connection().in_atomic_block`) so the
audit row commits or rolls back **with** the change it records.

---

## 6. Transactional outbox — atomic with the business change

`emit(event_type, aggregate_type, aggregate_id, payload)` asserts
`in_atomic_block` and inserts an `OutboxEvent` row. Because it runs in the
caller's transaction, the event and the state change are **one commit** — no
message broker, no dual‑write gap (ADR‑015).

`drain_outbox` (Celery, scheduled every 3s by beat) claims PENDING rows with
`select_for_update(skip_locked=True)`, runs the registered handlers, marks
`PUBLISHED`, retries with exponential backoff on failure, and dead‑letters after
`OUTBOX_MAX_ATTEMPTS` (5). Handlers are idempotent (keyed on the event id).

**Demonstrative atomicity test** (`test_outbox.py`):

- `test_state_change_and_outbox_commit_together` — a state row and its outbox row
  both exist after commit;
- `test_rollback_leaves_neither_row` — an exception after both writes leaves
  **neither** row;
- `test_poison_event_retries_then_dead_letters` — a handler that always throws is
  retried and finally marked `DEAD`.

The `/api/v1/_demo/atomic-outbox` endpoint exercises the same path end‑to‑end
(`test_api.py::TestDemoAtomicOutbox`), including `?fail=1` proving rollback of
both the audit row and the outbox row.

---

## 7. Transport, headers, input

| Concern | 2A posture |
| --- | --- |
| Error shape | RFC 9457 `application/problem+json` everywhere, with a stable machine `code` and a `request_id`; no stack traces or internal detail leak |
| Security headers | `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`, referrer policy, `SESSION_COOKIE_HTTPONLY`; `prod.py` adds HSTS, SSL redirect, secure cookies |
| CORS | explicit allow‑list from `API_CORS_ALLOWED_ORIGINS`; credentials allowed for the refresh cookie |
| Passwords | Argon2 hasher first in `PASSWORD_HASHERS` (users have unusable passwords — OTP auth) |
| PII in logs | structlog `_scrub` redacts `password`, `token`, `code`, `otp`, `phone`, `id_number`, `payout_number`, … |
| Secrets | never in the repo; `prod.py` requires `DJANGO_SECRET_KEY`; `.env` git‑ignored |
| IDs | UUIDv7 primary keys — non‑sequential, not guessable, part of the IDOR defence |
| Private files | `PrivateStorage` returns an **opaque signed token** pointing at an API path, never a bucket URL; path‑traversal guarded |

---

## 8. Known limitations (explicit)

- **RLS** is not enabled; row authorization is application‑layer only (ADR‑004
  permits this; RLS is optional hardening).
- **`REVOKE UPDATE, DELETE`** on audit tables is documented for production but
  not applied by local compose (triggers cover the gap).
- **MFA / step‑up** is a stub (§4).
- **Envelope encryption for HIGH‑PII** (ADR‑014) has an interface seam only; no
  KMS wiring in 2A.
- **S3 storage backend** raises `NotImplementedError`; only `local` works.
- **Rate limiting** is a fixed window, not a token bucket (ADR‑2A‑05).
