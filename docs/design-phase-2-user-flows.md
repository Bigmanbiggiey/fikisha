# FIKISHA

## Design Phase 2 — User Flows Specification

**Status:** APPROVED WITH CLARIFICATIONS — 2026-09-10
**Design Track:** Phase 2 (the formal User Flows deliverable)
**Predecessors:**

* `docs/design-brief.md` — Design Phase 0 foundation/context
* `docs/design-phase-1-ia.md` — Design Phase 1 Information Architecture
* `docs/phase-0/` — Approved product decisions
* `docs/phase-1/` — Approved architecture
* `docs/phase-2/` — Implemented foundation, identity, organizations, vehicles and verification

**Pilot:** Kitengela, Kajiado County + environs
**Client:** Responsive PWA
**Languages:** English + Swahili

---

# 0. Purpose

This document defines the principal user journeys through Fikisha.

It translates the approved Information Architecture into behavioral flows that can later become:

* wireframes
* interaction specifications
* high-fidelity screens
* frontend implementation requirements
* usability-test scenarios

This document defines **what users do and what the system must communicate**, not the final visual design.

---

# 0.1 Document Lineage & Approval Status

## Provenance

| Phase | Artifact | Role |
| --- | --- | --- |
| Design Phase 0 | `docs/design-brief.md` | Design foundation / context / constitution |
| Design Phase 1 | `docs/design-phase-1-ia.md` | Information architecture & navigation |
| **Design Phase 2** | `docs/design-phase-2-user-flows.md` (this document) | Principal user journeys through the IA |
| Design Phase 3 | *(not started)* | Wireframes & interaction structure |

Lineage:

```text
docs/design-brief.md              → Design Phase 0
        ↓
docs/design-phase-1-ia.md         → Design Phase 1
        ↓
docs/design-phase-2-user-flows.md → Design Phase 2
        ↓
Design Phase 3 — Wireframes        (not started)
```

This is the single Design Phase 2 artifact; there is no competing document.

## Status

**APPROVED WITH CLARIFICATIONS — 2026-09-10.**

Reviewed against `docs/phase-0/`, `docs/phase-1/`, `docs/phase-2/`,
`docs/design-brief.md`, and `docs/design-phase-1-ia.md`. **No product
contradictions were found.** Five precision corrections were folded in at
approval; each is additive and presentation-level and changes no approved
product decision from Phases 0–2C.

## Corrections incorporated at approval (2026-09-10)

| # | Correction | Where |
| --- | --- | --- |
| 1 | Pickup proof is **band-dependent**, not universally OTP-mandatory. STANDARD: pickup-contact OTP or in-app business confirmation, with an operator-attested fallback (goods photo + pickup-contact name → recorded as operator-attested / unverified, timeline-flagged, Job capped at STANDARD) when OTP is undeliverable. ELEVATED / HIGH / VERY_HIGH: OTP or in-app business confirmation, **no fallback** — the transition is refused with the appropriate error. | §38–§40 |
| 2 | Delivery proof is **band-dependent**. STANDARD: OTP / SIGNATURE / PHOTO. ELEVATED / HIGH / VERY_HIGH: OTP **+** PHOTO. Presented contextually; not a generic optional upload. | §44 |
| 3 | `DISPUTED → RESUME` is **Platform Admin-only**, as is binding dispute resolution **above the Standard band**. Separated from the Operations Officer flow family. The exact `RESUME_PRIOR` preconditions remain an open Phase-0 / product-architecture item and are not invented here. | §58, §59, §62.1 |
| 4 | Cancellation flagging is the **late-cancellation / wasted-trip** rule: 3 late cancellations (after `ASSIGNED`, before `AT_PICKUP`) or wasted trips in a rolling 30-day window → admin-review flag, tracked **per side**. No generic all-cancellations counter; cancelling an unengaged `REQUESTED` Job does not count. | §79–§80 |
| 5 | Notification wording: **SMS is the reliable / default OTP carrier; WhatsApp may be an additional OTP carrier.** For ordinary Job notifications the fallback direction is **WhatsApp → SMS**. WhatsApp is never the system of record. | §65 |

## What this update did not touch

No application code, backend models, APIs, database schemas, or frontend
components were modified. No approved product decision from Phases 0–2C was
reopened. Design Phase 3 (Wireframes) has not started.

---

# 1. Source-of-Truth Rules

The following are immutable during this design phase.

## 1.1 Job

The Job is the central product object.

The authoritative Job lifecycle contains exactly:

```text
DRAFT
REQUESTED
NEGOTIATING
CONFIRMED
ASSIGNED
AT_PICKUP
PICKED_UP
IN_TRANSIT
AT_DESTINATION
DELIVERED
COMPLETED
CANCELLED
FAILED
DISPUTED
```

The UI may use human-friendly terminology but must not invent or collapse authoritative states.

---

# 1.2 Verification

Authoritative verification states:

```text
NOT_SUBMITTED
SUBMITTED
IN_REVIEW
INFO_REQUESTED
VERIFIED
REJECTED
EXPIRED
```

User-facing grouping:

```text
Required
Submitted
Under Review
Verified
Needs Attention
```

`Needs Attention` represents:

* `INFO_REQUESTED`
* `REJECTED`
* `EXPIRED` where effective expiry applies

---

# 1.3 Trust

Verification and trust are separate concepts.

The interface must never imply:

> Verified = Trusted

Verification communicates evidence-backed facts.

Trust/reputation communicates the separately defined trust model.

---

# 1.4 Driver

There is no standalone Driver account type.

A driver is:

* a GroupMembership with `role=DRIVER`, or
* an individual operator acting as their own driver.

The Driver experience is therefore a **role-scoped workspace**.

A group Driver's work/discovery permissions remain governed by the existing `DRIVER_ACCEPTS` authorization rule.

---

# 1.5 Operator Groups

Groups remain intentionally minimal.

The UX must not evolve into:

* payroll
* shift management
* complex fleet scheduling
* driver transfers
* enterprise fleet management

---

# 1.6 Communication

Negotiation is an in-app system-of-record experience.

