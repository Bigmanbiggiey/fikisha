# Pilot Strategy

## 1. Purpose

The pilot is **not** just a software launch. Its purpose is to generate
**operational knowledge** that will refine the product before any scaling
decision. Every feature in the MVP exists to let real jobs run and to capture
data about how they run.

---

## 2. Pilot shape

| Parameter | Value | Category |
|-----------|-------|----------|
| Geographic area | **Kitengela, Kajiado County**, serving Kitengela town and its environs: Namanga-road corridor, Athi River / Mavoko boundary, Isinya, Kisaju, Kaputiei, and links to Nairobi's Industrial Area / CBD | CONFIRMED (founder, 2026-09-08) |
| UI languages | **English & Swahili** (Swahili prominent on operator screens) | CONFIRMED (founder, 2026-09-08) |
| Zone breakdown | Founder will supply later; **deferred** — treated as a `PlatformConfig.zones` update, not a Phase 1 blocker; pilot area is one zone until then | DEFERRED (D-PIL-5) |
| Operator supply | The founder's existing riders and drivers | CONFIRMED |
| Vehicle classes in pilot | At least two distinct classes (e.g. motorcycle + a truck class); ideally the full range the network has | WORKING ASSUMPTION |
| Business demand | A hand-picked set of pilot businesses recruited by the founder | WORKING ASSUMPTION |
| Duration | Long enough to observe repeat behaviour, incidents, and seasonality effects — **suggested 8–12 weeks minimum** | WORKING ASSUMPTION — founder to confirm |
| Money | Direct payment between parties; commission recorded and settled via periodic statement | WORKING ASSUMPTION (see business-model.md) |
| Support model | Founder + at least one administrator handling verification, monitoring, and disputes | WORKING ASSUMPTION |

---

## 3. Onboarding plan

Phased, to keep manual verification tractable:

1. **Week 0 (pre-launch):** verify a first cohort of operators (identity,
   licence, vehicle, base) and 3–5 pilot businesses. Dry-run 2–3 test jobs
   end to end.
2. **Weeks 1–2:** live with the first cohort. Small daily job volume. Daily
   founder/admin review of every job and every incident.
3. **Weeks 3+:** widen operator and business cohorts as verification and support
   capacity allow. Begin weekly metric reviews.

---

## 4. Learning agenda — what the pilot must measure

Grouped by the areas named in the brief. Each metric should be derivable from
platform data with no extra manual bookkeeping.

### 4.1 Demand
- Jobs created per day/week; by vehicle class; by business; by area/zone.
- Job value distribution (declared cargo value; agreed price).
- Time-of-day / day-of-week patterns.
- Repeat-business rate.

### 4.2 Supply & utilization
- Active operators per day; by vehicle class; by base/stage.
- Jobs offered vs. accepted per operator.
- Operator idle time proxy (available time with no job vs. time on jobs).
- Vehicle utilization (jobs per vehicle per week; laden vs. empty where known).
- Coverage gaps (job requirements with no eligible/available operator).

### 4.3 Pricing & negotiation
- Proposed vs. agreed price; delta and number of counter-offers to agreement.
- Agreed price vs. distance, weight, vehicle class, area — the raw material for
  future price guidance.
- Negotiation abandonment rate; time from REQUESTED to CONFIRMED.
- Cases where price was far outside any soft band (if bands are configured).

### 4.4 Matching & response
- Time from REQUESTED to first offer.
- Time from CONFIRMED to ASSIGNED to AT_PICKUP.
- Number of operators who viewed vs. offered on a job.
- Reassignment rate and reasons.

### 4.5 Reliability
- Cancellation rate; by state at cancellation; by party; reasons.
- FAILED rate; reasons.
- On-time pickup and delivery vs. agreed times.
- No-show rate (ASSIGNED but never AT_PICKUP).

