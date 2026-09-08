# Project Structure

```
LOGISTIX/
├── .editorconfig                 4‑space Python, 2‑space everything else
├── .env.example                  variable NAMES + safe local defaults (never a real secret)
├── .gitignore                    excludes .env, venvs, node_modules, build output, DB/volume data, logs
├── docker-compose.yml            db · redis · backend · worker · beat · frontend
├── .github/workflows/ci.yml      backend + frontend + compose‑build pipelines
├── README.md                     top‑level quick start
├── CONTRIBUTING.md               workflow, commit conventions, checks to run
├── docs/
│   ├── phase-0/                  product discovery (20 docs) — approved
│   ├── phase-1/                  architecture & technical design (28 docs) — approved
│   └── phase-2/                  ← this phase
├── backend/
└── frontend/
```

## Backend (`backend/`)

```
backend/
├── Dockerfile                    python:3.12-slim, non‑root, entrypoint roles: api | worker | beat
├── .dockerignore
├── manage.py
├── pyproject.toml                ruff · pytest · coverage · mypy config
├── requirements/
│   ├── base.txt                  runtime deps (pinned ~=)
│   ├── dev.txt                   + test/lint/type deps
│   └── prod.txt                  + sentry-sdk
├── scripts/entrypoint.sh         wait‑for‑db, migrate, collectstatic, then serve/worker/beat
├── conftest.py                   shared pytest fixtures (api, user, other_user, platform_admin, ...)
├── config/                       Django project (not a business module)
│   ├── settings/
│   │   ├── base.py               shared settings, reads env via config/env.py
│   │   ├── dev.py                DEBUG, demo endpoints on, OTP dev‑expose on
│   │   ├── test.py               eager Celery, locmem cache, fixed OTP code
│   │   └── prod.py               secrets required; forces every dev‑only switch OFF
│   ├── env.py                    ~50‑line dependency‑free typed env reader (ADR‑2A‑02)
│   ├── urls.py                   /healthz /readyz /api/v1/ (+ /django-admin/ in DEBUG)
│   ├── celery.py                 Celery app + autodiscover + debug_ping
│   ├── asgi.py / wsgi.py
└── fikisha/                      the modular monolith — one package per bounded module
    ├── common/                   cross‑cutting primitives, imported by everything
    │   ├── models.py             UUIDv7 PK base, TimestampedModel, AppendOnlyModel/QuerySet
    │   ├── uuid7.py              RFC 9562 UUIDv7 generator (stdlib has it only in 3.14)
    │   ├── exceptions.py         DomainError hierarchy + RFC 9457 problem+json handler
    │   ├── ratelimit.py          fixed‑window limiter over the Django cache (fail‑closed)
    │   ├── request_id.py         RequestIDMiddleware + contextvar
    │   ├── logging_setup.py      structlog JSON pipeline + PII scrub
    │   ├── pagination.py         cursor pagination ({data, page:{next_cursor,prev_cursor}})
    │   └── money.py              integer‑minor‑unit Money value object (KES)
    ├── audit/                    append‑only, hash‑chained audit log
    │   ├── models.py             AuditLogEntry (AppendOnlyModel), AuditChainHead singleton
    │   ├── services.py           record(...)  ·  verify_chain(...)
    │   └── migrations/0003…      Postgres BEFORE UPDATE/DELETE triggers + prod REVOKE note
    ├── outbox/                   transactional outbox (ADR‑015, no message broker)
    │   ├── models.py             OutboxEvent (PENDING/PUBLISHED/DEAD, partial index)
    │   ├── services.py           emit(...) — asserts it runs inside a DB transaction
    │   ├── registry.py           @register(event_type) handler registry
    │   ├── tasks.py              drain_outbox — select_for_update(skip_locked), retry, dead‑letter
    │   └── handlers.py           demo handler (idempotent on event id)
    ├── platform_config/          versioned singleton configuration
    │   ├── defaults.py           DEFAULT_CONFIG + validate() (commission, value bands, roles, flags)
    │   ├── models.py             PlatformConfig (pk=1) + PlatformConfigVersion (AppendOnlyModel)
    │   └── services.py           current() · get(path) · apply_change(patch, changed_by, rationale)
    ├── identity/                 users, phone+OTP auth, sessions, authorization
    │   ├── models.py             User, OtpChallenge, AuthSession, RefreshToken, AdminProfile,
    │   │                         RoleAssignment, TotpDevice (MFA foundation stub)
    │   ├── phone.py              Kenya E.164 normalisation + masking
    │   ├── services/
    │   │   ├── otp.py            request_otp · verify_otp (attempt counter commits on failure)
    │   │   ├── tokens.py         signed access token (carries session id) · refresh token hashing
    │   │   └── auth.py           start_session · refresh (reuse detection) · resolve_session · logout
    │   ├── authz/
    │   │   ├── actors.py         Actor / AnonymousActor / SystemActor, actor_from_request
    │   │   ├── engine.py         authorize(actor, action, resource) → Decision  (default deny)
    │   │   ├── policies.py       per‑action policy functions; admin perms from platform_config
    │   │   ├── permissions.py    DRF ActionPermission (reads view.required_action; 401 vs 403)
    │   │   └── authentication.py DRF BearerSessionAuthentication
    │   └── api/                  serializers · views · urls  (auth, me, sessions, reference, admin/ping, _demo)
    ├── storage/                  private object storage abstraction
    │   ├── base.py               PrivateStorage ABC + StoredObject
    │   ├── local.py              LocalPrivateStorage (path‑traversal guarded, signed opaque token)
    │   ├── s3.py                 S3PrivateStorage — interface stub, raises NotImplementedError
    │   └── service.py            get_storage() resolver
    ├── observability/            health.py (/healthz /readyz /api/v1/health/) · metrics.py (no‑op hooks)
    └── api/                      URL aggregation + problem+json catch‑all 404
```

