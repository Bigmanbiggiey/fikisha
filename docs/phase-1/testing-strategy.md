# Testing Strategy

Implements Phase 0 `NFR-MNT-2` and Phase 1 brief §29. The MVP is a **pilot
instrument** and a **safety-critical custody + money system**; the test suite is
weighted toward the invariants that protect those.

Tooling: `pytest` + `pytest-django` + `factory_boy` (fixtures/builders),
`pytest-cov`, DRF's `APIClient`, Playwright for E2E, `schemathesis` for API
contract fuzzing, `locust` for a light load check.

---

## 1. Layers

### 1.1 Unit — domain rules & calculations

- **Commission calculator** — every boundary of `FLAT_WITH_MIN_CAP`: below floor,
  at floor, mid, at cap, above cap, `ROUND_HALF_UP` at the half-shilling, zero /
  negative rejected. Config-version pinning: a rate change after confirm does not
  change a completed job's record.
- **Trust criteria evaluation** — an operator with exactly N-1 vs N completed
  jobs; rating exactly at / below threshold; at-fault-incident count edges;
  `criteria_snapshot` correctness.
- **Value-band computation** — declared value at each band boundary (50k, 250k,
  1M); band frozen at CONFIRMED; `latent_risk_cargo` flag.
- **Guards** — each guard in isolation ([job-state-machine.md](job-state-machine.md)
  §4): pass and every fail mode raising the right typed error/code.
- **Money type** — minor-unit arithmetic, no float, formatting.
- **Localization** — `code` → key resolution; ICU plural/select rendering in
  `en`/`sw`.

### 1.2 Integration — DB, auth, storage, notifications, config

- **Append-only enforcement** — for each append-only table (`audit_log_entry`,
  `job_event`, `negotiation_entry`, `commission_*`, `statement_*`,
  `trust_level_change`, `verification_decision`, `platform_config_version`,
  `incident_statement`, `evidence_access_log`, `analytics_event`): an attempted
  ORM `update()` / `delete()` raises; a raw `UPDATE`/`DELETE` as the `app_rw`
  role is denied by the grant.
- **DB trigger backstop** — a raw `UPDATE job SET status=...` with an illegal
  `(from,to)` is rejected by the `BEFORE UPDATE` trigger; a legal one made by the
  service (with the session flag set) succeeds.
- **Outbox** — a state change writes the outbox row in the same txn; a rollback
  leaves no row; the publisher marks rows published exactly once under
  concurrency (`SKIP LOCKED`); a poison event dead-letters after N attempts.
- **Auth** — OTP hash/TTL/attempt-lockout; enumeration-safe `202`; refresh-token
  rotation; **reuse detection revokes the family**; admin login blocked without a
  confirmed TOTP; step-up nonce single-use.
- **Evidence** — magic-byte sniffing rejects a renamed executable; EXIF/GPS
  stripped on re-encode; SHA-256 recorded on the domain row; non-image stays
  `PENDING` until ClamAV `CLEAN`; retention sweep deletes past-window objects and
  nulls refs but keeps the domain row; `legal_hold` skips.
- **Notifications** — template resolves per `(key, locale, channel)`; OTP goes
  SMS-first; WhatsApp `FAILED` triggers an SMS fallback row; idempotent per
  `(recipient, template_key, dedupe_key)`; cost recorded per `job_id`.
- **Config** — a change appends a version with a rationale; consumers reload;
  historical rows keep their pinned `config_version_id`.

### 1.3 API — authorization & business flows

- **Authorization matrix** — a parametrized test over `{actor kind} × {action} ×
  {resource ownership}` asserting the [authentication-authorization.md](authentication-authorization.md)
  §3 matrix. Every `Allow`/`Deny` cell. New endpoints must extend the matrix or
  CI fails (a registry check).
- **IDOR / BOLA** — actor A cannot `GET`/`POST` actor B's job, thread, evidence,
  statement, incident; a guessed/adjacent UUID → `404`; RLS (if enabled) returns
  empty even if the app filter is bypassed in a test harness.
- **Idempotency** — the same `Idempotency-Key` replays the stored response with
  **no** second side effect; a missing key on a creating route → `400`.
- **Concurrency** — stale `If-Match` → `412`.
- **Error contract** — every error path returns `problem+json` with a `code` that
  exists in `errors.*` for `en` **and** `sw` (contract test).
- **Schema** — `schemathesis` fuzzes generated OpenAPI: no `500`s, responses
  match the schema, auth is enforced on every non-public route.

### 1.4 State-machine tests (brief §29) — **every valid and invalid transition**

