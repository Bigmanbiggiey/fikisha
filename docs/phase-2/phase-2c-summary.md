# PHASE 2C — VEHICLES & VERIFICATION REPORT

## 1. Status

**COMPLETE — AWAITING APPROVAL.**

Establishes *who operates which vehicle* and *which verification facts have been
independently checked* about an operator / vehicle / operating base — on top of
Phases 2A (foundation) and 2B (identity & organisation), reusing their
authentication, authorization engine, audit, outbox, storage abstraction, API
conventions, CI, and test infrastructure unchanged. **Verification records the
facts; it computes no trust, value-band, or job/assignment eligibility.**

## 2. Branch

`feat/phase-2c-vehicles-verification` (off `feat/phase-2b-identity-orgs`; not
merged to `main`).

## 3. Commits

```
feat(config): VehicleClass lookup table + verification config
feat(evidence): private evidence objects + HIGH-PII access log
feat(vehicles): vehicle registry — control, class, capacity, status
feat(verification): per-domain records + append-only review workflow
feat(app): register & wire the Phase 2C modules
feat(web): vehicle + verification screens
docs(phase-2): document the Phase 2C vehicles & verification domain
```

## 4. Files / Modules Added

**Backend (new apps):** `fikisha/evidence/` (`models`, `services`, `migrations`,
`tests`), `fikisha/vehicles/` (`models`, `services`, `authz`, `policies`,
`api/{serializers,views,urls}`, `migrations`, `tests`), `fikisha/verification/`
(`models`, `services`, `requirements`, `authz`, `policies`,
`api/{serializers,views,urls}`, `management/commands/verification_expire.py`,
`migrations`, `tests`), `fikisha/api/tests/test_phase_2c_smoke.py`,
`fikisha/platform_config/migrations/0004_vehicleclass.py`,
`.../0005_seed_vehicle_classes.py`.
**Backend (modified):** `platform_config/models.py` (`VehicleClass`),
`platform_config/defaults.py` (drop `vehicle_types`; add `verification` +
`verification_requirements`; `OPERATIONS_OFFICER` gains `vehicle.read`),
`platform_config/services.py` (`vehicle_class_codes`),
`identity/api/views.py` (`ConfigPublicView` builds `vehicle_types` from the
table), `config/settings/base.py` (LOCAL_APPS), `fikisha/api/urls.py`.
**Frontend (new):** `src/features/vehicles/*` (VehiclesPage, VehicleDetailPage,
vehiclesApi, `VehiclesPage.test.tsx`), `src/features/verification/*`
(VerificationPanel, VerificationQueuePage, VerificationRecordPage,
verificationApi).
**Frontend (modified):** `src/services/apiClient.ts` (FormData bodies +
`fetchBlob`), `src/features/org/OperatorProfilePage.tsx` (embed the panel),
`src/app/router.tsx`, `src/shell/TopBar.tsx`, `src/i18n/locales/{en,sw}/org.json`.
**Docs (new):** this file + `vehicles-and-verification.md`,
`phase-2c-privacy-security.md`, `phase-2c-decisions.md`.

## 5. Domain Model

Full detail: [`vehicles-and-verification.md`](vehicles-and-verification.md).

```
OperatorProfile / OperatorGroup ──< Vehicle >── VehicleClass (config: code, name_en/sw, heavy)
        │                              │            vehicle: one controller (operator XOR group, CHECK);
        │                              │            registration + normalized (partial-unique among active);
        │                              │            capacity value + unit; status ACTIVE/INACTIVE/UNDER_REPAIR/SUSPENDED
        └── VerificationRecord ────────┘   one per (subject, domain); state is a cache; effective_state() folds expiry
                 ├──< VerificationDecision   append-only: SUBMIT/START_REVIEW/REQUEST_INFO/APPROVE/REJECT/EXPIRE/RENEW
                 └──< VerificationEvidence >── evidence.EvidenceObject ──< EvidenceAccessLog (append-only, HIGH-PII)
```

## 6. Vehicle Model

`Vehicle` — controlled by exactly one operator OR one group (DB `CHECK`); FK to
`VehicleClass`; `registration` + `registration_normalized` (a plate is reusable
after deactivation — brief §6); numeric `capacity_value` + `capacity_unit`
(KG / TONNES); `ownership` (OWNED / AUTHORISED_DRIVER); operator-declared
`speed_limiter_fitted` / `telematics_installed` claims (the *verified* facts
live in HEAVY_CLASS_COMPLIANCE); `status` (operator sets ACTIVE / INACTIVE /
UNDER_REPAIR; **SUSPENDED is admin-only** — ADR-2C-02); soft delete. Ownership
fixed at registration in 2C (ADR-2C-07).