Every module owns its `tests/` directory. Modules interact only through another
module's `services` / `authz` surface or via outbox events — never by importing
another module's models.

## Frontend (`frontend/`)

```
frontend/
├── Dockerfile                    deps → dev (Vite server) → build → runtime (nginx)
├── nginx.conf                    SPA fallback + asset caching for the runtime image
├── index.html
├── vite.config.ts                React plugin · PWA plugin · path alias · vitest config
├── tsconfig.json                 strict, noUncheckedIndexedAccess, @/* → src/*
├── tailwind.config.ts · postcss.config.js
├── eslint.config.js              flat config (ESLint 9 + typescript-eslint)
├── public/                       favicon.svg · robots.txt
└── src/
    ├── main.tsx                  createRoot + StrictMode + SW registration
    ├── App.tsx
    ├── app/
    │   ├── providers.tsx         ErrorBoundary → i18n → QueryClient → Router → AuthProvider
    │   ├── router.tsx            /login (public) · everything else behind <RequireAuth>
    │   ├── queryClient.ts        retry policy: never retry 4xx (ApiError)
    │   └── ErrorBoundary.tsx
    ├── shell/                    AppShell · TopBar · LanguageSwitcher
    ├── services/
    │   ├── env.ts               validated import.meta.env access
    │   ├── problem.ts           ProblemDetail type + ApiError class
    │   ├── apiClient.ts         fetch wrapper: bearer header, problem+json parse, 401→refresh→retry
    │   └── errorMessage.ts      ApiError → localized string via the `errors` namespace
    ├── features/
    │   ├── auth/                AuthContext · AuthProvider · useAuth · RequireAuth · authApi · LoginPage
    │   ├── home/                HomePage (signed‑in landing)
    │   └── diagnostics/        DiagnosticsPage (calls /health/ and /reference)
    ├── components/              Button · Input · Field · Card · Alert · Spinner · StatusBadge ·
    │                            PageLoader · EmptyState · ErrorState  (+ Button.test.tsx)
    ├── i18n/
    │   ├── index.ts
    │   └── locales/{en,sw}/{common,auth,errors}.json
    ├── pwa/registerServiceWorker.ts
    ├── styles/index.css          Tailwind layers
    └── test/                    setup.ts · renderWithProviders.tsx · *.test.tsx
```
