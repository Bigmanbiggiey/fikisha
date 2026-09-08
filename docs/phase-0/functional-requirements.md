# Functional Requirements

Scope: the MVP for the local pilot. Each requirement has an ID (`FR-<area>-<n>`),
a priority (**MUST** / **SHOULD** / **MAY** for MVP), and, where relevant, a
pointer to the document that expands on it.

Priorities:
- **MUST** — MVP is not complete without it.
- **SHOULD** — strongly wanted for the pilot; may be simplified if time-boxed.
- **MAY** — nice to have during the pilot; safe to defer.

Open questions and legal-validation items are not repeated exhaustively here;
see the referenced documents and [decisions.md](decisions.md).

> **Founder-approved parameters (2026-09-08) that make several FRs concrete —
> full detail in [decisions.md](decisions.md) D-BIZ-4…7, D-TRU-5…7, D-DIS-3,
> D-JOB-5, D-CUS-2, D-ADM-1 and [decision-memo-2026-09-08.md](decision-memo-2026-09-08.md):**
> - **Commission** (FR-M-1): operator pays; 10% headline, KES 40 min, taper
>   10/5/3% (or flat 10% capped KES 5,000), optional 0→5→10% intro ramp; weekly
>   M-Pesa statement + eTIMS invoices; platform never holds the fare.
> - **Trust & value bands** (FR-T-1/2/5, FR-J-6): Standard ≤ KES 50k → L1;
>   Elevated ≤ 250k → L2; High ≤ 1M → L3; > 1M → L3 + per-job approval.
>   `high_value_threshold` = KES 250k. L2 = 8 jobs / 14 days / 4.2★; L3 = 30 jobs
>   / 60 days / 4.5★ / 3 clean Elevated. Certificate of Good Conduct before
>   Elevated. Progression auto-proposed, admin-confirmed.
> - **Cancellation** (FR-J-13, FR-R-5): reputation-only; "3 in rolling 30 days"
>   → auto admin-review flag; courtesy fee built, default-off.
> - **Windows** (FR-J-11/12): delivery-acceptance auto-complete 24h
>   Standard/Elevated, 48h High+; post-completion dispute 72h all bands, 7 days
>   High+ and latent-risk cargo.
> - **Proof of pickup** (FR-C-3): mandatory pickup-side OTP; operator-attested
>   photo fallback Standard band only (caps job at Standard); no fallback at
>   Elevated+.
> - **Admin roles** (FR-ADM-8): 2 for the pilot (Platform Admin + Operations
>   Officer); 4-role split in `PlatformConfig` for later; all admin actions incl.
>   founder's logged; admin MFA.
> - **UI languages**: English & Swahili.
> - **Zones** (FR-O-3, FR-J-6): Kitengela zone list deferred by founder — treat
>   the pilot area as one zone until supplied; adding zones is config.
>
> **Further founder decisions 2026-09-08 (D-CLIENT-1, D-NOTIF-1, D-OPR-GRP-1,
> D-RCP-1):**
> - **Client**: a responsive **Progressive Web App** (installable, offline-tolerant
>   custody steps, camera for photos/POD); no native app-store builds for MVP.
> - **Notifications** (FR-NOTIF-*): channels are **in-app + SMS + WhatsApp**
>   (WhatsApp Business Platform via a BSP); OTP stays **SMS-primary**; WhatsApp
>   failure falls back to SMS.
> - **Operator groups** (FR-O-6, FR-J-*): **in scope, minimal** — group profile +
>   `GroupMembership(OWNER/MANAGER/DRIVER)` + group-owned vehicles; every driver
>   and vehicle individually verified; a group job names a specific driver +
>   vehicle at ASSIGNED; value-band gating uses the assigned driver's trust
>   level; commission statement to the group. No payroll/scheduling/transfers.
> - **Recipient link** (FR-C-*, FR-D-2): **no account** — a scoped, time-limited,
>   single-job link lets the recipient view their delivery, confirm receipt
>   (name + OTP/signature/photo), and raise an incident; link expires after the
>   post-completion dispute window.