## 7. Verification Workflow

`submit` (create record → attach evidence → mark submitted) → `START_REVIEW` →
`{REQUEST_INFO → resubmit | APPROVE(+expires_at) → VERIFIED | REJECT(+reason) →
REJECTED}`; `VERIFIED → EXPIRED` when `expires_at` passes (folded in on read;
materialised by `verification_expire`). Review actions need the
`verification.decide` permission (Ops Officer / Platform Admin); an operator or
business user gets **403**; a permitted reviewer **cannot act on a record they
submitted** (422 `reviewer_is_submitter`). Every decision is append-only and
carries the reviewer's identity + role. Evidence of the same `kind` supersedes
(row kept) on resubmission — full history is preserved (brief §21).

Required domains are **config-driven** (`platform_config.verification_requirements`):
OPERATOR → IDENTITY, LICENCE, GOOD_CONDUCT; VEHICLE → VEHICLE, ASSOCIATION,
HEAVY_CLASS_COMPLIANCE (only when `VehicleClass.heavy` — ADR-2C-04); BASE → BASE.
`eligibility()` / `subject_meets()` / `requirements_status()` are fact readers
only.

## 8. Authorization

[`vehicles-and-verification.md`](vehicles-and-verification.md) §2/§3 +
[`phase-2c-privacy-security.md`](phase-2c-privacy-security.md). Extends the
Phase 2A engine (default deny). An operator controls their own vehicles; a group
OWNER/MANAGER the group's; a group DRIVER may **read** group vehicles but not
manage them. Verification: subject owner reads + submits; reviewer (permission)
reads any + acts. Evidence access is **explicitly** authorized per fetch (subject
owner or reviewer only — brief §26), not inherited from the parent record;
HIGH-PII fetches write an `EvidenceAccessLog` row. Cross-organisation → 403.

## 9. Audit

Every vehicle and verification mutation calls Phase 2A `audit.record(...)` in
the same `transaction.atomic` — founder actions included, no bypass. The hash
chain still verifies (`verify_chain()` → `[]`). Verification `VerificationDecision`
and `EvidenceAccessLog` are append-only at the service, model and DB-role
layers.

## 10. Privacy / Security

Evidence is private + API-mediated (no bucket URLs, no pre-signed PUT/GET),
per-purpose type allowlist + 10 MB cap, SHA-256 recorded, explicit per-fetch
authorization, HIGH-PII access logged. Deferred (documented production
hardening): ClamAV, EXIF strip / re-encode, envelope encryption of HIGH-PII
objects. No auto-approve — a human always decides. Details:
[`phase-2c-privacy-security.md`](phase-2c-privacy-security.md).

## 11. Configuration

`VehicleClass` table (8 seeded classes, `heavy` flag on 5); `config.verification`
(recheck cadence, expiry-lead days); `config.verification_requirements`
(mandatory domains per subject, `heavy_only`). `config.data["vehicle_types"]`
removed (ADR-2C-01). Clean DB seed verified. Kitengela stays configuration — no
geographic logic added.

## 12. Tests

**Backend — 258 pass (was 193), 87% line coverage.** New:

| File | Covers |
| --- | --- |
| `evidence/tests/test_evidence.py` | store + sha256 + metadata, type allowlist, size cap, empty upload, HIGH-PII access logged, MEDIUM not logged |
| `vehicles/tests/test_vehicles.py` | individual + group registration, ambiguous / no owner, unknown class, duplicate-active registration + reuse-after-deactivate, operator status vs SUSPENDED (403), admin suspend + lift, seeded classes + heavy flags, CHECK constraint |
| `vehicles/tests/test_vehicles_services.py` | field / class / registration update + conflict + no-op, status transitions + suspend rules, idempotent deactivate |
| `vehicles/tests/test_vehicles_security.py` | cross-operator read/update 403, cannot register to another operator, group DRIVER reads but cannot manage/status, group OWNER manages, unauthenticated 401, unknown id problem+json |
| `verification/tests/test_verification.py` | submit → pending (+ audit + event), full approve, reject-needs-reason, request-info round trip, cannot-review-before-start, cannot-resubmit-while-pending, **submitter-may-not-review**, expiry folded on read, `expire_due` materialises + event, evidence supersede/history, required domains per subject + heavy, wrong domain rejected, **decisions append-only**, CHECK constraint |
| `verification/tests/test_verification_more.py` | request-info note required, GOOD_CONDUCT recheck expiry, suggested expiry from evidence date, `invalidate_association`, subject-ownership authz (vehicle / base / stranger), `requirements_status` |
| `verification/tests/test_verification_api.py` | operator submits → Ops Officer approves (+ queue), operator cannot review (403), business cannot review (403), subject-status endpoint, **evidence access: owner + reviewer 200, stranger 403**, HIGH-PII fetch logged, unauth 401, queue needs permission (403) |
| `api/tests/test_phase_2c_smoke.py` | the full brief §38 flow end-to-end |

