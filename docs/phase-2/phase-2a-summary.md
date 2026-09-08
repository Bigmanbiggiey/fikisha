# Phase 2A — Foundation Implementation — Summary Report

> **PHASE 2A — COMPLETE — AWAITING FOUNDER REVIEW**
> Foundation implementation is complete.
> No Phase 2B business-domain implementation has been started.

---

## 1. Scope delivered

The technical foundation Fikisha's features will be built on:

- Git repository with `.editorconfig`, `.gitignore`, `.env.example` (names +
  non-secret defaults only), pinned dependency sets.
- Dockerised local environment: one `docker compose up` brings up Postgres,
  Redis, the Django API, a Celery worker, Celery beat, and the React PWA.
- Backend: Django 5.2 + DRF **modular monolith** with six foundation modules —
  `common`, `audit`, `outbox`, `platform_config`, `identity`, `storage`.
- **Authentication foundation** — phone + one-time-code login; opaque
  server-side sessions; short signed access token that only points at a session;
  rotating HttpOnly refresh cookie with reuse detection (Phase 1 ADR-011).
- **Authorization foundation** — one `authorize(actor, action, resource)`
  engine, default-deny, admin permissions sourced from `platform_config`;
  DRF `ActionPermission` distinguishing 401 from 403.
- **Audit foundation** — append-only, hash-chained `audit_log_entry`; the
  founder's/admin's actions are audited on the same path as everyone's; no
  ordinary code can UPDATE/DELETE an audit row (service, model, **and Postgres
  triggers**).
- **Transactional outbox foundation** — `emit()` writes in the emitting
  operation's DB transaction; `drain_outbox` Celery task publishes with retry
  and dead-lettering (Phase 1 ADR-015); demonstrative atomicity tests.
- **Platform configuration foundation** — versioned singleton +
  append-only version history; `apply_change` deep-merges, validates, audits,
  emits.
- Frontend: React 18 + TS + Vite PWA shell — i18n (English + Swahili),
  problem+json-aware API client with transparent 401→refresh→retry, login flow,
  auth/session context, diagnostics page.
- Automated tests: **114 backend (pytest)**, **9 frontend (vitest)**.
- CI: GitHub Actions — backend lint/type/migrations/test, frontend
  lint/type/test/build, `docker compose build`.

## 2. Explicitly NOT delivered (Phase 2A stop line)

No implementation of: Jobs, negotiation, assignment, chain of custody, trust
levels/thresholds, operator verification workflows, operator groups, commission
processing/ledger, disputes, recipient links, ratings/reputation, business
locations, vehicle management, delivery workflows, live GPS, AI matching,
dynamic pricing, or any WhatsApp / SMS / M-Pesa / eTIMS integration. Interfaces
and abstractions exist only where Phase 1 requires them for the foundation
(storage backend ABC, metrics hooks, MFA device model, envelope-encryption
seam).

## 3. Repository structure

See [`project-structure.md`](project-structure.md). Top level: `backend/`,
`frontend/`, `docs/`, `docker-compose.yml`, `.github/workflows/ci.yml`,
`scripts/smoke-test.sh`.

## 4. Technology versions

See [`technology-versions.md`](technology-versions.md). Every pin targets a
stable, maintained release compatible with the rest of the stack — not the
newest available. Key runtimes: Python 3.12, Node 22, PostgreSQL 16, Redis 7,
Django 5.2 LTS, DRF 3.16, React 18.3, Vite 5.4.

## 5. Backend modules

| Module | Responsibility | Key public surface |
| --- | --- | --- |
| `common` | UUIDv7 PKs, append-only base, problem+json, rate limiter, request-id, structured logging, cursor pagination, Money | `models`, `exceptions`, `ratelimit`, `pagination` |
| `audit` | append-only hash-chained audit log | `services.record()`, `services.verify_chain()` |
| `outbox` | transactional outbox + drain worker | `services.emit()`, `registry.register()`, `tasks.drain_outbox` |
| `platform_config` | versioned singleton config | `services.current()/get()/apply_change()` |
| `identity` | users, phone+OTP auth, sessions, authz engine | `services.otp`, `services.auth`, `authz.engine.authorize()`, `authz.permissions.ActionPermission` |
| `storage` | private object storage abstraction | `service.get_storage()`, `base.PrivateStorage` |

