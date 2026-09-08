# Development Environment

## Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Docker + Compose v2 | recent | The supported path. `docker compose version` should print v2.x. |
| Python | 3.12.x | Only needed for running the backend **without** Docker. |
| Node.js | 20+ (22 recommended) | Only needed for running the frontend **without** Docker. |
| Git | any | — |

## First run (Docker — recommended)

```bash
git clone <repo> LOGISTIX
cd LOGISTIX
cp .env.example .env                 # every default is a safe local value
docker compose up --build
```

This starts six services:

| Service | Host port | Purpose |
| --- | --- | --- |
| `db` (postgres:16) | `localhost:5433` | application database |
| `redis` (redis:7) | `localhost:6380` | Celery broker + Django cache + rate limiter |
| `backend` (Django) | `localhost:8000` | API (`/api/v1/`), health at `/healthz` `/readyz` |
| `worker` (Celery) | — | runs `drain_outbox` and other tasks |
| `beat` (Celery beat) | — | schedules `drain-outbox` every `OUTBOX_POLL_SECONDS` (3s) |
| `frontend` (Vite) | `localhost:5173` | the PWA |

The backend container runs `migrate` automatically on start (see
`scripts/entrypoint.sh`). Open **http://localhost:5173**.

Host ports are deliberately off the defaults (5433/6380 instead of 5432/6379) so
the stack does not clash with a local Postgres/Redis. Change them in `.env`
(`POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `BACKEND_HOST_PORT`,
`FRONTEND_HOST_PORT`).

### Logging in (no SMS provider)

Phase 2A has no SMS integration. In dev, `OTP_DEV_EXPOSE=true` makes the OTP
request endpoint return the code in its JSON response (and the LoginPage shows
it). Enter any Kenyan phone number (`07XXXXXXXX`), read the code off the screen,
submit it. See `security-baseline.md` §3 for why this is safe.

## Running without Docker

### Backend

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements/dev.txt

# Point at a local Postgres + Redis (or the compose ones on 5433/6380):
export DJANGO_SETTINGS_MODULE=config.settings.dev
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export POSTGRES_DB=fikisha POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev
export DJANGO_SECRET_KEY=dev-only-not-a-secret-change-me
export REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
# in another shell:
celery -A config worker -l info -Q default
celery -A config beat   -l info
```

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies nothing — talks to VITE_API_BASE_URL
```

## Environment variables

`.env.example` is the source of truth. Highlights:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | `dev` \| `test` \| `prod` |
| `DJANGO_SECRET_KEY` | `dev-only-not-a-secret-change-me` | **required** in `prod`; dev has a placeholder |
| `DJANGO_DEBUG` | `true` | server picks `runserver` vs `gunicorn` on this |
| `POSTGRES_*` | `fikisha` / `fikisha-local-dev` | DB connection |
| `REDIS_URL` / `CELERY_BROKER_URL` | `redis://redis:6379/0` `/1` | cache + broker |
| `OTP_DEV_EXPOSE` | `true` (dev/test) | return OTP codes in API responses — **forced `false` in prod** |
| `OTP_DEV_FIXED_CODE` | empty (dev), `000000` (test) | accept a fixed code — **forced empty in prod** |
| `ACCESS_TOKEN_TTL_SECONDS` | `900` | signed access‑token lifetime |
| `REFRESH_TOKEN_TTL_SECONDS` | `2592000` | refresh‑cookie lifetime |
| `AUTH_COOKIE_SECURE` / `AUTH_COOKIE_SAMESITE` | `false` / `Lax` (dev) | **forced `true` / `Strict` in prod** |
| `STORAGE_BACKEND` | `local` | `local` \| `s3` (s3 is a stub) |
| `FIKISHA_ALLOW_DEMO_ENDPOINTS` | `true` (dev/test), `false` (base/prod) | gates `/api/v1/_demo/atomic-outbox` |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | browser → API base |

Secrets are never committed. `.env` is git‑ignored; only `.env.example` (names +
non‑secret defaults) is tracked.

## Common tasks

| Task | Command (from `backend/`) |
| --- | --- |
| Run migrations | `python manage.py migrate` |
| Make migrations | `python manage.py makemigrations` |
| Check migrations are complete | `python manage.py makemigrations --check --dry-run` |
| Drain the outbox once (no worker) | `python manage.py outbox_drain` |
| Django shell | `python manage.py shell` |
| Verify the audit hash chain | `python manage.py shell -c "from fikisha.audit.services import verify_chain; print(verify_chain())"` |

| Task | Command (from `frontend/`) |
| --- | --- |
| Dev server | `npm run dev` |
| Type check | `npm run typecheck` |
| Lint | `npm run lint` |
| Unit tests | `npm run test` |
| Production build | `npm run build` |

## Ports already in use?

`docker compose` reads `.env`. Set `POSTGRES_HOST_PORT` / `REDIS_HOST_PORT` /
`BACKEND_HOST_PORT` / `FRONTEND_HOST_PORT` to free values and re‑run
`docker compose up`.