WhatsApp and SMS are communication/notification channels.

WhatsApp must not become the authoritative record of a Job.

---

# 1.7 Payments

Fikisha does not hold the transport fare.

There is no:

* wallet
* escrow
* fare custody

The approved commission model is:

> 10% of completed agreed transport price, minimum KES 40, maximum KES 5,000 per Job.

Payment implementation is a later product phase and is therefore not invented here.

---

# 1.8 Location

Fikisha prefers event-based location evidence over continuous GPS tracking.

UX must not imply continuous live tracking unless a future product decision explicitly introduces it.

---

# 2. Flow Notation

Flows use:

```text
[Actor action]
        ↓
<System response>
        ↓
[Next action]
```

Decision points use:

```text
                 ┌── Yes ──→ ...
[Decision?] ─────┤
                 └── No ───→ ...
```

Each major flow identifies:

* actor
* entry point
* prerequisites
* primary journey
* alternate paths
* failure states
* notifications
* authoritative state implications
* completion condition

---

# 3. Experience Map

The overall Fikisha journey is:

```text
BUSINESS
    │
    │ creates request
    ▼
JOB REQUESTED
    │
    ▼
NEGOTIATION
    │
    ▼
CONFIRMED
    │
    ▼
ASSIGNMENT
    │
    ▼
PICKUP
    │
    ▼
CUSTODY
    │
    ▼
TRANSIT
    │
    ▼
DESTINATION
    │
    ▼
DELIVERY
    │
    ▼
COMPLETED
```

With exception paths:

```text
                   ┌── CANCELLED
                   │
                   ├── FAILED
                   │
                   └── DISPUTED
                         │
                         └── resolution / admin recovery
```

The interface must make the current position in this journey obvious.

---

# 4. Flow Family A — Business

## A1. Business Onboarding

### Actor

Business owner.

### Entry point

Fikisha landing/authentication experience.

### Preconditions

User does not yet have an active Business workspace.

### Flow

```text
Open Fikisha
    ↓
Choose Business
    ↓
Authenticate with phone + OTP
    ↓
Create Business
    ↓
Enter business details
    ↓
Create initial business location
    ↓
Business workspace
```

### UX requirements

The user should understand:

* what Fikisha does
* why the business needs an account
* what information is required
* what can be completed later

Do not introduce unnecessary verification requirements at onboarding unless product rules require them.

### Failure paths

**OTP failure**

→ explain failure
→ allow retry
→ respect rate limits

**Existing account**

→ authenticate and enter the appropriate workspace.

**Connectivity failure**

→ clearly communicate that authentication requires server confirmation.

### Completion

Business workspace exists and user has appropriate owner context.

---

# 5. Flow A2 — Business Staff Setup

### Actor

Business Owner.

### Entry

Business → Staff.

### Flow

```text
Open Staff
    ↓
Add staff member
    ↓
Enter phone/contact
    ↓
Select role
    ↓
Confirm
    ↓
Membership created
```

Roles currently supported:

* OWNER
* DISPATCHER
* VIEWER

### UX requirements

The UI must clearly distinguish:

* owner
* dispatcher
* viewer

The system must prevent the business from accidentally removing its final active owner.

### Permission failure

A non-authorized user attempting management:

→ explain that they do not have permission.

Do not rely on hidden controls as the security mechanism.

---

# 6. Flow A3 — Business Location Setup

### Actor

Business owner/authorized staff.

### Flow

```text
Business
   ↓
Locations
   ↓
Add location
   ↓
Enter location details
   ↓
Select location type
   ↓
Save
```

A business may maintain multiple locations.

There must be one active MAIN location according to the established domain rules.

### UX principle

The interface should distinguish:

> Where the business operates

from:

> Where this particular Job will be collected.

---

# 7. Flow A4 — Create Transport Request

This is one of Fikisha's most important flows.

### Actor

Business user with Job-creation permission.

### Entry

Home → Request Transport.

### Preconditions

Business exists and is active.

### Primary flow

```text
Request Transport
       ↓
Pickup
       ↓
Destination
       ↓
Cargo
       ↓
Weight / dimensions
       ↓
Declared value
       ↓
Vehicle requirement
       ↓
Date / time
       ↓
Delivery requirements
       ↓
Proposed transport price
       ↓
Review request
       ↓
Submit
```

### Form design

The form should be progressive.

Do not expose every possible field simultaneously.

The user should always understand:

> Why are you asking me this?

---

# 8. Declared Value Flow

Declared value affects trust and eligibility.

The UI should explain the purpose without exposing unnecessary internal trust mechanics.

For example:

> **What's the approximate value of the goods?**

Then:

> This helps us apply appropriate transport and verification requirements.

Do not expose internal threshold calculations as though they are negotiable.

---

# 9. Vehicle Requirement Flow

The business specifies what kind of transport is needed.

The UI should use understandable categories rather than backend model terminology.

Examples:

* Motorcycle
* Pickup
* Canter
* Lorry
* Tipper
* Trailer
* Other supported class

Capacity requirements should be understandable to the user.

---

# 10. Job Request Submission

Before submission, provide a concise review:

```text
Pickup
Destination
Cargo
Estimated weight
Declared value
Vehicle requirement
Date/time
Delivery requirements
Proposed price
```

Primary action:

> **Request transport**

After successful submission:

```text
DRAFT
   ↓
REQUESTED
```

The user should see confirmation that the request is now active.

---

# 11. Flow A5 — Business Receives Response

The business sees available/eligible operator responses.

The interface should communicate:

* operator identity
* relevant verified facts
* applicable trust information
* vehicle
* price
* response status

Do not imply that Fikisha guarantees successful delivery.

---

# 12. Flow A6 — Negotiation

### Actors

Business + Operator.

### Flow

```text
Job
 ↓
Operator response
 ↓
View offer
 ↓
Accept
OR
Counter
OR
Decline
```

Counteroffer:

```text
Enter price
     ↓
Optional contextual message
     ↓
Send counteroffer
```

The negotiation history is immutable.

### Example UX