---

## FR-A — Accounts, authentication, profiles

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-A-1 | MUST | A user can register a **Business** account using a phone number; identity of the account is the phone number, verified by OTP. |
| FR-A-2 | MUST | A user can register a **Transport Operator** account using a phone number, verified by OTP. |
| FR-A-3 | MUST | **Administrator** accounts are provisioned internally (not self-service) and require stronger authentication than OTP alone (see NFR). |
| FR-A-4 | MUST | A Business can maintain a profile: trading name, contact person(s), phone, email (optional), business category; optional registration identifiers. |
| FR-A-5 | MUST | An Operator can maintain a profile: full name, photo, contact numbers, and the verification/vehicle/base data in FR-V / FR-O. |
| FR-A-6 | SHOULD | A Business account can have multiple users with roles (owner, dispatcher, viewer). MAY be reduced to a single user for MVP. |
| FR-A-7 | MUST | A user may hold both a Business and an Operator profile; they are separate profiles with separate verification. The same party cannot be requester and assigned operator on one job. |
| FR-A-8 | MUST | Session management: login, logout, session expiry; OTP resend with rate limiting. |
| FR-A-9 | SHOULD | Account recovery via the registered phone number. |
| FR-A-10 | MUST | The UI is available in **English and Swahili** (D-PIL-4), with a per-user language choice; Swahili is prominent on operator-facing screens. Transactional SMS content is available in both languages. |

## FR-B — Business locations

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-B-1 | MUST | A Business can add multiple locations, each with: label, type (MAIN / BRANCH / WAREHOUSE / STORE / PICKUP_POINT), address text, geo-coordinates, on-site contact + phone, operating hours, access notes. |
| FR-B-2 | MUST | A Business can designate exactly one location as the **main operating location**. |
| FR-B-3 | MUST | A Business can edit or deactivate a location. Locations referenced by historical jobs are retained (soft delete). |
| FR-B-4 | SHOULD | At least one confirmed location is required before the Business can publish a job. |

## FR-V — Verification

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-V-1 | MUST | The system stores per-domain `VerificationRecord`s for: identity, licence, vehicle, vehicle↔operator association, operating base, supporting documents. | trust-and-safety.md |
| FR-V-2 | MUST | Verification states: NOT_SUBMITTED, SUBMITTED, IN_REVIEW, INFO_REQUESTED, VERIFIED, REJECTED, EXPIRED. | |
| FR-V-3 | MUST | Operators upload required documents/images per domain; uploads are stored encrypted and access-controlled. | NFR |
| FR-V-4 | MUST | Administrators (Verifier sub-role) work a review queue: approve, reject (with reason), request more info; set expiry dates. | |
| FR-V-5 | MUST | Document expiry automatically moves the affected record to EXPIRED and applies the corresponding capability restriction (e.g. expired vehicle insurance → vehicle ineligible; expired licence → operator ineligible). | |
| FR-V-6 | MUST | A Business is marked verified/unverified by an administrator after a lightweight check (real business, ≥1 confirmed location). | |
| FR-V-7 | SHOULD | The system flags records nearing expiry (configurable lead time) to operator and admin. |
| FR-V-8 | MAY | Automated assist checks (e.g. document image quality, basic format validation) before human review. |

