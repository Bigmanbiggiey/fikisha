# Phase 0 — Product Discovery & Definition

**Project:** Fikisha — Local Logistics Marketplace *(brand confirmed 2026-09-08;
repo dir still `LOGISTIX`)*
**Phase:** 0 (Discovery & Definition)
**Status:** COMPLETE — AWAITING FOUNDER REVIEW
**Date:** 2026-09-08 (same-day addendum: pilot area, English & Swahili, brand
`Fikisha`, commission, trust bands/levels, cancellation, dispute windows, proof
of pickup, admin roles, PWA client, WhatsApp channel, operator groups, recipient
link)
**Author:** Product/Engineering agent

---

## Purpose of Phase 0

Establish the product definition, domain model, and technical requirements needed
before any implementation begins. **No application code, framework, dependency,
migration, or infrastructure has been created in this phase.**

The project directory was inspected and found empty (non-git, Windows host,
Node.js available). This documentation set is the sole Phase 0 output.

---

## Document set

| # | Document | Purpose |
|---|----------|---------|
| 1 | [product-vision.md](product-vision.md) | What the platform is, who it serves, the long-term direction |
| 2 | [problem-statement.md](problem-statement.md) | The problem, current workarounds, why now |
| 3 | [users-and-roles.md](users-and-roles.md) | Business, Operator, Administrator — capabilities and boundaries |
| 4 | [mvp-scope.md](mvp-scope.md) | What the MVP includes and — explicitly — what it excludes |
| 5 | [business-model.md](business-model.md) | Commission model, configuration, future revenue |
| 6 | [operator-model.md](operator-model.md) | Stages/bases/yards, vehicles, availability, service areas |
| 7 | [job-lifecycle.md](job-lifecycle.md) | Job states and the enforced transition rules |
| 8 | [pricing-and-negotiation.md](pricing-and-negotiation.md) | Negotiation flow, history preservation, agreed price |
| 9 | [trust-and-safety.md](trust-and-safety.md) | VERIFIED vs TRUSTED, progressive trust levels, high-value safeguards |
| 10 | [dispute-and-liability.md](dispute-and-liability.md) | Incidents, evidence, resolution, liability boundaries |
| 11 | [pilot-strategy.md](pilot-strategy.md) | Local pilot goals, metrics, learning agenda |
| 12 | [functional-requirements.md](functional-requirements.md) | Numbered functional requirements (FR-*) |
| 13 | [non-functional-requirements.md](non-functional-requirements.md) | Security, privacy, auditability, performance, availability (NFR-*) |
| 14 | [domain-model.md](domain-model.md) | Conceptual entities, relationships, the JOB aggregate |
| 15 | [future-roadmap.md](future-roadmap.md) | Post-MVP considerations, explicitly deferred |
| 16 | [decisions.md](decisions.md) | Decision log: confirmed / assumed / open |
| — | [phase-0-report.md](phase-0-report.md) | Executive summary, risks, open questions, recommended next phase |
| — | [brand-name.md](brand-name.md) | Consumer brand analysis and recommendation (added 2026-09-08) |
| — | [legal-scope.md](legal-scope.md) | Kenyan regulatory map, legal posture, required contracts, pre-pilot legal checklist (added 2026-09-08) |
| — | [decision-memo-2026-09-08.md](decision-memo-2026-09-08.md) | Founder memo: brand, Kitengela pilot area, and six operating-policy recommendations |

---

## How to read the status markers

Every document separates four categories. They are never blended.

- **CONFIRMED DECISION** — stated in the founder brief or an unavoidable consequence of it. Safe to build on.
- **WORKING ASSUMPTION** — a reasonable default chosen to make progress. Reversible. Should be confirmed.
- **OPEN QUESTION** — genuinely undecided; needs a founder answer or external validation before implementation depends on it.
- **FUTURE CONSIDERATION** — deliberately out of scope for now; recorded so it is not lost.

Legal, tax, insurance, licensing, and liability points are flagged
**REQUIRES KENYAN PROFESSIONAL VALIDATION** and are not treated as settled.

---

## What Phase 0 does NOT do

- It does not choose a technology stack (a recommendation is offered in
  `non-functional-requirements.md` as a WORKING ASSUMPTION only).
- It does not commit the founder to any pricing number, geographic area, launch
  date, or legal position.
- It does not begin implementation. Implementation is Phase 1 and starts only
  after founder review of this set.