```text
KES 8,000
Operator proposal

Your response:

KES 7,500
Counteroffer sent

Operator:
KES 7,800

You:
Accept
```

Once agreement is reached:

```text
NEGOTIATING
     ↓
CONFIRMED
```

The agreed price becomes visually authoritative.

---

# 13. Negotiation Failure Paths

### Declined

Show:

> Offer declined.

The Job remains governed by its authoritative lifecycle.

### Expired / unavailable response

Clearly distinguish:

> No longer available

from:

> Declined

### Connection failure

Do not display an offer as sent until server confirmation exists.

---

# 14. Flow A7 — Confirmed Job

Once price and required agreement are established:

```text
CONFIRMED
```

Business sees:

* agreed price
* operator
* vehicle where assigned/known
* expected timing
* next milestone

Primary action becomes monitoring rather than negotiation.

---

# 15. Flow A8 — Assignment

Assignment may involve an operator/group assigning:

* specific driver
* specific vehicle

The business should receive a clear assignment summary.

Example:

```text
Transport assigned

Operator: ABC Transport
Driver: [name]
Vehicle: [registration/class]

Pickup: Kitengela
Destination: ...
```

Do not expose unnecessary internal verification records.

Show relevant verified facts.

---

# 16. Flow A9 — Monitor Job

The Business Job page becomes a timeline.

Example:

```text
✓ Request submitted
✓ Price agreed
✓ Transport assigned
● At pickup
○ Picked up
○ On the way
○ At destination
○ Delivered
○ Completed
```

The current state is prominent.

---

# 17. Off-Happy-Path Business Job States

## DRAFT

Communicate:

> This request has not been submitted yet.

Provide the appropriate editing/submission action.

---

## CANCELLED

Communicate:

> This Job was cancelled.

Do not visually present it as failed delivery.

---

## FAILED

Communicate:

> This Job could not be completed.

Where allowed, show relevant next action.

---

## DISPUTED

Communicate:

> This Job is under dispute.

Explain:

* normal completion is suspended
* the issue is under review/resolution
* what the business can do next

Do not imply guilt before resolution.

---

# 18. Flow A10 — Delivery Confirmation

After the operator records delivery:

```text
DELIVERED
```

Business receives the appropriate notification.

The business may review delivery information/evidence and complete the Job according to the established workflow.

Completion:

```text
DELIVERED
    ↓
COMPLETED
```

The UI must distinguish:

> Delivered

from:

> Fully completed/closed.

---

# 19. Flow A11 — Business Reports Incident

### Entry

Job → Report an issue.

### Categories

The established incident model includes:

* damage
* loss
* missing goods
* wrong recipient
* pickup issue
* misconduct
* breakdown
* accident
* delay
* cancellation
* other

### Flow

```text
Report issue
    ↓
Select category
    ↓
Describe what happened
    ↓
Attach evidence where applicable
    ↓
Submit
    ↓
Incident recorded
```

The user should understand:

> Reporting an incident does not automatically mean a refund or compensation has been granted.

The resolution process is separate.

---

# 20. Flow A12 — Business Rating

After eligible completion:

```text
Completed Job
    ↓
Rate operator
    ↓
Optional comment
    ↓
Submit
```

Rating must not be presented before the Job is eligible.

Anti-manipulation and visibility rules remain governed by the later reputation/rating product phase.

---

# 21. Flow Family B — Operator

# B1. Operator Onboarding

### Actor

Individual transport operator.

### Flow

```text
Authenticate
    ↓
Create operator profile
    ↓
Add operating location
    ↓
Add vehicle
    ↓
Review required verification
```

The system should not present all possible verification requirements blindly.

Requirements should be contextual.

---

# 22. Flow B2 — Operator Operating Location

```text
Operator
   ↓
Operating locations
   ↓
Add stage/base/yard/waiting area
   ↓
Enter location
   ↓
Save
```

UX must not state:

> "You own this stage"

unless that fact is actually established.

The relationship represents an operating/presence context.

---

# 23. Flow B3 — Register Vehicle

### Entry

Operator → Vehicles → Add vehicle.

### Flow

```text
Select vehicle class
       ↓
Registration
       ↓
Capacity
       ↓
Ownership/control
       ↓
Vehicle details
       ↓
Safety declarations where applicable
       ↓
Save
```

The user should immediately see:

> What verification is required for this vehicle?

---

# 24. Flow B4 — Vehicle Verification

After vehicle creation:

```text
Vehicle
   ↓
Verification
   ↓
Required domains
   ↓
Submit evidence
   ↓
Under review
   ↓
Verified / Needs attention
```

For heavy vehicles, requirements are determined by the configured vehicle-class rules.

The UI must not hard-code the heavy-vehicle rules as arbitrary screen logic.

---

# 25. Flow B5 — Verification Submission

### Actor

Subject owner/authorized user.

### Flow

```text
Required verification
       ↓
Select domain
       ↓
Read requirement
       ↓
Add evidence
       ↓
Review
       ↓
Submit
```

Submission produces:

```text
NOT_SUBMITTED
     ↓
SUBMITTED
```

Review then produces the appropriate state.

---

# 26. Flow B6 — Verification Under Review

The user sees:

> **Under review**

rather than internal reviewer mechanics.

Where useful:

* submission date
* domain
* current state
* expected next action

Do not promise a review completion time unless such an SLA exists.

---

# 27. Flow B7 — Verification Needs Attention

When:

* `INFO_REQUESTED`
* `REJECTED`
* effective `EXPIRED`

the user sees:

> **Needs attention**

The interface explains the reason.

### INFO_REQUESTED

```text
Reviewer request
     ↓
User provides requested information
     ↓
Resubmit
```

### REJECTED

Explain what was rejected and what correction/resubmission is possible.

### EXPIRED

Explain:

> This verification is no longer current.

Provide the appropriate renewal/resubmission path.

---

# 28. Flow B8 — Discover Work

### Entry

Operator → Work.

### Flow

```text
Open Work
    ↓
Review available Jobs
    ↓
Filter where appropriate
    ↓
Open Job
    ↓
Review eligibility/details
    ↓
Respond
```