## FR-O — Operator profile: vehicles, bases, service areas, availability

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-O-1 | MUST | An Operator can register one or more **vehicles**: type (from a configurable set seeded with MOTORCYCLE, PICKUP, CANTER, TIPPER, LORRY, SEMI_TRUCK, TRAILER, OTHER), optional sub-descriptor, registration/plate, payload weight capacity, load dimensions/volume where relevant, feature tags, documents, ownership/association. | operator-model.md |
| FR-O-2 | MUST | An Operator can register one or more **operating bases**: type (STAGE / BASE / YARD / WAITING_AREA), name, geo-coordinates, area/zone, optional landmark/photo. | |
| FR-O-3 | MUST | An Operator can declare **service areas** as a set of named zones plus an optional maximum distance from a base. | |
| FR-O-4 | MUST | An Operator can set **availability**: AVAILABLE / BUSY / UNAVAILABLE. BUSY is set automatically while on an active job. | |
| FR-O-5 | SHOULD | An Operator can mark a vehicle active / inactive / under-repair. |
| FR-O-6 | MUST | **Operator group** support (D-OPR-GRP-1): create a group (name, type YARD_OWNER/FLEET/SACCO/PARTNERSHIP, primary-contact user, base(s), payout details); add members via `GroupMembership(role: OWNER/MANAGER/DRIVER)`; register **group-owned vehicles**. Each member driver and each group vehicle goes through the **same individual verification** as a solo operator (identity, licence class, Certificate of Good Conduct, vehicle docs, heavy-class NTSA items). | operator-model.md |
| FR-O-7 | MUST | A job assigned to a group **must name a specific driver + specific vehicle** at ASSIGNED (manager assigns, or an authorised group driver accepts per a per-group setting). Value-band eligibility (FR-T-5) is evaluated against the **assigned driver's** trust level; the group's aggregate standing can independently restrict/suspend the group. | operator-model.md |
| FR-O-8 | MUST | The commission statement (FR-M-4) for a group job is issued to the **group**; the platform does not handle internal driver settlement in MVP. Ratings (FR-R-1) attach to **both** the assigned driver and the group. |
| FR-O-9 | — | Out of MVP scope for groups: internal payroll, shift scheduling, inter-group driver/vehicle transfers. |

## FR-T — Trust levels

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-T-1 | MUST | The system maintains an operator **trust level** with at least: Pending(0), Verified(1), Established(2), Trusted(3), plus Restricted. | trust-and-safety.md |
| FR-T-2 | MUST | Each trust level has a configurable **job-value ceiling** and configurable **entry criteria**. Pilot values (D-TRU-5/6): ceilings **Standard KES 50k / Elevated 250k / High 1M / Very-high > 1M (+ per-job approval)**; L2 = **8 jobs · 14 days · 4.2★ · ≤1 at-fault/20**; L3 = **30 jobs · 60 days · 4.5★ · 0 unremediated serious · 3 clean Elevated**; Restricted at **< 3.5★/10 jobs** or an at-fault serious incident. |
| FR-T-3 | MUST | The system proposes trust-level progression automatically when criteria are met; an administrator confirms it for MVP. |
| FR-T-4 | MUST | Serious or repeated confirmed fault can trigger administrator-applied regression or Restricted status, with a recorded reason. |
| FR-T-5 | MUST | A job whose declared value (and/or agreed price) exceeds the configurable **high-value threshold (pilot: KES 250,000)** is **high-value** and requires: operator trust level ≥ configured minimum (**L3**), current verification incl. re-checked goods-in-transit/carrier's cover, two contacts on file, and **administrator pre-assignment review/approval**. Jobs > KES 1,000,000 additionally require **per-job founder/admin approval**. |
| FR-T-6 | MUST | Operator eligibility requires a valid **DCI Certificate of Good Conduct**; it is **mandatory before L2 / Elevated-band** access. For heavy vehicle classes, vehicle verification additionally requires proof of NTSA commercial-service-vehicle operator licence + speed limiter + telematics + inspection + insurance (exact list pending legal validation — see legal-scope.md §3.3). |