Module rule: interact only via another module's `services`/`authz` surface or its
outbox events — never import another module's models.

## 6. Authentication foundation

- `POST /api/v1/auth/otp/request` → `{challenge_id, dev_code?}` (202). `dev_code`
  only present when `OTP_DEV_EXPOSE` is on (dev/test).
- `POST /api/v1/auth/otp/verify` → `{access_token, access_expires_in, user}` +
  `Set-Cookie: fikisha_refresh` (HttpOnly, path `/api/v1/auth/`).
- `POST /api/v1/auth/refresh` (cookie) → new access token, rotated refresh
  cookie. Replaying a spent refresh token revokes the session and writes
  `auth.refresh_reuse_detected`.
- `POST /api/v1/auth/logout` → 204, session revoked.
- OTP codes: Argon2-hashed at rest, 5-minute TTL, 5-attempt lockout,
  rate-limited (per phone/minute, per phone/hour, per IP), single-use.

## 7. Authorization foundation

- `authorize(actor, action, resource) -> Decision`, default-deny
  (`authz.no_policy`).
- Policy resolution: exact action match, then longest wildcard prefix
  (`admin.*`).
- Admin permissions come from `platform_config.role_permissions`
  (`PLATFORM_ADMIN = ["*"]`) — granting/revoking is an audited config change,
  not a deploy.
- Row-level ownership checks live in the policy functions (ADR-004,
  application-layer authorization; RLS is optional later hardening).
- `ActionPermission` reads `view.required_action`; unauthenticated → 401,
  authenticated-but-forbidden → 403; both as problem+json.

## 8. Audit foundation

- `row_hash = sha256("{seq}\n{prev_hash}\n{canonical_json(payload)}")`; `seq` /
  `prev_hash` from the `AuditChainHead` singleton under `SELECT … FOR UPDATE`.
- `record()` runs inside the caller's transaction (asserts `in_atomic_block`),
  so the audit row commits or rolls back with the change.
- Immutability: no service update/delete path; `AppendOnlyModel` /
  `AppendOnlyQuerySet` raise; Postgres `BEFORE UPDATE/DELETE` triggers on
  `audit_log_entry` and `platform_config_version`.
- Production hardening documented: `REVOKE UPDATE, DELETE … FROM app_rw` (in the
  migration docstring; triggers are the always-on guarantee in dev).
- `verify_chain()` detects `row_hash_mismatch`, `gap_or_reorder`,
  `prev_hash_mismatch`.
- **The founder is not exempt.** `ConfigService.apply_change` and every
  sensitive mutation call `audit.record()`; there is no bypass flag.

## 9. Transactional outbox foundation

- `emit(event_type, aggregate_type, aggregate_id, payload)` asserts
  `in_atomic_block`; the event row and the business row are one commit
  (ADR-015, no message broker).
- `drain_outbox` (Celery, scheduled every `OUTBOX_POLL_SECONDS`=3 by beat):
  `select_for_update(skip_locked=True)`, run handlers, `PUBLISHED`; retry with
  exponential backoff; `DEAD` after `OUTBOX_MAX_ATTEMPTS`=5. Handlers idempotent
  on event id.
- Atomicity proven by `test_outbox.py` (commit-together, rollback-leaves-neither,
  poison→dead-letter) and end-to-end by `/api/v1/_demo/atomic-outbox`
  (incl. `?fail=1` rollback of both the audit and outbox rows).

## 10. Platform configuration foundation

- `PlatformConfig` (pk=1) + append-only `PlatformConfigVersion`.
- `DEFAULT_CONFIG` carries the Phase 1 values (commission
  `FLAT_WITH_MIN_CAP` 10% / min KES 40 / cap KES 5,000, value bands, vehicle
  types, role permissions, feature flags, retention windows). **These are
  defaults in code, not an approval to activate any business rule** — nothing
  reads them for a delivery decision in 2A.
