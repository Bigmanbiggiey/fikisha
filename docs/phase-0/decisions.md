# Decision Log

Single source of truth for the state of every product/technical decision in
Phase 0. Four categories, never blended:

- **CONFIRMED** — from the founder brief or an unavoidable consequence of it.
- **ASSUMPTION** — a working default chosen to make progress; reversible; should
  be confirmed.
- **OPEN** — undecided; needs a founder answer and/or external validation before
  implementation depends on it.
- **VALIDATION** — legal/tax/insurance/licensing/regulatory; **REQUIRES KENYAN
  PROFESSIONAL VALIDATION**; not treated as settled.

`ID` format: `D-<area>-<n>`. "Owner" = who must decide/act.

---

## 1. CONFIRMED decisions

| ID | Decision | Source |
|----|----------|--------|
| D-VIS-1 | The product is a marketplace coordinating **non-owned** local transport capacity. | Brief |
| D-VIS-2 | Transport spans **all vehicle classes** from motorcycle to trailer. | Brief |
| D-VIS-3 | The platform **digitizes and improves existing practice** (stages/bases/yards, direct contact, negotiation, amicable resolution) rather than eliminating it. | Brief / core principle |
| D-VIS-4 | Direct off-platform contact between matched parties is **expected and permitted**. | Consequence of D-VIS-3 |
| D-USR-1 | Three account roles: **Business, Transport Operator, Platform Administrator**. | Brief |
| D-USR-2 | Administrator actions are **role-based and fully audit-logged**. | Brief / security rule |
| D-JOB-1 | The **JOB** is the fundamental transaction, spanning small parcels to large commercial hauls, with the field set listed in the brief. | Brief |
| D-JOB-2 | Job status is a **finite state machine**; only explicitly allowed transitions are permitted; arbitrary status changes are rejected. | Brief |
| D-JOB-3 | Lifecycle states: DRAFT, REQUESTED, NEGOTIATING, CONFIRMED, ASSIGNED, AT_PICKUP, PICKED_UP, IN_TRANSIT, AT_DESTINATION, DELIVERED, COMPLETED + CANCELLED, FAILED, DISPUTED. | Brief |
| D-JOB-4 | Every transition is **audit-logged**; custody-relevant transitions also write a **chain-of-custody** entry. | Brief / security rule |
| D-NEG-1 | **No enforced/fixed price** in MVP. Both parties negotiate (propose / counter / accept / reject). | Brief |
| D-NEG-2 | A job is **CONFIRMED only on mutual agreement**. | Brief |
| D-NEG-3 | **Full negotiation history is preserved, immutable and append-only**; the final agreed price is recorded and frozen. | Brief |
| D-NEG-4 | Historical "recommended price ranges" are **out of MVP** (future only). | Brief |
| D-TRU-1 | The platform distinguishes **VERIFIED** (identity/eligibility/documents) from **TRUSTED** (earned through successful activity). | Brief |
| D-TRU-2 | **Progressive operator trust levels**; new operators do **not** get automatic unrestricted access to high-value jobs. | Brief |
| D-TRU-3 | **High-value jobs** require a higher trust level, current/enhanced verification, and administrator review before assignment. | Brief |
| D-TRU-4 | Verification is per-domain (identity, licence, vehicle, association, base, documents, history) with expiry. | Brief |
| D-CUS-1 | The platform provides an **auditable chain of custody** from assignment to completion, retaining timestamps, actors, locations, confirmations, and evidence, subject to privacy/retention rules. | Brief |
| D-DIS-1 | The platform supports the incident types listed in the brief; it **records evidence and facilitates resolution**, starting with structured amicable resolution, then admin review, then escalation. | Brief |
| D-DIS-2 | The platform is **not automatically liable** for every incident; it does **not** invent legal/insurance guarantees. | Brief |
| D-BIZ-1 | Revenue = **transaction fee / commission on successfully facilitated (COMPLETED) jobs**. | Brief |
| D-BIZ-2 | The commission fee is **configurable** and validated through the pilot. | Brief |
| D-BIZ-3 | **No other revenue model** is implemented during MVP without explicit founder approval. | Brief |
| D-PIL-1 | Initial deployment is a **local pilot** on the founder's existing operator network, in a limited area. | Brief |
| D-PIL-3 | **Pilot area = Kitengela, Kajiado County**, serving Kitengela town and its environs (Namanga-road corridor, Athi River / Mavoko boundary, Isinya, Kisaju, Kaputiei, links to Nairobi Industrial Area / CBD). Zone breakdown + UI language still to be provided by founder. | Founder, 2026-09-08 |
| D-PIL-2 | The pilot's purpose is to **generate operational knowledge** (demand, supply, utilization, pricing, negotiation, matching, response times, cancellations, incidents, disputes, earnings, costs, platform economics), and product decisions are refined from that evidence. | Brief |
| D-SEC-1 | Security, privacy, authorization, auditability, trust, operational safety are **first-class MVP requirements**, not post-MVP additions, wherever they touch the job lifecycle or user model. | Brief / security rule |
| D-SEC-2 | Sensitive PII/documents are **encrypted at rest** with access-controlled, audit-logged retrieval. | Security rule + NFR |
| D-SEC-3 | Authorization is enforced **server-side on every state-changing action**. | Security rule + NFR |
| D-DOC-1 | Documentation always separates CONFIRMED / ASSUMPTION / OPEN / VALIDATION and never silently invents product decisions. | Brief / documentation rules |
| D-PH0-1 | Phase 0 produces **no application code, framework, dependency, migration, source file, deployment config, or infrastructure**. | Brief / operating rule |