## FR-J — Jobs: creation, discovery, lifecycle

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-J-1 | MUST | A Business can create a **Job** in DRAFT with: pickup location (own location or ad-hoc), destination (address + geo + recipient name + phone), cargo description, cargo category (configurable set), estimated weight, dimensions (optional), declared value, required vehicle type, required capacity, pickup date/time, delivery requirements/notes, proposed price. | domain-model.md |
| FR-J-2 | MUST | A Business can publish a Job (DRAFT → REQUESTED) only when required fields are present. |
| FR-J-3 | MUST | Job status is implemented as a **finite state machine**; only transitions in the allowed set (job-lifecycle.md §2) are permitted; a disallowed `(from,to)` request is rejected with no side effects. | job-lifecycle.md |
| FR-J-4 | MUST | Every successful transition appends an audit entry (actor, timestamp, from, to, reason). Custody-relevant transitions also append a chain-of-custody entry. |
| FR-J-5 | MUST | Concurrent transition attempts are serialised (version check); the job cannot branch. |
| FR-J-6 | MUST | An **Operator** sees a Job in discovery only if: they have a verified vehicle matching required type AND capacity; the pickup is within/near a declared service area or base distance; their trust level meets the job's requirement; they are not suspended and identity+licence are current. | operator-model.md |
| FR-J-7 | MUST | Discovery is a browsable, filterable list. Ranking signals (base proximity, reputation, responsiveness, availability) order it but do not hard-filter beyond FR-J-6. |
| FR-J-8 | MUST | A Business can view its jobs by status: active (with live status + chain of custody), completed (with delivery records / proof of delivery), and cancelled/failed. |
| FR-J-9 | MUST | An Operator can view assigned/active jobs and full job history with earnings. |
| FR-J-10 | MUST | A Business, an Operator (own jobs), and Administrators can each view the full chain of custody for a job. |
| FR-J-11 | SHOULD | Configurable timeouts drive automatic transitions/alerts: request expiry → FAILED; **delivery-acceptance window → COMPLETED (24h Standard/Elevated, 48h High/Very-high)**; stale-assignment alert to admin. | job-lifecycle.md §5 |
| FR-J-12 | SHOULD | A configurable **post-completion dispute window (72h all bands; 7 days High/Very-high & latent-risk cargo)** permits COMPLETED → DISPUTED. |
| FR-J-13 | MUST | Cancellation is permitted only from allowed states and by allowed parties; the reason is recorded. |

## FR-N — Negotiation

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-N-1 | MUST | Business and Operator can each **propose**, **counter-offer**, **accept**, and **reject** a price. | pricing-and-negotiation.md |
| FR-N-2 | MUST | Each action creates an **immutable, append-only `NegotiationEntry`** (actor, role, type, amount, currency KES, note, timestamp, in_response_to, thread_id, status). Entries are never edited or deleted. |
| FR-N-3 | MUST | Multiple operators may negotiate the same job in parallel, each in a separate **sealed thread**; operators cannot see each other's offers. |
| FR-N-4 | MUST | A Job becomes **CONFIRMED** only on mutual acceptance in one thread; on confirmation all other threads for that job are closed (SUPERSEDED). |
| FR-N-5 | MUST | On confirmation the system creates an **Agreement** recording the frozen agreed price, currency, operator, the accepting entry ids from both sides, timestamp, and terms note. |
| FR-N-6 | MUST | If two acceptances race, the server serialises them; the first succeeds, the second is told the job is no longer available. |
| FR-N-7 | SHOULD | Offers expire after a configurable time (does not change job state). |
| FR-N-8 | SHOULD | Basic sanity validation: reject non-positive amounts; warn (non-blocking) on likely mistyped values and on price far below a very high declared value. |
| FR-N-9 | MAY | Configurable non-binding soft ceiling/floor per vehicle class, shown as a warning only. |
| FR-N-10 | MUST | The MVP does **not** enforce or auto-set prices, and does **not** show historical "recommended ranges". |