### 4.6 Incidents & disputes
- Incident rate per 100 completed jobs; by type; by vehicle class; by value band.
- Share resolved amicably vs. by admin review vs. escalated.
- Time to acknowledge / first action / resolution vs. SLA targets.
- Repeat-offender operators/businesses.
- Any incident involving high declared value — did trust gating work?

### 4.7 Economics
- Commission revenue per completed job; total.
- Variable cost per job (SMS/WhatsApp, maps/geocoding, storage) — instrument
  from the start.
- Contribution per job = commission − variable cost.
- Operator earnings per job / per week / per vehicle class.
- Business logistics cost per job / per delivered tonne-km where computable.
- Commission collection rate (invoiced vs. settled) under the statement model.
- Off-platform diversion signal: repeat business↔operator pairs whose job
  frequency drops after a first on-platform match.

### 4.8 Product & UX
- Drop-off in onboarding (registration → documents submitted → verified →
  first job).
- Steps where operators/businesses call support instead of using the app.
- Feature usage: proof-of-delivery method chosen; evidence uploads;
  chain-of-custody completeness per job.

---

## 5. Instrumentation requirements (feeds functional/NFR)

- Every job carries enough structured data (timestamps per transition, distances,
  weights, prices, actors, outcomes) to compute the metrics above **without
  spreadsheets**.
- An **operational dashboard** for the founder/admin: live job list, funnel,
  incident queue, and the weekly metrics.
- **Event log / analytics export** (CSV or similar) so the founder can analyse
  freely.
- Cost counters for external API calls attributable per job where feasible.
- Privacy: analytics use the minimum personal data necessary; exports are
  access-controlled (see [non-functional-requirements.md](non-functional-requirements.md)).

---

## 6. Pilot governance

- **Weekly review** (founder + admin): metrics, incidents, config changes.
  Config changes (commission rate, thresholds, timeouts, trust criteria) are
  logged with date and rationale so their effect can be read in the data.
- **Decision log** ([decisions.md](decisions.md)) updated with anything the pilot
  resolves or newly raises.
- **Kill / iterate / scale criteria:** define, with the founder, what pilot
  outcomes would justify continuing, changing direction, or expanding. Suggested
  dimensions: contribution per job trending positive, incident rate acceptable,
  operator earnings competitive with informal channels, commission collection
  workable, businesses returning. **OPEN QUESTION — founder to set targets.**

---

## 7. Exit of Phase 0 into pilot

The pilot cannot start until:
- This documentation set is reviewed and approved by the founder.
- The founder specifies: pilot area/zones, working language, commission
  rate + who pays + collection mechanism, trust-level numbers, and the
  escalation contact.
- Legal/insurance items marked **REQUIRES KENYAN PROFESSIONAL VALIDATION** are at
  least triaged with a qualified advisor (what must be settled before onboarding
  real operators and moving real goods).
- Phase 1 builds the MVP per [functional-requirements.md](functional-requirements.md)
  and [non-functional-requirements.md](non-functional-requirements.md).

---

## 8. Status summary

| Item | Category |
|------|----------|
| Pilot is a learning instrument, local, on the founder's network | CONFIRMED DECISION |
| Pilot area = Kitengela, Kajiado County + environs | CONFIRMED (founder, 2026-09-08) |
| UI languages = English & Swahili | CONFIRMED (founder, 2026-09-08 — D-PIL-4) |
| Zone breakdown | DEFERRED — founder to supply; config update, not a blocker (D-PIL-5) |
| Kajiado County Single Business Permit for the Kitengela premises | CONFIRMED required action — see [legal-scope.md](legal-scope.md) §3.1 |
| Duration 8–12 weeks minimum | WORKING ASSUMPTION — founder to confirm |
| Phased onboarding to keep verification tractable | WORKING ASSUMPTION |
| Full metric set in §4 must be instrumented from day one | CONFIRMED DECISION (requirement) |
| Kill / iterate / scale targets | OPEN QUESTION — founder to set |