### 1a. CONFIRMED by founder on 2026-09-08 (see [decision-memo-2026-09-08.md](decision-memo-2026-09-08.md))

| ID | Decision | Source |
|----|----------|--------|
| D-BRAND-1 | **Consumer brand name = `Fikisha`** (Swahili "deliver / get it there"). "Logistix" may remain a legal-entity/holding name. Next: confirm exact spelling, run **BRS name reservation** + **KIPI trade-mark** search/application (Nice classes 39, 42, 35), secure `.co.ke`/`.com` + handles, informal-use check in Kajiado. Not a Phase 1 blocker. | Founder, 2026-09-08 |
| D-PIL-4 | **UI languages = English & Swahili** (both supported; Swahili prominent on operator-facing screens). | Founder, 2026-09-08 |
| D-PIL-5 | The **Kitengela zone breakdown is deferred** — the founder will supply it later. It is a **configuration/data update** to `PlatformConfig.zones`, **not a blocker** for Phase 1. Until supplied, the pilot area is treated as a single zone. | Founder, 2026-09-08 |
| D-BIZ-4 | **Commission: the operator pays**, shown transparently as a line item in the earnings breakdown (`agreed price − commission = payout`). | Founder-approved, 2026-09-08 |
| D-BIZ-5 | **Commission rate (pilot default, configurable):** 10% headline; **KES 40 minimum** per completed job; large-job taper 10% ≤50k / 5% on 50k–150k / 3% >150k (equivalently: flat 10% capped at KES 5,000); optional **introductory ramp 0% weeks 1–4, 5% weeks 5–8, 10% thereafter**. | Founder-approved, 2026-09-08 |
| D-BIZ-6 | **Commission collection (pilot):** weekly per-operator statement, settled by M-Pesa to a **merchant paybill**; **eTIMS-compliant** invoices; platform **never holds the transport fare**. Ledger designed so point-of-completion collection can be added later. | Founder-approved, 2026-09-08 |
| D-BIZ-7 | **Disputed jobs:** commission held until resolution decides apply/reduce/waive. **Cancelled/failed jobs:** no commission. | Founder-approved, 2026-09-08 |
| D-TRU-5 | **Declared-cargo-value bands & gating:** Standard ≤ KES 50,000 → min trust L1; Elevated 50,001–250,000 → L2 (+ mandatory recipient OTP & photo POD & pickup-side OTP); High 250,001–1,000,000 → L3 (+ admin pre-assignment review, current goods-in-transit/carrier's cover, two contacts); Very high > 1,000,000 → L3 + per-job founder/admin approval. **`high_value_threshold` = KES 250,000.** All configurable. | Founder-approved, 2026-09-08 |
| D-TRU-6 | **Operator trust levels (pilot starting values, configurable, auto-proposed + admin-confirmed):** L0 Pending (can't accept). L1 Verified = identity + correct-class licence + ≥1 verified vehicle + verified base (0 jobs OK) → Standard ceiling. L2 Established = ≥ 8 completed jobs + ≥ 14 days active + avg rating ≥ 4.2/5 + no unresolved incident + ≤ 1 at-fault incident in last 20 → Elevated ceiling. L3 Trusted = ≥ 30 completed jobs + ≥ 60 days active + avg rating ≥ 4.5/5 + 0 unresolved/unremediated at-fault serious incidents + ≥ 3 clean Elevated-band jobs → High ceiling. Restricted = admin-imposed after at-fault serious incident or avg rating < 3.5 over last 10 → Standard or zero, remediation plan to exit. | Founder-approved, 2026-09-08 |
| D-TRU-7 | **DCI Certificate of Good Conduct** required for all operators; **mandatory before L2 / Elevated eligibility**. For canter/lorry/tipper/semi-truck/trailer operators, proof of **NTSA commercial service vehicle operator licence + speed limiter + telematics + inspection + insurance** is part of vehicle verification (see [legal-scope.md](legal-scope.md) §3.3). | Founder-approved, 2026-09-08 |
| D-DIS-3 | **Cancellation policy (pilot): reputation-only, no fees.** Structured reason capture. Before ASSIGNED = no consequence; after ASSIGNED before AT_PICKUP = "late cancellation"; after AT_PICKUP before custody = "wasted-trip". **3 late cancellations/wasted-trips in a rolling 30 days (or last 20 jobs) → automatic admin-review flag** (operator: blocks L2, repeat → Restricted; business: repeat → standing GOOD → RESTRICTED). A configurable wasted-trip courtesy fee (KES 100–300, payable by the canceller) is **built but default-OFF**. | Founder-approved, 2026-09-08 |
| D-JOB-5 | **Dispute/acceptance windows (configurable):** delivery-acceptance auto-complete = **24h** (Standard/Elevated) / **48h** (High/Very-high). Post-completion dispute (COMPLETED → DISPUTED) = **72h** all bands / **7 days** for High+ and latent-risk cargo categories (electronics, packaged goods, perishables). After the window an incident may still be recorded for reputation/audit but does not reopen job state or commission. | Founder-approved, 2026-09-08 |
| D-CUS-2 | **Proof of pickup: pickup-side confirmation is mandatory; operator self-declaration alone is not sufficient.** Primary method = OTP to the person releasing the goods. **Standard band only** fallback: operator captures goods photo + pickup contact name → custody entry marked "operator-attested, unverified" and that job is capped at Standard band unless the business later confirms in-app. **Elevated band and above: pickup-side OTP (or in-app business confirmation) required, no fallback.** Every pickup event records server timestamp, actor, geolocation where available, method, condition note/photos. | Founder-approved, 2026-09-08 |
| D-ADM-1 | **Admin role structure: 2 roles for the pilot** — Platform Admin (founder; all powers) and Operations Officer (verification queue, job monitoring/intervention, incident intake, facilitates amicable resolution, proposes trust changes; **cannot** change platform config, suspend/offboard accounts, or issue binding dispute resolutions above Standard band). The **4-role split** (Verifier / Operations / Dispute Officer / Platform Admin) is defined in `PlatformConfig` as a role→permission map, enabled later by configuration. **Every admin action — including the founder's — is audit-logged** (actor + reason + before/after); raw PII/document access is limited to the verification permission and is itself logged; **MFA mandatory** on all admin accounts. | Founder-approved, 2026-09-08 |
| D-CLIENT-1 | **MVP client = a responsive Progressive Web App (PWA)** — installable, offline-tolerant for custody steps, camera access for photos / proof of delivery. **No app-store native builds for MVP.** Native apps are a FUTURE CONSIDERATION. | Founder, 2026-09-08 |
| D-NOTIF-1 | **WhatsApp is an MVP notification channel** (via the WhatsApp Business Platform through an authorised BSP), alongside in-app and SMS. Used for job-event notifications and the recipient link; **OTP stays on SMS as primary** with WhatsApp as an additional option. WhatsApp delivery failure falls back to SMS. Data sent to WhatsApp/Meta is a **cross-border transfer** and must be covered in the DPA + Privacy Notice ([legal-scope.md](legal-scope.md) §3.4, §3.9). Per-message cost is tracked in pilot economics. | Founder, 2026-09-08 |
| D-OPR-GRP-1 | **Operator groups are IN scope for the MVP** (minimal but real). A **group** (yard/base owner, small fleet, SACCO, partnership) has a primary-contact user, one or more operating bases, group-owned vehicles, and members via `GroupMembership(role: OWNER / MANAGER / DRIVER)`. **Each member driver and each group vehicle is still individually verified** — the group does not shortcut per-person identity/licence or per-vehicle verification. A job assigned to a group **must name a specific driver + specific vehicle** at ASSIGNED. **Value-band gating uses the assigned driver's trust level**; the group also has an aggregate standing used as a monitoring/suspension lever. The **commission statement goes to the group** (group payout details); internal driver settlement is off-platform for MVP. Out of MVP scope: internal payroll, shift scheduling, inter-group transfers. | Founder, 2026-09-08 |
| D-RCP-1 | **Recipient (consignee) confirmation and incident reporting via a per-job link, no account required** — IN scope for the MVP. At dispatch/arrival the recipient receives a **scoped, time-limited, single-job link** (SMS/WhatsApp). Through it the recipient can: view **their** delivery's status only; **confirm receipt** (name + OTP to their phone / signature / photo); **raise an incident** (wrong recipient, damage, missing/short, wrong goods) with photos + a short statement, entering the standard incident workflow. The link expires after the post-completion dispute window. Recipient short terms are shown on the link. | Founder, 2026-09-08 |

---

## 2. ASSUMPTIONS (working defaults — please confirm)

| ID | Assumption | Reversible? | Owner |
|----|-----------|-------------|-------|
| D-A-CLIENT-1 | ~~MVP client is a responsive web app / PWA~~ → **CONFIRMED, see D-CLIENT-1.** | — | — |
| D-A-AUTH-1 | Users authenticate with **phone number + OTP**; password/PIN optional. Admins use MFA. | Yes | Founder |
| D-A-CURR-1 | Single currency **KES**; money stored as integer minor units. | Yes | Founder |
| D-A-MONEY-1 | MVP holds **no funds**: transport fee paid **directly** between parties; platform **records** payment reports. | Yes | Founder |
| D-A-COMM-1 | ~~Commission paid by the operator~~ → **CONFIRMED, see D-BIZ-4.** | — | — |
| D-A-COMM-2 | ~~Periodic per-operator statements~~ → **CONFIRMED, see D-BIZ-6.** | — | — |
| D-A-COMM-3 | ~~Cancellation reputation-only~~ → **CONFIRMED, see D-DIS-3.** | — | — |
| D-A-TRUST-1 | Trust progression is **auto-proposed but admin-confirmed** during MVP. (Now part of CONFIRMED D-TRU-6.) | — | — |
| D-A-TRUST-2 | ~~Four trust levels + Restricted; thresholds in config~~ → **CONFIRMED with values, see D-TRU-6.** | — | — |
| D-A-NEG-1 | Multiple operators negotiate a job in **parallel sealed threads**; the first to reach mutual acceptance wins; others auto-close. | Yes | Founder |
| D-A-NEG-2 | Price is a **single all-in KES amount + free-text note**; no structured line items in MVP. | Yes | Founder |
| D-A-NEG-3 | **No in-flight re-negotiation** in MVP; scope changes are handled as a new job or an admin/incident adjustment. | Yes | Founder |
| D-A-AREA-1 | Service areas represented as **named zones + optional radius from base**; polygons deferred. | Yes | Founder |
| D-A-AVAIL-1 | Availability is a **manual toggle**; no scheduling in MVP. | Yes | Founder |
| D-A-DISC-1 | Job discovery is a **filtered, browsable list**; no auto-assign or auction bidding. | Yes (this one is also a CONFIRMED MVP boundary per the brief's "refine through experience") | Founder |
| D-A-POD-1 | Proof of delivery = recipient name **plus one or more of** OTP / signature / photo. **Proof of pickup now CONFIRMED with mandatory pickup-side OTP + fallback rules, see D-CUS-2.** | Yes (delivery side) | Founder |
| D-A-NOTIF-1 | ~~MVP channels: in-app + SMS~~ → **CONFIRMED with WhatsApp added, see D-NOTIF-1** (in-app + SMS + WhatsApp; OTP SMS-primary). | — | — |
| D-A-LIFE-1 | The detailed allowed-transition table in `job-lifecycle.md` §2 (refined from the brief's state list). | Yes | Founder review |
| D-A-LIFE-2 | Configurable timeouts framework: request expiry, offer expiry, stale-assignment alert (default ranges given). **Delivery-acceptance & post-completion windows now CONFIRMED with values, see D-JOB-5.** | Yes (remaining ranges) | Founder |
| D-A-DISP-1 | Dispute SLA targets by severity (given as ranges). | Yes | Founder |
| D-A-DISP-2 | On resolution, an admin **may resume** a disputed job to its pre-dispute state if it can continue. | Yes | Founder |
| D-A-ADMIN-1 | ~~Admin sub-roles may be collapsed to one role~~ → **CONFIRMED: 2 roles for pilot, see D-ADM-1.** | — | — |
| D-A-SCALE-1 | Pilot-scale sizing: hundreds of operators/businesses, low-thousands of jobs/month; RPO ≤ 24h, RTO ≤ 8h. | Yes | Founder |
| D-A-STACK-1 | Indicative stack: PWA client + server framework + PostgreSQL + object storage + SMS/maps providers + managed hosting. **Not a decision** — chosen in Phase 1. | Yes | Phase 1 team |
| D-A-HAZ-1 | Hazardous / dangerous goods are **flagged and excluded** from the pilot. | Yes | Founder + VALIDATION |

---

## 3. OPEN questions (need a founder answer / external input)

| ID | Question | Options | Recommendation | Blocks |
|----|----------|---------|----------------|--------|
| D-O-NAME-1 | Platform / brand name. | — | **RESOLVED 2026-09-08 → D-BRAND-1: `Fikisha`.** (`Mzigo` was rejected; `Fikisha` chosen from the round-2 shortlist.) Remaining: BRS + KIPI + domain/handle steps. | Branding, not build |
| D-O-AREA-1 | Exact pilot area, zone breakdown, and working language. | — | **RESOLVED:** area CONFIRMED (D-PIL-3); UI language CONFIRMED English & Swahili (D-PIL-4); zone breakdown DEFERRED — founder to supply, config update not a blocker (D-PIL-5) | Pilot start, config seed |
| D-O-COMM-1 | Who pays commission: operator / business / split? | See business-model.md §3 | **CONFIRMED 2026-09-08 → D-BIZ-4** (operator pays, shown transparently) | Earnings UI, statements |
| D-O-COMM-2 | Commission **rate** and structure. | See business-model.md §4 | **CONFIRMED 2026-09-08 → D-BIZ-5** (10% headline; KES 40 min; taper 10/5/3% or flat 10% capped KES 5,000; optional 0→5→10% intro ramp) | Commission calc config |
| D-O-COMM-3 | Commission **collection mechanism** for the pilot. | Statement / prepaid credits / defer | **CONFIRMED 2026-09-08 → D-BIZ-6** (weekly per-operator statement via merchant M-Pesa paybill; eTIMS invoices; platform never holds the fare) | Ledger scope |
| D-O-TRUST-1 | Trust-level thresholds and KES value bands / high-value threshold. | — | **CONFIRMED 2026-09-08 → D-TRU-5, D-TRU-6, D-TRU-7** (bands 50k/250k/1M; high-value review at KES 250k; L2 = 8 jobs/14d/4.2★; L3 = 30 jobs/60d/4.5★/3 clean Elevated; Good-Conduct cert before Elevated) | Trust gating config |
| D-O-CANCEL-1 | Cancellation policy: fees or reputation-only. | See business-model.md §6 | **CONFIRMED 2026-09-08 → D-DIS-3** (reputation-only; "3 in 30 days" → admin flag; courtesy fee built but default-off) | Cancellation flow |
| D-O-WHATSAPP-1 | Is WhatsApp a required channel for MVP? | — | **RESOLVED 2026-09-08 → D-NOTIF-1: YES** (in-app + SMS + WhatsApp; OTP stays SMS-primary) | Notification integration |
| D-O-CLIENT-1 | PWA vs. native app for MVP. | — | **RESOLVED 2026-09-08 → D-CLIENT-1: PWA** (installable, offline-tolerant; no native builds for MVP) | Client architecture |
| D-O-GROUP-1 | "Operator groups" (base owner, multiple drivers/vehicles) in MVP? | — | **RESOLVED 2026-09-08 → D-OPR-GRP-1: YES**, minimal-but-real (group + membership + group-owned vehicles + per-person verification; assignment names a driver; statement to the group) | Operator model scope |
| D-O-RECIP-1 | Recipients confirm delivery / raise incidents via a link without an account? | — | **RESOLVED 2026-09-08 → D-RCP-1: YES** (scoped, time-limited, single-job link; confirm receipt + raise incident; no account) | Recipient flow |
| D-O-PODWIN-1 | Delivery-acceptance + post-completion dispute window lengths. | — | **CONFIRMED 2026-09-08 → D-JOB-5** (acceptance 24h Std/Elevated, 48h High+; post-completion 72h all bands, 7d High+ & latent-risk cargo) | Lifecycle timers |
| D-O-PROOF-1 | Who provides proof-of-pickup. | — | **CONFIRMED 2026-09-08 → D-CUS-2** (mandatory pickup-side OTP; operator-attested photo fallback Standard band only; none at Elevated+) | Custody step design |
| D-O-ADMIN-1 | Admin role structure for the earliest pilot. | — | **CONFIRMED 2026-09-08 → D-ADM-1** (2 roles: Platform Admin + Operations Officer; 4-role split in config for later; all admin actions incl. founder's logged; admin MFA) | Admin auth model |
| D-O-KILL-1 | Pilot kill / iterate / scale criteria and targets. | — | **Deferred by founder to post-launch** ("we'll talk scaling post launch"). Pilot still instruments the full metric set (pilot-strategy.md §4); targets set after launch. | Pilot governance |
| D-O-RENEG-1 | Is in-flight re-negotiation needed, or is "new job / adjustment" enough? | — | New job / adjustment for MVP | Negotiation scope |
| D-O-ESCAL-1 | Named escalation point of last resort during the pilot + contact/hours. | — | The founder | Dispute process |

---

## 4. VALIDATION items (REQUIRES KENYAN PROFESSIONAL VALIDATION)

None of these are assumed settled. They must be triaged with qualified Kenyan
professionals before onboarding real operators and moving real goods.
**[legal-scope.md](legal-scope.md) now expands every item below** into a full
regulatory map, a recommended legal posture (neutral intermediary / digital
marketplace), a required-contracts list, a proposed data-retention schedule, and
an ordered pre-pilot legal checklist. Newly surfaced by that research:
the **NTSA Transport Network Company** licensing question (2022 regs are
passenger-focused; a High Court ruling of ~2 Sept 2026 struck down parts of them,
suspended 12 months); **NTSA commercial-service-vehicle operator** obligations on
heavy-vehicle operators (speed limiter, telematics, inspection, insurance);
**ODPC registration + DPIA + DPO** as pre-pilot actions; **eTIMS** mandatory
e-invoicing for commission; **CBK PSP licensing** avoided only if the platform
never holds the fare; **Consumer Protection Act** limits on liability-exclusion
wording; the pending **platform-worker / "dependent contractor" Bill**.

| ID | Item | Advisor type |
|----|------|--------------|
| D-V-LIC-1 | Whether operating this coordination/brokerage platform itself requires any transport / logistics / brokerage licence or registration. | Legal / regulatory |
| D-V-LIC-2 | Which driving licence classes and commercial/PSV endorsements are legally required per vehicle class carried on the platform. | Legal / transport authority |
| D-V-DOC-1 | Which vehicle documents (registration/logbook, inspection, insurance, goods-in-transit) are mandatory for each vehicle class. | Legal / insurance |
| D-V-LIAB-1 | Legal characterisation of the platform (carrier? forwarder? intermediary?) and the resulting liability exposure. | Legal |
| D-V-INS-1 | Insurance expectations for operators and any cargo-in-transit cover; whether the platform may/should facilitate cover. | Insurance |
| D-V-DPA-1 | Kenya Data Protection Act 2019 obligations: registration, DPO, lawful basis, consent wording, DSAR handling, retention periods, cross-border processing by SMS/maps/hosting providers. | Data-protection / legal |
| D-V-TAX-1 | Tax treatment of commission: VAT, withholding tax, e-invoicing/KRA obligations, invoicing operators vs. businesses. | Tax / accounting |
| D-V-PAY-1 | If/when the platform handles money (escrow, wallet, mobile-money collection): payment-service provider / e-money implications and licensing. | Legal / financial-services |
| D-V-CONS-1 | Consumer-protection obligations toward businesses and recipients. | Legal |
| D-V-HAZ-1 | Dangerous/hazardous goods rules if such cargo is ever allowed. | Legal / transport authority |
| D-V-INC-1 | External reporting obligations for accidents/theft (e.g. police documentation) and how platform records interact with them. | Legal |
| D-V-TOS-1 | Terms of Service, operator agreement, privacy notice — drafted and reviewed by qualified Kenyan counsel. | Legal |

---

## 5. Change discipline

- This log is the reference. Any change to a decision is made **here first**,
  with date and rationale, then reflected in the other documents.
- Pilot weekly reviews (see [pilot-strategy.md](pilot-strategy.md) §6) update this
  log with anything resolved or newly raised.
- Moving an item from OPEN/ASSUMPTION to CONFIRMED requires an explicit founder
  decision recorded with a date.