## FR-C — Chain of custody, pickup, delivery, proof

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-C-1 | MUST | On ASSIGNED, the system records the specific operator (for a group job, the specific **assigned driver** and, where relevant, the group) and the specific vehicle. | trust-and-safety.md §4 |
| FR-C-2 | MUST | The operator can mark **arrival at pickup** (AT_PICKUP): server timestamp, actor, location captured where available/permitted, else named location / "not captured". |
| FR-C-3 | MUST | **Custody confirmation** (AT_PICKUP → PICKED_UP) requires a proof-of-pickup: **mandatory pickup-side OTP** to the person releasing the goods (D-CUS-2). *Standard band only* fallback where OTP fails: operator photo of goods + pickup-contact name → entry flagged "operator-attested, unverified", job capped at Standard band unless the business later confirms in-app. **Elevated band and above: pickup-side OTP (or in-app business confirmation) required, no fallback.** Optional cargo-condition note/photos. |
| FR-C-4 | MUST | The operator can mark **in transit**, **arrival at destination**, each with timestamp/actor/location. |
| FR-C-5 | MUST | **Delivery** (AT_DESTINATION → DELIVERED) requires recipient verification: recipient name plus one or more of OTP (to the recipient phone), signature capture, photo at handover. |
| FR-C-5a | MUST | The recipient can complete this verification themselves through a **scoped, time-limited, single-job link** (SMS/WhatsApp) that requires **no account** (D-RCP-1). The link exposes only that delivery's status; it expires after the post-completion dispute window; recipient short terms are shown on it. |
| FR-C-6 | MUST | All chain-of-custody entries are **append-only and immutable**; corrections are new entries with a reason. |
| FR-C-7 | MUST | Evidence media is stored with an integrity hash, encrypted at rest, access-controlled, and retained per the configured retention window. | NFR |
| FR-C-8 | SHOULD | The system shows a completeness indicator for a job's chain of custody (which steps have evidence). |
| FR-C-9 | MAY | Optional in-transit check-in prompt for high-value jobs. |

## FR-D — Incidents and disputes

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-D-1 | MUST | Any involved party (Business, Operator) and any Administrator can open an **Incident** against a job with: type (DAMAGE, LOSS, MISSING_GOODS, WRONG_RECIPIENT, WRONG_PICKUP, MISCONDUCT, BREAKDOWN, ACCIDENT, DELAY, CANCELLATION, OTHER), description, and initial evidence. | dispute-and-liability.md |
| FR-D-2 | MUST | A Recipient can open an incident (wrong recipient, damage, missing/short, wrong goods) via the per-job link **without an account** (D-RCP-1), attaching photos and a short statement; it enters the standard workflow and notifies business + operator + admin. |
| FR-D-3 | MUST | Opening an incident that blocks progression moves the job to DISPUTED (per allowed transitions). |
| FR-D-4 | MUST | Parties can upload **Evidence** (append-only) and submit **Statements** (append-only; further statements allowed, prior ones not editable). Relevant chain-of-custody entries are auto-attached. |
| FR-D-5 | MUST | The system presents both parties' positions and a structured **amicable-resolution** step; an agreed outcome is recorded as the Resolution. |
| FR-D-6 | MUST | If unresolved, a Dispute Officer performs **administrative review** and records a **Resolution**: outcome code, rationale, recorded financial adjustment (agreed compensation and/or commission waive/reduce), actions (rating impact, trust change, suspension), resolver, timestamp. |
| FR-D-7 | MUST | Resolution routes the job to COMPLETED / FAILED / CANCELLED; MAY resume to the pre-dispute state if an administrator determines the job can continue. |
| FR-D-8 | MUST | Critical incidents (accident/injury, theft, fraud) and unresolved disputes can be **escalated** to the founder; the system records that parties were advised of external options. |
| FR-D-9 | SHOULD | Per-incident-type evidence checklists prompt the reporter for the right materials. |
| FR-D-10 | MUST | The MVP does not process forced refunds/payouts between parties; it records adjustments and adjusts its own commission only. |

