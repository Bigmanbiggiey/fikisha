# MVP Scope

The MVP exists to run a **local pilot** (see [pilot-strategy.md](pilot-strategy.md))
with the founder's existing operator network. Scope is deliberately narrow:
enough to run real jobs end to end, capture the chain of custody, handle
incidents, and produce operational data.

---

## 1. In scope

### 1.1 Accounts & onboarding
- Business account creation + profile + multiple locations (main + secondary).
- Operator account creation + identity + licence + vehicle(s) + operating
  base/stage + service areas + availability.
- Phone-number auth with OTP.
- Administrator accounts with role-based permissions.

### 1.2 Verification (administrator-driven)
- Per-domain verification records: identity, licence, vehicle, vehicle↔operator
  association, operating base, supporting documents.
- Verification states: not submitted / submitted / in review / verified /
  rejected / expired.
- Manual review queue for administrators, with request-more-info.

### 1.3 Trust levels
- At least three progressive operator trust levels, each with a job-value
  ceiling and eligibility criteria (see [trust-and-safety.md](trust-and-safety.md)).
- Automatic progression proposals based on completed-job history; administrator
  confirmation required for MVP.
- High-value jobs restricted by trust level + enhanced verification.

### 1.4 Jobs
- Create job with: requester, pickup location, destination, cargo description,
  cargo category, estimated weight, dimensions (optional), declared value,
  required vehicle type, required capacity, pickup date/time, delivery
  requirements, proposed price.
- Job lifecycle with **enforced state transitions** (see
  [job-lifecycle.md](job-lifecycle.md)).
- Job discovery for operators (filter by vehicle type/capacity, base proximity,
  service area, trust eligibility).

### 1.5 Negotiation
- Business and operator: propose / counter / accept / reject.
- Full negotiation history preserved and immutable.
- Job confirmed only on mutual agreement; agreed price recorded.

### 1.6 Assignment
- Operator + specific vehicle attached to a confirmed job.
- Administrator can reassign with reason.

### 1.7 Chain of custody
- Timestamped, actor-attributed events: assignment → arrival at pickup → custody
  confirmed → in transit → arrival at destination → recipient verification →
  delivery confirmed → completion.
- Location capture at custody-relevant events (**WORKING ASSUMPTION:** device
  geolocation where available; manual/stage fallback otherwise).
- Proof of delivery: recipient name + one or more of OTP / signature / photo.

### 1.8 Incidents & disputes
- Report incident (damage, loss, missing goods, wrong recipient, wrong pickup,
  misconduct, breakdown, accident, delay, cancellation, other).
- Evidence upload (photos, documents, notes).
- Statements from involved parties.
- Administrative review workflow: open → under review → resolved / escalated.
- Structured "amicable resolution first" step before escalation.

### 1.9 Ratings / reputation
- Post-completion two-way rating (business↔operator).
- Reputation summary contributes to trust-level assessment.

### 1.10 Money handling (minimal)
- **CONFIRMED (D-BIZ-4/6):** payment for the transport happens **directly
  between business and operator** (cash or their own transfer), matching current
  practice. The platform **records** the agreed price and marks the job's
  payment as reported/confirmed by each party. **The platform never holds the
  transport fare** (keeps it outside CBK PSP licensing — see
  [legal-scope.md](legal-scope.md) §3.6).
- **Commission** on completed jobs is **paid by the operator** and collected via
  a **weekly per-operator statement to a merchant M-Pesa paybill**, with
  **eTIMS-compliant** invoices. Rate: 10% headline, KES 40 minimum, taper
  10/5/3% (or flat 10% capped KES 5,000), optional 0→5→10% intro ramp. See
  [business-model.md](business-model.md).
- No escrow, no wallet, no in-app card processing in MVP. The ledger is designed
  so point-of-completion or prepaid-credit collection can be added later.

### 1.11 Notifications
- Job events to relevant parties. **CONFIRMED channels (D-NOTIF-1): in-app + SMS
  + WhatsApp** (WhatsApp Business Platform via an authorised BSP). WhatsApp
  carries job-event notifications and the recipient link; **OTP stays SMS-primary**
  (WhatsApp optional). WhatsApp delivery failure falls back to SMS. Data to
  WhatsApp/Meta is a cross-border transfer — covered in the DPA + Privacy Notice.

### 1.12 Client
- **CONFIRMED (D-CLIENT-1): a responsive Progressive Web App (PWA)** —
  installable, works on low-end Android, tolerant of intermittent connectivity
  for custody steps, with camera access for photos and proof of delivery. No
  native app-store builds for MVP.

### 1.13 Operator groups (minimal)
- **CONFIRMED IN SCOPE (D-OPR-GRP-1).** A group (yard/base owner, small fleet,
  SACCO, partnership) with a primary-contact user, operating base(s),
  group-owned vehicles, and members (`OWNER / MANAGER / DRIVER`). **Every member
  driver and every group vehicle is individually verified.** A job assigned to a
  group names a specific driver + vehicle at ASSIGNED; value-band gating uses the
  **assigned driver's** trust level; the group carries an aggregate standing.
  Commission statement goes to the group. **Out of MVP:** internal payroll, shift
  scheduling, inter-group transfers.

