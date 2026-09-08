# Problem Statement

## 1. The problem

Businesses and individuals who need goods moved locally, and the transport
operators who could move them, currently find each other through an informal
network of phone calls, personal contacts, and WhatsApp groups. This works, but
it has structural weaknesses:

### For the party needing transport (Business)

- **Discovery is limited to who you already know.** Finding an operator with the
  right vehicle (a canter vs. a pickup vs. a lorry) for a specific load means
  calling around. If your usual contact is busy, you start over.
- **No shared record of what was agreed.** Price, pickup time, and cargo details
  live in a chat thread or a memory. Disagreements have no reference point.
- **No visibility once goods leave.** After handover there is a phone number and
  a hope. No status, no location checkpoints, no delivery confirmation beyond a
  call.
- **Uneven trust.** A new operator is an unknown. There is no portable track
  record.
- **Weak recourse.** If goods are damaged, delayed, delivered to the wrong
  person, or lost, resolution depends entirely on the personal relationship.

### For the party providing transport (Operator)

- **Idle time.** Riders wait at stages; trucks wait at yards. Demand is real but
  not visible to them until someone calls.
- **Work depends on a personal contact list.** A capable operator outside a
  business's existing network never gets the opportunity.
- **No accumulating reputation.** Every good job builds goodwill with one
  customer only. It does not travel.
- **Payment and dispute exposure.** Agreements are verbal. Non-payment or
  after-the-fact price disputes are hard to contest.

### For the ecosystem

- Capacity and demand are poorly matched. Vehicles run empty or wait; loads are
  delayed or overpriced because the nearest suitable operator was never reached.
- There is no data. Nobody knows the real local rate for a 3-tonne load over
  10 km, typical response times, or incident rates.

## 2. Current workarounds (validated practice)

These are how the market operates today. The platform digitizes and improves
them; it does not pretend they are absent.

- **Stages, bases, yards, waiting locations.** Operators cluster physically.
  Customers who know a stage go there or call someone at it.
- **Phone + WhatsApp brokering.** Jobs are described, negotiated, and confirmed
  in chat and calls. Sometimes an informal broker coordinates.
- **Negotiation before commitment.** Both sides propose and counter until a price
  is agreed. Then the job is "on".
- **Amicable resolution.** Faults and disagreements are typically settled by
  discussion between the parties, sometimes with a respected third party at the
  stage/yard.

## 3. Why a platform helps

| Weakness today | What the platform adds |
|----------------|------------------------|
| Discovery limited to known contacts | Structured discovery by vehicle type, capacity, base/stage, service area, availability |
| No shared agreement record | Negotiation history + agreed price preserved on the job |
| No visibility after handover | Enforced job lifecycle + timestamped chain of custody |
| Trust is non-portable | Verification + progressive, platform-wide trust levels |
| Weak recourse | Structured incident reporting, evidence, statements, admin review, resolution |
| No market data | Every job produces structured operational data for pricing, matching, and policy |

## 4. Why now

- The founder already has an existing, reachable network of riders and drivers —
  the classic marketplace cold-start (supply) is substantially solved for a
  local pilot.
- Smartphone and WhatsApp usage among operators is already the norm for getting
  work, so a digital tool fits existing behaviour rather than fighting it.
- Starting local and small allows the product to be shaped by real operations
  before any scaling decision.

## 5. Problem scope for MVP

**In scope:** the coordination gap — discovery, negotiation, agreement,
assignment, chain of custody, delivery confirmation, incident/dispute capture,
and the data exhaust from all of it, within one local pilot area.

**Out of scope for MVP:** owning transport, guaranteeing price, guaranteeing
delivery outcomes, holding funds/escrow at scale, insurance products, and
expansion beyond the pilot area. See [mvp-scope.md](mvp-scope.md).

## 6. Assumptions and unknowns

| Statement | Category |
|-----------|----------|
| Operators in the founder's network will use a digital tool if it fits existing practice | WORKING ASSUMPTION (to validate in pilot) |
| Businesses in the pilot area have unmet or inconvenient transport demand | WORKING ASSUMPTION (to validate in pilot) |
| Operators are willing to have a portable, platform-held reputation | WORKING ASSUMPTION |
| Direct off-platform contact between matched parties is acceptable and expected | CONFIRMED DECISION (follows from discovered practice) |
| Real local rates, response times, incident rates | OPEN QUESTION — the pilot exists to measure these |
| Whether disintermediation (parties going off-platform after first match) is a material risk to the commission model | OPEN QUESTION — see business-model.md |