The interface must not imply that the operator is seeing every Job in the marketplace if matching/authorization restricts the result.

> **Note (Design Phase 1 §4.3):** for a group Driver this surface exists only
> when the group is configured for `DRIVER_ACCEPTS`. In `MANAGER_ASSIGNS` groups
> the Driver has no discovery surface and sees only assignments made to them. An
> individual operator is always their own driver.

---

# 29. Flow B9 — Review Job Opportunity

The operator should see:

* pickup
* destination
* cargo
* estimated weight/dimensions
* declared value where appropriate
* vehicle requirement
* date/time
* delivery requirements
* proposed price
* relevant business information
* applicable verified/trust information

The most important question:

> **Can I safely and legitimately take this Job?**

---

# 30. Flow B10 — Operator Negotiates

Same negotiation system as Business.

```text
Review request
     ↓
Accept proposed price
OR
Counteroffer
OR
Decline
```

Negotiation history remains immutable.

---

# 31. Flow B11 — Operator Accepts

After agreement:

```text
NEGOTIATING
     ↓
CONFIRMED
```

The operator sees:

> Price agreed: KES X

The interface should make it clear that the agreement is now fixed according to the approved product rules.

---

# 32. Flow B12 — Group Assignment

For a group:

```text
Confirmed Job
     ↓
Assign driver
     ↓
Select eligible driver
     ↓
Select eligible vehicle
     ↓
Review assignment
     ↓
Confirm
```

The UI must not permit assignment that violates trust/verification/value-band eligibility.

The assigned driver's trust ceiling is authoritative.

The group itself must not be treated as a substitute for the driver's required trust eligibility.

---

# 33. Flow B13 — Assignment Failure

If a driver/vehicle is not eligible:

> **This driver cannot be assigned to this Job.**

Where useful:

> Required verification/trust conditions have not been met.

Do not expose sensitive internal scoring or allow a client-side workaround.

---

# 34. Flow B14 — Operator Executes Job

Once assignment is established:

```text
ASSIGNED
   ↓
AT_PICKUP
   ↓
PICKED_UP
   ↓
IN_TRANSIT
   ↓
AT_DESTINATION
   ↓
DELIVERED
   ↓
COMPLETED
```

The operator's interface should always expose the next appropriate action.

---

# 35. Flow Family C — Driver

## C1. Driver Entry

A driver does not sign up separately.

Possible entry:

```text
Group
  ↓
Assign driver
  ↓
Driver receives assignment
```

The driver enters the role-scoped experience using the existing identity/authentication model.

---

# 36. Flow C2 — Driver Assignment

Driver receives notification:

> **You have been assigned a delivery.**

Opening it shows:

* pickup
* destination
* cargo summary
* vehicle
* relevant instructions
* Job status

Primary CTA:

> **View Job**

---

# 37. Flow C3 — Driver Goes to Pickup

Job state:

```text
ASSIGNED
```

Primary action:

> **Go to pickup**

Navigation may use an external map capability later, but Fikisha must not imply continuous GPS tracking.

---

# 38. Flow C4 — Driver Arrives at Pickup

Driver selects:

> **I'm at pickup**

The system records the appropriate custody/location event and issues the
pickup-contact OTP (see §39).

The Job progresses toward:

```text
AT_PICKUP
```

The interface confirms server-side recording.

---

# 39. Flow C5 — Pickup Proof (Band-Dependent)

Pickup confirmation is **proof-gated**, and the accepted proof depends on the
Job's value band. The pickup-contact OTP is the primary, strongest mechanism —
it is **not** the only permitted proof, and it is **not** universally mandatory.

### Clarification (approval, 2026-09-10) — the approved pickup proof matrix

| Band | Accepted pickup proof | Fallback when OTP is undeliverable / unusable |
| --- | --- | --- |
| **STANDARD** (declared value ≤ KES 50,000) | pickup-contact OTP **or** in-app business confirmation | operator-attested fallback: goods photo **+** pickup-contact name → recorded as the operator-attested proof (`OPERATOR_ATTESTED_UNVERIFIED`); the timeline **visibly flags the proof as unverified**; the Job is **capped at STANDARD** (a later in-app business confirmation can flip it to verified) |
| **ELEVATED / HIGH / VERY_HIGH** (> KES 50,000) | pickup-contact OTP **or** in-app business confirmation | **none** — if the required confirmation cannot be obtained, the transition is **refused** with the appropriate product/API error (`AT_PICKUP → PICKED_UP` does not occur) |

Conceptual flow (OTP path):

```text
At pickup
    ↓
Pickup OTP issued to the pickup contact
    ↓
Driver enters the code the pickup contact reads out
    ↓
Validate
    ↓
Goods handover confirmed  →  PICKED_UP
```

Decision points:

```text
                         ┌── OTP entered & valid ─────────→ handover confirmed
                         │
[How is pickup proven?] ─┼── In-app business confirmation ─→ handover confirmed
                         │
                         └── OTP undeliverable? ──┬── STANDARD ──→ operator-attested
                                                  │                (photo + contact name;
                                                  │                 flagged unverified;
                                                  │                 Job capped at STANDARD)
                                                  │
                                                  └── ELEVATED+ ─→ transition refused
```

Incorrect OTP:

```text
Invalid OTP
   ↓
Retry within permitted limits
   ↓
Repeated failure → security / rate-limiting behavior defined by the system
   ↓
(STANDARD only) offer the operator-attested fallback
(ELEVATED+)      the transition stays refused
```

The driver must not be able to bypass the required pickup proof through an
ordinary UI action. The UI must make the Standard vs. Elevated+ difference
understandable — e.g. *"This delivery needs a verified pickup code"* — without
exposing unnecessary internal implementation detail. **No additional fallback
mechanisms are introduced.**

---

# 40. Flow C6 — Goods Received / Custody

Once the pickup event is successfully completed (by any of the proof paths in
§39):

```text
PICKED_UP
```

The driver should see a clear confirmation:

> **Goods received**

Relevant evidence/custody information may be attached.