- `apply_change(patch, changed_by, rationale)` — non-empty rationale required;
  deep-merge; `validate()`; new version; audit `platform_config.changed`; emit
  `platform_config.changed`. Historical snapshots are preserved (not
  retroactive).

## 11. Frontend foundation

- Vite + `vite-plugin-pwa` (Workbox) app-shell precache. **No API response is
  cached**; the offline-safe vs server-confirmed split is Phase 2B.
- `services/apiClient.ts` — bearer header from an in-memory token (never
  `localStorage`), problem+json parsed to a typed `ApiError`, one transparent
  refresh-and-retry on 401, `onAuthLost` broadcast on give-up.
- `features/auth` — `AuthProvider` resumes a session from the refresh cookie on
  load; `LoginPage` (phone → code, dev code surfaced in dev); `RequireAuth`
  route guard.
- i18n — English + Swahili, namespaces `common` / `auth` / `errors`; server
  error `code`s map to localized strings; language persisted to `localStorage`.
- `features/diagnostics` — calls `/health/` and `/reference`, renders status.
- Design-system primitives: Button, Input, Field, Card, Alert, Spinner,
  StatusBadge, PageLoader, EmptyState, ErrorState.

## 12. Dev OTP safety

Two switches, off by default in `base.py`, **forced off unconditionally in
`prod.py`**: `OTP_DEV_EXPOSE` (echo the code in the response + DEBUG log) and
`OTP_DEV_FIXED_CODE` (accept a constant). The real path — generate → Argon2 hash
→ store → compare → consume, with TTL, attempt cap, rate limit, single-use — is
identical in every environment. Delivery is a logging stub; no SMS provider is
pretended. See [`security-baseline.md`](security-baseline.md) §3.

## 13. MFA status

Foundation only: `identity.TotpDevice`, `OtpPurpose.STEP_UP`,
`Actor.is_step_up_fresh` (always `False`). No secret is generated or verified; no
step-up challenge is issued. Not to be described as "Fikisha has MFA". See
ADR-2A-07.

## 14. Security tests (brief §30)

All present and passing — invalid/expired/reused OTP, attempt lockout,
unauthorized access, IDOR/BOLA (User A cannot touch User B's session — 404,
existence not revealed), vertical escalation (ordinary user → admin route → 403;
anonymous → 401), malformed JSON, missing fields, invalid path IDs, missing
auth, rate limiting, audit records for sensitive actions. Full mapping in
[`testing-foundation.md`](testing-foundation.md) §4.

## 15. Test results

| Suite | Command | Result |
| --- | --- | --- |
| Backend | `cd backend && pytest` | **114 passed**, ~90% line coverage |
| Frontend | `cd frontend && npm run test` | **9 passed** |
| Backend lint | `ruff check . && ruff format --check .` | clean |
| Backend types | `mypy .` | clean (0 errors, 78 files; pragmatic config, ADR-2A-08) |
| Migrations | `python manage.py makemigrations --check --dry-run` | "No changes detected" |
| Frontend lint | `npm run lint` | clean |
| Frontend types | `npm run typecheck` | clean |
| Frontend build | `npm run build` | succeeds |

## 16. CI

`.github/workflows/ci.yml` runs on push/PR to `main`:

- **backend** — Postgres 16 + Redis 7 services; `pip install -r
  requirements/dev.txt`; `ruff check`; `ruff format --check`; `mypy`;
  `makemigrations --check`; `pytest`.
- **frontend** — Node 22; `npm ci`; `npm run lint`; `npm run typecheck`;
  `npm run test`; `vite build`.
- **compose** — `docker compose build` (all service images).

## 17. Deviations from Phase 1

Four, all documented in [`phase-2a-decisions.md`](phase-2a-decisions.md) and none
touching an approved product decision: MFA step-up is a stub (ADR-2A-07); mypy
runs pragmatic not `--strict` (ADR-2A-08); `eslint-plugin-react-hooks` bumped
4→5 for ESLint 9 (ADR-2A-09); `ActorRole.USER` added to the audit enum — a
latent-bug fix (ADR-2A-10).