### 1.14 Recipient (consignee) link
- **CONFIRMED IN SCOPE (D-RCP-1).** No account. A scoped, time-limited,
  single-job link (SMS/WhatsApp) lets the recipient view their delivery's status,
  **confirm receipt** (name + OTP/signature/photo), and **raise an incident**
  (wrong recipient, damage, missing/short, wrong goods) with photos + a short
  statement into the standard incident workflow. Link expires after the
  post-completion dispute window; recipient short terms shown on the link.

### 1.15 Administration
- Verification queue, active-job monitor, intervention actions, dispute console,
  account suspension, platform configuration, audit-log viewer, basic
  operational dashboard.

### 1.16 Audit & security (first-class, not deferred)
- Immutable audit log of all state-changing actions.
- Role- and trust-based authorization on every action.
- Encryption of sensitive documents at rest; access-controlled retrieval.
- Data-retention configuration.

---

## 2. Explicitly OUT of scope for MVP

These are recorded here so exclusion is a decision, not an omission. Several
appear in [future-roadmap.md](future-roadmap.md).

| Excluded from MVP | Why | Category |
|-------------------|-----|----------|
| Platform-held escrow / in-app wallet / card & mobile-money processing at scale | Regulatory and operational weight; current practice is direct payment | FUTURE CONSIDERATION (pilot to inform) |
| Enforced or fixed pricing / automated tariffs | Founder principle: negotiation stays during MVP | FUTURE CONSIDERATION |
| Recommended price ranges from historical data | Needs data the pilot will generate | FUTURE CONSIDERATION |
| Live GPS tracking / telematics / route optimization | Heavy; checkpoint-based custody is enough to learn from | FUTURE CONSIDERATION |
| Automated matching / auto-assign / bidding auctions | Learn manual + filtered discovery first | FUTURE CONSIDERATION |
| Business subscriptions, enterprise contracts, fleet management, analytics products, public API | Founder rule: no future revenue models in MVP without approval | FUTURE CONSIDERATION |
| Multi-area / multi-city operation | Pilot is one local area | FUTURE CONSIDERATION |
| Insurance products or platform-provided cargo cover | Legal/financial; not a platform role now | REQUIRES KENYAN PROFESSIONAL VALIDATION |
| In-app chat/messaging system | Parties already use phone/WhatsApp | FUTURE CONSIDERATION |
| Native mobile apps (iOS/Android store builds) | **CONFIRMED: PWA for MVP (D-CLIENT-1)**; native is future | FUTURE CONSIDERATION |
| Multi-language beyond **English & Swahili** | English & Swahili are in scope (D-PIL-4); further languages/Sheng later | FUTURE CONSIDERATION |
| Advanced fraud detection / ML risk scoring | Manual review sufficient at pilot volume | FUTURE CONSIDERATION |
| Operator-group **payroll, shift scheduling, inter-group transfers** | The group entity + membership + group-owned vehicles + driver-named assignment **are in scope (D-OPR-GRP-1)**; these extras are not | FUTURE CONSIDERATION |
| Recipient **accounts / full tracking portal** | Recipient **link** for confirmation + incidents is in scope (D-RCP-1); a full account/portal is not | FUTURE CONSIDERATION |
| Accounting / tax-system integration beyond eTIMS invoicing | eTIMS-compliant commission invoicing is in scope; deeper integration later | REQUIRES KENYAN PROFESSIONAL VALIDATION |

---

## 3. MVP success definition

The MVP is successful as a **pilot instrument** if it can:

1. Onboard and verify the founder's operator network and a set of pilot
   businesses.
2. Run real jobs end to end across at least two vehicle classes (e.g. motorcycle
   and canter/lorry).
3. Preserve negotiation history and agreed price for every job.
4. Produce a complete, auditable chain of custody for completed jobs.
5. Capture and resolve at least the common incident types.
6. Emit structured operational data for every metric in
   [pilot-strategy.md](pilot-strategy.md).

Commercial success targets for the pilot are set in pilot-strategy.md and are
the founder's to confirm.

---

## 4. Scope risks

| Risk | Note |
|------|------|
| Money-handling | RESOLVED 2026-09-08: direct payment between parties; operator pays commission via weekly M-Pesa statement + eTIMS invoices; platform never holds the fare (D-BIZ-4/6). Residual: confirm with bank/counsel that a merchant paybill for own-commission collection stays outside PSP licensing (legal-scope.md §3.6) |
| WhatsApp channel | RESOLVED 2026-09-08: WhatsApp is an MVP channel (D-NOTIF-1). Residual: WhatsApp Business Platform / BSP onboarding lead time and per-message cost; template approval; cross-border-transfer paperwork. Build SMS fallback. |
| Verification throughput | Manual verification is a bottleneck if onboarding is large on day one; plan a phased onboarding. Operator groups add per-driver verification load — onboard groups driver-by-driver. |
| Client — PWA | RESOLVED 2026-09-08: PWA for MVP (D-CLIENT-1). Residual: test camera/offline/push reliability on representative low-end Android in the pilot area during Phase 1; iOS PWA push limitations. |
| Operator-group model creep | Keep it minimal (D-OPR-GRP-1). Resist adding payroll/scheduling during the pilot. |
