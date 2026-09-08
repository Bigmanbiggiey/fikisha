# Technology Stack

**Status of this document:** RECOMMENDED. The founder / Phase 2 team may
override any line with reasons. Nothing here is a Phase 0 CONFIRMED decision
except the **client form factor = PWA** (D-CLIENT-1), **channels = in-app + SMS +
WhatsApp** (D-NOTIF-1), **relational data** (Phase 0 NFR-INT), and **English +
Swahili** (D-PIL-4).

---

## 1. What the stack must support (from Phase 0)

| Requirement | Source |
|-------------|--------|
| Responsive **PWA**, installable, low-end Android, unreliable connectivity, camera | D-CLIENT-1, NFR-PERF-4/5, NFR-ACC-* |
| Phone + **OTP** auth for users; **MFA** for admins | FR-A-1/2/3, NFR-SEC-3 |
| **SMS + WhatsApp + in-app** notifications; OTP SMS-primary; WhatsApp via BSP with SMS fallback | D-NOTIF-1, FR-NOTIF-* |
| **Role-based + attribute-based authorization**, enforced server-side on every state-changing action | NFR-SEC-2, trust-and-safety §5 |
| **Transactional consistency** for the job state machine, negotiation, assignment, commission | NFR-INT-1/2, FR-J-3/5, FR-N-6 |
| **Append-only audit** + chain of custody + negotiation history; storage-level write protection where possible | NFR-AUD-1/2/3 |
| **Private, encrypted evidence storage** with signed, time-limited, authorized access | NFR-SEC-4/8, FR-C-7 |
| **Background processing** (notifications, statements, expiry sweeps, image processing, exports) | FR-M-4, FR-J-11/12, pilot-strategy §5 |
| **PostgreSQL-style relational** data | NFR-INT-3/5 |
| **Secure API** access | NFR-SEC-1/6/7 |
| Room for **future native clients** and **future integrations** without a rewrite | Phase 1 brief §6, future-roadmap |
| **Pilot scale**: hundreds of operators, hundreds of businesses, low-thousands of jobs/month | NFR-PERF-1 |
| **Bootstrapped budget**; modular monolith, not premature microservices | Phase 1 brief §7, §30, §34 P15 |
| **English + Swahili** from day one, including server-rendered SMS text | D-PIL-4, NFR-ACC-1 |
| Configurable-not-coded: state machine, permission matrix, config schema, enums | NFR-MNT-1 |

---

## 2. Backend framework — evaluation

| Option | Strengths for Fikisha | Weaknesses | Verdict |
|--------|----------------------|------------|---------|
| **Django + Django REST Framework (Python)** | Batteries-included; **mature transactional ORM** (`select_for_update`, savepoints) ideal for the state machine, negotiation-accept, and the commission ledger; first-class **migrations**; a permission framework to build RBAC/ABAC on; **Django Admin** gives a large head start on the internal admin surface (verification queue, config, audit viewer, job monitor) — a major cost saving for a 1–2-person ops team; large talent pool; **Celery + Redis** is the standard, well-trodden background path; clean mapping of **Django apps → bounded modules** (modular monolith). | Python async story is weaker (irrelevant at pilot scale); ORM can hide N+1s (mitigated by discipline + `django-debug-toolbar` in dev). | **RECOMMENDED** |
| **Node.js / TypeScript (NestJS + Prisma or Drizzle)** | One language front-to-back; shared types; Node already on the dev host; NestJS module system fits the modular monolith; good DI. | The **admin surface must be built from scratch** (weeks of work vs. days with Django Admin); transaction ergonomics across Prisma are less battle-tested for complex multi-row invariants; more assembly (auth, permissions, migrations, background jobs each a separate choice). | Strong #2. Choose only if the team is Node-only and will not use an admin scaffold. |
| **Ruby on Rails** | Comparable batteries-included story; excellent transactions; ActiveAdmin. | Smaller local hiring pool than Python/PHP/JS; otherwise fine. | Viable #3. |
| **Laravel (PHP)** | Batteries included; Nova admin; large PHP hiring pool in Kenya. | Queue/worker story workable but less standard than Celery; team familiarity dependent. | Viable #4. |
| **Go** | Great deploy story and throughput. | Slow to build a CRUD- and workflow-heavy domain app; overkill at pilot scale; admin from scratch. | Not recommended for the MVP. |

**Recommendation: Django + Django REST Framework.** The decisive factors are the
**admin surface** (large slice of MVP scope, cheaply covered), the **transactional
ORM** (the state machine, negotiation, and ledger all depend on it), and the
**app → module** structure for a clean modular monolith.