## 18. No contradiction with the approved architecture

No point where implementing the foundation required contradicting the approved
Phase 0 product decisions or Phase 1 architecture was found. Where Phase 1 left
an implementation detail open, the choice is recorded in the decisions log.

## 19. How to run it

```bash
git clone <repo> LOGISTIX && cd LOGISTIX
cp .env.example .env
docker compose up --build
# PWA:  http://localhost:5173
# API:  http://localhost:8000/api/v1/
```

Non-Docker instructions: [`development-environment.md`](development-environment.md).

## 20. Reproduce the checks

```bash
# Backend
cd backend
python -m venv .venv && . .venv/Scripts/activate        # or .venv/bin/activate
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.test
export POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=fikisha \
       POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev \
       DJANGO_SECRET_KEY=test-secret \
       REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1
ruff check . && ruff format --check . && mypy .
python manage.py makemigrations --check --dry-run
pytest

# Frontend
cd ../frontend
npm ci
npm run lint && npm run typecheck && npm run test && npm run build
```

(The `pytest` step needs a Postgres + Redis reachable on the ports above — the
compose `db` / `redis` services provide them.)

## 21. Reproducible end-to-end smoke test (brief §40)

`scripts/smoke-test.sh` runs the full path and is the canonical reproduction.
Manual equivalent:

```bash
cp .env.example .env
docker compose up -d --build

# 1. infra + health
docker compose ps
curl -fsS http://localhost:8000/healthz            # {"status":"ok"}
curl -fsS http://localhost:8000/readyz             # database + cache True
curl -fsS http://localhost:8000/api/v1/health/     # {"status":"ok", checks:{database:true}}

# 2. PWA served
curl -fsS http://localhost:5173 | grep '<div id="root">'

# 3. auth foundation
REQ=$(curl -fsS -X POST http://localhost:8000/api/v1/auth/otp/request \
      -H 'Content-Type: application/json' -d '{"phone":"+254700000123"}')
CHALLENGE=$(echo "$REQ" | python -c 'import sys,json;print(json.load(sys.stdin)["challenge_id"])')
CODE=$(echo "$REQ"      | python -c 'import sys,json;print(json.load(sys.stdin)["dev_code"])')
VERIFY=$(curl -fsS -X POST http://localhost:8000/api/v1/auth/otp/verify \
      -H 'Content-Type: application/json' \
      -d "{\"challenge_id\":\"$CHALLENGE\",\"code\":\"$CODE\"}")
TOKEN=$(echo "$VERIFY" | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 4. authenticated request reaches the API
curl -fsS http://localhost:8000/api/v1/me -H "Authorization: Bearer $TOKEN"

# 5. authorization enforced — ordinary user -> admin route
curl -s -o /dev/null -w '%{http_code}\n' \
     http://localhost:8000/api/v1/admin/ping -H "Authorization: Bearer $TOKEN"   # 403

# 6. DB write + audit row + outbox row in ONE transaction (admin only)
ADMIN_TOKEN=$(docker compose exec -T backend \
  python manage.py create_admin +254700000009 --print-token \
  | grep '^ACCESS_TOKEN=' | cut -d= -f2-)
DEMO=$(curl -fsS -X POST http://localhost:8000/api/v1/_demo/atomic-outbox \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"note":"smoke"}')
OUTBOX_ID=$(echo "$DEMO" | python -c 'import sys,json;print(json.load(sys.stdin)["outbox_event_id"])')

# 7. Celery worker drains it
docker compose exec -T backend python manage.py shell -c \
  "from fikisha.outbox.models import OutboxEvent; print(OutboxEvent.objects.get(pk=$OUTBOX_ID).status)"
#   -> PENDING for a moment, then PUBLISHED

# 8. audit chain still verifies
docker compose exec -T backend python manage.py shell -c \
  "from fikisha.audit.services import verify_chain; print(verify_chain())"   # []

# 9. frontend authenticated state — open http://localhost:5173, sign in with
#    +254700000123 and the code shown on screen; the home page greets the user
#    and lists roles.
```