**Frontend — 13 pass (was 11).** New: `features/vehicles/VehiclesPage.test.tsx`
(lists; registers to my operator profile).

## 13. Security Tests

Brief §28 §"Security" — all pass:

- unauthenticated → **401** (`test_vehicles_security`, `test_verification_api`);
- unauthorized / cross-org → **403** (cross-operator vehicle, cross-owner
  verification record, group DRIVER manage, business user review, stranger
  evidence fetch);
- object enumeration protection: UUIDv7 ids + 403 (not 404 that reveals nothing
  extra) + `application/problem+json` on unknown ids;
- privilege escalation: operator → review (403), non-admin → SUSPEND a vehicle
  (403), submitter → review own record (422);
- evidence access control: not inherited from the parent — owner or reviewer
  only;
- audit immutability: `VerificationDecision` / `EvidenceAccessLog`
  `.save()` / `.update()` raise `AppendOnlyModelError`; the hash chain verifies.

## 14. Migration check

```
empty PostgreSQL 16  →  migrate  →  Phase 2A + 2B + 2C schema  →  258 tests pass
python manage.py makemigrations --check --dry-run   ->  "No changes detected"
```

New migrations: `platform_config/0004_vehicleclass`, `.../0005_seed_vehicle_classes`,
`evidence/0001_initial`, `vehicles/0001_initial`, `verification/0001_initial`.

## 15. Verification / Definition of Done

| Gate | Result |
| --- | --- |
| Backend `pytest` | **258 passed**, ~87% coverage |
| Backend `ruff check` / `ruff format --check` | clean |
| Backend `mypy` | clean (0 errors, 139 files) |
| Backend `makemigrations --check` | "No changes detected" |
| Frontend `eslint` / `tsc --noEmit` / `vitest` / `vite build` | clean · **13 passed** · build ok |
| Docker | `docker compose up --build` → 6 services healthy; migrations run on start; live API smoke (§17) PASS |

## 16. Manual Smoke Test — actual results

`pytest fikisha/api/tests/test_phase_2c_smoke.py` — **pass**. Also run live
against `docker compose up --build` (2026-09-09):

```
1-3. operator + individual vehicle (LORRY)                  -> 201; vehicle_class_heavy = True; appears under the operator
4-7. group + group PICKUP vehicle; add DRIVER
     owner PATCH group vehicle                              -> 200
     driver GET group vehicle                               -> 200
     driver PATCH group vehicle                             -> 403
8-13 operator IDENTITY verification:
     create record -> add NATIONAL_ID evidence (multipart)  -> 201
     submit                                                 -> SUBMITTED
     operator POST review/start                             -> 403   (no verification.decide)
     Ops Officer review/start                               -> 200
     Ops Officer review/approve {reason}                    -> VERIFIED
     decision history                                       -> ['SUBMIT', 'START_REVIEW', 'APPROVE']
14-16 vehicle VEHICLE verification approved; evidence access:
     owner  GET .../evidence/{id}/content                   -> 200
     reviewer GET                                           -> 200
     stranger GET                                           -> 403
17.  verify_chain()                                         -> []       (audit intact)
     EvidenceAccessLog rows                                 -> 2        (HIGH-PII fetches logged)
18.  stranger GET another operator's vehicle                -> 403
     operator GET another operator's profile                -> 403
19-20 LICENCE approved with a past expiry:
     record.state = VERIFIED, effective_state = EXPIRED     (deterministic, no sweep)
     re-submit LICENCE -> prior evidence superseded (kept), state -> SUBMITTED
RESULT: PASS
```

## 17. Deviations / ADRs

[`phase-2c-decisions.md`](phase-2c-decisions.md). Distinguished there:

- **Approved inherited decisions:** verification is per-domain not a boolean;
  states `NOT_SUBMITTED…EXPIRED`; VERIFIED ≠ TRUSTED; heavy classes need NTSA
  licence + speed limiter + telematics + inspection + insurance; Good Conduct is
  a domain; evidence is private + API-mediated; append-only decision history.