Supporting libraries (RECOMMENDED, not load-bearing):

- **Celery** + **Redis** — background jobs, beat scheduler, rate-limit counters, locks, caching.
- **django-storages** + **boto3** — S3-compatible object storage.
- **django-otp** / **pyotp** — TOTP for admin MFA (custom flow for user phone OTP).
- **structlog** / **django-structlog** — structured logging.
- **drf-spectacular** — OpenAPI schema generation.
- **pytest** + **pytest-django** + **factory_boy** — testing.
- A small **state-machine** module authored in-house (not a heavyweight FSM library) so the allowed-transition table is one readable declaration — see [job-state-machine.md](job-state-machine.md).

> **Note on D-A-STACK-1.** Phase 0 said "Node.js is already available on the dev
> host" but explicitly marked the stack "Not a decision — chosen in Phase 1."
> This document exercises that. If the founder prefers Node, the architecture in
> the other Phase 1 documents is framework-agnostic at the design level (modules,
> the state-machine seam, the outbox, the authorization engine, the ledger) and
> ports to NestJS with the admin-surface cost noted above.

---

## 3. Frontend — evaluation

| Option | Strengths | Weaknesses | Verdict |
|--------|-----------|------------|---------|
| **React + TypeScript + Vite** (+ `vite-plugin-pwa`/Workbox, Tailwind CSS) | Largest ecosystem and hiring pool; `vite-plugin-pwa` handles the service worker; TanStack Query for server state; mature i18n (`react-i18next` + ICU); code-splitting keeps the shell small. | React + ReactDOM ≈ 45 KB gzipped — heavier than alternatives on low-end devices (mitigated by route-level lazy-loading, a lean dependency budget, and optionally `preact/compat`). | **RECOMMENDED** |
| **Svelte / SvelteKit** | Smallest runtime; excellent on low-end devices; built-in stores. | Smaller hiring pool; SvelteKit's SSR/routing model is more than a pure SPA-PWA needs. | Worth a **device-performance spike** in early Phase 2; adopt if React bundle size proves a real problem in Kitengela field tests. |
| **Preact + preact-router** | ~4 KB runtime; near-React API. | Smaller ecosystem; some React libraries need `preact/compat` shims. | Fallback optimization path. |

**Recommendation: React + TypeScript + Vite**, with **`preact/compat`** and a
strict dependency budget as the first optimization lever, and a Svelte spike as
the contingency (tracked in [technical-risks.md](technical-risks.md)).

Frontend libraries (RECOMMENDED):

- **Vite** + **vite-plugin-pwa** (Workbox) — build + service worker.
- **Tailwind CSS** — styling; small, purge-able, good for consistent large tap targets.
- **TanStack Query** — server-state caching + retries + background refetch.
- **react-i18next** + **i18next-icu** — localization (see [localization.md](localization.md)).
- **idb** (thin IndexedDB wrapper) — the offline mutation queue and photo queue.
- **MapLibre GL JS** + a tile provider, or a static-map-image fallback for the lowest-end devices — see §5.
- **zod** — client-side form/response validation mirroring server error codes.

---

## 4. Data & infrastructure

| Concern | Recommendation | Notes |
|---------|----------------|-------|
| **Relational DB** | **PostgreSQL 16** | Transactions, `JSONB` (config snapshots, event payloads), partial/expression indexes, check constraints, exclusion constraints (e.g. one active `Agreement` per job). Non-negotiable given NFR-INT. |
| **Object storage** | **S3-compatible** API. Pilot: either a managed S3 bucket in the nearest acceptable region, or **MinIO** co-located with the app on the pilot VPS. | Provider/region choice is **OPEN** and **REQUIRES VALIDATION** (data residency — legal-scope §3.4). App-level envelope encryption for HIGH-PII objects (ID/licence images) reduces exposure regardless of region. |
| **Cache / queue broker / locks / rate-limit counters** | **Redis 7** | One instance for the pilot. |
| **Background workers** | **Celery** (worker + beat) | See [events-and-background-jobs.md](events-and-background-jobs.md). |
| **Reverse proxy / TLS** | **Caddy** (automatic HTTPS) or nginx + certbot | HSTS, security headers, request-size limits. |
| **Containerisation** | **Docker** + **docker compose** for dev, staging, production (single host) | No Kubernetes for the pilot (Phase 1 brief §30, §34 P15). |
| **CI/CD** | **GitHub Actions** — build, test, lint, dependency + image scan, push image, deploy over SSH | See [deployment-architecture.md](deployment-architecture.md). |

