# Non-Functional Requirements

Security, privacy, authorization, auditability, trust, and operational safety are
**first-class requirements**. Where they touch the job lifecycle or user model
they are treated as MUST for MVP, not post-MVP additions.

IDs: `NFR-<area>-<n>`. Priority: **MUST** / **SHOULD** / **MAY** for MVP.

---

## NFR-SEC — Security

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-SEC-1 | MUST | All client-server traffic over TLS (HTTPS). No sensitive data over plaintext channels. |
| NFR-SEC-2 | MUST | Authorization is enforced **server-side on every state-changing action**, checking role, verification state, trust level, suspension state, and resource ownership. Hiding controls in the UI is not a security control. |
| NFR-SEC-3 | MUST | Administrator accounts require multi-factor authentication (e.g. password + OTP/TOTP). Operator/Business accounts use phone + OTP; a password/PIN is optional. |
| NFR-SEC-4 | MUST | Sensitive documents and PII at rest (national ID / passport numbers and images, licence images, vehicle documents, payout numbers) are **encrypted at rest** and stored in access-controlled storage; retrieval requires the Verifier sub-role or an explicit dispute need, and each access is audit-logged. |
| NFR-SEC-5 | MUST | Secrets (API keys, DB credentials, signing keys) are held in a secrets manager / environment configuration, never in source control. |
| NFR-SEC-6 | MUST | Input validation and output encoding on all inputs; protection against injection, XSS, CSRF as applicable to the chosen stack. |
| NFR-SEC-7 | MUST | Rate limiting and lockout on authentication, OTP requests, and negotiation actions. |
| NFR-SEC-8 | MUST | Uploaded files are validated (type, size), stored outside the web root / in object storage, served via signed time-limited URLs, and scanned for malware where feasible. |
| NFR-SEC-9 | SHOULD | Dependency and container image vulnerability scanning in CI. |
| NFR-SEC-10 | SHOULD | A basic security review / threat model is completed before the pilot goes live with real operators and real goods. |
| NFR-SEC-11 | MAY | Third-party penetration test before any scaling beyond the pilot. |

## NFR-PRIV — Privacy & data protection

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-PRIV-1 | MUST | Personal data collection is limited to what each function needs (data minimisation). Analytics and exports use the minimum necessary personal data and prefer aggregation/pseudonymisation. |
| NFR-PRIV-2 | MUST | Configurable **data-retention windows** per data class (accounts, job records, chain-of-custody evidence, ID/licence documents, audit logs, dispute records). Data past its window is deleted or irreversibly anonymised, except where a legal hold applies. |
| NFR-PRIV-3 | MUST | A documented lawful basis, privacy notice, and consent flow for collecting ID/licence/vehicle data and location data. **Content REQUIRES KENYAN PROFESSIONAL VALIDATION** (Kenya Data Protection Act 2019 and any sector rules). |
| NFR-PRIV-4 | MUST | Location data is captured only at custody-relevant events, only with permission, and only at the precision needed; "not captured" is an acceptable recorded value. |
| NFR-PRIV-5 | SHOULD | Data-subject request handling (access, correction, deletion) process exists, consistent with the validated legal position. |
| NFR-PRIV-6 | MUST | Role-based visibility: businesses see operator reputation/verification **status** only, never raw ID documents; operators see only the business/job data a job requires; recipients see only their delivery. |
| NFR-PRIV-7 | SHOULD | Register of data processors / third parties (SMS, WhatsApp, maps, hosting) and what data each receives. |

## NFR-AUD — Auditability

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-AUD-1 | MUST | Every state-changing action (by any role, including admins and automated timers) writes an **immutable, append-only** audit entry: actor id + role, action, entity type + id, before/after (where applicable), server timestamp, request source metadata (IP / device / channel). |
| NFR-AUD-2 | MUST | Negotiation entries, chain-of-custody entries, evidence, statements, resolutions, verification decisions, trust-level changes, suspensions, and configuration changes are all append-only; corrections are new records referencing the original. |
| NFR-AUD-3 | MUST | Audit and chain-of-custody records are protected from modification and deletion by application roles; storage-level protections (e.g. write-once/retention lock) SHOULD be used. |
| NFR-AUD-4 | MUST | Timestamps are server-authoritative and stored in UTC; any client-supplied time is stored separately and labelled "reported". |
| NFR-AUD-5 | SHOULD | Audit records are exportable for a given job or account for dispute or investigation purposes, access-controlled. |
| NFR-AUD-6 | MUST | Clock synchronisation (NTP) on all servers. |

