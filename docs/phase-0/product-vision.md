# Product Vision

## 1. One-sentence description

A local logistics marketplace that connects businesses and customers who need
goods moved with verified local transport operators — motorcycles through
semi-trucks — by digitizing the way those operators already get work, rather than
replacing it.

## 2. Vision statement

Local transport capacity already exists in every town: riders at stages, drivers
at yards and bases, trucks parked waiting for a call. Work reaches them today
through phone calls, personal contacts, and WhatsApp. That network is effective
but invisible, hard to scale, and offers no shared record of what was agreed or
what happened to the goods.

The platform's role is to make that existing network **addressable, accountable,
and trustworthy** — a place where a business can reach the right operator for a
load, negotiate as they already would, agree a price, and have an auditable
record of the goods from pickup to delivery. Over time the accumulated record of
completed jobs becomes the basis for trust, pricing guidance, and better
matching.

We are a coordination layer over capacity we do not own. We succeed when
operators earn more with less idle time and businesses move goods with less
friction and less risk.

## 3. Core product principle (restated)

**Design around discovered practice, not assumed practice.**

The following practices are treated as the ground truth to build on, not
problems to eliminate:

| Practice | Product implication |
|----------|---------------------|
| Operators work from physical stages, bases, yards, waiting locations | Operating base/stage is a first-class registered entity, used for discovery and matching |
| Riders operate from stages; drivers from bases/yards | Operator model must represent both without forcing one shape |
| Work is obtained via calls, contacts, WhatsApp | Platform augments these channels; direct contact is expected, not blocked. Notifications may use the same channels |
| Price negotiation is normal | Negotiation is a core flow with preserved history, not an afterthought |
| Both parties negotiate before accepting | A job is confirmed only on mutual agreement |
| Faults/disagreements are usually resolved amicably | Dispute handling starts with structured amicable resolution before escalation |

## 4. Who it serves

- **Businesses / customers** needing transport: retailers, wholesalers,
  distributors, hardware and construction suppliers, agricultural traders, market
  vendors, and individuals with occasional loads. Ranges from a single documents
  envelope on a motorcycle to a multi-tonne construction load on a lorry.
- **Transport operators**: individual riders and drivers, and small owner
  operators, already active in the founder's network. Not an owned fleet.
- **Platform administrators**: verification, monitoring, intervention, dispute
  handling, configuration.

## 5. What makes it different

1. **Operator-practice-first.** Stages/bases/yards, negotiation, and direct
   contact are designed in, not designed out.
2. **Any vehicle class.** One job model spans a motorcycle parcel and a
   semi-trailer haul.
3. **Auditable chain of custody.** Every job carries a timestamped, actor-attributed
   record from assignment to completion.
4. **Progressive trust, not binary access.** New operators are verified but earn
   access to high-value work through demonstrated performance.
5. **Evidence-based iteration.** The local pilot exists to produce operational
   data that drives product decisions.

## 6. Long-term direction (not commitments)

- Pricing guidance derived from historical platform data (recommended ranges,
  never forced).
- Richer matching (utilization-aware, return-trip aware, stage-cluster aware).
- Business tooling: recurring lanes, scheduled logistics, cost analytics.
- Fleet and enterprise services for larger operators and shippers.
- Geographic expansion, one validated area at a time.

All of the above are **FUTURE CONSIDERATION** and covered in
[future-roadmap.md](future-roadmap.md).

## 7. Explicit non-goals for the near term

- Not an owned-fleet carrier.
- Not a fixed-tariff service (no enforced pricing during MVP).
- Not a courier brand with its own last-mile staff.
- Not a payments/wallet business (payment rails are minimized in MVP — see
  [business-model.md](business-model.md)).
- Not a regulated freight forwarder or insurer. Any such role
  **REQUIRES KENYAN PROFESSIONAL VALIDATION** before it is even considered.

## 8. Status summary

| Item | Category |
|------|----------|
| Marketplace coordinating non-owned local transport capacity | CONFIRMED DECISION |
| Multi-vehicle-class from motorcycle to trailer | CONFIRMED DECISION |
| Digitize existing workflow (stages, negotiation, direct contact) rather than replace it | CONFIRMED DECISION |
| Progressive trust model | CONFIRMED DECISION |
| Commission-based revenue | CONFIRMED DECISION (rate open) |
| Platform/brand name = **`Fikisha`** | CONFIRMED 2026-09-08 (D-BRAND-1); BRS/KIPI/domain registration pending |
| Specific pilot geography | OPEN QUESTION (see pilot-strategy.md) |
| Any legal/insurance/forwarder positioning | REQUIRES KENYAN PROFESSIONAL VALIDATION |
