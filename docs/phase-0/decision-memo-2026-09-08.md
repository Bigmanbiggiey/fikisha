# Decision Memo — 2026-09-08

**From:** Product/Engineering agent
**To:** Founder
**Re:** Brand, pilot area, and six operating-policy decisions

**Status (updated 2026-09-08, later same day):**
- **§0 Pilot area — CONFIRMED** (Kitengela, Kajiado + environs).
- **§0 UI language — CONFIRMED: English & Swahili.**
- **§0 Zone breakdown — DEFERRED**: founder will supply later; treated as a
  configuration/data update to the existing architecture, **not** a blocker for
  Phase 1 development.
- **§2–§7 the six operating policies — APPROVED by the founder as written.** Now
  CONFIRMED in [decisions.md](decisions.md) and propagated to the referenced
  documents.
- **§1 Brand — DECIDED: `Fikisha`** ("deliver / get it there"). `Mzigo` was
  rejected; `Fikisha` chosen from the round-2 shortlist. Recorded as D-BRAND-1.
  Remaining: BRS name reservation + KIPI trade-mark + domains/handles.
- **Legal (`legal-scope.md`) — retained as-is; founder is engaging a lawyer.**

Related new document: [legal-scope.md](legal-scope.md) (full regulatory map and
pre-pilot legal checklist). Brand analysis: [brand-name.md](brand-name.md).

---

## 0. Pilot area — CONFIRMED by founder