## NFR-INT — Data integrity & consistency

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-INT-1 | MUST | Job status transitions are atomic and serialised (optimistic locking / version check); a job cannot enter an invalid or branched state. |
| NFR-INT-2 | MUST | The allowed-transition set is enforced centrally (a single state-machine definition), not duplicated ad hoc across endpoints. |
| NFR-INT-3 | MUST | Money amounts stored as integer minor units (cents) or fixed-precision decimal; never binary floating point. Single currency: KES for MVP. |
| NFR-INT-4 | MUST | Evidence media stored with a content hash; the hash is recorded in the chain-of-custody/evidence entry so tampering is detectable. |
| NFR-INT-5 | MUST | Referential integrity for job ↔ operator ↔ vehicle ↔ location ↔ negotiation ↔ custody ↔ incident. Historical references survive soft-deletion of the parent. |
| NFR-INT-6 | SHOULD | Idempotency keys on create/transition endpoints to make retries safe. |

## NFR-PERF — Performance & capacity (pilot-scale)

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-PERF-1 | MUST | Sized for pilot volume: order of hundreds of operators, hundreds of businesses, low-thousands of jobs per month. No need for large-scale architecture. |
| NFR-PERF-2 | SHOULD | Interactive actions (login, create job, place offer, mark a custody step) respond in < 2 s p95 on a typical mobile connection in the pilot area. |
| NFR-PERF-3 | SHOULD | Job discovery list loads in < 3 s p95 for the pilot dataset. |
| NFR-PERF-4 | MUST | The app is usable on low-end Android phones and on intermittent connectivity: small payloads, graceful handling of a dropped request, no data loss on retry (see NFR-INT-6). |
| NFR-PERF-5 | SHOULD | Media uploads tolerate poor networks (resumable or chunked, client-side compression of photos before upload). |

## NFR-AVAIL — Availability & resilience

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-AVAIL-1 | SHOULD | Target ~99% monthly availability during the pilot; brief maintenance windows acceptable with notice. |
| NFR-AVAIL-2 | MUST | Automated database backups at least daily, stored off the primary host, with a tested restore procedure. |
| NFR-AVAIL-3 | MUST | Defined RPO/RTO for the pilot (WORKING ASSUMPTION: RPO ≤ 24h, RTO ≤ 8h) — founder to confirm acceptability. |
| NFR-AVAIL-4 | SHOULD | Graceful degradation: if SMS/WhatsApp/maps providers are down, core job actions still work and notifications queue for retry. |
| NFR-AVAIL-5 | SHOULD | Health checks and basic uptime/error alerting to the admin/founder. |

## NFR-OBS — Observability

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-OBS-1 | MUST | Centralised application logs (structured), with PII kept out of logs or masked. |
| NFR-OBS-2 | MUST | Error tracking/alerting for unhandled failures. |
| NFR-OBS-3 | MUST | Product/operational event stream feeding the pilot dashboard and export (see FR-DASH). |
| NFR-OBS-4 | SHOULD | Per-job cost counters for external API calls. |

## NFR-COMP — Compliance & legal posture

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-COMP-1 | MUST | Before onboarding real operators and moving real goods, obtain qualified Kenyan advice on: data protection registration/obligations; whether the platform's activity requires any transport/logistics/brokerage licensing; tax treatment of commission (VAT, withholding, invoicing); consumer-protection obligations; carrier/liability characterisation; insurance expectations and any e-money/payment-service implications if money handling is added. **REQUIRES KENYAN PROFESSIONAL VALIDATION.** |
| NFR-COMP-2 | MUST | Terms of Service, operator agreement, and privacy notice drafted with qualified Kenyan counsel and presented/accepted at onboarding. |
| NFR-COMP-3 | MUST | The product makes no user-facing legal, insurance, or guarantee claims that have not been validated (see dispute-and-liability.md §7). |
| NFR-COMP-4 | SHOULD | Record-keeping (retention windows, audit) aligned with the validated legal requirements. |