- A parametrized test over the **full cross-product** of `JobStatus × JobStatus`:
  - a pair **in** `ALLOWED_TRANSITIONS` with a valid `context` and an authorized
    actor → succeeds; writes exactly one `job_status_event`, the expected
    `job_event` custody rows, one `audit_log_entry`, and the expected side-effect
    rows; bumps `version`.
  - a pair **not in** the table → `422 job.transition_not_allowed` with **zero**
    rows written anywhere (assert row counts before/after).
  - a valid pair with a **failing guard** → `409`/`422` with **zero** side
    effects.
  - a valid pair with an **unauthorized initiator** → `403`.
- **RESUME** (`DISPUTED → pre_dispute_status`) — Platform Admin only; restores
  the recorded status; paused timers resume with elapsed-time compensation;
  Operations Officer is denied.
- **Forced transition** by admin — only to a reachable state; writes the
  intervention + audit + reason.

### 1.5 Negotiation tests (brief §29) — **race conditions and agreement freeze**

- **Two concurrent ACCEPTs** on different threads of the same job (run in
  parallel transactions / threads) → **exactly one** `CONFIRMED`; the loser gets
  `409 job_no_longer_available`; the losing thread ends `SUPERSEDED`; exactly one
  `agreement` row.
- **Offer expiry** — an `EXPIRED` entry cannot complete mutual acceptance; the
  expiry sweep does not change `job.status`.
- **Immutability** — an attempted edit/delete of a `negotiation_entry` raises; an
  attempted `UPDATE` of `agreement.agreed_price_kes` raises.
- **Sealed thread** — operator B cannot read operator A's thread on the same job;
  the business can read both.
- **Sanity** — non-positive amount rejected; a 10× mistype returns a
  **non-blocking** warning, not a rejection.

### 1.6 Trust tests (brief §29) — **value-band restrictions**

- L1 operator cannot be assigned an `ELEVATED` job (guard
  `DriverTrustCeilingCoversValue` fails); L2 can; L2 cannot take `HIGH`.
- **Group job**: gating uses the **assigned driver's** ceiling, not the group's —
  a low-trust driver in a "trusted" group is still blocked.
- HIGH job not assignable without an `APPROVED` `high_value_approval`; `VERY_HIGH`
  requires the approval to have been made by a `PLATFORM_ADMIN`.
- Progression is **proposed** by the system, **applied** only after admin
  confirm; there is no code path that sets a level directly.
- At-fault serious incident → auto-Restricted; exit requires a remediation-exit
  change.
- Good-conduct certificate missing → operator cannot reach L2 / take Elevated.

### 1.7 Custody tests (brief §29) — **OTP and evidence requirements**

- `AT_PICKUP → PICKED_UP` **fails** without a verified pickup-side OTP on an
  `ELEVATED+` job (no fallback); **succeeds** on a `STANDARD` job with the
  operator-attested photo fallback and the job is **capped at STANDARD**
  (`proof_of_pickup.attestation = OPERATOR_ATTESTED_UNVERIFIED`); the business
  later confirming flips it to `VERIFIED`.
- Pickup OTP: goes to the **pickup contact's** phone; a driver-entered wrong code
  fails; 5 attempts lock the challenge; re-issue is rate-limited.
- Delivery: `AT_DESTINATION → DELIVERED` requires recipient name + ≥1 method;
  `ELEVATED+` requires recipient OTP **and** a photo.
- Custody rows are append-only; a correction is a `NOTE` with `corrects_event_id`
  and the original stays visible.
- `geo_state = NOT_CAPTURED` is accepted; the step still succeeds.
- `content_hashes` on the custody row match the `evidence_object.sha256`.

### 1.8 Recipient-link tests

- Token: ≥128-bit; stored hashed; a wrong token → `404` (not `403`); resolve
  issues a link-scoped bearer bound to `job_id` + `allowed_actions`.
- Scope: the link cannot read another job, cannot see prices/negotiation, sees
  only first-name + plate + photo of the operator.
- Confirm-receipt requires the recipient OTP; a forwarded link without the OTP
  cannot complete `DELIVERED`.
- Incident creation allowed without OTP but rate-limited; flagged
  `reported_by_kind = RECIPIENT_LINK`.
- Expiry: after `expires_at` → `404`; `revoked_at` → `404`.
- Rate limits: a `/r/` 404 storm from one IP is throttled + alerted.
- Audit: every resolve/view/confirm/incident writes `actor_role = RECIPIENT`.

### 1.9 Security tests (brief §29)