The user should understand that responsibility has entered the transport/custody stage without the interface making unsupported legal-liability claims.

---

# 41. Flow C7 — Start Transit

Primary action:

> **Start transit**

Server confirmation moves the Job toward:

```text
IN_TRANSIT
```

The UI must not claim transit has started merely because a local button was tapped.

---

# 42. Flow C8 — Arrive at Destination

Driver:

> **I've arrived**

System records destination arrival.

State:

```text
AT_DESTINATION
```

---

# 43. Flow C9 — Recipient Handover

Driver identifies the intended delivery/recipient context.

Recipient uses the scoped Job link where applicable.

The recipient can:

* inspect delivery information
* verify receipt
* confirm delivery
* report an issue

---

# 44. Flow C10 — Delivery Confirmation (Band-Dependent Proof)

Delivery confirmation is proof-gated, and the accepted proof-of-delivery depends
on the Job's value band.

### Clarification (approval, 2026-09-10) — the approved delivery proof matrix

| Band | Proof of delivery |
| --- | --- |
| **STANDARD** | one of: OTP · SIGNATURE · PHOTO |
| **ELEVATED / HIGH / VERY_HIGH** | OTP **and** PHOTO (both required) |

The UI presents the applicable requirement **contextually** for the Job in hand —
delivery proof is **not** a generic optional upload, and **no other proof
mechanisms are introduced**. Recipient-side confirmation via the scoped link
(§43, §49) feeds the same proof record.

After the required proof is recorded:

```text
AT_DESTINATION → DELIVERED
```

The driver receives confirmation. The interface should make clear that
"Delivery has been recorded" — it should not present the Job as fully closed if
completion requires subsequent business/system processing (see §18, §83).

---

# 45. Flow C11 — Driver Incident

At any relevant execution stage:

```text
Job
 ↓
Report incident
 ↓
Select category
 ↓
Describe
 ↓
Evidence
 ↓
Submit
```

Examples:

* accident
* breakdown
* damage
* missing goods
* wrong recipient
* delay
* misconduct
* other

The incident flow should be reachable without forcing the driver to abandon the current Job.

---

# 46. Driver Safety Principle

During active transport, the UI should minimize interaction.

Avoid:

* long forms
* dense dashboards
* unnecessary typing
* repeated navigation
* complex menus

The active Job should dominate the experience.

---

# 47. Flow Family D — Recipient

## D1. Open Scoped Link

Recipient receives a scoped link.

```text
Open link
   ↓
Authenticate access token
   ↓
Display Job-specific delivery view
```

No account creation.

No password.

No marketplace navigation.

---

# 48. Recipient Information

Show only what the recipient needs to safely understand the delivery.

Potential information:

* delivery reference
* pickup/destination context
* cargo summary where appropriate
* current delivery status
* relevant operator/driver information
* delivery confirmation controls
* incident reporting

Do not expose unrelated business or operator data.

---

# 49. Recipient Confirmation

```text
Review delivery
    ↓
Confirm receipt
    ↓
Delivery recorded
```

The action should have clear wording.

Example:

> **Confirm I received the goods**

rather than ambiguous:

> Submit

---

# 50. Recipient Incident

If goods are:

* damaged
* missing
* incorrect
* delivered to wrong recipient

the recipient can:

```text
Report issue
    ↓
Select issue
    ↓
Describe
    ↓
Attach evidence where applicable
    ↓
Submit
```

The recipient should receive a clear confirmation that the report was recorded.

---

# 51. Recipient Security

The scoped link must not allow:

* access to unrelated Jobs
* account management
* browsing the marketplace
* access to business history
* unrestricted evidence browsing

The recipient experience is Job-scoped and permission-scoped.

---

# 52. Flow Family E — Operations Officer

## E1. Verification Queue

### Entry

Operations → Verification.

### Flow

```text
Verification queue
     ↓
Filter records
     ↓
Open record
     ↓
Review subject/domain
     ↓
Review evidence
     ↓
Start review
     ↓
Approve
OR
Request information
OR
Reject
```

The Operations Officer's permissions remain authoritative.

---

# 53. Verification Review States

Review progression:

```text
SUBMITTED
    ↓
IN_REVIEW
    ├── VERIFIED
    ├── INFO_REQUESTED
    └── REJECTED
```

Expired records may become:

```text
EXPIRED
```

The UI must preserve the historical review trail.

---

# 54. Evidence Review

Reviewer sees:

* evidence metadata
* relevant document information
* submitted date
* current state
* prior decisions where authorized

HIGH-PII evidence access must remain explicitly authorized and audited.

The interface should avoid unnecessary exposure of sensitive documents.

---

# 55. Flow E2 — Operations Job Monitoring

Operations → Jobs.

Primary views:

* active Jobs
* exceptions
* disputed Jobs
* failed Jobs
* Jobs requiring intervention

The interface should prioritize:

> **What needs attention?**

rather than merely listing everything.

---

# 56. Flow E3 — High-Value Job Review

For Jobs meeting the approved high-value threshold:

```text
Job enters applicable review path
       ↓
Operations/Admin sees review requirement
       ↓
Review trust + verification eligibility
       ↓
Approve / intervene according to authorization
```

The UI must not allow an ordinary user to bypass this requirement.

High-value thresholds remain:

* KES 50,000
* KES 250,000
* KES 1,000,000

with the approved trust/verification rules. The point at which
**admin pre-assignment review** is required is the configured
`high_value_threshold_kes` (KES 250,000): the HIGH band (250,001–1,000,000)
requires admin pre-assignment review, and VERY_HIGH (> 1,000,000) additionally
requires per-Job Platform-Admin approval.

---

# 57. Flow E4 — Incident Review

```text
Incidents
   ↓
Open incident
   ↓
Review Job context
   ↓
Review statements/evidence
   ↓
Communicate / investigate
   ↓
Resolution
```

Operations should see enough context to understand:

* Job
* actors
* vehicle
* custody history
* evidence
* incident chronology

---

# 58. Flow E5 — Dispute Resolution

Fikisha follows:

