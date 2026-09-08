# Phase 0 — Summary Report

**Project:** Fikisha — Local Logistics Marketplace *(brand confirmed 2026-09-08; repo dir `LOGISTIX`)*
**Phase:** 0 — Product Discovery & Definition
**Date:** 2026-09-08
**Prepared by:** Product/Engineering agent
**Status:** COMPLETE — AWAITING FOUNDER REVIEW

> **Addendum 2026-09-08 (same day, several rounds):** the founder confirmed the
> pilot area (**Kitengela, Kajiado County**), **UI languages English & Swahili**,
> the **brand name `Fikisha`** (`Mzigo` rejected), and **all operating-policy
> decisions**: commission, trust bands & levels + Certificate of Good Conduct,
> cancellation, dispute windows, proof of pickup, admin roles, **PWA client**,
> **WhatsApp as an MVP channel**, **operator groups (minimal) in scope**, and a
> **recipient no-account confirmation/incident link in scope**. Three documents
> were added — [brand-name.md](brand-name.md), [legal-scope.md](legal-scope.md),
> [decision-memo-2026-09-08.md](decision-memo-2026-09-08.md) — and
> [decisions.md](decisions.md) (new §1a) plus every domain doc were updated.
> **Still open:** the Kitengela zone list (deferred; config, not a blocker) and
> the pilot kill/iterate/scale targets (deferred to post-launch). Legal items
> still require qualified Kenyan validation — the founder is engaging a lawyer.
> §4, §7 and §8 below reflect the addendum. Phase 0 status is otherwise
> unchanged.

---

## 1. Environment inspection

The working directory `C:\Users\PCMF\PROJECTS\LOGISTIX` was inspected and is
**empty** — not a git repository, no files, no prior work. Host is Windows 11
with Node.js v24 available and no Python. There was nothing to analyse or build
on. Per the Phase 0 operating rule, **no application code, framework, dependency,
migration, source file, deployment configuration, or infrastructure was
created.** The sole output of Phase 0 is the documentation set in
`docs/phase-0/`.

---

## 2. What has been established

A complete product definition for the MVP and the local pilot, in **19 documents**
plus this report (the 16 required deliverables plus `brand-name.md`,
`legal-scope.md`, and `decision-memo-2026-09-08.md`):