## FR-R — Ratings and reputation

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-R-1 | MUST | After COMPLETED, Business and Operator can each rate the other (score + optional dimensions + comment), within a configurable window. |
| FR-R-2 | MUST | Ratings can be submitted only for jobs that reached COMPLETED. |
| FR-R-3 | MUST | An operator reputation summary (average rating, completed-job count, incident summary) is available to Businesses during discovery/negotiation; raw identity data is not. |
| FR-R-4 | MUST | Reputation feeds trust-level assessment (FR-T-3). |
| FR-R-5 | SHOULD | Bad-faith reports / non-payment are recorded and can restrict the offending party. |

## FR-M — Commission and money recording

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-M-1 | MUST | On COMPLETED, the system computes commission from the agreed price using the configurable rate structure — **pilot default: 10% headline, KES 40 minimum, taper 10% ≤50k / 5% 50k–150k / 3% >150k (or flat 10% capped KES 5,000), optional intro ramp 0%→5%→10%** — with **party liable = OPERATOR**, and records a **CommissionRecord** (job, gross, rate, amount, party liable, status PENDING/DUE/SETTLED/WAIVED/REDUCED). Commission on DISPUTED jobs is held until resolution; CANCELLED/FAILED jobs incur none. | business-model.md |
| FR-M-2 | MUST | The system records each party's report/confirmation that the transport payment was made directly between them (no funds held by the platform). |
| FR-M-3 | MUST | For jobs in DISPUTED, commission status is held until resolution decides apply/reduce/waive. |
| FR-M-4 | MUST | The system generates a **weekly per-operator commission statement**, settled by M-Pesa to a merchant paybill; statements/invoices are **eTIMS-compliant** (see legal-scope.md §3.2). The platform never holds the transport fare. |
| FR-M-5 | MUST | Jobs ending CANCELLED/FAILED incur no commission (a configurable cancellation fee is out of scope unless the founder enables it). |
| FR-M-6 | MAY | Prepaid commission-credit balance per operator. |

## FR-ADM — Administration and configuration

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-ADM-1 | MUST | Administrators can review businesses, operators, and vehicles, and act on verification (FR-V). | users-and-roles.md |
| FR-ADM-2 | MUST | Administrators can monitor active jobs (list, filter, drill into chain of custody) and intervene: reassign, cancel, force an allowed transition, contact parties — each logged with actor + reason + before/after. |
| FR-ADM-3 | MUST | Administrators can manage incidents/disputes (FR-D). |
| FR-ADM-4 | MUST | Administrators can suspend / restrict / offboard accounts with reason and duration. |
| FR-ADM-5 | MUST | Administrators can review the audit log (filter by actor, entity, action, time). |
| FR-ADM-6 | MUST | Administrators (Platform Admin sub-role) can configure platform rules: commission rate/bands/floor and party liable; high-value threshold; trust-level criteria and value ceilings; allowed vehicle types; cargo categories; pilot-area zones; cancellation policy; timeout values; data-retention windows. |
| FR-ADM-7 | MUST | All configuration changes are versioned with actor, timestamp, and rationale. |
| FR-ADM-8 | MUST | Admin permissions are a **role→permission map in `PlatformConfig`**. **Pilot: 2 roles active** — Platform Admin (all powers) and Operations Officer (verification queue, job monitoring/intervention, incident intake, facilitates amicable resolution, proposes trust changes; cannot change config, suspend/offboard accounts, or issue binding dispute resolutions above Standard band). The 4-role split (Verifier / Operations / Dispute Officer / Platform Admin) is enabled later by configuration. |
| FR-ADM-9 | MUST | **Every admin action — including the Platform Admin's / founder's — is audit-logged** with actor, reason, and before/after. Access to raw PII / document images is limited to the verification permission and each access is logged. |

## FR-DASH — Operational dashboard and data export

