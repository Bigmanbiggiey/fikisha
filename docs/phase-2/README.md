# Phase 2A — Foundation Implementation

This directory documents the **technical foundation** of Fikisha. Phase 2A builds
the scaffolding every later feature stands on and **deliberately stops there** —
no Jobs, negotiation, assignment, chain of custody, trust levels, operator
verification, commission processing, disputes, recipient links, ratings,
business/vehicle management, delivery workflows, or WhatsApp / SMS / M‑Pesa /
eTIMS integration have been implemented.

## What Phase 2A delivers

| Area | Outcome |
| --- | --- |
| Repository & tooling | Git repo, `.editorconfig`, `.gitignore`, `.env.example`, pinned dependency sets |
| Local environment | `docker compose up` → Postgres + Redis + API + Celery worker + Celery beat + PWA |
| Backend | Django 5.2 + DRF modular monolith: `common`, `audit`, `outbox`, `platform_config`, `identity`, `storage` |
| Authentication | Phone + one‑time‑code login, opaque server‑side sessions, rotating refresh cookie with reuse detection (ADR‑011) |
| Authorization | Central `authorize(actor, action, resource)` engine, default‑deny, admin permissions from `platform_config` |
| Audit | Append‑only, hash‑chained `audit_log_entry`; founder/admin actions are audited too; DB triggers block mutation |
| Transactional outbox | `emit()` writes in the caller's DB transaction; Celery `drain_outbox` publishes with retry + dead‑letter (ADR‑015) |
| Platform config | Versioned singleton + append‑only version history; `ConfigService.apply_change` audits + emits |
| Frontend | React 18 + TS + Vite PWA shell: i18n (English + Swahili), login flow, auth/session handling, diagnostics page |
| Automated tests | 111 backend tests (pytest), 9 frontend tests (vitest) |
| CI | GitHub Actions: backend lint/type/test, frontend lint/type/test/build, `docker compose build` |

## Documents

| File | Contents |
| --- | --- |
| [`technology-versions.md`](technology-versions.md) | Every pinned language, framework, and library version, with the reason for each choice |
| [`project-structure.md`](project-structure.md) | Directory layout of the repo, backend modules, and frontend feature folders |
| [`development-environment.md`](development-environment.md) | How to run the stack locally (Docker and non‑Docker), environment variables, common tasks |
| [`security-baseline.md`](security-baseline.md) | The security properties the foundation guarantees and how each is enforced |
| [`testing-foundation.md`](testing-foundation.md) | Test layout, what is covered, how to run tests, the required security tests |
| [`phase-2a-decisions.md`](phase-2a-decisions.md) | ADRs made during implementation and any deviations from Phase 1 |
| [`phase-2a-summary.md`](phase-2a-summary.md) | The Phase 2A completion report (with exact reproduction commands) |

## Guardrails honoured

- **No approved product decision was silently changed.** Where implementation
  needed a detail Phase 1 left open, it is recorded in `phase-2a-decisions.md`.
  No contradiction with the approved architecture was found.
- **The dev OTP mechanism is not a fake production auth system.** It is gated by
  `OTP_DEV_EXPOSE` / `OTP_DEV_FIXED_CODE`, which `config/settings/prod.py` forces
  off unconditionally. See `security-baseline.md` §3.
- **MFA is foundation only.** `identity.TotpDevice` and the `is_step_up_fresh`
  actor flag exist; no TOTP secret is generated or verified in 2A. See
  ADR‑2A‑07.
- **Administrative actions are audited.** There is no code path that performs a
  sensitive change without `audit.record(...)` in the same transaction, and no
  ordinary code can `UPDATE`/`DELETE` an audit row (service layer, model layer,
  and Postgres triggers each forbid it). See `security-baseline.md` §5.
