# Users and Roles

Three primary roles for MVP: **Business**, **Transport Operator** (individual
**or** a minimal **operator group** — D-OPR-GRP-1), **Platform Administrator**.
A fourth actor, the **Recipient** (consignee), confirms delivery and can raise
incidents through a per-job link **without an account** (D-RCP-1).

---

## 1. Role summary

| Role | Holds account | Primary purpose | Verification |
|------|---------------|-----------------|--------------|
| Business | Yes | Create and manage transport jobs, negotiate, track, confirm | Business identity + at least one confirmed location |
| Transport Operator (individual) | Yes | Discover jobs, negotiate, execute pickup→delivery, build reputation | Identity + licence + vehicle + base + Certificate of Good Conduct; progressive trust |
| Operator Group | Yes (primary contact) | Same, for a fleet: manager assigns an internal driver + vehicle per job | Group profile + base; **each member driver and vehicle individually verified** |
| Platform Administrator | Yes (staff) | Verify, monitor, intervene, resolve disputes, configure | Internal; role-based permissions (2 roles for pilot) |
| Recipient / Consignee | **No account** | Confirm receipt; raise incidents — via a scoped per-job link | Lightweight (name + OTP/signature/photo) |

---

## 2. Business

### 2.1 Account & profile
- Create an account (phone number is the primary identifier; email optional).
- Maintain a business profile: legal/trading name, contact person(s), phone,
  email, business category. Optional registration identifiers (e.g. KRA PIN,
  business registration number) — **collection and any verification of these
  REQUIRES KENYAN PROFESSIONAL VALIDATION** for data-handling obligations.
- Multiple users under one business account with roles (owner, dispatcher,
  viewer) — **WORKING ASSUMPTION**; may be simplified to a single user in MVP if
  the pilot does not need it.

### 2.2 Locations
- Add multiple pickup locations.
- Designate one **main operating location**.
- Add secondary stores / branches / warehouses.
- Each location: label, type (MAIN, BRANCH, WAREHOUSE, STORE, PICKUP_POINT),
  address text, geo-coordinates, on-site contact person + phone, operating hours,
  access notes.

### 2.3 Jobs
- Create transportation/delivery jobs (see [domain-model.md](domain-model.md)
  and [job-lifecycle.md](job-lifecycle.md)).
- Specify cargo information, category, estimated weight, dimensions where
  relevant, declared approximate cargo value.
- Specify destination and delivery requirements.
- Specify required vehicle type and required capacity.
- Propose a price.
- Negotiate with operators (propose / accept / counter / reject).
- Confirm a job (mutual agreement required).
- Track active jobs (status + chain-of-custody events).
- View completed jobs and delivery records (proof of delivery).
- Participate in dispute resolution (report incidents, submit evidence and
  statements).
- Rate operators after completion.

### 2.4 Business cannot
- See an operator's raw identity documents (only verification status + trust
  level + reputation).
- Change job status fields that belong to the operator's custody actions.
- Alter negotiation history.
- Access other businesses' data.

---

## 3. Transport Operator

### 3.1 Account & identity
- Create an account (phone number primary identifier).
- Submit identity information (national ID / passport) — stored under strict
  access control; see [trust-and-safety.md](trust-and-safety.md) and
  [non-functional-requirements.md](non-functional-requirements.md).
- Submit licence information (driving licence class appropriate to vehicle;
  PSV/commercial endorsements where applicable — **REQUIRES KENYAN PROFESSIONAL
  VALIDATION** for which classes/endorsements are legally required per vehicle
  class).

### 3.2 Vehicles
- Register one or more vehicles.
- Specify vehicle type (MOTORCYCLE, PICKUP, CANTER, TIPPER, LORRY, SEMI_TRUCK,
  TRAILER, OTHER) and capacity (payload weight, and volume/bed dimensions where
  relevant).
- Provide vehicle documents (registration/logbook, inspection certificate,
  insurance) — **which documents are mandatory REQUIRES KENYAN PROFESSIONAL
  VALIDATION**.
- Establish vehicle ↔ operator association (owner, or authorised driver).

### 3.3 Operating profile
- Specify operating location / base / stage (registered as an OperatingBase:
  type STAGE, BASE, YARD, WAITING_AREA; name; geo).
- Specify service areas (the zones/routes the operator will work).
- Set availability (available / unavailable / busy; optional schedule).

### 3.4 Jobs
- Discover suitable jobs (filtered by vehicle type/capacity, base proximity,
  service area, trust level eligibility).
- Submit price proposals; counter-offer; accept; reject.
- Execute pickup: mark arrival at pickup, confirm custody of goods.
- Update job status through transit (see [job-lifecycle.md](job-lifecycle.md)).
- Mark arrival at destination; complete delivery.
- Provide proof of delivery (recipient name + one or more of: OTP, signature,
  photo).
- View earnings (agreed price, commission deducted, net) and job history.
- Build a platform trust/reputation history.
- Report incidents; submit evidence and statements.
- Rate businesses after completion.

### 3.5 Operator cannot
- Accept jobs above the value ceiling for their current trust level (see
  [trust-and-safety.md](trust-and-safety.md)).
- Self-verify (verification is an administrator action, possibly assisted by
  automated checks).
- Edit chain-of-custody timestamps after they are recorded.
- See a business's data beyond what a job requires.

### 3.6 Operator sub-shape: individual and group — CONFIRMED 2026-09-08 (D-OPR-GRP-1)

**Individual operator:** owner-rider / owner-driver / authorised driver — one
person, one account, own vehicle(s) and base(s).

**Operator group (IN scope for MVP, minimal):** a yard/base owner, small fleet,
SACCO, or partnership.

