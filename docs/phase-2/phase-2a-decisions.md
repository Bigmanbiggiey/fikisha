# Phase 2A — Implementation Decisions

Decisions taken while building the foundation, and every place the
implementation differs from or fills a gap in the approved Phase 1 design.

**No approved Fikisha product decision was changed.** No contradiction between
the Phase 1 architecture and a workable implementation was found. Where Phase 1
left a detail open, it is recorded below and marked accordingly.

Status legend: **CONFIRMED** (settled for 2A) · **PROVISIONAL** (revisit in 2B) ·
**DEVIATION** (differs from a Phase 1 doc — with rationale).

---

## ADR‑2A‑01 — Python 3.12 in the container — CONFIRMED

Phase 1 `technology-stack.md` names Python 3.12+. The image pins
`python:3.12-slim` (not 3.13): 3.12 has full binary‑wheel coverage for
`psycopg`, `argon2-cffi`, and the type‑stub toolchain, plus a year of patch
releases. `uuid.uuid7` is stdlib only in 3.14, so we ship our own RFC 9562
generator (`fikisha/common/uuid7.py`) regardless. Revisit at the next LTS.

## ADR‑2A‑02 — Dependency‑free environment reader — CONFIRMED

`config/env.py` is a ~55‑line typed reader over `os.environ`
(`str_/bool_/int_/list_/path_`, each raising `ImproperlyConfigured` on a missing
required value). Rejected `django-environ` / `pydantic-settings`: the surface we
need is tiny, and a hand‑rolled reader keeps settings explicit and fail‑loud
with zero supply‑chain cost. `required=True` never returns a usable default, so
a missing production secret crashes at boot.

## ADR‑2A‑03 — Access token is a signed session pointer, not a JWT — CONFIRMED

Implements Phase 1 ADR‑011. `make_access_token` uses `django.core.signing`
(`salt="fikisha.access.v1"`) to sign `{sid, uid, n}` where `n` is a random nonce
so two tokens minted in the same second differ. It carries **no** authorization
claims; `resolve_session()` loads the `AuthSession` and re‑validates it on every
request, so revocation and account suspension take effect immediately. Refresh
tokens are opaque `secrets.token_urlsafe(48)` values stored only as SHA‑256
hashes, rotated on every use, with reuse detection revoking the whole session.

## ADR‑2A‑04 — Append‑only enforced at three layers — CONFIRMED

Phase 1 `database-design.md` requires audit/config‑version rows to be
immutable. 2A enforces this at (1) the service layer (no update/delete
function), (2) the model layer (`AppendOnlyModel` / `AppendOnlyQuerySet` raise),
and (3) the database — migration `audit/0003_append_only_db_guard.py` installs
`BEFORE UPDATE/DELETE` triggers via `fikisha_forbid_mutation()`. The
production‑only `REVOKE UPDATE, DELETE ON … FROM app_rw` is documented in that
migration's docstring; it is not run by local compose (superuser Postgres), so
the triggers are the always‑on guarantee. See `security-baseline.md` §5.

## ADR‑2A‑05 — Fixed‑window rate limiter now, token bucket later — PROVISIONAL

`common/ratelimit.py` is a fixed‑window counter over the Django cache,
**fail‑closed** (a cache error denies the request). It covers the 2A need (OTP
request throttling, per‑IP caps). A sliding‑window / token‑bucket limiter and a
shared Redis Lua implementation are deferred to when traffic shaping matters.

## ADR‑2A‑06 — `platform_config` is the source of admin permissions — CONFIRMED

Implements Phase 1 `admin-architecture.md`. `role_permissions` in
`DEFAULT_CONFIG` maps role → permission list; `PLATFORM_ADMIN = ["*"]`. The
authorization engine reads this at decision time, so granting or revoking an
admin capability is an audited, versioned **config change**, not a code deploy.
`ConfigService.apply_change` requires a non‑empty rationale.

## ADR‑2A‑07 — MFA / step‑up is a foundation stub — CONFIRMED (DEVIATION from a strict reading of Phase 1 auth)