---

## 5. External service adapters (provider-agnostic; specific vendors are OPEN)

Each is behind an interface so the vendor can change without touching business logic.

| Capability | Interface | Candidate providers (OPEN — pick on cost + coverage + compliance) |
|------------|-----------|------------------------------------------------------------------|
| **SMS** (OTP + notifications) | `SmsGateway.send(to, text, ref)` + delivery-receipt webhook | **Africa's Talking** (Kenyan, strong local coverage, competitive pricing) — leading candidate; Twilio; Infobip. |
| **WhatsApp** (notifications + recipient link) | `WhatsappGateway.send_template(to, template, params, ref)` + status webhook | An **authorised WhatsApp BSP**: Africa's Talking WhatsApp, 360dialog, Twilio, Infobip. Requires template pre-approval; **US cross-border transfer to Meta** — REQUIRES VALIDATION (legal-scope §3.9). |
| **Geocoding + distance** | `GeoService.geocode(text)`, `GeoService.route_distance(a, b)` | Google Maps Platform (best local coverage, metered cost); Mapbox; self-hosted OSRM/OpenRouteService (cheapest, coverage risk on Kitengela outskirts). Cache aggressively; allow ops manual distance override. |
| **Map tiles** (client) | Tile URL template | MapLibre-compatible: MapTiler, Mapbox tiles, or a self-hosted style. For the lowest-end devices, a **static map image + pin** avoids shipping a GL renderer. |
| **eTIMS** (commission invoices) | `EtimsService.submit_invoice(statement)` | KRA eTIMS via OSCU/VSCU/eTIMS-Lite or an accredited middleware. **Integration mode REQUIRES VALIDATION** (tax advisor + KRA). Fallback: generate compliant-format invoices and record eTIMS reference entered manually until integration lands. |
| **M-Pesa commission settlement** (collection of the platform's own commission only) | `PaybillGateway.reconcile()` — optional C2B confirmation webhook | Safaricom Daraja C2B on a **merchant paybill**. **Manual settlement recording** by ops is the week-1 default; webhook added if the paybill supports it. The platform **never** holds the transport fare (D-BIZ-6, legal-scope §3.6). |
| **Error tracking** | SDK | Sentry (SaaS) or self-hosted **GlitchTip** (cheap). |
| **Malware scan** (non-image uploads) | `FileScanner.scan(object)` | **ClamAV** in a Celery task; quarantine until clean. |

---

## 6. Rejected / deferred technology choices

| Choice | Why not now |
|--------|-------------|
| Microservices / service mesh / message broker (Kafka/RabbitMQ) | Pilot scale does not need it; Phase 1 brief mandates a modular monolith; a **transactional outbox + Celery** covers async fan-out. |
| Kubernetes / autoscaling / multi-region | Bootstrapped pilot; single VPS + compose + good backups is sufficient (NFR-AVAIL-1 ≈ 99%). |
| GraphQL | REST + OpenAPI is simpler for a small team and a PWA; no client-shape diversity that GraphQL would earn. |
| Native iOS/Android apps | D-CLIENT-1: PWA for MVP; native is future-roadmap. |
| A third-party workflow/FSM engine | The lifecycle is small and safety-critical; an in-house table + one service function is clearer and fully testable. |
| Event-sourcing the Job aggregate | Overkill; append-only `job_event` + a mutable `job.status` row gives the audit trail without the read-model complexity. |
| Blockchain / external notarisation for the audit log | App-level append-only + DB privilege revocation + row hash-chaining is proportionate for the pilot (see [security-architecture.md](security-architecture.md)). |

---

## 7. Summary of the recommended stack

```
Client:     React + TypeScript + Vite + Tailwind + vite-plugin-pwa (Workbox)
            react-i18next (+ ICU), TanStack Query, idb, MapLibre (or static maps)

API:        Django + Django REST Framework (Python), drf-spectacular (OpenAPI)

Domain:     Modular monolith — Django apps as bounded modules;
            an in-house state-machine module; an authorization policy engine;
            a transactional outbox

Async:      Celery (worker + beat) on Redis

Data:       PostgreSQL 16
Storage:    S3-compatible (managed bucket in nearest acceptable region, or MinIO)
Cache/broker: Redis 7

Edge:       Caddy (automatic TLS, security headers)
Runtime:    Docker + docker compose (single host per environment)
CI/CD:      GitHub Actions

Adapters:   SMS gateway · WhatsApp BSP · Geo/distance · eTIMS · M-Pesa paybill
            reconcile · error tracking · file scan   (all interface-first, vendors OPEN)
```
