# Testing Foundation

## Backend — pytest

- **Runner:** `pytest` + `pytest-django`, config in `backend/pyproject.toml`.
- **Settings:** `config.settings.test` — `DEBUG=False`, locmem cache,
  `CELERY_TASK_ALWAYS_EAGER=True`, `OTP_DEV_FIXED_CODE="000000"`, MD5 password
  hasher (speed), demo endpoints enabled.
- **Coverage:** `--cov=fikisha`, term + XML report. **114 tests, ~90% line
  coverage.**
- **Warnings are errors:** `filterwarnings = ["error::DeprecationWarning:fikisha.*"]`
  — our own deprecations fail the suite.

```bash
cd backend
pytest                                    # full suite + coverage
pytest fikisha/identity -q                # one module
pytest -k "otp or session" -q             # by name
pytest fikisha/audit/tests/test_audit.py::test_verify_chain_detects_a_seq_gap
```

Needs a reachable Postgres + Redis. With the compose stack up:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.test
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export POSTGRES_DB=fikisha POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev
export DJANGO_SECRET_KEY=test-secret
export REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1
pytest
```

### Layout

| File | Covers |
| --- | --- |
| `common/tests/test_common.py` | UUIDv7 (version/variant bits, ordering, uniqueness), `Money` (minor units only, rejects float/bool), `RequestID` middleware, `RateLimiter` (limit, isolation, fail‑closed) |
| `audit/tests/test_audit.py` | chain links + verifies, head tracks tail, empty first `prev_hash`, `verify_chain` detects bad hash + seq gap, ORM + QuerySet mutation raises, **DB triggers block raw UPDATE/DELETE**, `record()` outside a transaction raises |
| `outbox/tests/test_outbox.py` | `emit()` outside a transaction raises, **state + outbox commit together**, **rollback leaves neither row**, drain publishes + runs handler once, handler idempotent on reprocess, **poison event retries then dead‑letters** |
| `platform_config/tests/test_config.py` | bootstrap seeds v1, `get(path)` resolution, `apply_change` validates + versions + audits + emits, rejects empty rationale, historical snapshots preserved |
| `identity/tests/test_phone.py` | Kenya normalisation (`07…`, `01…`, `254…`, `00254…`, `+…`), rejects junk, masking |
| `identity/tests/test_otp.py` | request creates hashed challenge + audit, per‑minute rate limit, verify success creates user, wrong / expired / already‑used / too‑many‑attempts / unknown challenge |
| `identity/tests/test_sessions.py` | start issues access+refresh, resolve rejects garbage / revoked / inactive, **refresh rotates**, **reuse detection revokes the family**, refresh rejects expired, own‑session revoke works, another user's does not |
| `identity/tests/test_authz_engine.py` | default deny, exact vs wildcard resolution, admin permissions from config, `require()` raises `AuthorizationError` |
| `identity/tests/test_api.py` | full OTP→verify→`/me` flow, refresh rotates the token, logout revokes, bad OTP → problem+json, unauthenticated + malformed bearer, **vertical escalation** (admin route), **horizontal escalation / IDOR** (another user's session → 404), reference endpoint, **demo endpoint audit+outbox atomicity** incl. `?fail=1` rollback |
| `api/tests/test_health_and_errors.py` | `/healthz` `/readyz` `/api/v1/health/` (no infra leak), unknown route → problem+json 404, **malformed JSON body → 400**, **missing field → field errors**, **invalid UUID in path → not a 500**, request‑id header echoed |
| `storage/tests/test_storage.py` | local backend put/stat/open/delete, path‑traversal rejected, signed token round‑trips, S3 backend raises `NotImplementedError` |

## Frontend — vitest

- **Runner:** `vitest` + `@testing-library/react`, jsdom, config in
  `frontend/vite.config.ts`. **9 tests.**

```bash
cd frontend
npm run test          # once
npm run test:watch
```

| File | Covers |
| --- | --- |
| `components/Button.test.tsx` | fires `onClick`, disabled + `aria-busy` while `loading` |
| `services/apiClient.test.ts` | parses JSON + attaches bearer, throws typed `ApiError` with the problem+json `code`, **refreshes once on 401 then retries**, **notifies subscribers and gives up when refresh fails** |
| `features/auth/LoginPage.test.tsx` | walks phone → code → verified (dev code pre‑filled), shows a **localized** error when the code is rejected |
| `shell/LanguageSwitcher.test.tsx` | switches the active language to Swahili and persists it |

`src/test/renderWithProviders.tsx` wraps a component in i18n + QueryClient +
MemoryRouter (+ AuthProvider) for realistic rendering.

## The required security tests (Phase 2A brief §30)

| Requirement | Where |
| --- | --- |
| Invalid / expired OTP rejected | `test_otp.py`, `test_api.py::test_bad_otp_returns_problem_json` |
| Too many OTP attempts locks the challenge | `test_otp.py::test_verify_too_many_attempts_locks` |
| A used OTP cannot be reused | `test_otp.py::test_verify_already_used` |
| Unauthorized access to a protected resource is denied | `test_api.py::TestUnauthenticated` |
| User A cannot access User B's resources (IDOR/BOLA) | `test_api.py::test_user_cannot_revoke_another_users_session`, `test_user_lists_only_own_sessions` |
| An ordinary user cannot reach admin resources | `test_api.py::test_plain_user_cannot_hit_admin_route` (403), `test_anonymous_cannot_hit_admin_route` (401) |
| Malformed requests handled gracefully | `test_health_and_errors.py::test_malformed_json_body_is_problem_json`, `test_missing_required_field_returns_field_errors` |
| Missing authentication handled | `test_api.py::test_me_requires_auth`, `test_reference_requires_auth` |
| Invalid IDs handled | `test_health_and_errors.py::test_invalid_uuid_in_path_is_not_a_server_error` |
| Rate limiting works | `test_common.py` (`RateLimiter`), `test_otp.py::test_request_rate_limited_per_minute` |
| Audit records generated for sensitive actions | `test_otp.py` (`auth.otp.requested` / `auth.otp.verified`), `test_config.py` (`platform_config.changed`), `test_api.py` (`user.profile.updated`, `demo.atomic`) |

## What is deliberately **not** tested in 2A

No tests exist for Jobs, negotiation, assignment, custody, trust, verification,
delivery, commission, disputes, recipient links, ratings, or provider
integrations — none of that is implemented.