| Area | Document | What it fixes |
|------|----------|---------------|
| Vision & problem | `product-vision.md`, `problem-statement.md` | A coordination layer over **non-owned** local transport capacity across **all vehicle classes**, that **digitizes existing practice** (stages/bases/yards, direct contact, negotiation, amicable resolution) rather than replacing it. |
| Users | `users-and-roles.md` | Business, Transport Operator (individual **or** a minimal operator group), Platform Administrator (2 pilot roles), plus a no-account Recipient link. Capabilities and hard boundaries per role. |
| Scope | `mvp-scope.md` | What the MVP includes — incl. PWA client, WhatsApp channel, operator groups, recipient link — and, explicitly, what it excludes and why. |
| Revenue | `business-model.md` | Commission on **COMPLETED** jobs; **operator pays 10%** (KES 40 min, large-job taper, optional intro ramp); weekly M-Pesa statement + eTIMS invoices; platform never holds the fare. |
| Operators | `operator-model.md` | Stage/base/yard as a first-class entity used in matching; configurable vehicle types; zone-based service areas; manual availability; **filtered discovery, no auto-assign**; minimal operator-group model. |
| Job lifecycle | `job-lifecycle.md` | All 14 states from the brief, an **enforced allowed-transition table**, concurrency/atomicity rules, and configurable timeouts (delivery-acceptance 24/48h; post-completion dispute 72h/7d). |
| Pricing | `pricing-and-negotiation.md` | Two-way negotiation, **parallel sealed threads**, **immutable append-only history**, frozen agreed price, **no enforced pricing**, no historical price guidance in MVP. |
| Trust & safety | `trust-and-safety.md` | **VERIFIED vs TRUSTED**; per-domain verification with expiry; L1/L2/L3 trust levels with KES value bands (50k/250k/1M); **high-value gated** at KES 250k by trust + verification + admin review; Certificate of Good Conduct before Elevated; append-only chain of custody. |
| Disputes & liability | `dispute-and-liability.md` | All incident types from the brief; evidence + statements; **amicable-first**, then admin review, then escalation; **platform not automatically liable**; no forced refunds in MVP (records adjustments + adjusts its own commission). |
| Pilot | `pilot-strategy.md` | The pilot as a **learning instrument** in **Kitengela, Kajiado**; a full metric set covering every dimension named in the brief; phased onboarding; weekly governance. |
| Requirements | `functional-requirements.md`, `non-functional-requirements.md` | ~100 numbered FRs with MVP priorities and full traceability to the brief; NFRs treating **security, privacy, authorization, auditability as first-class MUSTs**; client form factor = PWA. |
| Domain | `domain-model.md` | ~33 conceptual entities (incl. `OperatorGroup`, `GroupMembership`, `RecipientAccessLink`), key enumerations, and 12 invariants, organised around the **JOB aggregate**. Not a schema. |
| Roadmap | `future-roadmap.md` | Everything deferred, recorded, and explicitly out of MVP. |
| Decisions | `decisions.md` | Every decision classified CONFIRMED / ASSUMPTION / OPEN / VALIDATION, with owners; §1a lists the 2026-09-08 founder-confirmed set. |
| Brand | `brand-name.md` | Consumer brand `Fikisha` (chosen from a shortlist; `Mzigo` rejected) + the BRS/KIPI/domain steps. |
| Legal | `legal-scope.md` | Kenyan regulatory map, recommended legal posture, required contracts, data-retention schedule, ordered pre-pilot legal checklist, sources. |
| Decision memo | `decision-memo-2026-09-08.md` | The founder memo: brand, Kitengela area, and the operating-policy decisions with their approved values. |

---

## 3. What assumptions have been validated (and by what)

"Validated" here means **grounded in the founder brief and the discovered
operator practice it reports** — not yet validated by pilot data.

| Assumption | Basis |
|-----------|-------|
| Operators work from physical stages/bases/yards and these matter for discovery | Discovered practice reported in the brief; modelled as first-class `OperatingBase` |
| Work is obtained via calls / contacts / WhatsApp, and direct contact continues | Discovered practice; platform augments rather than blocks it |
| Price negotiation is normal and both sides negotiate before committing | Discovered practice; negotiation is a core flow, job confirmed only on mutual agreement |
| Faults are usually resolved amicably | Discovered practice; dispute flow starts with a structured amicable step |
| Supply cold-start is largely solved for a local pilot | Founder has an existing network of riders/drivers |
| One job model must span a motorcycle parcel and a trailer haul | Stated in the brief; reflected in the domain model and vehicle/requirement entities |

**Not yet validated — the pilot exists to measure these:** real local rates,
response times, cancellation rates, incident/dispute rates, operator earnings vs.
informal channels, per-job platform economics, whether disintermediation
threatens the 10% commission, whether the weekly-statement collection model
holds, whether the trust thresholds and value bands are set right, and how
reliably operators can complete custody steps on a PWA on low-end devices.

---

## 4. What remains uncertain

### 4.1 Needs a founder decision (see `decisions.md` §3)

**CONFIRMED by the founder on 2026-09-08 (recorded in `decisions.md` §1a as
D-BRAND-1, D-PIL-3…5, D-BIZ-4…7, D-TRU-5…7, D-DIS-3, D-JOB-5, D-CUS-2, D-ADM-1;
propagated to the domain docs):**
- **Brand name:** `Fikisha`.
- **Pilot area:** Kitengela, Kajiado County + environs.
- **UI languages:** English & Swahili (Swahili prominent on operator screens).
- **Commission:** operator pays; **10%** headline; KES 40 minimum; taper 10/5/3%
  (or flat 10% capped KES 5,000); optional 0→5→10% intro ramp; weekly statement
  via merchant M-Pesa paybill + eTIMS invoices; platform never holds the fare.