- **Implementation decisions:** ADR-2C-05 (validity computed on read, no beat
  job), ADR-2C-06 (`evidence` module, no API), ADR-2C-07 (control fixed at
  registration — PROVISIONAL), ADR-2C-08 (evidence stream; hardening deferred),
  ADR-2C-09 (`OPERATIONS_OFFICER` gains `vehicle.read`).
- **Deviations requiring approval:** ADR-2C-01 (vehicle classes → lookup table),
  ADR-2C-02 (`Vehicle.status` gains `SUSPENDED`), ADR-2C-03 (one
  `VerificationEvidence` table vs `vehicle_document` + `heavy_class_compliance`),
  ADR-2C-04 (heavy keyed off `VehicleClass.heavy` vs per-vehicle tare). None
  changes a product decision.

## 18. Explicitly NOT Implemented

Jobs · job lifecycle · job requests · negotiation · pricing · assignment ·
dispatch · trust score / reputation / trust level / value-band eligibility
engine · ratings · incidents · disputes · custody · pickup OTP · delivery ·
recipient links · commission · payments · M-Pesa · eTIMS · SMS · WhatsApp · GPS ·
route optimisation · AI matching / dispatch · fleet scheduling · payroll · driver
transfers · wallets · escrow · insurance claims · native mobile apps. No
placeholder implementations of any of these were created.

## 19. Known Limitations

- Vehicle control is fixed at registration (ADR-2C-07); no transfer endpoint
  (`invalidate_association` exists for the future path).
- Evidence hardening deferred: no ClamAV, no EXIF strip / re-encode, no
  envelope encryption of HIGH-PII objects (documented production controls).
- The "operator sees only a thumbnail of their own HIGH-PII" refinement is not
  built — the owner can fetch the full document they submitted.
- No expiry beat job (by design — brief §31); run `manage.py verification_expire`
  or wait for a later notification phase to schedule it.
- `HISTORY` domain is defined but not submittable (it is derived; belongs to
  Trust).
- Idempotency records live in the cache, not a durable table (inherited from 2B).
- RLS still not enabled (Phase 1 OD-10); row scoping is application-layer.

## 20. Phase 2D Handoff — clean inputs only

Phase 2D (recommended: **Trust & Reputation**, then **Jobs**) can consume,
without touching 2C internals:

- `verification.services.subject_meets(subject, [domains]) -> bool` and
  `eligibility(subject) -> {domain: effective_state}` — per-domain verified
  facts, expiry already folded in.
- `verification.requirements.required_domains(subject_type, vehicle_is_heavy=…)`
  and `requirements_status(subject)` — the mandatory-domain set.
- Domain events `verification.decided` / `verification.expired` (and
  `verification.submitted`) via the outbox — for eligibility re-computation and
  notifications.
- `Vehicle` — controller (`owner_operator` / `owner_group`), `vehicle_class`
  (+ `heavy`), `status` / `is_active`, `capacity_value` + `capacity_unit`.
- `platform_config.VehicleClass` and `config.verification_requirements` /
  `config.verification` for tunable rules.

**Do not start Phase 2D.**

---

## Exact commands

```bash
# ── Backend ───────────────────────────────────────────────────────────
cd backend
python -m venv .venv && . .venv/Scripts/activate            # or .venv/bin/activate
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.test
export POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=fikisha \
       POSTGRES_USER=fikisha POSTGRES_PASSWORD=fikisha-local-dev \
       DJANGO_SECRET_KEY=test-secret \
       REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1

python manage.py migrate
python manage.py makemigrations --check --dry-run           # -> "No changes detected"
ruff check .
ruff format --check .
mypy .                                                      # -> 0 errors, 139 files
pytest                                                      # 258 passed, ~87% coverage
python manage.py verification_expire                        # (ad-hoc expiry sweep)

# ── Frontend ──────────────────────────────────────────────────────────
cd ../frontend
npm ci
npm run lint
npm run typecheck
npm run test                                                # 13 passed
npx vite build

# ── Docker / smoke ───────────────────────────────────────────────────
cp .env.example .env
docker compose up -d --build
pytest fikisha/api/tests/test_phase_2c_smoke.py             # the §38 flow (in-process)
# or the live curl sequence in §16 against http://localhost:8000
docker compose exec backend python manage.py shell -c \
  "from fikisha.audit.services import verify_chain; print(verify_chain())"   # -> []
docker compose down
```

---

## Phase 2C Status

COMPLETE — AWAITING APPROVAL