| Element | MVP behaviour |
|---------|---------------|
| Group profile | Name, type (`YARD_OWNER / FLEET / SACCO / PARTNERSHIP`), primary-contact user, operating base(s), payout details, status, aggregate standing |
| Members | `GroupMembership(user_id, role: OWNER / MANAGER / DRIVER, since, status)`. **Each member driver is individually identity- + licence-verified** — no shortcut. |
| Vehicles | Owned by the group; **each vehicle individually verified** (incl. NTSA operator licence etc. for heavy classes) |
| Getting work | The group **manager** browses eligible jobs for the group's fleet and negotiates; or an authorised **driver** negotiates directly (per-group setting) |
| Assignment | A job assigned to a group **must name a specific driver + specific vehicle** at ASSIGNED (chain of custody needs a real person) |
| Trust / gating | **Value-band gating uses the assigned driver's trust level.** The group's aggregate standing is a monitoring / suspension lever, not the value gate |
| Custody & POD | Performed by the assigned driver, exactly as for an individual operator |
| Earnings & commission | Commission computed identically; the **weekly statement goes to the group**; internal driver settlement is off-platform for MVP |
| Ratings | Business rates the job; the rating attaches to **both** the assigned driver and the group |

**Out of MVP scope:** internal payroll, shift scheduling, inter-group vehicle/
driver transfers, group-level sub-dashboards beyond a member + vehicle list.

A single individual may also hold a Business profile; each role is separately
verified; a job cannot have the same party as requester and assigned operator
(nor a group the requester controls).

---

## 4. Platform Administrator

Administrators act under **role-based permissions** with every action written to
an immutable audit log.

- Review businesses; review operators; review vehicles.
- Manage verification (approve, reject, request more information, set/expire
  verification per domain: identity, licence, vehicle, association, base,
  document, history).
- Set and adjust operator trust levels (and the job-value ceilings attached to
  them), within configured rules.
- Monitor active jobs (list, filter, drill into chain of custody).
- Intervene in jobs (reassign, cancel, force-status with reason, contact
  parties) — every intervention logged with actor + reason.
- Manage disputes and incidents (review evidence and statements, record
  resolution, escalate).
- Suspend or restrict accounts (business or operator) with reason and duration.
- Review audit records.
- Configure platform rules (commission rate, high-value threshold, trust
  thresholds, allowed vehicle types, pilot-area boundary, cancellation policy,
  data-retention windows).
- Monitor platform performance (operational dashboards — see
  [pilot-strategy.md](pilot-strategy.md)).

### 4.1 Administrator roles — CONFIRMED 2026-09-08 (founder-approved; see [decisions.md](decisions.md) D-ADM-1)

**Pilot: 2 roles.**

| Pilot role | Who | Can | Cannot |
|------------|-----|-----|--------|
| **Platform Admin** | Founder | Everything: platform config (commission, thresholds, timeouts), verification decisions, account suspension/offboarding, binding dispute resolution (all bands), job intervention, manage other admins | — |
| **Operations Officer** | Ops staff | Process the verification queue; monitor active jobs; intervene in jobs (reassign / cancel / contact parties); incident intake; **facilitate** amicable resolution; propose trust-level changes | Change platform config; suspend / offboard accounts; issue a **binding** dispute resolution above Standard band (routes to Platform Admin) |

**Defined in `PlatformConfig` for later** (enabled by configuration when volume /
staffing grow): split Operations into **Verifier**, **Operations**, **Dispute
Officer**, keeping **Platform Admin** as superuser.

| Later sub-role | Can do | Cannot do |
|----------------|--------|-----------|
| Verifier | Verification decisions, view submitted documents | Change commission/config, suspend accounts |
| Operations | Monitor + intervene in jobs, contact parties | Verification decisions, config |
| Dispute officer | Manage incidents/disputes, record resolutions | Config, verification |
| Platform admin | Configuration, account suspension, manage other admins | — |

Non-negotiable regardless of role count: **every admin action — including the
founder's — is audit-logged** (actor + reason + before/after); raw PII/document
access is limited to the verification permission and is itself logged; **MFA is
mandatory** on all admin accounts.

---

## 5. Recipient / Consignee — CONFIRMED 2026-09-08 (D-RCP-1)

- The person receiving goods at the destination. Often not the business user.
- **No account required.** Identified by name and phone on the job.
- At dispatch / arrival the recipient receives a **scoped, time-limited,
  single-job link** (SMS/WhatsApp). Through it the recipient can:
  - **view their delivery's status only** (nothing else on the platform);
  - **confirm receipt** — name + OTP (to their phone) and/or signature and/or
    photo at handover;
  - **raise an incident** — wrong recipient, damage, missing/short, wrong goods —
    with photos and a short statement, entering the standard incident workflow
    (see [dispute-and-liability.md](dispute-and-liability.md)); this notifies the
    business, the operator, and an administrator.
- The link **expires after the post-completion dispute window**. Recipient short
  terms are shown on the link (see [legal-scope.md](legal-scope.md) §4, item 7).
- The recipient is **not** an account holder and cannot negotiate, see other
  jobs, or act on the platform beyond their own delivery.

---

## 6. Cross-cutting rules

- **Authentication:** phone-number-based with OTP is the **WORKING ASSUMPTION**
  for all account holders; password optional. Admin accounts require stronger
  auth (see [non-functional-requirements.md](non-functional-requirements.md)).
- **Authorization:** every capability above is gated by role and, for operators,
  by trust level and verification state. Authorization is a first-class
  requirement, not a later addition.
- **One person, multiple roles:** a single individual could be both a business
  user and an operator. **WORKING ASSUMPTION:** allowed, but each role is a
  separate profile with its own verification; a job cannot have the same party
  as both requester and assigned operator.
- **Audit:** all state-changing actions by any role are logged with actor, time,
  entity, and before/after where applicable.