```text
Incident/dispute
      ↓
Amicable-first
      ↓
Admin review where necessary
      ↓
Resolution
      ↓
Record outcome
```

### Clarification (approval, 2026-09-10) — who resolves

* An **Operations Officer** may facilitate **amicable** resolution and
  **propose** trust / outcome changes.
* **Binding** dispute resolution **above the Standard band** is **Platform
  Admin-only** (D-ADM-1). The UI must route these to a Platform Admin — not
  present them as an Operations Officer action.

The UI must not prematurely frame one party as guilty.

---

# 59. Flow E6 — DISPUTED → RESUME  (Platform Admin only)

`DISPUTED` is a freeze. Moving a Job out of it is an **administrative recovery
path**, listed alongside the Operations family here only for lifecycle
continuity — the action itself is **Platform Admin-only**.

```text
DISPUTED
    ↓
Platform Admin reviews
    ↓
Resolution supports continuation
    ↓
Platform Admin resumes the Job → job.status = pre-dispute state
```

### Clarification (approval, 2026-09-10)

* This transition (`DISPUTED → <pre_dispute_status>`, `RESUME_PRIOR`) is
  **Platform Admin-only**. It must never be presented as an Operations Officer
  capability.
* The exact preconditions for `RESUME_PRIOR` remain an **open Phase-0 /
  product-architecture item**. This document does **not** invent them. The flow
  communicates only that an authorized Platform Admin may resume a disputed Job
  **when the authoritative system permits it** — without defining additional
  product rules.
* Only authorized Platform Admin action can trigger the transition; the action
  is **audited**.

The UI should show:

> Job resumed by an authorized Platform Administrator.

---

# 60. Flow E7 — Restriction

Where an admin restriction is permitted:

```text
Review subject
    ↓
Restriction action
    ↓
Explain reason
    ↓
Confirm
    ↓
System records action
```

Dangerous administrative actions require explicit confirmation and auditability.

---

# 61. Flow E8 — Search

Operations/Admin search may locate:

* Job
* business
* operator
* vehicle
* phone/contact where authorized
* registration
* incident
* verification

Search results must obey authorization.

---

# 62. Flow E9 — Audit

Authorized admins can inspect activity.

Audit information should answer:

* who acted?
* what happened?
* when?
* to what resource?
* what was the resulting action?

Audit data is not a normal end-user feature.

---

# 62.1 Platform Admin-Only Actions (Boundary Note)

Design Phase 1 §9–§10 separates the Operations Officer workspace from the
Platform Admin workspace. For the flows above, the following are **Platform
Admin-only** and must not appear as Operations Officer capabilities (D-ADM-1):

* `DISPUTED → RESUME` (`RESUME_PRIOR`) — §59;
* **binding** dispute resolution **above the Standard band** — §58;
* platform configuration changes;
* account suspension / offboarding.

An Operations Officer may **facilitate** amicable resolution, work the
verification queue, monitor and intervene in Jobs, intake incidents, and
**propose** trust changes — but not issue the binding calls above. Server-side
authorization remains the enforcement mechanism; this note governs how the UI
presents the boundary.

---

# 63. Flow Family F — Cross-Cutting Authentication

All authenticated experiences inherit the Phase 2A authentication architecture.

Conceptually:

```text
Enter phone
   ↓
Request OTP
   ↓
Receive OTP
   ↓
Enter OTP
   ↓
Authenticated session
   ↓
Determine role/context
   ↓
Enter appropriate workspace
```

The UX should never expose token/session implementation details.

---

# 64. Cross-Cutting Context Switching

Where a user has multiple organizational contexts:

```text
User
├── Business
└── Operator
```

the active context must be visible.

Before a consequential action:

> **Operating as: ABC Transport**

This reduces wrong-context actions.

---

# 65. Cross-Cutting Notifications

Notifications are triggered by meaningful events.

Examples:

### Business

* request received
* offer received
* counteroffer received
* Job confirmed
* assignment made
* pickup completed
* delivery recorded
* incident opened
* dispute update

### Operator

* Job opportunity
* offer response
* Job confirmed
* assignment
* verification update
* incident update
* statement availability

### Driver

* assignment
* Job update
* pickup requirement
* destination requirement
* incident update

### Recipient

* delivery notification
* delivery status
* issue/report confirmation

Channels remain:

* in-app
* SMS
* WhatsApp

### Clarification (approval, 2026-09-10) — channel wording

* **OTP:** SMS is the **reliable / default OTP carrier**. WhatsApp **may** be an
  **additional** OTP carrier where configured. SMS is never removed from the OTP
  path.
* **Ordinary Job notifications:** the fallback direction is **WhatsApp → SMS**
  (a WhatsApp send that fails falls back to SMS; an in-app notification is always
  written).
* WhatsApp remains a communication / notification channel and **never** becomes
  the system of record (see §1.6).

---

# 66. Notification Principle

A notification should answer:

> **Why am I receiving this?**

and:

> **What should I do?**

Notifications should deep-link to the relevant Job/resource whenever appropriate.

---

# 67. Cross-Cutting Offline Behavior

The PWA must distinguish:

### Local interaction

from:

### Server-confirmed action

For example:

```text
Tap "Confirm pickup"
       ↓
Request sent
       ↓
Waiting for server
       ↓
Server confirms
       ↓
"Pickup confirmed"
```

Not:

```text
Tap
 ↓
Immediately show "Pickup confirmed"
```

unless the system genuinely has server confirmation.

---

# 68. Cross-Cutting Error Handling

Every failed operation should communicate:

1. What happened.
2. Why it matters.
3. What the user can do.

Example:

> **Pickup could not be confirmed.**

> The pickup OTP was incorrect.

> Check the code and try again.

---

# 69. Authorization Failure

When the server returns a permission denial:

Do not expose:

> `403 Forbidden`

Primary UX:

> **You don't have permission to perform this action.**

Where appropriate:

> Contact your business owner/group manager.

Server-side authorization remains authoritative.

---

# 70. Cross-Cutting Loading States

Avoid blank screens.

Use contextual loading:

```text
Loading Job...
Loading verification...
Checking eligibility...
```

