# Fikisha

Local logistics marketplace for **Kitengela, Kajiado County and its environs**.
Fikisha connects people and businesses who need something moved with local
transport operators. English and Swahili throughout (Swahili prominent on
operator screens).

> **Status: Phase 2A — Foundation Implementation.**
> This repository currently contains the technical foundation only:
> repo + tooling, a Dockerised dev environment, the Django/DRF modular‑monolith
> backend skeleton, authentication and authorization foundations, the audit and
> transactional‑outbox foundations, the platform‑configuration foundation, the
> React PWA shell, tests, and CI. **No delivery/business features are
> implemented** — no Jobs, negotiation, assignment, chain of custody, trust
> levels, operator verification, commission processing, disputes, recipient
> links, ratings, or provider integrations.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then open **http://localhost:5173**. Sign in with any Kenyan phone number
(`07XXXXXXXX`); in dev the one‑time code is shown on screen (no SMS provider is
wired yet — see `docs/phase-2/security-baseline.md` §3).

| Service | URL |
| --- | --- |
| PWA | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| API health | http://localhost:8000/healthz · http://localhost:8000/readyz |
| API docs (DEBUG) | http://localhost:8000/api/v1/docs/ |

## Repository layout

| Path | What |
| --- | --- |
| `backend/` | Django 5.2 + DRF modular monolith (`fikisha/` = one package per bounded module) |
| `frontend/` | React 18 + TypeScript + Vite PWA |
| `docs/phase-0/` | Product discovery (approved) |
| `docs/phase-1/` | Architecture & technical design (approved) |
| `docs/phase-2/` | **This phase** — start at [`docs/phase-2/README.md`](docs/phase-2/README.md) |
| `docker-compose.yml` | db · redis · backend · worker · beat · frontend |
| `.github/workflows/ci.yml` | backend + frontend + compose‑build pipelines |

## Development

See **[`docs/phase-2/development-environment.md`](docs/phase-2/development-environment.md)**
for the non‑Docker path, environment variables, and common tasks.

```bash
# backend checks
cd backend && ruff check . && ruff format --check . && mypy . && pytest

# frontend checks
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: branch, keep commits small
and meaningful, run the checks above, never commit `.env` or secrets.

## Licence

Proprietary — © Fikisha. All rights reserved.