**Kitengela, Kajiado County**, serving Kitengela town and its environs
(Namanga-road corridor, Athi River / Mavoko boundary, Isinya, Kisaju, Kaputiei,
and links to Nairobi's Industrial Area / CBD).

Actions taken: recorded in [decisions.md](decisions.md) (D-O-AREA-1 → CONFIRMED),
[pilot-strategy.md](pilot-strategy.md), and [legal-scope.md](legal-scope.md)
(Kajiado County Single Business Permit added to the pre-pilot checklist).

**Still needed from founder:** the specific **zone breakdown** to seed
`PlatformConfig.zones` (a short list, e.g. *Kitengela Central / Milimani /
EPZ–Export / Athi River / Isinya / Kisaju / Nairobi-IndustrialArea*), and the
**working language** for the UI (recommend **English + Swahili** labels, Swahili
primary for operator-facing screens).

---

## 1. Brand name

**DECIDED: `Fikisha`** (founder, 2026-09-08) — Swahili "deliver / get it there".
`Mzigo` was rejected; `Fikisha` was chosen from the round-2 shortlist (`Tuma`,
`Fikisha`, `Relay`, `Boma`, `Njia` — see [brand-name.md](brand-name.md)).
Recorded as **D-BRAND-1**. "Logistix" may remain a legal-entity/holding name.
Remaining (not a Phase 1 blocker): **BRS name reservation** + **KIPI trade-mark
search/application** (Nice classes 39, 42, 35) + `fikisha.co.ke`/`.com` +
handles + an informal-use check in Kajiado.

---

## 2. Commission

| Parameter | Recommendation (pilot default; all configurable) |
|-----------|--------------------------------------------------|
| **Who pays** | **Operator pays**, shown transparently as a line item in the earnings breakdown (`agreed price − commission = your payout`). Supply is your controlled network; simplest to align during a pilot; matches what operators already understand from boda/ride-hailing. |
| **Headline rate** | **10%** of the agreed price. |
| **Minimum fee** | **KES 40** per completed job (so a small motorcycle parcel still covers messaging + processing cost). |
| **Large-job taper** | 10% up to KES 50,000; **5%** on the portion KES 50,001–150,000; **3%** above KES 150,000. Equivalent simple alternative: flat 10% but **cap absolute commission at KES 5,000** for the pilot. |
| **Introductory period** | **0% for the first 4 weeks**, then **5% for weeks 5–8**, then 10%. Drives onboarding; the zero weeks still generate the data. |
| **Collection** | **Weekly statement per operator**, settled by M-Pesa to a **merchant paybill**. The platform never holds the fare (business pays operator directly). Design the ledger so point-of-completion collection can be added later. |
| **Invoicing** | Commission statements must be **eTIMS-compliant** (KRA validates returns against eTIMS from Jan 2026). |
| **Disputed jobs** | Commission status **held** until resolution decides apply / reduce / waive. |
| **Cancelled / failed jobs** | **No commission.** |

**Why 10%:** comfortably below the 18% figure the government tried (and a court
recently suspended) to impose on ride-hailing, and well below the 25–30% that
triggered driver protests there. It leaves headroom to add a small business-side
fee later without the total looking extractive.

**Legal note:** collecting only your own commission via a merchant paybill is
designed to stay **outside CBK payment-service-provider licensing** — but this
**requires validation** (see legal-scope.md §3.6). Do **not** move to holding or
escrowing the fare without CBK advice.

**Confirm:** who pays; the 10% headline; the minimum fee; taper vs. flat+cap;
whether to run the introductory 0%→5%→10% ramp.

---

## 3. Trust thresholds and value bands

### 3a. Declared-cargo-value bands (the primary gate)

| Band | Declared cargo value (KES) | Min operator trust level | Extra safeguards |
|------|---------------------------|--------------------------|------------------|
| **Standard** | ≤ 50,000 | L1 Verified | Standard proof of pickup/delivery |
| **Elevated** | 50,001 – 250,000 | L2 Established | Recipient **OTP mandatory**; **photo POD mandatory**; pickup-side OTP mandatory (no operator-attested fallback) |
| **High** | 250,001 – 1,000,000 | L3 Trusted | **Admin pre-assignment review**; operator insurance (goods-in-transit / carrier's liability) re-checked current; two contacts on file |
| **Very high** | > 1,000,000 | L3 Trusted **+ per-job founder/admin approval** | Case-by-case; consider requiring the **business** to arrange its own goods-in-transit cover; possible in-transit check-in |

`high_value_threshold` (the point where admin review kicks in) = **KES 250,000**.

### 3b. Operator trust levels (entry criteria — pilot starting values, all configurable, all admin-confirmed)

| Level | Name | Criteria | Value ceiling |
|-------|------|----------|---------------|
| **L0** | Pending | Registered; verification incomplete | Cannot accept jobs |
| **L1** | Verified | Identity + licence (correct class) + ≥1 verified vehicle + verified base. **0 completed jobs is fine.** | Standard (≤ KES 50,000) |
| **L2** | Established | ≥ **8** completed jobs · ≥ **14 days** active · average rating ≥ **4.2/5** · **no unresolved** incident · ≤ **1** at-fault incident in the last 20 jobs · admin confirms | Elevated (≤ KES 250,000) |
| **L3** | Trusted | ≥ **30** completed jobs · ≥ **60 days** active · average rating ≥ **4.5/5** · **0** unresolved or unremediated at-fault *serious* incidents (loss / damage / misconduct) · ≥ **3** Elevated-band jobs completed cleanly · admin confirms | High (≤ KES 1,000,000); Very high only with per-job approval |
| **Restricted** | — | Admin-imposed after an at-fault serious incident, or average rating < **3.5** over the last 10 jobs. Remediation plan required to exit. | Standard or zero |

Rationale: numbers are deliberately modest so a diligent operator can reach L2
within the pilot; L3 will be a small group by pilot end, which is fine because
high-value jobs will be rare early and route through founder approval anyway.
Progression is **auto-proposed, admin-confirmed** (guards against gaming a thin
early dataset).

**Also require (from legal-scope.md §3.3):** a **DCI Certificate of Good
Conduct** for all operators, **mandatory before L2** (Elevated+); and for
canter/lorry/tipper/semi-truck/trailer operators, proof of **NTSA commercial
service vehicle operator licence + speed limiter + telematics + inspection +
insurance** as part of vehicle verification.

**Confirm:** the four band boundaries (50k / 250k / 1M); the L2 and L3 job-count
/ days / rating thresholds; that Certificate of Good Conduct is mandatory before
Elevated.

---

## 4. Cancellation policy

**Recommendation: reputation-only for the pilot — no fees — with structured
reason capture and an escalating-consequence ladder.**

| When cancelled | Consequence |
|----------------|-------------|
| Before **ASSIGNED** | None (normal marketplace behaviour). |
| After **ASSIGNED**, before **AT_PICKUP** | Recorded as a **late cancellation** on the canceller's record. |
| After **AT_PICKUP**, before custody confirmed | Recorded as a **wasted-trip** event on the canceller's record. |

Ladder (configurable):
- **Operator:** 3 late cancellations or wasted-trips in a rolling 30 days (or last
  20 jobs) → automatic **admin-review flag**; blocks L2 progression; repeat →
  **Restricted**.
- **Business:** 3 late cancellations in a rolling 30 days → **admin-review flag**;
  repeat → standing drops **GOOD → RESTRICTED** (reduced visibility; needs admin
  clearance to post new jobs).

A **configurable wasted-trip courtesy fee** (default **off**; suggested KES
100–300 payable by the canceller, recorded like commission) is **built but not
enabled** — turn on only if pilot data shows abuse.

Rationale: matches existing amicable practice, avoids money-movement and
fee-disputes during the pilot, and still deters abuse through the trust
consequences operators actually care about.

**Confirm:** reputation-only (yes/no); the "3 in 30 days" trigger; keep the
courtesy fee built-but-off.

---

## 5. Dispute-window length

Two distinct windows:

| Window | Recommendation |
|--------|----------------|
| **Delivery-acceptance** (DELIVERED → auto-COMPLETED if no objection) | **24 hours** for Standard & Elevated bands; **48 hours** for High & Very-high bands. |
| **Post-completion dispute** (COMPLETED → DISPUTED allowed for latent damage / shortage) | **72 hours** from COMPLETED for all bands; **7 days** for High & Very-high bands and for cargo categories flagged latent-risk (electronics, packaged goods, perishables). After the window: an incident can still be **recorded** for reputation/audit but does **not** reopen job state or commission. |

Both configurable. Keeps operator payout and commission timely while giving
businesses a real chance to inspect.

**Confirm:** 24h / 48h acceptance; 72h / 7d post-completion.

---

## 6. Proof-of-pickup responsibility

**Recommendation: pickup-side confirmation is mandatory; operator
self-declaration alone is not sufficient.**

- The person **releasing the goods** at pickup (the business's on-site contact
  named on the job, or the ad-hoc pickup contact) confirms handover via **OTP to
  their phone** — primary method.
- **Standard band only** fallback if OTP can't be delivered/entered: the operator
  captures a **photo of the goods at pickup + the pickup contact's name**; the
  custody entry is marked **"operator-attested, unverified"**, is shown as such
  to the business and admin, and **caps that job at the Standard band** unless the
  business later confirms in-app.
- **Elevated band and above:** pickup-side OTP (or in-app confirmation by the
  business user) is **required** — no operator-attested fallback.
- Every pickup event records server timestamp, actor, geolocation where
  available, method, and any condition note/photos.

Symmetry: delivery already uses recipient-side OTP / signature / photo.

Rationale: anchors the chain of custody at **both** ends and prevents
"operator says they picked up" disputes, while degrading gracefully so a rigid
OTP gate doesn't block low-value everyday work.

**Confirm:** mandatory pickup-side OTP; the Standard-band-only photo fallback;
no fallback at Elevated+.

---

## 7. Admin role structure

**Recommendation: start with 2 roles for the pilot; define the 4-role split in
config for later.**

| Pilot role | Who | Can | Cannot |
|------------|-----|-----|--------|
| **Platform Admin** | Founder | Everything: platform config (commission, thresholds, timeouts), verification decisions, account suspension/offboarding, dispute resolution (binding, all bands), job intervention, manage other admins | — |
| **Operations Officer** | Ops staff | Process the verification queue; monitor active jobs; intervene in jobs (reassign / cancel / contact parties); incident intake; **facilitate** amicable resolution; propose trust-level changes | Change platform config; suspend/offboard accounts; issue a **binding** dispute resolution above Standard band (those route to Platform Admin) |

Defined now, enabled by config when volume/staffing grow: split Operations into
**Verifier**, **Operations**, **Dispute Officer**, keeping **Platform Admin** as
superuser. The role→permission mapping lives in `PlatformConfig` so enabling the
finer split is a configuration change, not a rebuild.

Non-negotiable regardless of role count:
- **Every admin action is audit-logged** with actor + reason + before/after —
  **including the founder's** (no silent superuser).
- Access to raw PII / documents (IDs, licences, payout numbers) is limited to the
  **verification permission** and is **itself logged**.
- **MFA mandatory** on all admin accounts.

**Confirm:** 2 roles for the pilot with the split defined for later; founder
actions are logged like everyone's.

---

## 8. What still needs the founder after this memo

1. Pick/confirm the **brand** (§1) and authorise the BRS + KIPI steps.
2. Confirm the **six policy decisions** (§2–§7), or adjust the numbers.
3. Provide the **zone list** and **UI language** choice (§0).
4. Authorise engaging a **Kenyan advocate + tax advisor + insurance broker** and
   work through [legal-scope.md](legal-scope.md) §9 — this runs in parallel with
   Phase 1 build and **gates pilot go-live**.
5. Set the **pilot kill / iterate / scale** targets (still open — see
   [pilot-strategy.md](pilot-strategy.md) §6).
