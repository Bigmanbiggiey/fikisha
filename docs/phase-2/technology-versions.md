# Technology Versions

Every runtime and library used by the foundation, the version constraint we
pin, the version actually resolved at the time of writing, and why the choice
was made. **Newest was not chosen by default** — each pin targets a release that
is stable, currently maintained, and compatible with the rest of the stack.

Constraint style:
- **Python** — `~=X.Y.0` compatible‑release ranges in `backend/requirements/*.txt`
  (allows patch/minor within a major, blocks surprise majors).
- **Node** — caret ranges in `frontend/package.json`, with an exact tree locked
  in `frontend/package-lock.json` (CI and Docker use `npm ci`).

## Languages / runtimes

| Component | Pinned | Resolved | Rationale |
| --- | --- | --- | --- |
| Python | `>=3.12,<3.13` | 3.12.10 | Django 5.2 LTS supports 3.10–3.13; 3.12 is the newest with full C‑extension wheel coverage for our deps and a year of patch history. 3.13 deferred (ADR‑2A‑01). |
| Node.js | `>=20` (CI/Docker on 22) | 22.x (Docker), 24.x (local dev seen) | 22 is the active LTS line. The image pins `node:22-bookworm-slim`. |
| PostgreSQL | `16` | 16 (alpine image) | Current stable major with the longest support runway; `skip_locked`, partial indexes, generated columns all available. |
| Redis | `7` | 7 (alpine image) | Broker + cache only. v7 is stable and ubiquitous. |

## Backend — `requirements/base.txt`

| Package | Pinned | Resolved | Rationale |
| --- | --- | --- | --- |
| Django | `~=5.2.0` | 5.2.17 | **LTS** (supported into 2028). Long runway, no rush to 6.x. |
| djangorestframework | `~=3.16.0` | 3.16.1 | Current DRF; supports Django 5.2. |
| psycopg[binary] | `~=3.2.0` | 3.2.13 | psycopg 3 (not 2) — modern, async‑ready, better type handling. Binary build for dev simplicity. |
| django-cors-headers | `~=4.6.0` | 4.6.0 | SPA on `localhost:5173` calls the API on `:8000`. |
| celery | `~=5.4.0` | 5.4.0 | Background worker for `drain_outbox` and future scheduled jobs. |
| redis | `~=5.2.0` | 5.2.1 | redis‑py client for the Celery broker and Django cache. |
| structlog | `~=24.4.0` | 24.4.0 | JSON structured logging with a request‑id contextvar and PII scrubbing. |
| gunicorn | `~=23.0.0` | 23.0.0 | Production WSGI server (image entrypoint uses it outside DEBUG). |
| whitenoise | `~=6.8.0` | 6.8.2 | Static file serving for the API/admin without a separate web server. |
| argon2-cffi | `~=23.1.0` | 23.1.0 | Argon2 password hasher — used to hash OTP codes at rest. |
| drf-spectacular | `~=0.28.0` | 0.28.0 | OpenAPI 3 schema + Redoc at `/api/v1/docs/` (DEBUG only). |

## Backend — `requirements/dev.txt` (adds)

| Package | Pinned | Resolved | Rationale |
| --- | --- | --- | --- |
| pytest | `~=8.3.0` | 8.3.5 | Test runner. |
| pytest-django | `~=4.9.0` | 4.9.0 | DB fixtures, settings integration. |
| pytest-cov | `~=6.0.0` | 6.0.0 | Coverage (`--cov=fikisha`). |
| factory-boy | `~=3.3.0` | 3.3.3 | Test data factories. |
| fakeredis | `~=2.26.0` | 2.26.2 | In‑memory Redis for tests that touch the cache/rate limiter. |
| freezegun | `~=1.5.0` | 1.5.5 | Deterministic time in OTP/session expiry tests. |
| ruff | `~=0.8.0` | 0.8.6 | Linter + formatter (replaces flake8 + isort + black). |
| mypy | `~=1.13.0` | 1.13.0 | Static type checking (pragmatic config — ADR‑2A‑08). |
| django-stubs[compatible-mypy] | `~=5.1.0` | 5.1.3 | Django type stubs + mypy plugin. |
| djangorestframework-stubs | `~=3.15.0` | 3.15.3 | DRF type stubs. |

## Backend — `requirements/prod.txt` (adds)

| Package | Pinned | Resolved | Rationale |
| --- | --- | --- | --- |
| sentry-sdk | `~=2.17.0` | — (not installed in dev) | Error tracking hook. Wired in `prod.py`, inert without `SENTRY_DSN`. Not exercised in 2A. |

## Frontend — `package.json`

| Package | Pinned | Resolved | Rationale |
| --- | --- | --- | --- |
| react / react-dom | `^18.3.1` | 18.3.1 | React 18 is stable and fully supported by the ecosystem below. React 19 deferred until the router/query/i18n stack has caught up. |
| react-router-dom | `^6.26.1` | 6.30.6 | v6 data router. v7 deferred (breaking changes, future flags still settling). |
| @tanstack/react-query | `^5.51.23` | 5.102.8 | Server‑state caching, retry policy, request dedup. |
| i18next / react-i18next | `^23.12.2` / `^15.0.1` | 23.16.8 / 15.7.4 | English + Swahili with namespaces (`common`, `auth`, `errors`). |
| i18next-browser-languagedetector | `^8.0.0` | 8.2.1 | Remembers the chosen language in `localStorage`. |
| typescript | `^5.5.4` | 5.9.3 | `strict`, `noUncheckedIndexedAccess`. |
| vite | `^5.4.2` | 5.4.21 | Build tool + dev server. v6 deferred. |
| @vitejs/plugin-react | `^4.3.1` | 4.7.0 | React fast refresh + JSX transform. |
| vite-plugin-pwa | `^0.20.1` | 0.20.5 | Workbox service worker + web manifest generation. |
| tailwindcss | `^3.4.10` | 3.4.19 | Utility CSS. v4 deferred (new engine, config format still stabilising). |
| vitest | `^2.0.5` | 2.1.9 | Test runner (shares Vite config). |
| @testing-library/react | `^16.0.0` | 16.3.3 | Component tests. |
| jsdom | `^24.1.1` | 24.1.3 | DOM for tests. |
| eslint | `^9.9.0` | 9.39.5 | Flat‑config lint. |
| typescript-eslint | `^8.2.0` | 8.70.0 | TS lint rules. |
| eslint-plugin-react-hooks | `^5.0.0` | 5.x | **Bumped from 4.x during install** — 4.x does not support ESLint 9. Recorded in ADR‑2A‑09. |
| @types/node | `^22.5.0` | 22.x | Types for `vite.config.ts` (`node:url`). Added during setup. |

## How to update

1. Change the constraint in `requirements/*.txt` or `package.json`.
2. `pip install -r requirements/dev.txt` / `npm install` to re‑resolve.
3. Run the full check suite (see `testing-foundation.md`).
4. Note anything material in `phase-2a-decisions.md` (or the Phase 2B log).
