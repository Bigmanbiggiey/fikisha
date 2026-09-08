# Legal Scope of the Platform (Working Draft)

> **This is a product-scoping document, not legal advice.** It was assembled from
> secondary sources (law-firm briefings, news reports, regulator pages) and a
> small number of official documents, in September 2026. Kenyan law and
> regulator practice change; several relevant instruments are actively in flux
> (see §3.3 and §12). **Every item marked REQUIRES VALIDATION must be confirmed
> by a qualified Kenyan advocate and, where noted, by the relevant authority,
> against primary sources (the Kenya Law site, `new.kenyalaw.org`, and the
> regulators themselves) before the pilot onboards real users or moves real
> goods.** Nothing here creates or implies any legal or insurance guarantee by
> the platform.

Pilot location: **Kitengela, Kajiado County**, serving Kitengela town and its
environs (the Namanga-road corridor, Athi River / Mavoko boundary, Isinya,
Kisaju, Kaputiei, and links to Nairobi's Industrial Area / CBD).

---

## 1. Purpose

Define, at Phase-0 depth, **what legal and regulatory obligations the platform
and its participants are likely to have**, what legal posture the product should
take, which contracts must exist, and the ordered pre-pilot legal checklist.
This lets Phase 1 build compliantly and lets the founder brief advisors
efficiently.

---

## 2. The core characterisation question

How the platform is legally characterised drives almost everything else. Three
possibilities:

| Posture | Description | Consequence |
|---------|-------------|-------------|
| **A. Neutral intermediary / digital marketplace** *(recommended)* | The platform introduces independent businesses and independent transport operators, hosts negotiation, and keeps records. The **carriage contract is directly between the business and the operator**. The platform is **not a party to the carriage**, never takes custody of goods, and never holds the transport fare. | Lightest liability exposure; platform's duties are about running a fair, safe, well-recorded marketplace. Requires the product and all contracts to be consistent with this (no fixed pricing, no fare-holding, no custody). |
| **B. Transport Network Company (TNC)** | The platform is treated as a regulated dispatch network under NTSA rules. | Likely needs an **NTSA TNC licence**, physical presence, prescribed driver/vehicle standards, and data provisions. The 2022 TNC Regulations are written for **passengers**; applicability to a **goods** platform is **unsettled** — see §3.3. |
| **C. Contractual carrier / freight forwarder** | The platform contracts with the business to move the goods and subcontracts operators. | Heaviest exposure: platform becomes the carrier of record, directly liable for loss/damage, needs carrier/goods-in-transit insurance, and arguably freight-forwarder standing. **Not the intended model.** |

**Recommended posture: A (neutral intermediary).** The MVP design already
supports it — negotiation-first (no platform-set price), direct payment between
parties (no fare-holding), operator-executed custody (platform never holds
goods). The Terms of Service, Operator Agreement, and every user-facing screen
must state and reflect this consistently.

**REQUIRES VALIDATION:** a written opinion from a qualified Kenyan advocate
confirming posture A is defensible for a goods-matching platform, and whether
NTSA nonetheless asserts TNC jurisdiction over goods platforms.

---

## 3. Regulatory & licensing map

### 3.1 Company & tax registration (platform)

| Item | What it means for the platform | Source | Status |
|------|-------------------------------|--------|--------|
| **Incorporation** — Companies Act 2015, via BRS on eCitizen | Register a **private limited company** (recommended over sole proprietorship for liability separation and investment). Name reservation, CR1/CR2/CR8, Statement of Nominal Capital, Model Articles, **Beneficial Ownership Register** filing. ~KES 10,000–10,650, 3–7 business days. | eCitizen / BRS guidance | CONFIRMED required action |
| **Company KRA PIN** — via iTax using the incorporation certificate | Needed for banking, VAT, eTIMS, contracts. | KRA / iTax | CONFIRMED required action |
| **Kajiado County Single (Unified) Business Permit** — Kajiado County Trade Licence / Finance Act | Required for the Kitengela office/premises. County officer inspects premises; fee by category (small business ~KES 5,000–15,000; larger ~KES 15,000–50,000+). Bundles trade licence, fire safety, signage, health (if applicable). | Kajiado County e-services; InvestKenya eProcedures | CONFIRMED required action |
| **NSSF / SHIF / PAYE** for any employees | Statutory payroll deductions and employer contributions for staff (not for the independent operators). | KRA / NSSF / SHA | CONFIRMED required action (once staff hired) |

### 3.2 Tax obligations (platform)

| Item | Working position | REQUIRES VALIDATION (tax advisor) |
|------|-----------------|-----------------------------------|
| **Corporate income tax** | Resident company taxed at the standard corporate rate (30%) on profits. | Confirm rate, instalment-tax obligations, allowable deductions. |
| **VAT** — VAT Act 2013 | Registration threshold is **KES 5,000,000** annual taxable turnover. The platform's **commission is a supply of services and is likely VATable** once registered. Below threshold, registration is optional. | Confirm whether/when to register voluntarily; VAT treatment of the commission; place-of-supply rules; whether any part of the service is exempt/zero-rated. |
| **eTIMS (electronic Tax Invoice Management System)** | Electronic tax invoices are **mandatory**; from **1 January 2026 KRA validates income and expenses in returns primarily against eTIMS data**. The platform must issue **eTIMS-compliant invoices for its commission** (statements to operators/businesses). | Confirm eTIMS onboarding path (OSCU/VSCU/eTIMS-Lite or API), invoice content, and treatment of the operator-to-business fare (which the platform does not invoice). |
| **Significant Economic Presence (SEP) tax / former DST** | SEP tax replaced the Digital Services Tax (from 27 Dec 2024) and, under the Finance Act 2025, applies broadly to **non-resident** persons earning from services over the internet/electronic networks (deemed 10% margin × 30% CIT; the KES 5M threshold was removed). **A Kenyan-incorporated platform is a resident and is taxed under normal CIT, not SEP tax.** | Confirm SEP tax does not apply to the resident entity; confirm no withholding obligations on payments to operators (individuals) or to overseas service providers (SMS/maps/hosting) — **withholding tax on cross-border service payments is likely**. |
| **Withholding tax** | Payments to some service providers (professional fees, certain cross-border payments) attract WHT that the platform must deduct and remit. | Map every recurring payee (advocates, SMS aggregator, maps/hosting if non-resident) and confirm WHT rates. |

### 3.3 Transport regulation (NTSA / Traffic Act)

| Item | What it means | Source | Status |
|------|--------------|--------|--------|
| **Transport Network Company (TNC) licence** — NTSA (Transport Network Companies, Owners, Drivers and Passengers) Regulations, 2022 | Written for **passenger** ride-hailing (Uber, Bolt, Little, Yego are the licensed four). Requires local physical presence, an annual licence, prescribed driver/vehicle standards, and data provisions. A **commission cap of 18%** of trip earnings (Reg. 9) and a **3-year data retention + surrender-on-demand** provision (Reg. 17) were part of the 2022 rules. **On/about 2 September 2026 the High Court (Aburili J.) declared key parts of these Regulations unconstitutional** — including the commission cap (insufficient evidence of necessity/proportionality) and the data-retention/surrender provision (violating Article 31 privacy and the Data Protection Act) — but **suspended the declaration for 12 months** for fresh public participation and a regulatory impact assessment. | NTSA; news reports of the 2026 ruling; law-firm briefings | **APPLICABILITY TO A GOODS PLATFORM IS UNSETTLED — REQUIRES VALIDATION** with NTSA (formal written query) and counsel. Also monitor the replacement rules the government must now draft. |
| **Commercial Service Vehicle Operator Licence** — NTSA (Operation of Commercial Service Vehicles) Regulations, 2024/2025 | Applies to **commercial service vehicles with tare weight above ~3,048 kg** on public roads (i.e. the platform's canter/lorry/tipper/semi-truck/trailer operators, not motorcycles/pickups). Requires an **annual NTSA operator licence**, company registration + KRA PIN + physical address, **speed limiter**, **vehicular telematics**, retro-reflective markings, valid **inspection certificate**, at least **third-party insurance**, maintenance records kept ≥ 2 years, adherence to Traffic Act driving-hours, and a **preliminary report to NTSA within 24 hours of any fatal accident**. | NTSA Regulations 2024/2025; news summaries | **Obligation sits on the operator/vehicle owner.** The platform should **require proof of the operator licence, speed limiter, telematics, inspection and insurance as part of vehicle verification** for these vehicle classes, and should not surface such a vehicle for jobs without it. REQUIRES VALIDATION of the exact tare-weight trigger and current document list. |
| **Driver licensing** — Traffic Act (Cap 403) & NTSA | Correct licence **class per vehicle** (e.g. Category **C / C1 / CE / CD** for trucks and articulated combinations; A/B for motorcycles/light vehicles), and **PSV/commercial endorsements** where applicable. | NTSA licence categories | The platform's **Licence** verification domain must check class-against-vehicle. REQUIRES VALIDATION of the exact class map and which endorsements goods carriage needs. |
| **Certificate of Good Conduct (DCI)** | Police clearance certificate. Ride-hailing rules require it for drivers. | DCI | **RECOMMENDED**: require for all operators; **mandatory** for operators eligible for Elevated+ value bands. REQUIRES VALIDATION whether any rule makes it compulsory for goods operators. |
| **Load / axle limits & weighbridges** — Traffic Act; KeNHA/KURA | Overloading is an offence; axle-load limits enforced at weighbridges. | Traffic Act | ToS/Operator Agreement must require operators to comply and forbid the platform being used to arrange overloaded trips. Platform should let operators decline loads that exceed their vehicle's lawful capacity. |
| **Dangerous / hazardous goods** | Separately regulated carriage regime. | — | **Excluded from the pilot.** ToS prohibits. REQUIRES VALIDATION before ever enabling. |

### 3.4 Data protection (ODPC)

Governing law: **Data Protection Act, 2019** + **Data Protection (General)
Regulations, 2021** (plus Registration and Complaints-Handling Regulations).
Regulator: **Office of the Data Protection Commissioner (ODPC)**.

| Item | What it means for the platform | Status |
|------|-------------------------------|--------|
| **ODPC registration** as **data controller** (and as **data processor** where it processes on others' behalf) | Mandatory where annual turnover/revenue **> KES 5,000,000 AND > 10 employees**; **also mandatory regardless of size for higher-risk processing** and certain sectors. This platform processes **government ID / passport data, driving licences, location data, and builds trust profiles** — clearly higher-risk. | **RECOMMENDED: register as a data controller (and processor) before onboarding real users**, irrespective of the size threshold. REQUIRES VALIDATION of the exact registration category and fees. |
| **Data Protection Impact Assessment (DPIA)** | Required for processing likely to result in high risk to data subjects — here: **location capture, ID-document handling, and trust/eligibility profiling**. | **CONFIRMED required action** before pilot go-live. |
| **Lawful basis** per processing activity | Contract performance (running jobs, verification, payments records); legal obligation (tax records; NTSA reporting where applicable); legitimate interests (fraud prevention, trust & safety, dispute handling) with a balancing test; **consent** (device location capture; any marketing messages). | Document a processing register mapping each data item → purpose → basis → retention. |
| **Data-subject rights** | Access, rectification, erasure, restriction, objection, **data portability**, and not to be subject to solely automated decisions with significant effect. MVP trust-level progression is **admin-confirmed**, which helps avoid the automated-decision problem — keep a human in the loop for suspensions and high-value gating too. | Build a data-subject-request intake + response process. |
| **Breach notification** | Notify the ODPC (and, where high risk, affected data subjects) **within 72 hours** of becoming aware, where the breach poses a real risk to rights and freedoms. | **CONFIRMED required action**: a written breach-response plan before go-live. |
| **Cross-border transfers** | Permitted only with **adequacy**, **appropriate safeguards**, **necessity**, or **explicit informed consent**. If SMS aggregator / maps / cloud storage process data **outside Kenya**, each transfer must be mapped and lawful. | **RECOMMENDED: prefer Kenya-region (or, failing that, a safeguarded region) hosting and a Kenyan SMS aggregator** to minimise transfers; put **Data Processing Agreements** in place with every processor. REQUIRES VALIDATION of the transfer basis for each provider. |
| **Data minimisation & retention** | Collect only what each function needs; delete/anonymise on a schedule (see §7). | Configure retention windows in the platform **before** the first real job. |
| **DPO / contact person** | Appoint a Data Protection Officer or a designated contact, and publish the contact in the Privacy Notice. | **CONFIRMED required action.** |

### 3.5 Consumer protection

Governing law: **Consumer Protection Act, 2012** (No. 46 of 2012); Competition
Act (consumer-protection provisions); sector guidance. Body: Kenya Consumers
Protection Advisory Committee; the Competition Authority also acts on consumer
issues.

| Obligation | What it means for the platform |
|------------|-------------------------------|
| No unfair / misleading / unconscionable practices | Accurate representations about what the platform does, operator verification status, pricing, and dispute outcomes. **No "insured", "guaranteed", or "licensed by us" claims** unless literally true and substantiated (see §8). |
| Clear terms | Terms of Service must clearly state price basis, how negotiation works, delivery expectations, cancellation, **dispute resolution and governing law/jurisdiction**, and the limits of the platform's role. |
| Warranties / guarantees honoured | Any commitment the platform actually makes (e.g. an SLA on dispute response) must be honoured. Do not commit to what cannot be delivered. |
| Records & receipts | Provide clear records/receipts of the coordination service and commission. |
| Product-liability interaction | Liability for the **goods** and their carriage runs between operator and business; the platform should not position itself between them as a warrantor. |

**REQUIRES VALIDATION:** whether business users and recipients are "consumers"
for all provisions, and the **enforceability of liability caps / exclusions** in
the Terms of Service under the Act (some exclusions are void).

### 3.6 Payments (CBK) — and how the pilot stays outside the licence

Governing law: **National Payment System Act, 2011** + **National Payment System
Regulations, 2014**. Regulator: **Central Bank of Kenya (CBK)**.

| Fact | Consequence |
|------|-------------|
| **No person may conduct payment-service-provider business without CBK authorisation.** Holding customer funds, operating **escrow/wallet**, e-money issuance, and payment aggregation are PSP activities; PSPs must **segregate client funds / use trust or escrow accounts**. | If the platform **held the transport fare** or operated a wallet/escrow, it would need a **CBK PSP licence** — a heavy, slow, capital-intensive process. |
| **Pilot design avoids this:** the **business pays the operator directly** (cash or their own M-Pesa/bank). The platform **only ever collects its own commission** from the operator, via a **standard M-Pesa Paybill/Till as a merchant** and a periodic statement. The platform never touches third-party funds. | Keeps the pilot **outside PSP licensing**. **REQUIRES VALIDATION** that a merchant paybill used only to collect the platform's own commission is not itself "payment-service business", and confirmation from the bank/PSP providing the paybill. |
| Future in-app fare collection / escrow / instant operator payout | **Deferred.** If pursued, budget for **CBK engagement and likely PSP authorisation or a partnership with a licensed PSP**, plus AML/CFT obligations under POCAMLA. | See [future-roadmap.md](future-roadmap.md). REQUIRES VALIDATION before any design work. |

### 3.7 Insurance

| Layer | Working position | REQUIRES VALIDATION (licensed broker + IRA) |
|-------|-----------------|---------------------------------------------|
| **Operator statutory** | Every motor vehicle needs at least **third-party motor insurance**; commercial service vehicles (>~3,048 kg tare) need it as a licence condition. The platform **must verify** this per vehicle and block expired cover. | Confirm minimum cover per vehicle class. |
| **Goods-in-transit / carrier's liability** | These are **commercial products** offered by Kenyan insurers (Madison, Mayfair, Tausi, CIC, brokers, etc.), covering loss/damage to goods in transit by road and the carrier's legal liability. **They are not statutory.** | For **Elevated and higher value bands**, the platform should **require the operator to hold goods-in-transit or carrier's-liability cover**, or require the **business to arrange its own cover**, and record which. Confirm typical limits, exclusions, and cost. |
| **Platform's own cover** | The company should carry **commercial general / public liability** and **professional indemnity** (for the coordination service, data handling, advice). | Confirm appropriate sums insured for a pilot-stage platform. |
| **Any platform-branded "cover" or "guarantee"** | **Do not offer or market one** unless it is **underwritten by a licensed insurer** through a proper arrangement; acting as an unlicensed insurer/intermediary is an offence, and bancassurance-style/intermediary rules apply. | If a "protected delivery" product is ever wanted, it must be an **IRA-approved insurer partnership**. REQUIRES VALIDATION. |

### 3.8 Labour / worker classification

| Fact | Consequence for the platform |
|------|------------------------------|
| Kenya's Employment Act uses a **binary** model: employee **or** independent contractor. Operators here are intended to be **independent contractors**. | The **Operator Agreement** must state contractor status clearly and the product must **avoid employment indicia**: the platform **does not set prices** (negotiation-first), **does not mandate working hours** (availability is a self-toggle), does not require exclusivity, does not "discipline" like an employer (it applies transparent trust/verification rules and records). |
| A **"dependent contractor" / platform-worker** category has been debated (KUGWO memoranda; Business Laws (Amendment) discussions; a mooted **Labour Laws (Amendment) Bill**) but **is not yet law** (as of Sept 2026). | **Monitor.** If enacted, it could bring social-security/benefit obligations for operators who depend on the platform for most income. Keep the commercial model resilient to a later change (this is a stated risk — see [phase-0-report.md](phase-0-report.md) R-labour). |
| **Operator groups** (D-OPR-GRP-1): a group (yard owner / SACCO / partnership) is a **counterparty**, not an employer-of-record for the platform. But the **group↔driver** relationship may itself be employment or contractor — that is the group's affair, not the platform's, and the Operator Agreement should say so. | The **Operator Agreement / Group Agreement** must define: the group as an independent contractor; that each member driver is individually verified and bound; that the group is responsible for its drivers' conduct and for internal settlement; indemnity of the platform for the group's and its drivers' acts. The platform must not direct group drivers as if they were its own staff. |

**REQUIRES VALIDATION:** an employment-law review of the Operator Agreement /
Group Agreement and the product's control indicia, plus a watching brief on the
Bill; and whether the platform has any obligation regarding the group↔driver
relationship.

### 3.9 Messaging / communications

| Item | What it means |
|------|--------------|
| **A2P / bulk SMS** — Kenya Information and Communications Act; Communications Authority (CA) rules | Send transactional SMS (OTP, job events) through a **licensed SMS aggregator** with a **registered sender ID**. OTP/job notifications are **transactional**, not marketing. |
| **Marketing messages** | Require **consent** (Data Protection Act + CA guidance) and an opt-out. Keep marketing separate from transactional flows. |
| **WhatsApp** | **CONFIRMED MVP channel (D-NOTIF-1).** Via the **WhatsApp Business Platform** through an authorised BSP, within Meta's policy (approved transactional templates only). Data sent to WhatsApp/Meta is a **cross-border transfer to the US** — it needs a lawful transfer basis (consent and/or safeguards) and must be named in the **DPA and the Privacy Notice**, and the recipient link sent over WhatsApp means a **non-user's** phone number and delivery data also go to Meta — the recipient short terms must disclose this. |
| **Recipient link** | The per-job link (D-RCP-1) is sent to a person who has **no account**; it processes their name, phone, and any incident content. Lawful basis (legitimate interests / contract performance for the business), a short recipient-facing notice on the link, minimal retention, and link expiry are required. |

### 3.10 Prohibited & restricted goods

The Terms of Service and an **Acceptable Use / Prohibited Goods policy** must
forbid using the platform to move: illegal goods; counterfeit goods
(Anti-Counterfeit Act); **dangerous/hazardous goods** (separate regime — excluded
from pilot); restricted items (e.g. certain agricultural, wildlife, mineral,
or excisable products) without the required permits; human cargo; and anything
the operator's vehicle cannot lawfully carry. Operators must be able to report
and decline suspected prohibited cargo, and such reports feed trust & safety.

---

## 4. Contracts the platform needs

All to be **drafted / reviewed by a qualified Kenyan advocate** (commercial/tech)
before the pilot:

| # | Document | Covers |
|---|----------|--------|
| 1 | **Platform Terms of Service** (business users) | Nature of the service (intermediary, posture A); account rules; how jobs, negotiation, pricing, and confirmation work; that the **carriage contract is with the operator**; that payment is **direct between the parties**; cancellation; ratings; **limitation of platform liability** and disclaimers; dispute resolution (amicable-first → admin review → **mediation/arbitration**), **governing law = Kenya, courts of Kenya**; suspension/termination; changes to terms. |
| 2 | **Operator Agreement** (+ a **Group Agreement** schedule for operator groups) | **Independent-contractor status**; eligibility & continuous verification obligations (identity, licence class, vehicle documents, insurance, operator licence & telematics for heavy classes, Certificate of Good Conduct); conduct & safety standards; **operator is the carrier** and responsible for goods in custody; commission rate, deduction mechanism, and **statement/settlement terms**; prohibited goods; cancellation/no-show consequences; data consents (incl. WhatsApp cross-border); **indemnity** of the platform for the operator's acts/omissions; suspension, trust-level regression, offboarding; dispute process; governing law. **Group schedule:** the group is an independent contractor; each member driver is individually bound and verified; the group is responsible for its drivers' conduct and for internal settlement; the group↔driver relationship is the group's affair; group indemnifies the platform for its and its drivers' acts. |
| 3 | **Privacy Notice** | Identity of controller + DPO contact; data collected (incl. ID, licence, **location**, ratings); purposes and **lawful bases**; recipients/processors (SMS, maps, hosting) and **cross-border transfers**; **retention schedule**; **data-subject rights** and how to exercise them; ODPC complaint route; automated-processing statement. |
| 4 | **Data Processing Agreements** | One with **each processor** — SMS aggregator, **WhatsApp BSP / Meta** (US cross-border), maps/geocoding, hosting, cloud storage, any analytics — scope, security, sub-processors, transfer safeguards, breach support, deletion on termination. |
| 5 | **Acceptable Use / Prohibited Goods Policy** | Referenced by ToS and Operator Agreement; the §3.10 list; reporting and enforcement. |
| 6 | **Dispute Resolution & Liability Policy** | The amicable-first → evidence/statements → administrative review → resolution → escalation flow; SLA targets; that the platform **facilitates, does not adjudicate** and makes **no guarantee**; how commission is treated in disputes; mediation/arbitration seat and rules. |
| 7 | **Recipient / Consignee short terms** | Presented on the per-job link (D-RCP-1): what confirming delivery means, how to raise an incident, **privacy basics including that the link may arrive via WhatsApp and that name/phone/incident data is processed** (with the lawful basis and retention), link expiry, no account required. |
| 8 | **Cookie / telemetry notice** (web/PWA) | If any non-essential analytics/cookies are used. |
| 9 | **Employee / staff contracts + HR policies** | For the founder's ops/verification/dispute staff (separate from operators). |

---

## 5. Liability allocation — working position (to validate)

1. The **contract of carriage is between the business and the operator**. The
   operator, as carrier, is responsible for loss of or damage to goods while in
   their custody, subject to what the parties agree and to any cover in place.
2. The platform's role is **coordination, record-keeping, and dispute
   facilitation**. The platform is **not a party to the carriage**, does not take
   custody of goods, and does not hold the fare.
3. The platform is **not liable** for: the goods; the operator's or business's
   acts or omissions; the condition, safety, or roadworthiness of vehicles
   beyond checking documents in good faith; the parties' payment dealings; or
   outcomes of negotiations.
4. The platform **is responsible** for operating the service with reasonable
   care — running verification honestly, keeping accurate records, protecting
   personal data, and handling disputes per its published process.
5. Platform liability, where it arises, should be **capped** (e.g. to the
   commission earned on the affected job, or a modest fixed sum) — **but note
   that the Consumer Protection Act voids some exclusions/limitations; the
   enforceable wording REQUIRES VALIDATION.**
6. Nothing purports to exclude liability that **cannot lawfully be excluded**
   (e.g. for the platform's own negligence causing death or personal injury, or
   for fraud).
7. Each side **indemnifies** the platform for losses caused by their breach
   (operator indemnity in the Operator Agreement; business indemnity in the ToS).

---

## 6. Regulatory posture summary (what to tell advisors)

> "We are building a **Kenyan private limited company** operating a
> **digital marketplace** that introduces **independent businesses** to
> **independent local transport operators** (motorcycle to trailer) in the
> **Kitengela / Kajiado** area. Parties **negotiate their own price** and
> **pay each other directly**; we take a **configurable commission on completed
> jobs**, collected from operators via a **merchant M-Pesa paybill and periodic
> eTIMS invoices**. We **verify** operator identity, licence, vehicle documents
> and insurance, we keep an **auditable chain of custody**, and we run a
> structured **incident/dispute** process. We do **not** own vehicles, take
> custody of goods, hold the fare, set prices, or offer insurance. We need
> advice on: (a) whether this is defensible as a neutral intermediary vs. a
> regulated Transport Network Company; (b) NTSA licence applicability to a goods
> platform and the operator-side commercial-vehicle obligations we must enforce;
> (c) that our commission-collection mechanism stays outside PSP licensing;
> (d) ODPC registration, DPIA, retention, and cross-border transfers;
> (e) enforceable liability wording under the Consumer Protection Act;
> (f) tax (VAT, eTIMS, WHT); (g) the independent-contractor position and the
> pending platform-worker Bill; (h) the **operator-group** structure (group vs.
> member-driver liability, and any platform obligation toward group drivers);
> (i) the **WhatsApp/Meta cross-border transfer** and the **no-account recipient
> link** processing of non-users' data."

---

## 7. Proposed data-retention schedule (to validate)

| Data class | Proposed retention | Rationale |
|------------|--------------------|-----------|
| Account (business/operator) core data | Life of account + 7 years after offboarding | Tax/limitation periods |
| Job records, negotiation history, agreed price | 7 years after completion | Tax, dispute limitation, audit |
| Chain-of-custody entries & proof of delivery | 7 years after completion | Dispute/evidence |
| Evidence media (incident photos/docs) | 7 years after incident closure | Dispute/evidence; review sooner if large |
| ID / passport / licence images | **12 months** after offboarding **or** document expiry, whichever first (verification *outcome* + expiry date retained longer) | Minimisation — the document image is only needed to verify |
| Operator payout numbers | Life of account + statutory tax tail | Payments records |
| Device location points (raw) | Purge raw points after **12 months**; keep the **event-level summary** (arrived at pickup at HH:MM near <zone>) for the job-record period | Minimisation of precise location data |
| Audit logs | 7 years | Accountability, investigations |
| Dispute & resolution records | 7 years | Limitation, precedent, regulator queries |
| Marketing consents & opt-outs | Life of account + 2 years | Prove consent |
| Support/comms logs | 2–3 years | Service quality, disputes |
| Recipient (consignee) name/phone + link metadata | With the job record (7 years); the **access link itself expires** at COMPLETED + post-completion dispute window and is then unusable | Minimisation — recipient is a non-user |
| Operator-group member roster & group payout number | Life of group + statutory tax tail | Payments / accountability |

All configurable in `PlatformConfig`; **exact periods REQUIRES VALIDATION**
against tax law, the Limitation of Actions Act, NTSA rules, and ODPC guidance.

---

## 8. Hard guardrails — what the platform must NOT say or do (pilot)

| Guardrail | Reason |
|-----------|--------|
| Do **not** claim goods are "insured", "covered", or "guaranteed" by the platform | No insurance product; acting as unlicensed insurer is an offence; Consumer Protection Act on misrepresentation |
| Do **not** claim operators are "licensed by" or "certified by" the platform in a way implying a regulatory act | Verification is private due diligence, not certification |
| Do **not** set or "recommend" prices during MVP | Founder principle; keeps posture A (intermediary, not carrier); avoids competition-law questions about a platform coordinating prices among independent operators |
| Do **not** hold, route, or escrow the transport fare | Triggers CBK PSP licensing |
| Do **not** take custody of goods or describe the platform as the carrier/forwarder | Shifts to posture C liability |
| Do **not** use employment-style control (fixed shifts, exclusivity, employer-style discipline) | Worker-classification risk |
| Do **not** enable dangerous/hazardous goods | Separate regulatory regime; excluded from pilot |
| Do **not** retain ID images, precise location, or trip data longer than the schedule allows | Data Protection Act minimisation; the 2026 court ruling struck down open-ended trip-data retention as unconstitutional |
| Do **not** onboard real users before ODPC registration, DPIA, and the contract set are in place | Registration is a precondition to lawfully processing |

---

## 9. Pre-pilot legal checklist (ordered)

1. **Incorporate** the private limited company (BRS/eCitizen); file **beneficial
   ownership**; obtain the **company KRA PIN**; open a **business bank account**.
2. **Engage advisors**: a qualified Kenyan advocate (commercial/tech + data
   protection), a **tax advisor**, and a **licensed insurance broker**.
3. **Written legal opinion** on: platform characterisation (posture A);
   **NTSA TNC licence applicability** to a goods platform; the
   **commission-collection mechanism vs the National Payment System Act**;
   **enforceable liability wording** under the Consumer Protection Act;
   **independent-contractor** position.
4. **NTSA**: file a formal written query on TNC-licence applicability; document
   the **operator-side** obligations to enforce (commercial-vehicle operator
   licence, speed limiter, telematics, inspection, insurance, licence class,
   Certificate of Good Conduct) and build them into vehicle/operator
   verification.
5. **Kajiado County**: obtain the **Single Business Permit** for the Kitengela
   premises (premises inspection).
6. **ODPC**: register as **data controller** (and processor); appoint a **DPO /
   contact**; complete a **DPIA**; finalise the **retention schedule** and
   **breach-response plan**; execute **DPAs** with all processors; decide
   **hosting/SMS region** to minimise cross-border transfers.
7. **Contract set** (§4) drafted and finalised: ToS, Operator Agreement, Privacy
   Notice, DPAs, Acceptable Use / Prohibited Goods, Dispute & Liability policy,
   Recipient terms, staff contracts.
8. **Tax setup**: confirm VAT position; onboard to **eTIMS**; build
   eTIMS-compliant commission invoice/statement templates; set up **PAYE/NSSF/
   SHIF** for staff; confirm **WHT** obligations on payees.
9. **Insurance**: bind the platform's **CGL + professional indemnity**; define
   the **operator insurance requirement by value band**; confirm **no
   platform-branded cover** is offered unless underwritten by a licensed
   insurer.
10. **Messaging**: contract a **licensed SMS aggregator** and register the
    **sender ID**; engage an **authorised WhatsApp BSP** (WhatsApp is a
    confirmed MVP channel — D-NOTIF-1), get transactional templates approved, and
    put DPAs in place for both, with the **WhatsApp/Meta US cross-border
    transfer** documented and consented.
10a. **Operator-group & recipient paperwork**: add the **Group Agreement**
    schedule to the Operator Agreement; add the **recipient short terms** shown
    on the no-account link (disclosing WhatsApp delivery + data processing).
11. **Brand/IP**: BRS **name reservation** and **KIPI trade-mark** search/
    application (see [brand-name.md](brand-name.md)).
12. **Configure the platform**: retention windows, audit logging, consent
    capture, prohibited-goods rules, and value-band gating **before the first
    real job**.

---

## 10. Mapping to existing Phase-0 documents

| This document's item | Related Phase-0 doc |
|----------------------|---------------------|
| Characterisation, liability allocation | [dispute-and-liability.md](dispute-and-liability.md) |
| Verification domains, insurance-by-band, Certificate of Good Conduct | [trust-and-safety.md](trust-and-safety.md), [operator-model.md](operator-model.md) |
| No fare-holding, commission collection | [business-model.md](business-model.md) |
| No platform-set price | [pricing-and-negotiation.md](pricing-and-negotiation.md) |
| Data protection, retention, security | [non-functional-requirements.md](non-functional-requirements.md) |
| Open legal items | [decisions.md](decisions.md) §4 |
| Deferred payments/insurance | [future-roadmap.md](future-roadmap.md) |

---

## 11. Status summary

| Item | Category |
|------|----------|
| Recommended legal posture: neutral intermediary / digital marketplace (posture A) | RECOMMENDATION — REQUIRES VALIDATION by a qualified Kenyan advocate |
| Private limited company + county permit + company KRA PIN | CONFIRMED required actions |
| Commission collected via merchant paybill + eTIMS invoices; platform never holds the fare | WORKING ASSUMPTION designed to stay outside CBK PSP licensing — REQUIRES VALIDATION |
| NTSA TNC-licence applicability to a goods platform | OPEN / UNSETTLED — REQUIRES VALIDATION with NTSA + counsel; monitor post-2 Sept 2026 rule-making |
| Operator-side commercial-vehicle obligations (licence, speed limiter, telematics, inspection, insurance, licence class, good-conduct certificate) | CONFIRMED the platform must verify these for heavy vehicle classes — exact list REQUIRES VALIDATION |
| ODPC registration + DPIA + DPO + retention schedule + breach plan + DPAs | CONFIRMED required actions before pilot |
| Consumer Protection Act: fair-trading, clear terms, enforceable liability wording | CONFIRMED applies — exact wording REQUIRES VALIDATION |
| Tax: CIT, VAT (KES 5M threshold), eTIMS mandatory, WHT on some payees; SEP tax not applicable to a resident company | WORKING POSITION — REQUIRES VALIDATION by a tax advisor |
| Insurance: verify operator statutory cover; require goods-in-transit/carrier's cover for higher value bands; platform CGL+PI; no unlicensed platform "cover" | RECOMMENDATION — REQUIRES VALIDATION by a broker + IRA |
| Operators are independent contractors; monitor the platform-worker / "dependent contractor" Bill | WORKING POSITION — REQUIRES employment-law VALIDATION and a watching brief |
| **Operator groups** in the MVP: group is a counterparty, not employer-of-record for the platform; group↔driver relationship is the group's affair; Group Agreement schedule needed | WORKING POSITION — REQUIRES VALIDATION |
| **WhatsApp** as an MVP channel: WhatsApp Business Platform via BSP; approved templates; **US cross-border transfer** to Meta in DPA + Privacy Notice + recipient terms | CONFIRMED channel (D-NOTIF-1); transfer basis REQUIRES VALIDATION |
| **Recipient no-account link**: processes a non-user's name/phone/incident content; lawful basis + short notice + minimal retention + link expiry | CONFIRMED feature (D-RCP-1); wording REQUIRES VALIDATION |
| Full contract set drafted by a qualified Kenyan advocate (incl. Group Agreement schedule + recipient short terms) | CONFIRMED required action |

---

## 12. Sources (secondary; verify against primary law before relying)

- Kenya Data Protection Act 2019 / ODPC registration thresholds — Securiti DPA guide (`https://securiti.ai/kenya-data-protection-act-dpa/`); Njaga Advocates (`https://njagaadvocates.com/registration-as-a-data-controller-and-data-processor-in-kenya-with-the-odpc/`); MWC Legal (`https://mwc.legal/mandatory-registration-of-data-controllers-and-processors/`)
- Data Protection (General) Regulations 2021 — ODPC PDF (`https://www.odpc.go.ke/wp-content/uploads/2024/03/THE-DATA-PROTECTION-GENERAL-REGULATIONS-2021-1.pdf`); Kenya Law (`https://new.kenyalaw.org/akn/ke/act/ln/2021/263/eng@2022-12-31`); Oraro & Company (`https://www.oraro.co.ke/data-protection-the-coming-into-force-of-various-data-protection-regulations-and-what-you-need-to-know/`); DLA Piper Data Protection – Kenya (`https://www.dlapiperdataprotection.com/index.html?t=law&c=KE`)
- NTSA commercial service vehicle regulations 2024/2025 — NTSA draft (`https://ntsa.go.ke/cms/wp-content/uploads/2024/10/NTSA-Operation-of-Commercial-Service-Vehicles-Regulations-2024.doc`); Capital FM (`https://www.capitalfm.co.ke/news/2025/01/ntsa-issues-mandatory-rules-for-commercial-vehicles/`); Eastleigh Voice (`https://eastleighvoice.co.ke/national/65419/ntsas-new-rules-on-commercial-vehicles-seek-to-boost-road-safety`); Monolith Africa summary (`https://www.monolithafrica.com/blog/ntsa-commercial-vehicle-rules-2026-new-requirements-for-trucks-fleet-owners-transporters-in-kenya/`)
- NTSA Transport Network Company regulations 2022 + Form 11 checklist (`https://ntsa.go.ke/cms/wp-content/uploads/2023/10/tnc-checklist-1.pdf`); TechMoran on the four licensed TNCs (`https://techmoran.com/2022/10/31/ntsa-approves-four-companies-to-operate-as-transport-network-companies-in-kenya/`)
- 2 September 2026 High Court ruling on the TNC Regulations (commission cap + data retention struck down, suspended 12 months) — Kenyans.co.ke (`https://www.kenyans.co.ke/news/126753-high-court-blocks-enforcement-18-commission-cap-ride-hailing-platforms`); Business Daily (`https://www.businessdailyafrica.com/bd/economy/blow-to-uber-bolt-drivers-as-court-blocks-18pc-commission-cap-5581212`); techtrendske (`https://techtrendske.co.ke/2026/09/03/kenya-ride-hailing-commission-cap-court/`); techweez (`https://techweez.com/2026/09/03/kenya-uber-ride-hailing-commission-cap-court-ruling/`)
- National Payment System Act 2011 + Regs 2014; PSP authorisation & client-fund segregation/escrow — CBK Act PDF (`https://www.centralbank.go.ke/images/docs/legislation/NATIONAL%20PAYMENT%20SYSTEM%20ACT%20(No%2039%20of%202011)%20(2).pdf`); CBK PSP checklist (`https://www.centralbank.go.ke/wp-content/uploads/2020/06/Payment-Service-Providers-Authorization-checklist.pdf`); CM Advocates (`https://cmadvocates.com/blog/obtaining-a-psp-license-in-kenya-a-comprehensive-legal-and-regulatory-guide/`); KDS Advocates (`https://kdsadvocates.com/news-insights/psp-license-kenya/`)
- Consumer Protection Act 2012 & e-commerce — Oraro & Company (`https://www.oraro.co.ke/consumer-protection-law-in-kenya/`); CFL Advocates (`https://cfllegal.com/regulating-e-commerce-transactions-in-kenya-what-businesses-should-know-about-consumer-protection-and-data-compliance/`); AMG Advocates (`https://www.amgadvocates.com/post/consumer-protection-laws-in-kenya`)
- KRA VAT / eTIMS / SEP tax — CM Advocates on eTIMS (`https://cmadvocates.com/blog/demystifying-etims-why-every-business-in-kenya-should-pay-attention/`); Alphacap eTIMS guide (`https://alphacap.co.ke/etims-compliance-kenya/`); Taxually on SEP tax / digital-services VAT (`https://support.taxually.com/support/solutions/articles/80001216449-kenya-vat-for-foreign-providers-of-digital-services-what-you-need-to-know-about-significant-economic`); KPMG on SEP tax consultation (`https://kpmg.com/us/en/taxnewsflash/news/2025/09/kenya-public-consultation-application-sep-tax.html`)
- Goods-in-transit / carrier's-liability insurance — Madison (`https://www.madison.co.ke/protect-your-business/goods-in-transit/`); Mayfair (`https://ke.mayfairinsurance.africa/solutions/corporate-solutions/goods-in-transit/`); Kenya Law Insurance Regulations (`https://new.kenyalaw.org/akn/ke/act/ln/1986/312/eng@2022-12-31`)
- Gig / platform-worker classification — DLA Piper Africa / IKM (`https://www.dlapiperafrica.com/en/kenya/insights/2024/protecting-labour-rights-for-gig-workers-`); Njaga Advocates (`https://njagaadvocates.com/the-distinctions-between-employees-independent-contractors-and-gig-workers-under-the-kenyan-employment-and-labour-law/`); KIOI & Co (`https://www.kioi.co.ke/employment-law-and-the-gig-economy-are-freelancers-and-digital-workers-protected-in-kenya/`)
- Company registration — iBizAfrica/Strathmore (`https://ibizafrica.strathmore.edu/how-to-register-your-business-in-kenya-in-2025/`); MNA Registrars (`https://mnaregistrars.com/how-to-register-company-kenya-ecitizen-2025/`)
- Kajiado County Single Business Permit — InvestKenya eProcedures (`https://eprocedures.investkenya.go.ke/procedure/617`); Kitengelas.com guide (`https://kitengelas.com/guide-to-getting-your-kajiado-county-license/`); Kajiado County e-services (`https://eservices.kajiado.go.ke/`)
- Kenyan digital-logistics landscape (context) — Wikipedia: Kobo360 (`https://en.wikipedia.org/wiki/Kobo360`); LoadLink Kenya (`https://www.loadlinkkenya.com/`); CIO Africa on e-logistics startups (`https://www.cio.com/article/191506/these-7-e-logistics-start-ups-are-transforming-african-supply-chains.html`)

**Primary sources to consult before relying on any of the above:**
`new.kenyalaw.org` (Acts and subsidiary legislation), `odpc.go.ke`, `ntsa.go.ke`,
`centralbank.go.ke`, `kra.go.ke`, `kajiado.go.ke`, and the relevant advocates.
