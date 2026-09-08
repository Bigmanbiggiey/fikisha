# Phase 1 — Architecture & Technical Design

**Project:** Fikisha — Local Logistics Marketplace
**Pilot:** Kitengela, Kajiado County + environs
**UI languages:** English + Swahili (Swahili prominent on operator-facing screens)
**Phase:** 1 — Architecture & Technical Design
**Status:** COMPLETE — AWAITING FOUNDER REVIEW
**Date:** 2026-09-08

---

## What Phase 1 is

Phase 1 turns the founder-approved **Phase 0 product definition** (`docs/phase-0/`)
into a **production-quality technical blueprint** another engineer could implement
without rediscovering the product.

**Phase 1 is design only.** No application source, migrations, dependencies,
containers, databases, or deployment configuration were created. The output is
this documentation set.

Phase 0 remains the source of truth for *what* the product is. Phase 1 decides
*how* it is built, and never silently changes a confirmed Phase 0 decision. Where
Phase 1 found a contradiction between documents or the Phase 1 brief, it is
recorded in [`technical-risks.md`](technical-risks.md) and
[`phase-1-decisions.md`](phase-1-decisions.md), not resolved silently.

---

## Document set

| # | Document | Purpose |
|---|----------|---------|
| — | [phase-1-summary.md](phase-1-summary.md) | **Read first.** Executive summary of the whole architecture, risks, open decisions, Phase 2 sequence. |
| — | [phase-1-decisions.md](phase-1-decisions.md) | Architecture Decision Records (ADRs). Every significant choice, with options, rationale, trade-offs, and a CONFIRMED / RECOMMENDED / OPEN / REQUIRES VALIDATION label. |
| 1 | [technology-stack.md](technology-stack.md) | Stack evaluation and the one recommended stack. |
| 2 | [system-context.md](system-context.md) | Actors, external systems, trust boundaries (C4 level 1). |
| 3 | [architecture.md](architecture.md) | System architecture, layers, responsibilities, dependencies (C4 level 2–3). |
| 4 | [domain-architecture.md](domain-architecture.md) | Bounded modules: responsibility, owned entities, invariants, interfaces, events. |
| 5 | [database-design.md](database-design.md) | Relational design: tables, keys, constraints, indexes, enums, soft-delete, tenancy, sensitive-data handling. |
| 6 | [job-state-machine.md](job-state-machine.md) | The authoritative job lifecycle: states, transitions, guards, side effects, concurrency, idempotency. |
| 7 | [negotiation-architecture.md](negotiation-architecture.md) | Offer / counter / accept / decline / expiry / agreement-freeze; concurrency; immutability. |
| 8 | [verification-architecture.md](verification-architecture.md) | Per-domain verification records, lifecycles, expiry, derived eligibility. |
| 9 | [trust-architecture.md](trust-architecture.md) | VERIFIED ≠ TRUSTED; L1/L2/L3; evidence-based, auditable progression; value-band gating. |
| 10 | [chain-of-custody.md](chain-of-custody.md) | Append-only job-event timeline, custody subset, location-evidence privacy. |
| 11 | [recipient-access.md](recipient-access.md) | The no-account per-job link: scoping, token model, permissions, threat model. |
| 12 | [evidence-storage.md](evidence-storage.md) | Private object storage, encryption, signed access, authorization, retention. |
| 13 | [authentication-authorization.md](authentication-authorization.md) | Phone+OTP, admin MFA, sessions, and the server-side authorization model + permission matrix. |
| 14 | [security-architecture.md](security-architecture.md) | Security controls and threat models for the most sensitive workflows. |
| 15 | [api-architecture.md](api-architecture.md) | API conventions and per-module resource design. |
| 16 | [notification-architecture.md](notification-architecture.md) | Provider-agnostic notifications: in-app + SMS + WhatsApp, OTP SMS-primary, fallback, templates, localization. |
| 17 | [commission-ledger.md](commission-ledger.md) | Immutable commission records, statements, settlement, adjustments, config-version pinning. |
| 18 | [admin-architecture.md](admin-architecture.md) | Internal admin surface: queues, consoles, config, audit; founder actions are audited. |
| 19 | [events-and-background-jobs.md](events-and-background-jobs.md) | Sync vs async, the transactional outbox, domain events, scheduled jobs. |
| 20 | [pwa-architecture.md](pwa-architecture.md) | Service worker, caching, offline-safe vs server-confirmed actions, camera, sync. |
| 21 | [localization.md](localization.md) | English + Swahili from day one: catalogs, keys, formatting, notification templates. |
| 22 | [observability.md](observability.md) | Logging, error tracking, metrics, health checks, and the pilot metric pipeline. |
| 23 | [testing-strategy.md](testing-strategy.md) | Unit / integration / API / state-machine / security / E2E, with required scenarios. |
| 24 | [deployment-architecture.md](deployment-architecture.md) | Dev / staging / production; backups; migrations; rollback; bootstrapped cost. |
| 25 | [technical-risks.md](technical-risks.md) | Technical risks, contradictions found, and mitigations. |

## Diagrams

Mermaid diagrams live inline in the relevant documents:

| Diagram | Document |
|---------|----------|
| System architecture | [architecture.md](architecture.md) |
| System context / trust boundaries | [system-context.md](system-context.md) |
| Module relationships | [domain-architecture.md](domain-architecture.md) |
| Job lifecycle state machine | [job-state-machine.md](job-state-machine.md) |
| Negotiation flow | [negotiation-architecture.md](negotiation-architecture.md) |
| Chain of custody sequence | [chain-of-custody.md](chain-of-custody.md) |
| Authentication / authorization | [authentication-authorization.md](authentication-authorization.md) |
| Operator / group / vehicle relationship | [domain-architecture.md](domain-architecture.md) |
| Commission flow | [commission-ledger.md](commission-ledger.md) |
| Notification architecture | [notification-architecture.md](notification-architecture.md) |
| High-value job approval flow | [trust-architecture.md](trust-architecture.md) |

---

## Status markers (used throughout)

- **CONFIRMED** — fixed by Phase 0 (a founder decision) or an unavoidable consequence of one. Not re-litigated here.
- **RECOMMENDED** — a Phase 1 technical choice made to make progress; reversible by the founder / Phase 2 team with reasons given.
- **OPEN** — a technical decision that still needs a founder answer, a commercial input (provider terms), or a spike.
- **REQUIRES VALIDATION** — depends on qualified Kenyan legal / tax / insurance advice (per `docs/phase-0/legal-scope.md`); the architecture isolates it behind an adapter and does not hard-code an assumption.