- IDOR/BOLA (see §1.3), privilege escalation (a non-admin cannot grant a role;
  a `role_permissions` change needs Platform Admin + step-up), token abuse
  (refresh reuse → revoke; access token not in `localStorage` in the built PWA —
  a static check), replay (idempotency, single-use OTP/nonce), webhook forgery
  (bad HMAC → rejected; replayed event id → ignored), file-upload abuse (polyglot
  file, oversize, wrong type, EXIF GPS), CSP present and blocking inline script,
  rate limiting fails **closed** for auth/OTP.
- Audit integrity: tampering with an `audit_log_entry` (simulated) breaks the
  hash chain and the nightly verifier flags it.

### 1.10 E2E (Playwright) — the required scenarios (brief §29)

**Scenario A — happy path**

```
Business creates job → Operator discovers it → negotiates (counter, accept) →
Agreement → Assignment (driver + vehicle) → AT_PICKUP → pickup OTP → PICKED_UP →
IN_TRANSIT → AT_DESTINATION → recipient confirms via link (OTP) → DELIVERED →
business accepts → COMPLETED → CommissionRecord exists with the right amount →
weekly statement lists it.
```

**Scenario B — high-value**

```
Business creates a HIGH-value job (declared value > 250,000) → job discoverable
only to L3 operators → operator negotiates + confirms → CONFIRMED → attempt to
ASSIGN → blocked (no approval) → Platform Admin reviews + approves with a
check-in condition → ASSIGN succeeds → custody proceeds with the check-in prompt.
```

**Scenario C — delivery problem**

```
... IN_TRANSIT → AT_DESTINATION → recipient raises an incident (DAMAGE) via the
link → job → DISPUTED → commission HELD → parties add statements + evidence →
amicable proposal declined → Platform Admin records a resolution (REDUCE
commission, rating impact) → job routed to COMPLETED → CommissionRecord REDUCED +
a commission_adjustment row → statement reflects it.
```

Plus E2E smoke: operator onboarding + verification approval; group manager
assigns a member driver; offline queue — mark AT_PICKUP offline, reconnect,
replay, then a conflicting cancellation surfaces in the "Sync issues" tray.

### 1.11 Load (light — pilot scale, NFR-PERF-1)

A `locust`/`k6` profile at ~2–3× expected pilot peak (a few requests/sec, dozens
of concurrent users): assert p95 targets (NFR-PERF-2/3), no lock contention on
`job` beyond the intended serialisation, outbox lag stays near zero, Celery
queues drain.

---

## 2. Coverage targets

| Area | Target |
|------|--------|
| Job state machine (transitions + guards) | **~100%** of transition pairs and guard branches exercised |
| Authorization engine + matrix | **~100%** of the permission-matrix cells |
| Commission calculator + ledger flows | **~95%** incl. all boundaries + dispute treatments |
| Trust evaluation + band gating | **~95%** |
| Custody OTP / evidence rules | **~95%** |
| Recipient link | **~95%** |
| Overall backend line coverage | pragmatic (≈ 80%+), but the four areas above are the gate |
| PWA | component tests for the custody + negotiation flows in both locales; the offline-queue replay/conflict logic |

Coverage is a **floor for the critical modules**, not a vanity number elsewhere.

---

## 3. CI pipeline (NFR-MNT-3)

```
lint (ruff/eslint) → type-check (mypy/tsc) → unit + integration + API tests
(Postgres + Redis services) → state-machine + negotiation + trust + custody +
security suites → schema generate + schemathesis contract → dependency scan
(pip-audit/npm audit) → image scan (Trivy) → SAST (Bandit/Semgrep) → secret scan
(gitleaks) → build images → (on main) deploy to staging → E2E (Playwright) against
staging → manual gate → deploy to production.
```

- The **state-machine, authorization-matrix, negotiation-race, and
  ledger-boundary** suites are **required** — a failure blocks merge.
- A new API endpoint without an authorization-matrix entry fails a registry
  check.
- Migrations run against a copy of a realistic seed DB in CI to catch
  non-additive changes.

---

## 4. Test data

- `factory_boy` builders for every aggregate (`JobFactory`, `OperatorFactory`,
  `GroupFactory`, `AtStateJobFactory(state=...)` that fast-forwards a job through
  valid transitions).
- A **seed dataset** mirroring a small Kitengela pilot (a few operators across
  vehicle classes, a group, several businesses, a spread of jobs at each state)
  used for staging, demos, and the migration test.
- No real PII in fixtures; phone numbers are reserved test ranges.