### Recorded run

_Result of running the §21 sequence against a fresh `docker compose up --build`
on the implementation machine (2026‑09‑08):_

```
1. compose ps
   backend  :: Up (healthy)      db     :: Up (healthy)     redis :: Up (healthy)
   worker   :: Up                beat   :: Up               frontend :: Up

2. health
   GET /healthz            -> {"status": "ok"}
   GET /readyz             -> {"status": "ok", "checks": {"database": true, "cache": true}}
   GET /api/v1/health/     -> {"status":"ok","checks":{"database":true,"cache":true}}

3. PWA served
   GET http://localhost:5173            -> <div id="root"></div>
   GET http://localhost:5173/src/main.tsx -> Vite module served

4. auth foundation — request
   POST /api/v1/auth/otp/request {"phone":"+254700000123"}
   -> {"challenge_id":"01a08287-…","dev_code":"250268"}          (202)

5. auth foundation — verify
   POST /api/v1/auth/otp/verify {challenge_id, code}
   -> {"access_token":"eyJ…","access_expires_in":900,
       "user":{"phone":"+254700000123","roles":[],"is_admin":false}}   (200)
      + Set-Cookie: fikisha_refresh (HttpOnly)

6. authenticated request reaches the API
   GET /api/v1/me  (Bearer)   -> {"phone":"+254700000123","is_admin":false}   (200)

7. authorization enforced
   GET /api/v1/admin/ping  (ordinary user Bearer)   -> HTTP 403

8. create a platform admin
   docker compose exec backend python manage.py create_admin +254700000009 --print-token
   -> ACCESS_TOKEN=… (session started for the admin)

9. one transaction writes a DB row + an audit row + an outbox row
   POST /api/v1/_demo/atomic-outbox  (admin Bearer)  {"note":"phase-2a smoke"}
   -> {"audit_seq":6,"outbox_event_id":1,"note":"phase-2a smoke"}   (201)

10. the Celery worker drains the outbox event
    OutboxEvent(pk=1).status  ->  PUBLISHED
    worker log: drain_outbox … succeeded {'published': 1, 'failed': 0, 'dead': 0}

11. rollback proof — deliberate failure writes nothing
    audit / outbox counts before        -> 8 / 1
    POST /api/v1/_demo/atomic-outbox?fail=1  -> HTTP 500
    audit / outbox counts after         -> 8 / 1        (neither row survived)

12. audit chain still verifies
    verify_chain()  ->  []   (no breaks)

13. error contract
    GET /api/v1/nope -> HTTP 404, content-type application/problem+json,
       body {type,title,status,code:"not_found",detail,request_id}

RESULT: PASS
```

## 22. Known limitations

Carried forward, all intentional: RLS not enabled (app-layer authz only);
`REVOKE` on audit tables documented not auto-applied in dev (triggers cover it);
MFA/step-up is a stub; HIGH-PII envelope encryption is an interface seam;
S3 storage backend raises `NotImplementedError`; rate limiter is fixed-window.
See [`security-baseline.md`](security-baseline.md) §8.

## 23. Attribution & provenance

Commits on this work carry `Co-Authored-By: Claude Sonnet 5` and a
`Claude-Session` trailer. No founder approval is claimed or implied by any
commit message or document.

## 24. Recommended review focus

1. `security-baseline.md` end to end — confirm the guarantees match intent.
2. `phase-2a-decisions.md` §ADR-2A-07/08/09/10 — the four deviations.
3. `config/settings/prod.py` — the forced-off dev switches.
4. `audit/services.py` + `audit/migrations/0003_append_only_db_guard.py` — the
   append-only guarantee.
5. `outbox/services.py` + `test_outbox.py` — outbox/business atomicity.
6. `platform_config/defaults.py` — confirm nothing here activates a business
   rule.

## 25. Status

**PHASE 2A — COMPLETE — AWAITING FOUNDER REVIEW**
Foundation implementation is complete.
No Phase 2B business-domain implementation has been started.