For consequential actions:

> **Confirming pickup…**

This communicates that the system is waiting for server confirmation.

---

# 71. Cross-Cutting Empty States

Empty states should be useful.

Bad:

> No data.

Better:

> **No active Jobs**

> You don't have any deliveries in progress.

With an appropriate action:

> Request transport

or:

> Browse available work

depending on role.

---

# 72. Cross-Cutting Suspended/Restricted States

If a user, business, group, or vehicle is restricted:

The interface should clearly communicate:

* what is restricted
* whether the restriction is temporary/permanent where appropriate
* what actions remain available
* whether further action is possible

Do not simply hide the resource.

---

# 73. Cross-Cutting Evidence

Where evidence is required:

```text
Action
 ↓
Evidence requested
 ↓
Add evidence
 ↓
Submit
 ↓
Server confirmation
```

The UI should use human terminology:

* Add photo
* Upload document
* Add proof
* Attach evidence

not internal object names.

---

# 74. Cross-Cutting State Machine Principle

The UI must never independently decide that a Job changed state.

The backend lifecycle remains authoritative.

Conceptually:

```text
UI action
    ↓
Authorized API request
    ↓
Lifecycle service
    ↓
Validation + concurrency controls
    ↓
Authoritative state transition
    ↓
Event/audit/outbox
    ↓
UI receives confirmed state
```

---

# 75. Concurrency

The UX must account for two actors acting simultaneously.

Example:

```text
Business sees:
KES 8,000 offer

Operator changes offer first

Business attempts Accept
        ↓
Server rejects stale action
        ↓
UI refreshes negotiation
        ↓
Business sees current state
```

The interface must not overwrite newer server state.

---

# 76. Idempotent Actions

Actions such as:

* submit
* confirm
* create
* upload
* report incident

must not accidentally create duplicates because the user tapped twice or the connection retried.

The UX should tolerate delayed feedback without encouraging repeated submission.

---

# 77. Trust UX Across Flows

Trust should appear only where it helps a decision.

Examples:

Business evaluating an operator:

> Identity verified
> Licence verified
> Vehicle verified

Operator evaluating a Job:

> Job value requires eligible transport.

Admin:

> Full verification/trust context.

Avoid showing trust information everywhere.

---

# 78. High-Value UX

As Job value increases, the UX should communicate additional requirements progressively.

The user should understand:

> **Additional verification is required for this Job.**

rather than seeing an unexplained disabled button.

For KES 250k+ Jobs, admin review is required under the approved model.

---

# 79. Cancellation Flow

Cancellation should not be treated as a trivial button.

Conceptually:

```text
Job
 ↓
Cancel
 ↓
Select reason
 ↓
Review consequence
 ↓
Confirm
```

Cancellation reputation effects remain system-driven (see §80).

The UX should avoid threatening language.

---

# 80. Cancellation Flagging

### Clarification (approval, 2026-09-10) — the approved rule

> **3 late cancellations — after `ASSIGNED` and before `AT_PICKUP` — or wasted
> trips, within a rolling 30-day window → admin-review flag.**

* The rule is tracked **per side** (operator side and business side counted
  separately).
* The UX must **not** create a generic "cancellation counter" that counts every
  cancellation. Cancelling an unengaged `REQUESTED` Job (before assignment) does
  **not** count toward this late-cancellation rule.
* Cancellation reputation effects remain **system-driven**. The UI may
  eventually surface the resulting administrative flag where appropriate, but
  must not invent a new reputation mechanism or present an arbitrary punishment
  counter.

Admin / Operations sees the relevant reputation / flag context.

---

# 81. Failure Flow

A failed Job is different from cancellation.

```text
Execution problem
     ↓
Unable to complete
     ↓
Report/record failure
     ↓
Job = FAILED
```

The UI must clearly distinguish:

* user cancellation
* operational failure
* dispute

---

# 82. Dispute Flow

A dispute is not merely an error message.

```text
Problem
   ↓
Incident
   ↓
Dispute where required
   ↓
Review
   ↓
Amicable resolution
OR
Admin resolution
   ↓
Resolved
OR
Resume where authorized
```

The interface must preserve chronology and evidence.

> See §58–§59 and §62.1: binding resolution above the Standard band, and
> `DISPUTED → RESUME`, are Platform Admin-only.

---

# 83. Completed Job

A completed Job should provide a final summary:

```text
Completed
────────────
Pickup
Destination
Cargo
Operator
Vehicle
Agreed price
Delivery confirmation
Evidence
Incidents
Rating
```

Relevant commission/statement information may be available to the appropriate party later, but transport fare and platform commission must not be conflated.

---

# 84. Flow Completion Matrix

| Flow                   | Primary Actor           | Start                 | Primary Completion    |
| ---------------------- | ----------------------- | --------------------- | --------------------- |
| Business onboarding    | Business                | Authentication        | Business workspace    |
| Staff setup            | Owner                   | Staff                 | Membership active     |
| Location setup         | Business                | Locations             | Location created      |
| Job request            | Business                | Request Transport     | `REQUESTED`           |
| Negotiation            | Business/Operator       | Job                   | `CONFIRMED`           |
| Assignment             | Operator/Group          | Confirmed Job         | `ASSIGNED`            |
| Pickup                 | Driver/Operator         | Assigned Job          | `PICKED_UP`           |
| Transit                | Driver/Operator         | Pickup                | `IN_TRANSIT`          |
| Destination            | Driver                  | Transit               | `AT_DESTINATION`      |
| Delivery               | Driver/Recipient        | Destination           | `DELIVERED`           |
| Completion             | System/authorized actor | Delivered             | `COMPLETED`           |
| Verification           | Subject/Reviewer        | Required verification | `VERIFIED`            |
| Incident               | Any permitted actor     | Job                   | Incident recorded     |
| Dispute                | Parties/Admin           | Incident              | Resolution/recovery   |
| Recipient confirmation | Recipient               | Scoped link           | Delivery confirmation |

---

# 85. Primary Flow Priority

For subsequent wireframe work, flows should be prioritized in this order.

