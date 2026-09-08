# Future Roadmap

Everything here is **FUTURE CONSIDERATION** — recorded so it is not lost, and
explicitly **not** part of the MVP. Nothing in this document is to be built
during MVP without explicit founder approval. Order and grouping are indicative,
not a commitment.

---

## 1. Immediately after a successful pilot (Phase 2 candidates)

| Item | Notes / dependency |
|------|--------------------|
| **In-app / mobile-money commission collection** | Collect commission at point of completion instead of periodic statements. **REQUIRES KENYAN PROFESSIONAL VALIDATION** (payment-service, tax). Depends on pilot showing statement collection is a friction point. |
| **Recommended price ranges** | Non-binding "similar recent jobs: KES X–Y" from pilot data. Only meaningful once enough completed jobs exist. Must not replace negotiation. |
| **WhatsApp for job *actions*** | *Notifications + recipient link via WhatsApp are in the MVP (D-NOTIF-1).* This item is the further step of accepting/countering/confirming **from within WhatsApp**. |
| **Automated / assisted matching** | Suggest best-fit operators, notify likely acceptors first, still human-confirmed. Learn from pilot matching data. |
| **Operator groups — deeper fleet tooling** | *The group entity, membership, group-owned vehicles and driver-named assignment are in the MVP (D-OPR-GRP-1).* This item is the extras held back: internal payroll/settlement, shift scheduling, inter-group transfers, group sub-dashboards. |
| **Richer service-area geometry** | Map-drawn polygons and corridors instead of named zones. |
| **Native mobile apps** | The MVP client is a PWA (D-CLIENT-1). Native builds only if the pilot shows PWA limitations (offline, push, camera reliability on low-end devices). |
| **Recipient tracking portal** | *The MVP has a recipient confirmation/incident link (D-RCP-1).* This is a fuller consignee experience: live tracking link, delivery-window notifications, reschedule requests. |
| **Two-way in-app messaging** | Only if the pilot shows phone/WhatsApp is insufficient for coordination and dispute clarity. |

## 2. Trust, safety, and operations

| Item | Notes |
|------|-------|
| Automated verification assists | OCR/format checks on IDs and licences; liveness/selfie match; document-expiry pre-checks. |
| Risk scoring | Data-driven operator/business/job risk signals to prioritise review and gate high-value work; only after enough data. |
| In-transit check-ins / lightweight location updates | Beyond checkpoint custody, for high-value or long-haul jobs. Privacy-bounded. |
| Live tracking / telematics integration | GPS or device tracking during transit; route/ETA. Significant privacy and cost implications. |
| Resolution fund / facilitated compensation | Platform-mediated compensation for verified loss/damage. **REQUIRES KENYAN PROFESSIONAL VALIDATION** and a funding model. |
| Insurance partnerships | Optional cargo-in-transit cover offered through a licensed partner. **REQUIRES KENYAN PROFESSIONAL VALIDATION.** |
| Background checks | Deeper operator vetting via authorised providers, subject to legal basis. |

## 3. Business / shipper features

| Item | Notes |
|------|-------|
| Recurring lanes / scheduled jobs | Repeat the same route on a schedule; standing operator preferences. |
| Bulk job creation / import | For businesses with many daily deliveries. |
| Business team roles & approvals | Spend limits, job approval workflow, cost centres. |
| Logistics cost analytics | Spend per lane, per period, per vehicle class; delivered-tonne-km costs. |
| Address book / saved recipients | Faster job creation. |
| Consignee experience | Recipient tracking link, delivery window notifications, reschedule request. |

## 4. Operator features

| Item | Notes |
|------|-------|
| Earnings analytics & payout history | Trends by vehicle class, area, time; export. |
| Return-trip / backhaul matching | Fill empty return legs — high utilization value, needs matching maturity. |
| Availability scheduling | Recurring working hours, planned unavailability. |
| Maintenance / document reminders | Proactive nudges before licence/insurance/inspection expiry. |
| Operator onboarding self-service with staged auto-checks | Reduce manual verification load as volume grows. |

## 5. Marketplace / revenue (NONE without explicit approval)

| Item | Notes |
|------|-------|
| Business subscriptions | Priority matching, higher limits, analytics access. |
| Enterprise / contract logistics | Negotiated rates, dedicated capacity, SLAs. |
| Fleet-management tooling | For larger operators: vehicles, drivers, assignments, compliance. |
| Premium services | Dedicated support, insured lanes, guaranteed response (each needs legal validation). |
| Market-rate data / analytics products | Aggregated, anonymised pricing and demand insights. |
| API / integrations | Let business systems (ERP, e-commerce, POS) create and track jobs. |
| Value-added services | Warehousing referrals, packaging, loading crews, fuel/airtime partnerships. |

## 6. Platform / technical evolution

| Item | Notes |
|------|-------|
| Multi-area / multi-city | One validated area at a time; zone/config model already anticipates this. |
| Localization | Additional local languages; number/date/format handling. |
| Scale architecture | Only when pilot-scale assumptions (NFR-PERF-1) are exceeded. |
| Advanced observability & analytics warehouse | Dedicated analytics store as data volume grows. |
| Offline-first client | Fuller offline job execution for very poor connectivity areas. |
| Third-party penetration testing & formal security program | Before meaningful scale. |
| Formal data-protection program | DPO/registration, DSAR tooling, processor audits — scope set by validated legal advice. |

## 7. Explicitly parked questions (revisit with data)

- Does disintermediation materially threaten the commission model, and do we
  need loyalty/volume incentives?
- Should commission differ by vehicle class or value band?
- Should the platform ever hold funds / offer escrow?
- Are recipient **accounts** worthwhile? (The MVP already gives recipients a
  no-account link for confirmation + incidents — D-RCP-1.)
- Do businesses want structured price line items?
- Is a broker/dispatcher role (a person coordinating for a stage/yard) worth
  modelling as a first-class role? (Partly addressed by the MVP operator-group
  `MANAGER` role — D-OPR-GRP-1.)
- Does the operator-group model need internal settlement / scheduling during the
  pilot, or does off-platform settlement hold?

---

## Status summary

| Item | Category |
|------|----------|
| Everything in this document | FUTURE CONSIDERATION — not in MVP |
| Any revenue stream beyond commission | Requires explicit founder approval |
| Payments, insurance, resolution fund, tracking-heavy features | Also REQUIRES KENYAN PROFESSIONAL VALIDATION |