Phase 1 `authentication-authorization.md` describes TOTP step‑up for admin
actions. 2A ships **only** the seam: `identity.TotpDevice`
(`secret_encrypted`, `confirmed_at`), `OtpPurpose.STEP_UP`, and
`Actor.is_step_up_fresh` (always `False`). No secret is generated or verified;
no step‑up challenge is issued. This is called out in `security-baseline.md` §4
and the summary so nobody mistakes the stub for a working second factor. Full
implementation is Phase 2B.

## ADR‑2A‑08 — mypy runs in a pragmatic (non‑strict) mode — DEVIATION from `testing-strategy.md`

Phase 1 `testing-strategy.md` aspires to `mypy --strict`. Under
`django-stubs` + `djangorestframework-stubs`, strict mode produces a large
volume of low‑value errors on framework base classes (generic type parameters on
`Serializer`/`ModelAdmin`, `Any` from settings dicts, property/column overrides
on `AbstractBaseUser`). 2A keeps the checks that catch real bugs
(`disallow_untyped_defs`, `disallow_incomplete_defs`, `check_untyped_defs`,
`no_implicit_optional`, `warn_unused_ignores`, `warn_redundant_casts`) and
relaxes `disallow_any_generics` / `warn_return_any`. The suite is **clean** at
this level (`mypy .` → 0 errors, 75 files). Tightening toward strict is tracked
for a later phase. Three targeted `# type: ignore[…]` remain, each with a
one‑line reason.

## ADR‑2A‑09 — `eslint-plugin-react-hooks` bumped to v5 — CONFIRMED

The Phase 2A brief's suggested pin (`^4.6.2`) has a peer dependency of
`eslint@<9`, incompatible with the flat‑config ESLint 9 the rest of the frontend
toolchain uses. Bumped to `^5.0.0` (first release supporting ESLint 9 flat
config). No rule behaviour change for our code.

## ADR‑2A‑10 — `ActorRole.USER` added to the audit role enum — DEVIATION (bug fix)

`Actor.audit_role` returns `ActorRole.USER` for an authenticated non‑admin
actor, but the enum in `audit/models.py` lacked that member (it would have
raised `AttributeError` the first time a plain user triggered an audited action
via the authz `Actor`). Added `USER = "USER", "Authenticated user"` and migration
`audit/0004_alter_auditlogentry_actor_role.py`. Pre‑release, no data impact.

## ADR‑2A‑11 — Local host ports offset from the defaults — CONFIRMED

`docker compose` publishes Postgres on `5433` and Redis on `6380` (not
`5432`/`6379`) so the stack coexists with a developer's own local
Postgres/Redis. All four host ports are overridable in `.env`
(`POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `BACKEND_HOST_PORT`,
`FRONTEND_HOST_PORT`). In‑container ports are unchanged.

## ADR‑2A‑12 — Frontend served by nginx in the runtime image; Vite dev server in compose — CONFIRMED

`frontend/Dockerfile` has `dev` (hot‑reloading Vite) and `runtime` (static
build behind `nginx` with SPA fallback) targets. `docker compose` uses `dev` for
the local loop; CI builds all targets. No API responses are cached by the
service worker in 2A — the offline‑safe vs server‑confirmed split (Phase 1
`pwa-architecture.md`) lands with the delivery features.

## ADR‑2A‑13 — `whitenoise` for API static files — CONFIRMED

The API/admin static assets are served by `whitenoise` from the app process;
the SPA is a separate service. Avoids a third web server in the foundation. The
Phase 1 `deployment-architecture.md` CDN/static story is unchanged for later.

---

## Deviations summary

| # | Phase 1 reference | Deviation | Why it is safe |
| --- | --- | --- | --- |
| ADR‑2A‑07 | `authentication-authorization.md` (TOTP step‑up) | step‑up is a stub | flagged everywhere; no security claim made; 2B implements it |
| ADR‑2A‑08 | `testing-strategy.md` (`mypy --strict`) | pragmatic mypy config | real‑bug checks retained; suite is clean; path to strict tracked |
| ADR‑2A‑09 | brief's suggested lint pin | plugin v4 → v5 | v4 cannot run on ESLint 9; no rule change |
| ADR‑2A‑10 | `audit` role enum | added `USER` member | bug fix; pre‑release; migration included |

No item in this table changes an approved **product** decision (commission
model, trust thresholds, value bands, cancellation policy, dispute window, proof
‑of‑pickup responsibility, admin role structure, languages, pilot area). Those
are untouched and unimplemented in 2A.