## NFR-ACC — Accessibility & localization

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-ACC-1 | MUST | UI available in **English and Swahili** (D-PIL-4), per-user selectable, Swahili prominent on operator screens; simple, low-literacy-friendly flows; large tap targets; minimal typing (pickers, map, phone contacts). |
| NFR-ACC-2 | MAY | Additional local language(s) / Sheng register — FUTURE CONSIDERATION beyond the pilot. |
| NFR-ACC-3 | SHOULD | Reasonable contrast and text scaling; usable one-handed on a phone. |

## NFR-MNT — Maintainability & delivery

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-MNT-1 | MUST | Single authoritative definitions for: the job state machine, the role/permission matrix, the platform-configuration schema, and the vehicle/cargo/incident enumerations. |
| NFR-MNT-2 | MUST | Automated tests for the state machine (allowed and forbidden transitions), authorization checks, negotiation immutability, commission calculation, and verification/trust gating. |
| NFR-MNT-3 | SHOULD | CI pipeline: build, test, lint, dependency scan. |
| NFR-MNT-4 | SHOULD | Infrastructure and configuration reproducible from source (scripts / IaC) — created in Phase 1, not Phase 0. |
| NFR-MNT-5 | SHOULD | Seed/fixture data and a staging environment for pilot dry-runs. |

---

## Technology stack — WORKING ASSUMPTION (not a Phase 0 decision)

No backend/hosting stack is chosen in Phase 0. The **client form factor is
decided**: a **Progressive Web App** (D-CLIENT-1). The rest below is planning
default only.

| Concern | Assumption / decision | Rationale |
|---------|-----------------------|-----------|
| Client | **DECIDED: responsive Progressive Web App (PWA)**, mobile-first, installable, offline-tolerant for custody steps, camera for photos/POD. No native app-store builds for MVP. | Fastest to iterate; no app-store cycle; works on low-end Android. Native apps are FUTURE (see future-roadmap.md). |
| Backend | A single well-supported server framework with a relational database (PostgreSQL) | Strong transactional integrity for the job state machine, negotiation, and audit; relational fits the domain. Node.js is already available on the dev host. |
| Storage | Object storage for evidence media with server-side encryption + signed URLs | Meets NFR-SEC-4/8. |
| Messaging | **DECIDED channels: in-app + SMS + WhatsApp** (D-NOTIF-1). SMS via a Kenyan-coverage provider (OTP primary); WhatsApp via the WhatsApp Business Platform through an authorised BSP, with SMS fallback. | Matches FR-NOTIF; WhatsApp matches existing operator behaviour. |
| Maps/geocoding | A maps/geocoding provider with local coverage | Locations, base proximity, distance metrics. |
| Hosting | A single managed region close to the pilot; managed Postgres with automated backups | Meets NFR-AVAIL-2/3 at low ops cost. |
| Auth | Phone + OTP for users; MFA for admins | FR-A-3, NFR-SEC-3. |

The founder / Phase 1 team may choose differently. This table exists so effort
and cost can be estimated, and is explicitly **not** a committed decision.

---

## Status summary

| Item | Category |
|------|----------|
| Security, privacy, authorization, auditability treated as MUST for MVP | CONFIRMED DECISION |
| Immutable append-only audit + chain of custody + negotiation | CONFIRMED DECISION |
| Server-side authorization on every action; admin MFA | CONFIRMED DECISION |
| Encryption at rest for PII/documents; access-logged retrieval | CONFIRMED DECISION |
| Configurable retention windows | CONFIRMED DECISION (values OPEN) |
| Pilot-scale performance/availability targets | WORKING ASSUMPTION — founder to confirm RPO/RTO |
| Client form factor = PWA | CONFIRMED 2026-09-08 (D-CLIENT-1) |
| Notification channels = in-app + SMS + WhatsApp | CONFIRMED 2026-09-08 (D-NOTIF-1) |
| UI languages = English & Swahili | CONFIRMED 2026-09-08 (D-PIL-4) |
| Backend / hosting stack | WORKING ASSUMPTION — decided in Phase 1 |
| Legal/tax/licensing/data-protection specifics | REQUIRES KENYAN PROFESSIONAL VALIDATION |