## Priority 1 — Core Marketplace

1. Business creates Job
2. Operator discovers Job
3. Negotiation
4. Confirmation
5. Assignment

## Priority 2 — Physical Delivery

6. Driver active Job
7. Pickup
8. Pickup proof (OTP + band-dependent alternatives)
9. Custody
10. Transit
11. Destination
12. Recipient confirmation
13. Delivery (band-dependent proof)

## Priority 3 — Trust & Safety

14. Vehicle registration
15. Verification submission
16. Verification review
17. Verification remediation
18. Incident reporting
19. Dispute handling

## Priority 4 — Management

20. Business staff
21. Business locations
22. Operator locations
23. Group management
24. Vehicles
25. Statements

## Priority 5 — Administrative

26. Operations monitoring
27. High-value review
28. Restrictions
29. Audit
30. Recovery

---

# 86. Wireframe Readiness Requirements

Before Design Phase 3 begins, the following must be clear:

### Business

* onboarding
* dashboard/home
* Job creation
* Job detail
* negotiation
* monitoring
* delivery
* incident

### Operator

* home
* available work
* Job detail
* negotiation
* assignment
* vehicle
* verification

### Driver

* assignment
* active Job
* pickup
* pickup proof (OTP + band-dependent alternatives)
* custody
* transit
* destination
* delivery (band-dependent proof)
* incident

### Recipient

* scoped delivery page
* confirmation
* issue reporting

### Operations/Admin

* verification queue
* verification detail
* Job monitoring
* incident/dispute
* search
* administrative actions (with the Platform Admin-only boundary from §62.1)

---

# 87. UX Principles for the Next Phase

Wireframes must preserve:

## One primary action

Every major workflow screen should have an obvious next action.

## Progressive disclosure

Do not expose complexity until necessary.

## Context preservation

The user should not lose the Job they're working on.

## Server-confirmed reality

Never display an important state transition as complete before confirmation.

## Safety over speed

Where physical goods, custody, identity or high-value transport are involved, correctness wins.

## Human language

Use language users understand, not database terminology.

## Role-specific experience

Do not force all users into one generic dashboard.

---

# 88. Open Design Questions for Phase 3

These are deliberately **design questions**, not unresolved product architecture.

### 1. Job status vocabulary

What exact human-facing labels should represent the 14 backend states?

### 2. Job timeline

What visual treatment best communicates:

* current
* completed
* upcoming
* cancelled
* failed
* disputed?

### 3. Negotiation

Should the interaction resemble:

* chat
* offer cards
* timeline
* combination?

### 4. Location entry

What is the easiest Kitengela-friendly method for entering pickup/destination?

### 5. Operator discovery

How much operator information should appear on a response card?

### 6. Trust presentation

How should verified facts and trust level be visually distinguished?

### 7. Evidence

When should photo/document capture be inline versus a dedicated screen?

### 8. Active Job

What information is essential enough to remain visible throughout execution?

### 9. Pickup / delivery proof

How should the UI present the Standard vs. Elevated+ proof requirement (and the
Standard-band operator-attested fallback) so it is understandable at the moment
of handover without exposing internal mechanics?

These questions must be resolved through design, not by altering the product architecture.

---

# 89. Explicit Non-Goals

This flow specification does not introduce:

* AI dispatch
* automatic route optimization
* continuous GPS tracking
* wallet
* escrow
* in-app transport fare custody
* native apps
* complex fleet management
* payroll
* automated insurance claims
* autonomous pricing
* nationwide logistics workflows
* predictive analytics
* standalone driver accounts
* recipient accounts
* WhatsApp as system of record
* new pickup/delivery proof mechanisms beyond the approved matrices

---

# 90. Design Phase 2 Exit Criteria

Phase 2 is complete when:

* all primary role journeys are mapped;
* happy paths are mapped;
* major exception paths are mapped;
* the 14 Job states have UX treatment requirements;
* verification states have UX treatment requirements;
* the pickup proof matrix (OTP + band-dependent alternatives) is explicitly represented;
* the delivery proof matrix is explicitly represented;
* custody flow is represented;
* recipient flow is represented;
* incident/dispute paths are represented;
* high-value review is represented;
* Platform Admin-only actions (`DISPUTED → RESUME`, binding above-Standard dispute resolution) are explicitly bounded;
* role/context switching is represented;
* authorization boundaries are preserved;
* offline/server-confirmed behavior is represented;
* no new product requirements have been silently introduced.

---

# 91. Approval Gate

**DESIGN PHASE 2 — APPROVED WITH CLARIFICATIONS (2026-09-10).**

The review against `docs/phase-0/`, `docs/phase-1/`, `docs/phase-2/`,
`docs/design-brief.md`, and `docs/design-phase-1-ia.md` found **no product
contradictions**. The five corrections in §0.1 are folded in and are additive /
presentation-level only. This approval confirms:

1. The user journeys accurately represent the approved Fikisha product.
2. The Job lifecycle remains authoritative (14 states, §1.1).
3. Business, Operator, Group Manager, Driver, Operations Officer, Platform Admin
   and Recipient experiences are correctly differentiated.
4. Driver remains a role-scoped workspace rather than an account type.
5. Verification remains separate from trust.
6. Pickup and delivery proof matrices and custody are correctly represented
   (§38–§40, §44).
7. `DISPUTED → RESUME` and binding above-Standard dispute resolution are
   Platform Admin-only (§58–§59, §62.1).
8. Recipient remains accountless and Job-scoped.
9. Negotiation remains the authoritative in-app workflow; history is immutable.
10. WhatsApp / SMS remain communication channels; SMS is the default OTP carrier.
11. Exceptions and recovery paths are represented without inventing new states.
12. No product, legal, commercial or architectural decision has been changed.

Upon this approval, the next phase is:

> **Design Phase 3 — Wireframes & Interaction Structure**

which will translate these flows into screen inventories and low-fidelity
layouts, starting with the highest-priority Business → Operator → Driver →
Recipient delivery journey.

**Design Phase 3 has not started.** Do not proceed to wireframes until separately
instructed.
