# Contributing to Fikisha

## Ground rules

- **Never commit secrets.** No `.env` with real values, no provider keys, no
  private uploads, no DB dumps, no local logs. `.env.example` carries variable
  names and safe non‑secret defaults only.
- **Do not change an approved product decision** (commission model, trust
  thresholds, value bands, cancellation policy, dispute window, proof‑of‑pickup
  responsibility, admin role structure, languages, pilot area) without founder
  sign‑off. If implementation seems to contradict the approved architecture,
  **stop and raise it** — record it in `docs/phase-2/phase-2a-decisions.md`
  (or the current phase's decisions log), don't silently pick a direction.
- **Respect module boundaries.** A `fikisha/<module>` package may import another
  module's `services` / `authz` surface or react to its outbox events. It must
  **not** import another module's models directly.
- **Keep the phase scope.** Phase 2A is foundation only. Business‑domain code
  (Jobs, negotiation, operators, businesses, vehicles, trust, verification,
  delivery, commission, disputes) is out of scope until that phase is approved.

## Workflow

1. Branch off `main`: `git checkout -b <area>/<short-description>`.
2. Make focused changes. **Several small, meaningful commits** beat one large
   one.
3. Run the checks (below). They must pass.
4. Open a PR against `main`. CI runs the same checks plus `docker compose build`.

## Checks to run before pushing

### Backend (`cd backend`)

```bash
ruff check .              # lint
ruff format --check .     # formatting
mypy .                    # types (pragmatic config — see ADR‑2A‑08)
python manage.py makemigrations --check --dry-run   # migrations complete
pytest                    # tests + coverage
```

### Frontend (`cd frontend`)

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

A running Postgres + Redis is needed for `pytest` (use the compose stack; see
`docs/phase-2/development-environment.md`).

## Commit messages

- Imperative subject line, ≤ 72 chars: `Add outbox dead-letter handling`.
- Body: what changed and **why**, wrapped at ~72 chars.
- One logical change per commit. Formatting‑only churn goes in its own commit.

## Migrations

- Generate with `python manage.py makemigrations`; commit the generated file.
- `makemigrations --check --dry-run` must report "No changes detected" on a
  clean tree — CI enforces this.
- Never edit a migration that has run anywhere shared.

## Tests

- New behaviour needs a test. Bug fixes need a regression test.
- Security‑relevant paths (auth, authorization, audit, outbox atomicity) must
  keep their existing coverage — see `docs/phase-2/testing-foundation.md`.

## Code style

- Python: `ruff` (lint + format), 4‑space indent, type annotations on new
  functions.
- TypeScript: `eslint` flat config + `prettier`, 2‑space indent, `strict` TS.
- Match the surrounding code's naming and comment density.