- **Trust:** value bands 50k / 250k / 1M; high-value admin review at KES 250k;
  L2 = 8 jobs / 14 days / 4.2★; L3 = 30 jobs / 60 days / 4.5★ / 3 clean Elevated
  jobs; DCI Certificate of Good Conduct mandatory before Elevated; heavy-vehicle
  operators must show NTSA operator licence + speed limiter + telematics +
  inspection + insurance.
- **Cancellation:** reputation-only; "3 in 30 days" → admin flag; courtesy fee
  built but default-off.
- **Dispute windows:** acceptance 24h (Std/Elevated) / 48h (High+); post-completion
  72h all bands, 7 days for High+ and latent-risk cargo.
- **Proof of pickup:** mandatory pickup-side OTP; operator-attested photo fallback
  Standard band only; no fallback at Elevated+.
- **Admin roles:** 2 for the pilot (Platform Admin + Operations Officer); 4-role
  split defined in config for later; every admin action (incl. founder's) logged;
  admin MFA.
- **Client:** responsive **Progressive Web App** (D-CLIENT-1) — no native builds
  for MVP.
- **Notifications:** in-app + **SMS + WhatsApp** (D-NOTIF-1); OTP stays
  SMS-primary; WhatsApp failure falls back to SMS.
- **Operator groups:** **in scope, minimal** (D-OPR-GRP-1) — group + membership +
  group-owned vehicles; per-driver + per-vehicle verification; a group job names
  a specific driver + vehicle; value-band gating uses the assigned driver's
  trust; statement to the group. No payroll/scheduling/transfers.
- **Recipient link:** **in scope** (D-RCP-1) — no account; a scoped, time-limited
  per-job link to view the delivery, confirm receipt, and raise an incident.

**Still open:**
- **Brand registration:** name is `Fikisha` (D-BRAND-1); remaining work is BRS
  name reservation + KIPI trade-mark filing + domains/handles + a Kajiado
  informal-use check. Not a Phase 1 blocker.
- **Zone breakdown** to seed `PlatformConfig.zones` — founder will supply later;
  DEFERRED, handled as a config/data update (D-PIL-5).
- **Pilot kill / iterate / scale criteria** — deferred by the founder to
  post-launch. The pilot still instruments the full metric set.

### 4.2 Needs Kenyan professional validation
Now expanded in full in **[legal-scope.md](legal-scope.md)** (regulatory map,
recommended posture, required contracts, retention schedule, ordered checklist).
Not assumed settled — highlights:
- **Platform characterisation** — recommended posture is *neutral intermediary /
  digital marketplace* (not a carrier, not holding goods or the fare); needs a
  written advocate's opinion.
- **NTSA Transport Network Company licence** — the 2022 TNC Regulations are
  passenger-focused; applicability to a **goods** platform is unsettled, and a
  High Court ruling of ~2 Sept 2026 struck down parts of those regulations
  (commission cap; open-ended trip-data retention) and suspended the declaration
  for 12 months pending fresh rule-making. Formal NTSA query needed.
- **NTSA commercial-service-vehicle operator** obligations (speed limiter,
  telematics, inspection, insurance, annual operator licence, 24-hr fatal-accident
  reporting) sit on heavy-vehicle operators; the platform must verify them.
- **Data protection** — ODPC registration (controller + processor), a DPIA, a
  DPO/contact, a retention schedule, a breach-response plan, and DPAs with every
  processor are **pre-pilot actions**; cross-border transfers (SMS/maps/hosting
  and the **WhatsApp/Meta US transfer**) must be lawful; the **no-account
  recipient link** processes a non-user's data and needs its own basis + notice.
- **Tax** — corporate income tax; VAT (KES 5M threshold; commission likely
  VATable); **eTIMS e-invoicing is mandatory** and KRA validates returns against
  it from Jan 2026; withholding tax on some payees. (SEP tax is a non-resident
  tax — not applicable to a Kenyan-incorporated entity.)
- **Payments** — collecting only the platform's own commission via a merchant
  paybill is designed to stay outside **CBK PSP licensing**; holding/escrowing
  the fare would trigger it. Needs confirmation.
- **Consumer Protection Act 2012** — fair-trading duties; some liability
  exclusions/limitations are void — the enforceable Terms-of-Service wording
  needs validation.
- **Worker classification** — operators are independent contractors; a
  "dependent contractor" / platform-worker Bill is under debate (not yet law) —
  keep the model resilient and monitor. **Operator groups** add a group↔driver
  relationship that is the group's affair, not the platform's — the Operator
  Agreement needs a Group Agreement schedule.
- **Company + county** — incorporate a Kenyan private limited company (BRS,
  beneficial ownership, company KRA PIN) and obtain the **Kajiado County Single
  Business Permit** for the Kitengela premises.
- **Insurance** — verify operator statutory cover; require goods-in-transit /
  carrier's-liability cover for higher value bands; the platform carries its own
  CGL + professional indemnity; **no platform-branded "cover" unless underwritten
  by a licensed insurer**.
- **Contract set** — Terms of Service, Operator Agreement, Privacy Notice, DPAs,
  Acceptable Use / Prohibited Goods, Dispute & Liability policy, Recipient terms
  — all drafted by a qualified Kenyan advocate.
- **Prohibited/dangerous goods** — excluded from the pilot; ToS prohibits.

---

## 5. Important risks

| # | Risk | Impact | Mitigation / owner |
|---|------|--------|--------------------|
| R1 | **Legal/regulatory exposure** (licensing, liability, data protection, tax) is unquantified | Could block the pilot or create liability | Triage all `legal-scope.md` §9 items with qualified Kenyan advisors **before** onboarding real operators / moving real goods; **lawyer engagement in progress** |
| R2 | **Commission collection depends on operator compliance** — MVP holds no funds, so the 10% is billed by weekly statement | Revenue leakage; unit economics unclear | Trusted pilot network; keep commission low; design the ledger so prepaid credits or point-of-completion M-Pesa collection can be added in Phase 1; **measure invoiced-vs-settled in the pilot** |
| R3 | **Disintermediation** — parties can (by design) go off-platform to avoid commission | Erodes the only revenue stream | Keep on-platform value high (custody, dispute protection, reputation, easy re-booking); 10% is deliberately low; **measure repeat-pair behaviour in the pilot** |
| R4 | **WhatsApp BSP dependency** — onboarding lead time, per-message cost, template approval, and the Meta cross-border transfer | Delivery/adoption + compliance | Start BSP onboarding early in Phase 1; SMS fallback on every WhatsApp send; document the transfer in the DPA/Privacy Notice/recipient terms |
| R5 | **Verification throughput** — manual verification is a bottleneck at onboarding, worsened by per-driver checks for operator groups | Slow pilot ramp | Phased onboarding cohorts; onboard groups driver-by-driver; simple base verification via founder local knowledge; automated assist later |
| R6 | **Trust model gamed on thin early data** — few jobs make ratings/criteria easy to manipulate | Under-verified operators reach high-value jobs | Admin-confirmed progression in MVP; admin review + trust gate on every high-value (KES 250k+) job; watch collusive rating and repeat-pair patterns |
| R7 | **Safety incidents** (theft, accident, wrong recipient) during a pilot moving real goods | Harm, loss, reputational damage, possible liability | Chain of custody + mandatory pickup-side OTP + recipient verification + high-value gating + a named founder escalation point + validated ToS boundaries; exclude hazardous goods |
| R8 | **Scope creep** into payments, tracking, matching automation, extra revenue models, or a heavier operator-group build | Delays the pilot; dilutes the learning goal | `mvp-scope.md` exclusions + `future-roadmap.md`; group model kept minimal (no payroll/scheduling/transfers); founder rule that no extra revenue model ships without approval |
| R9 | **Location & recipient-data privacy** captured during custody / via the no-account link without a validated legal basis | Compliance breach | NFR-PRIV-3/4; DPIA before pilot; capture minimally, with permission; short recipient notice; link expiry; validate under DPA 2019 |
| R10 | **PWA limitations** on low-end devices / poor connectivity (camera, offline, push — esp. iOS push) | Operators/recipients can't complete custody or confirmation steps reliably | Test on representative devices in the pilot area during Phase 1; SMS carries the critical OTP/link steps; native app remains the future fallback (D-CLIENT-1) |
| R11 | **Kitengela zones not yet defined** | Discovery/matching runs coarse until supplied | Pilot runs with the area as one zone; adding zones is a `PlatformConfig` update, no rebuild |

---

## 6. Important product decisions (the ones that shape everything downstream)

1. **Non-owned marketplace over discovered practice.** Stages/bases/yards,
   direct contact, and negotiation are designed *in*.
2. **One JOB model for all vehicle classes**, with an **enforced state machine**
   and an **append-only chain of custody**.
3. **Negotiation is core and unconstrained** in MVP; history is immutable; the
   agreed price is frozen; no platform price-fixing and no historical price
   guidance yet.
4. **VERIFIED ≠ TRUSTED.** Progressive trust levels with job-value ceilings;
   high-value jobs are gated by trust + verification + admin review.
5. **Platform is a facilitator, not a guarantor.** It records and helps resolve
   incidents; it makes no unvalidated legal/insurance claims; it holds no funds
   in MVP.
6. **Commission on completed jobs is the only revenue stream** for MVP —
   **operator pays 10%** (KES 40 minimum, large-job taper, optional intro ramp),
   billed by weekly M-Pesa statement with eTIMS invoices; the platform never
   holds the transport fare (keeping it outside CBK payment-service licensing).
7. **The MVP is a pilot instrument.** Every job must emit the structured data
   needed to compute the full pilot metric set with no spreadsheets.
8. **Security, privacy, authorization, auditability are MUSTs**, not later
   additions.

---

## 7. Recommended next phase

**Phase 1 — MVP build for the local pilot**, starting only after founder review
of this set, and gated on two parallel workstreams:

1. **Founder decisions** — mostly done (§8.A). Remaining: the Kitengela zone list
   (deferred; config, not a blocker) and the pilot kill/iterate/scale targets
   (deferred to post-launch).
2. **Legal/insurance triage** — incorporate the Kenyan company; engage a
   qualified advocate + tax advisor + insurance broker; work the ordered
   pre-pilot checklist in [legal-scope.md](legal-scope.md) §9 (ODPC registration
   + DPIA, NTSA query, Kajiado County permit, contract set, eTIMS, insurance).
   This runs parallel to the build and **gates pilot go-live**.

**Phase 1 build sequence (suggested):**
1. Foundations: **PWA shell** (installable, offline-tolerant, camera) with
   **English/Swahili** i18n; accounts + phone/OTP auth + admin MFA;
   role→permission map in `PlatformConfig` (2 pilot roles); audit-log spine;
   `PlatformConfig` with versioning.
2. Operator onboarding + per-domain verification queue (identity, licence,
   Certificate of Good Conduct, vehicle docs, heavy-class NTSA items); vehicles;
   bases; service areas. **Operator groups**: group profile + `GroupMembership` +
   group-owned vehicles + per-driver verification.
3. Business onboarding + locations.
4. Job creation + the **state machine** (allowed transitions, concurrency,
   status events) as a single authoritative module with tests.
5. Negotiation (parallel sealed threads, append-only entries, agreement freeze).
6. Assignment (solo **and group — names a specific driver + vehicle**) + chain of
   custody + proof of pickup (mandatory pickup-side OTP) / delivery + evidence
   storage (encrypted, hashed, signed URLs).
7. Trust levels + value-band gating (driver-level for groups) + high-value admin
   review at KES 250k.
8. **Recipient no-account link**: view status, confirm receipt, raise incident;
   expiry after the post-completion dispute window.
9. Incidents + disputes (amicable-first → admin review → resolution → escalation),
   including recipient-initiated.
10. Ratings/reputation feeding trust (driver + group).
11. Commission records + **weekly per-operator/-group statements**, eTIMS-compliant.
12. Notifications: in-app + SMS + **WhatsApp** (BSP, templates, SMS fallback);
    OTP SMS-primary.
13. Admin console + operational dashboard + data export.
14. Staging environment + pilot dry-run + security review before go-live.

Then **Phase 2 — run the local pilot** per `pilot-strategy.md`: phased
onboarding, weekly metric reviews, config tuning, decision-log updates, and a
go/no-go against kill/iterate/scale criteria set after launch.

---

## 8. Questions requiring founder approval

**A. APPROVED by the founder on 2026-09-08** — brand name (`Fikisha`), pilot area
(Kitengela), UI languages (English & Swahili), commission, trust bands, trust
levels + Good-Conduct requirement, cancellation policy, dispute windows, proof of
pickup, admin role structure, **PWA client**, **WhatsApp as an MVP channel**,
**operator groups (minimal) in scope**, **recipient no-account link in scope**.
All recorded in `decisions.md` §1a and propagated to the domain docs. No further
action needed unless the founder revises a value later. Follow-up (not blocking
Phase 1): BRS name reservation + KIPI trade-mark filing + domains/handles for
`Fikisha`.

**B. Still open — founder input needed:**

1. **Zone breakdown** for Kitengela + environs — founder to supply when ready;
   deferred, handled as configuration (D-PIL-5). Not a Phase 1 blocker.
2. **Pilot kill / iterate / scale criteria and targets** — the founder deferred
   these to post-launch; the pilot still instruments the full metric set.

**C. Legal / commercial:**

3. **In progress** — the founder is engaging a lawyer. Also engage a tax advisor
   and a licensed insurance broker to work through
   [legal-scope.md](legal-scope.md) §9 (incorporate the Kenyan private limited
   company; ODPC registration + DPIA; NTSA query; Kajiado County permit; contract
   set; eTIMS; insurance). Runs parallel to Phase 1; **gates pilot go-live**.
   *Additions from this round:* the DPA/Privacy Notice must cover the
   **WhatsApp/Meta cross-border transfer**; the Operator Agreement must cover the
   **operator-group** relationship (group vs. member-driver responsibilities);
   the **recipient short terms** on the link are contract-set item 7.
4. Confirmation that **no revenue model beyond commission** is in scope for the
   MVP.
5. Acknowledgement of the **recommended legal posture** — neutral intermediary /
   digital marketplace: the platform never sets prices, holds goods, holds the
   fare, or offers insurance — so Phase 1 builds consistently with it.

---

## 9. Completion checklist (from the brief)

| Criterion | Where |
|-----------|-------|
| Product scope documented | `mvp-scope.md`, `product-vision.md` |
| User roles documented | `users-and-roles.md` |
| Job lifecycle documented | `job-lifecycle.md` |
| Price negotiation documented | `pricing-and-negotiation.md` |
| Operator verification model documented | `trust-and-safety.md`, `operator-model.md` |
| Trust model documented | `trust-and-safety.md` |
| Chain of custody documented | `trust-and-safety.md` §4, `job-lifecycle.md`, `domain-model.md` |
| Incident/dispute model documented | `dispute-and-liability.md` |
| Revenue model documented | `business-model.md` |
| Pilot model documented | `pilot-strategy.md` |
| Domain concepts documented | `domain-model.md` |
| MVP exclusions documented | `mvp-scope.md` §2, `future-roadmap.md` |
| Open decisions clearly identified | `decisions.md` §3–§4, this report §4 and §8 |
| No implementation begun | Confirmed — only `docs/phase-0/*.md` exist; no code, framework, dependencies, migrations, deployment config, or infrastructure |

---

# PHASE 0 — COMPLETE — AWAITING FOUNDER REVIEW

No approval is claimed on the founder's behalf. Implementation does not begin
until this set is reviewed and the §8 questions are answered.