| ID | Priority | Requirement | Ref |
|----|----------|-------------|-----|
| FR-DASH-1 | MUST | A founder/admin dashboard shows: live job list and funnel (created → confirmed → assigned → delivered → completed), incident queue with SLA status, and the weekly pilot metrics. | pilot-strategy.md §4 |
| FR-DASH-2 | MUST | Every job records per-transition timestamps, distances, weights, prices, actors, and outcome sufficient to compute all pilot metrics without manual bookkeeping. |
| FR-DASH-3 | MUST | Access-controlled data export (CSV or equivalent) of jobs, negotiations (amounts + timestamps), incidents, and cost counters, using minimum necessary personal data. |
| FR-DASH-4 | SHOULD | Per-job cost counters for external API usage (SMS/WhatsApp, geocoding) where attributable. |

## FR-NOTIF — Notifications

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-NOTIF-1 | MUST | Relevant parties are notified on key job events (published to eligible operators, new offer/counter, confirmed, assigned, arrival/custody/delivery, incident opened/updated/resolved, verification outcome). |
| FR-NOTIF-2 | MUST | Channels for MVP: **in-app + SMS + WhatsApp** (D-NOTIF-1). |
| FR-NOTIF-3 | MUST | WhatsApp notifications via the **WhatsApp Business Platform** through an authorised BSP (approved message templates), carrying job-event notifications and the recipient link. **WhatsApp delivery failure falls back to SMS.** Data sent to WhatsApp/Meta is a cross-border transfer and is covered in the DPA + Privacy Notice. |
| FR-NOTIF-4 | MUST | OTP delivery for auth, pickup handover, and recipient verification **via SMS (primary)**; WhatsApp may additionally carry OTP but SMS remains the reliable default. |
| FR-NOTIF-5 | SHOULD | Per-user notification preferences and quiet hours. |

---

## Traceability

| Brief requirement | Covered by |
|-------------------|-----------|
| Business: account, profile, multiple pickup locations, main + secondary locations | FR-A-1/4, FR-B-1/2 |
| Business: create jobs, cargo info, destination, declared value, vehicle requirements, propose price | FR-J-1 |
| Business: negotiate, confirm, track active, view completed, delivery records, disputes | FR-N-1, FR-J-2/8, FR-C-*, FR-D-* |
| Operator: account, identity, licence, register vehicles, type/capacity, base/stage, service areas, availability | FR-A-2, FR-V-1/3, FR-O-1/2/3/4 |
| Operator: discover jobs, propose/counter/accept/reject | FR-J-6/7, FR-N-1 |
| Operator: pickup, confirm custody, update status, complete delivery, proof of delivery | FR-C-2/3/4/5 |
| Operator: earnings, history, trust/reputation history | FR-J-9, FR-M-1, FR-R-3/4, FR-T-1 |
| Admin: review businesses/operators/vehicles, verification, monitor, intervene, disputes, suspend, audit, configure, monitor performance | FR-ADM-*, FR-DASH-* |
| JOB object fields | FR-J-1, domain-model.md |
| Price negotiation both ways, history preserved, agreed price | FR-N-1..N-6, N-10 |
| Job lifecycle states + enforced transitions | FR-J-3/4/5, job-lifecycle.md |
| VERIFIED vs TRUSTED, progressive trust, high-value safeguards | FR-V-*, FR-T-* |
| Chain of custody, timestamps/actors/locations/confirmations/evidence, retention | FR-C-*, NFR |
| Incidents (all listed types), evidence, statements, admin review, resolution, escalation | FR-D-* |
| Revenue: configurable commission on successful jobs | FR-M-1, FR-ADM-6 |
| Pilot: operational knowledge / metrics | FR-DASH-*, pilot-strategy.md |
| Security/privacy/authorization/auditability as first-class | FR-J-4, FR-ADM-5/7, FR-C-6/7, and non-functional-requirements.md |
