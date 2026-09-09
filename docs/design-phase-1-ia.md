# FIKISHA

## Design Phase 1 — Information Architecture & Navigation

**Status:** APPROVED WITH CLARIFICATIONS — 2026-09-09
**Design-track position:** Design Phase 1 (the formal IA deliverable)
**Depends on:** Approved Product Phases 0–2C · Approved Design Phase 0 (`docs/design-brief.md`)
**Supersedes:** the working-draft IA circulated for review
**Product:** Fikisha
**Pilot:** Kitengela, Kajiado County + environs

---

# 0. Document Lineage & Status

## 0.1 Where this document sits

| Phase | Artifact | Defines |
| --- | --- | --- |
| **Design Phase 0** | `docs/design-brief.md` | The design foundation / context and the design constitution — brand meaning, audiences, personality, EN/SW voice, visual-identity deliverable list, engineering constraints, domain state vocabularies. It is the approved Design Phase 0 / context artifact for the whole design track. |
| **Design Phase 1** | `docs/design-phase-1-ia.md` (this document) | The information architecture and navigation structure derived from that foundation — role workspaces, primary/secondary navigation, the Job's internal IA, mobile vs. desktop, the recipient experience. |
| **Design Phase 2** | *(not started)* | User Flows — the actual journeys through the IA. Begins only after this document is approved. |

There is a single Design Phase 0 artifact — `docs/design-brief.md`. This document
does not introduce a competing one. Any later reference to "Design Phase 0"
means `docs/design-brief.md`.

## 0.2 Review outcome

This IA was reviewed against the approved product architecture in `docs/phase-0/`,
`docs/phase-1/`, `docs/phase-2/`, and `docs/design-brief.md`. **No product
contradictions were found.** Phase 1 is approved **with clarifications**; the
clarifications are additive and presentation-level only — none changes an
approved product decision from Phases 0–2C.

## 0.3 Clarifications incorporated at approval (2026-09-09)

| # | Clarification | Where it now lives |
| --- | --- | --- |
| 1 | **Driver is a role-scoped workspace**, not a standalone account type or registration path. A driver is a `GroupMembership` with `role = DRIVER`, or an individual operator acting as their own driver. A group DRIVER sees Work/discovery only when the group is in `DRIVER_ACCEPTS` mode. | §4.3, §7, §26 note |
| 2 | **Verification "Needs Attention"** maps to effective states `INFO_REQUESTED`, `REJECTED`, and `EXPIRED` (where effective expiry applies). The full authoritative state vocabulary is preserved; the five user-facing buckets are a presentation layer only. | §16 |
| 3 | **The Job timeline must handle off-happy-path states.** Design Phase 2 must provide user-facing rendering for every real Job state, including `DRAFT`, `CANCELLED`, `FAILED`, `DISPUTED`. The 14-state backend lifecycle stays authoritative and unchanged. | §13 |
| 4 | **Design Phase 0 lineage** is explicit: `docs/design-brief.md` is the approved Design Phase 0 / context artifact; this file is the formal Design Phase 1 deliverable. | §0.1 |
| 5 | **Design brief vs. IA relationship** is recorded near the top: the brief is the design foundation / constitution; the IA is the navigation structure derived from it. | §0.1 |

## 0.4 What this update did not touch

No application code, backend models, APIs, database schemas, or frontend
components were modified. No approved product decision from Phases 0–2C was
reopened. Where this document could have implied a change, it instead states the
authoritative product rule and, where genuinely open, records an open design
question for a later phase.

---

# 1. Purpose

This phase defines the information architecture and navigation model for Fikisha.

It answers:

* What are the major areas of the product?
* What does each role need access to?
* What belongs in primary navigation?
* What belongs in secondary navigation?
* What should be immediately visible?
* Which concepts are shared across roles?
* Which experiences should be role-specific?
* How should mobile and desktop navigation differ?

This phase does **not** define final colors, typography, component styling, or high-fidelity screens.

---

# 2. IA Principles

The architecture follows six rules.

## 2.1 Jobs are the center of the product

The fundamental product object is the **Job**.

Most future functionality should eventually connect back to a job:

```text
Business
   ↓
Job
   ├── Negotiation
   ├── Operator
   ├── Vehicle
   ├── Custody
   ├── Delivery
   ├── Evidence
   ├── Incidents
   ├── Rating
   └── Commission
```

The interface should therefore make Jobs easy to find and understand.

---

# 2.2 People should navigate by task, not by database model

Users should not see navigation such as:

* Verification Records
* Vehicle Control Entities
* Evidence Objects
* Operating Location Entities

unless those concepts genuinely represent a user task.

The interface translates the domain model into human tasks.

---

# 2.3 Role determines the workspace

Fikisha has multiple fundamentally different users.

The same backend may contain the same Job, but the interface should expose different information depending on the actor.

For example:

```text
Business
→ "My deliveries"

Operator
→ "Available work"

Driver
→ "Current job"

Operations Officer
→ "Operations"

Admin
→ "Control"
```

---

# 2.4 Active work comes before historical information

A user with an active Job should not have to search for it.

Active work receives priority.

Historical information remains accessible but secondary.

---

# 2.5 Navigation should remain shallow

Avoid deep menu trees.

Target:

```text
Home
  ↓
Section
  ↓
Item
```

rather than:

```text
Dashboard
 → Operations
   → Jobs
     → Active
       → Assigned
         → Vehicle
           → Verification
```

Complexity should be handled through contextual navigation inside a resource.

---

# 2.6 Mobile navigation must prioritize the next action

On mobile, navigation should not attempt to expose the entire application.

The bottom navigation should represent the user's most frequent destinations.

Everything else can live behind:

* More
* Profile
* contextual menus
* resource-level navigation

---

# 3. Global Product Structure

The conceptual Fikisha information architecture is:

```text
FIKISHA
│
├── Home
│
├── Jobs
│   ├── Active
│   ├── Available
│   ├── Requests
│   └── History
│
├── Messages / Negotiations
│
├── People / Organizations
│
├── Vehicles
│
├── Locations
│
├── Verification
│
├── Operations
│
├── Earnings / Statements
│
├── Notifications
│
└── Account
```

Not every role sees every section.

This is a **conceptual IA**, not a universal navigation menu.

---

# 4. Role Workspaces

Fikisha should have six primary UX workspaces.

## 4.1 Business Workspace

Mental model:

> **My transport and deliveries**

Primary concerns:

* create transport request
* monitor active Jobs
* negotiate
* see assigned operator
* monitor delivery
* confirm completion
* review history
* manage staff
* manage locations
* view statements

---

## 4.2 Operator Workspace

Mental model:

> **Find and execute transport work**

Primary concerns:

* available Jobs
* requests
* negotiations
* accepted Jobs
* assigned Jobs
* vehicles
* verification
* operating bases
* earnings
* reputation

---

## 4.3 Driver Workspace

Mental model:

> **My current assignment**

The driver experience should be intentionally narrower.

Primary concerns:

* current Job
* next action
* pickup
* custody
* transit
* destination
* delivery
* incident reporting

The driver should not be forced to navigate through operator-management features.

### Clarification (approval, 2026-09-09) — Driver is a role-scoped view, not an account type

The Driver workspace is a **role-scoped view of the product**, not a separate
account model or registration path. In the approved identity model a driver is
either:

* a `GroupMembership` with `role = DRIVER`, when operating inside an operator
  group; or
* an individual operator acting as their own driver.

Consequences for design:

* Do **not** design a standalone "Driver Sign Up" or a separate driver account
  model. There is no independent driver registration — a person reaches the
  Driver workspace through the existing identity / operator model, by role.
* The Driver workspace is entered by **role and context**, not by account type.
  When the same person also holds operator-management responsibilities, the
  organization-context switch (§18) governs which workspace they are in.
* **Authorization rule preserved:** a group DRIVER sees Work / job-discovery only
  when the group is configured for `DRIVER_ACCEPTS` mode. In
  `MANAGER_ASSIGNS` mode the driver has no discovery surface and sees only
  assignments made to them. Design Phase 2 user flows inherit this rule and must
  not present a discovery experience to a driver whose group does not permit it.
* Server-side authorization remains authoritative; the Driver workspace's
  narrower navigation is a usability choice layered on top of it, never the
  enforcement mechanism.

---

## 4.4 Group Manager Workspace

Mental model:

> **Manage our transport operation**

Primary concerns:

* available work
* Jobs
* drivers
* vehicles
* group members
* assignments
* verification
* statements

Group functionality remains deliberately minimal.

---

## 4.5 Operations Workspace

Mental model:

> **What needs attention?**

Primary concerns:

* Jobs requiring intervention
* verification queue
* incidents
* disputes
* exceptions
* operators
* businesses
* vehicles
* search
* audit/recovery

---

## 4.6 Platform Admin Workspace

Mental model:

> **Control and safeguard the platform**

Primary concerns:

* users
* organizations
* permissions
* verification
* trust
* Jobs
* incidents/disputes
* configuration
* commission
* audit
* system health

Admin navigation can be substantially denser than the consumer/operator experience.

---

# 5. Business Navigation

Recommended mobile structure:

```text
┌──────────────────────────────┐
│ Home                         │
├──────────────────────────────┤
│ Jobs                         │
├──────────────────────────────┤
│ Messages                     │
├──────────────────────────────┤
│ More                         │
└──────────────────────────────┘
```

### Home

Shows:

* active Jobs
* Jobs needing action
* recent activity
* quick action: Request transport

The primary CTA should be immediately accessible.

---

### Jobs

Organized around:

```text
Active
Requests
Completed
Cancelled
```

Avoid exposing the entire 14-state lifecycle as navigation.

The lifecycle is represented visually within a Job.

---

### Messages

Contains:

* negotiation conversations
* structured offers/counteroffers
* relevant Job context

WhatsApp remains an external communication channel and is not the authoritative Fikisha record.

---

### More

Potential destinations:

* Business profile
* Staff
* Locations
* Statements
* Notifications
* Help
* Settings

---

# 6. Operator Navigation

Recommended mobile structure:

```text
┌──────────────────────────────┐
│ Home                         │
├──────────────────────────────┤
│ Work                         │
├──────────────────────────────┤
│ My Jobs                      │
├──────────────────────────────┤
│ More                         │
└──────────────────────────────┘
```

---

## Home

Primary content:

### Available work

and/or:

### Current job

The home screen should immediately answer:

> **What work can I take or what am I currently doing?**

---

## Work

Contains available/requested opportunities.

Potential filters:

* vehicle class
* location
* date
* cargo requirements
* value band
* eligibility

The matching logic determines what is actually offered; the UI must not imply unsupported autonomy.

---

## My Jobs

Contains:

* active
* upcoming
* completed
* cancelled/disputed

---

## More

Contains:

* Vehicles
* Verification
* Operating locations
* Group
* Earnings/statements
* Profile
* Notifications
* Settings

---

# 7. Driver Navigation

The driver experience should be even simpler.

Recommended:

```text
┌──────────────────────────────┐
│ Current Job                  │
│                              │
│ [Primary next action]        │
│                              │
│ Pickup → Transit → Delivery  │
│                              │
├──────────────────────────────┤
│ Jobs                         │
├──────────────────────────────┤
│ More                         │
└──────────────────────────────┘
```

The **Current Job** should dominate.

If there is no active assignment:

> No active job

with relevant available/request information if the driver's permissions allow it.

> **Clarification (approval, 2026-09-09):** "if the driver's permissions allow
> it" is governed by the group's assignment mode — the available/request surface
> appears only for a group DRIVER whose group is in `DRIVER_ACCEPTS` mode, or for
> an individual operator acting as their own driver. A driver in a
> `MANAGER_ASSIGNS` group sees "No active job" with no discovery affordance. See
> §4.3.

---

# 8. Group Manager Navigation

Group managers need access to group resources without turning Fikisha into fleet-management software.

```text
Home
Jobs
Team
More
```

### Team

Contains:

* Members
* Drivers
* Vehicles
* Group operating context

There should be no payroll, scheduling, or complex fleet-management navigation in MVP.

---

# 9. Operations Officer Navigation

Desktop/tablet-first workspace:

```text
Operations
│
├── Overview
├── Jobs
├── Verification
├── Incidents
├── Disputes
├── Businesses
├── Operators
├── Vehicles
├── Search
└── Audit / Activity
```

The exact permission boundary remains governed by backend authorization.

Operations Officers are not Platform Admins.

---

# 10. Platform Admin Navigation

Recommended structure:

```text
Control
│
├── Overview
├── Users & Organizations
├── Operators
├── Businesses
├── Vehicles
├── Verification
├── Trust & Reputation
├── Jobs
├── Incidents & Disputes
├── Commission
├── Configuration
├── Audit
└── System
```

Dangerous actions should never be hidden merely because the UI is simplified.

Authorization remains server-side.

---

# 11. Job Information Architecture

The Job should have a consistent internal structure.

Conceptually:

```text
JOB
│
├── Overview
├── Activity
├── Negotiation
├── Transport
├── Custody
├── Delivery
├── Evidence
├── Incidents
└── Completion
```

Not every tab is visible at every stage.

The interface should progressively reveal sections as they become relevant.

---

# 12. Job Overview

Every Job should provide a strong summary.

The user should immediately understand:

* Job status
* pickup
* destination
* cargo
* vehicle requirement
* date/time
* assigned operator/driver
* assigned vehicle
* agreed price
* next action

A Job should never require opening multiple screens to answer:

> **"What's happening with this delivery?"**

---

# 13. Job Timeline

The lifecycle should be represented as a human-readable timeline.

Conceptually (happy path):

```text
Request
   │
   ● Negotiation
   │
   ● Confirmed
   │
   ● Assigned
   │
   ● Pickup
   │
   ● In transit
   │
   ● Destination
   │
   ● Delivered
   │
   ● Completed
```

The timeline becomes the primary visual representation of progress.

Technical lifecycle states remain authoritative underneath.

## 13.1 Authoritative lifecycle

The backend Job lifecycle has **14 states** and they remain authoritative and
unchanged by this document:

```text
DRAFT · REQUESTED · NEGOTIATING · CONFIRMED · ASSIGNED · AT_PICKUP ·
PICKED_UP · IN_TRANSIT · AT_DESTINATION · DELIVERED · COMPLETED ·
CANCELLED · FAILED · DISPUTED
```

The IA must not collapse, remove, rename, or redefine any of these at the
product / domain level. The human-readable timeline above is a **presentation**
of the happy-path progression; it is not a redefinition of the state machine.

## 13.2 Off-happy-path states — required in Design Phase 2

### Clarification (approval, 2026-09-09)

The timeline illustration covers only the happy path. Design Phase 2 **must**
provide a user-facing rendering for every real Job state, explicitly including
the ones the happy-path timeline does not show: `DRAFT`, `CANCELLED`, `FAILED`,
`DISPUTED`. User-facing terminology and visual treatment for these will be
designed in Phase 2 **while preserving the authoritative state semantics** —
Phase 2 chooses the words and the visual language, not the meaning.

Minimum UX principles established now:

| State | The user-facing rendering must clearly communicate | Notes |
| --- | --- | --- |
| **DRAFT** | The Job has **not yet entered** the active / requested workflow — it is being prepared and is not visible to operators. | Distinct from `REQUESTED`. Typically only the creating Business (and permitted staff) sees it. |
| **CANCELLED** | The Job **was cancelled** and did not complete. It must be **visually distinct from successful completion** (`COMPLETED`), never shown with success styling. | Cancellation reason / actor surfaced where the viewer is permitted to see it. |
| **FAILED** | The Job **did not complete successfully**. Provide appropriate **contextual next actions where permitted** (e.g. raise an incident, contact operations, re-request). | Distinct from both `CANCELLED` (deliberate stop) and `COMPLETED`. |
| **DISPUTED** | The Job is **under dispute / review**; **normal completion semantics are suspended** until the dispute is resolved or the Job is administratively resumed. Ordinary progress actions should be unavailable or clearly gated. | The timeline should show the dispute as an overlay on the last known progress point, not as erasure of prior steps. |

No additional lifecycle states are invented. Terminal and exception states are
rendered on the same timeline component as a distinct terminal/branch treatment
rather than as separate screens.

---

# 14. Contextual Actions

The primary action on a Job should depend on the user's role and current state.

Examples:

### Business

**Request transport**

**Accept counteroffer**

**Confirm**

**Report issue**

**Confirm delivery**

---

### Operator

**Counteroffer**

**Accept job**

**Assign driver**

**Start pickup**

**Report issue**

---

### Driver

**I'm at pickup**

**Confirm pickup**

**Start transit**

**I've arrived**

**Confirm delivery**

---

### Operations

**Review**

**Resolve**

**Restrict**

**Intervene**

---

This creates a consistent principle:

> **One primary next action, supported by secondary actions.**

---

# 15. Vehicle Information Architecture

Vehicles belong primarily under the operator/group workspace.

Structure:

```text
Vehicles
│
├── Active
├── Under Repair
├── Suspended
└── Inactive
```

Vehicle detail:

```text
Vehicle
│
├── Overview
├── Capacity
├── Control / Operator
├── Verification
└── History
```

The UI should make the distinction between:

* vehicle information
* operator control
* verified facts

clear.

---

# 16. Verification Information Architecture

Verification should be accessible from:

1. the user's profile
2. the vehicle
3. relevant operating location
4. admin/operations queue

But there should be **one underlying verification model**.

User-facing structure:

```text
Verification
│
├── Required
├── Submitted
├── Under Review
├── Verified
└── Needs Attention
```

The user should not have to understand `VerificationRecord` or `VerificationDecision`.

## 16.1 Authoritative verification state vocabulary

### Clarification (approval, 2026-09-09)

The five user-facing groupings above are a **presentation layer only**. They do
not replace or alter the authoritative backend state model, which is:

```text
NOT_SUBMITTED
SUBMITTED
IN_REVIEW
INFO_REQUESTED
VERIFIED
REJECTED
EXPIRED
```

`EXPIRED` may apply as an **effective** state folded in deterministically on read
from the record's stored state plus its expiry — the presentation must reflect
the effective state, not only the last persisted label.

## 16.2 Grouping map

| User-facing bucket | Underlying / effective state(s) | Meaning to the user |
| --- | --- | --- |
| **Required** | `NOT_SUBMITTED` for a domain that is required for this subject | "You still need to submit this." |
| **Submitted** | `SUBMITTED` | "Received, not yet being reviewed." |
| **Under Review** | `IN_REVIEW` | "A reviewer is looking at it." |
| **Verified** | `VERIFIED` (and not effectively expired) | "Independently checked; recorded as fact." |
| **Needs Attention** | `INFO_REQUESTED`, `REJECTED`, `EXPIRED` (where effective expiry applies) | "Action or remediation is needed from you." |

"Needs Attention" is therefore precisely the set of records whose
underlying / effective state requires user action or remediation:
`INFO_REQUESTED` (reviewer asked for more), `REJECTED` (submission not accepted),
and `EXPIRED` (validity has lapsed). Optional (non-required) domains that were
never submitted are **not** surfaced under "Required" or "Needs Attention".

## 16.3 Verification is not trust

Verification records **facts** that were independently checked. It does not, in
this IA or in the product, compute trust, reputation, eligibility, or job
eligibility. "Verified" is never presented as a generic trust score, badge of
merit, or ranking. Trust & Reputation is a separate concept with its own future
surface (§10, §26).

---

# 17. Operating Locations

Operating locations should be presented as:

```text
My operating locations
│
├── Main stage/base
├── Other stages/bases
├── Yards
└── Waiting areas
```

The distinction is important:

> An operating location is a place/context, not proof of ownership or membership.

The UI must avoid implying that being associated with a Stage means the platform has verified formal membership unless that fact actually exists.

---

# 18. Organization Switching

Some users may have multiple contexts.

For example:

```text
User
├── Business
└── Operator
```

Or a user may belong to a group.

The interface should make the active context obvious.

Example:

> **Operating as: ABC Transport**

with a controlled context switch.

Never silently perform an action in the wrong organization context.

---

# 19. Notifications

Notifications should not become a primary navigation destination that users must constantly monitor.

They are supporting infrastructure.

Notification center:

```text
Notifications
│
├── Action required
├── Job updates
├── Verification
├── Messages
└── System
```

Important notifications should lead directly to the relevant resource.

Example:

> **Your vehicle verification needs attention**

→ Open vehicle verification.

---

# 20. Search

Search becomes increasingly important for Operations/Admin.

For businesses/operators, search should initially remain contextual.

Operations/Admin can eventually search:

* Job ID
* phone number
* registration
* business
* operator
* group
* incident
* verification record

Search results must respect authorization.

---

# 21. Account / Settings

Account should contain:

```text
Account
│
├── Profile
├── Language
├── Notifications
├── Security
└── Help
```

MFA/security controls appear where appropriate.

Business-specific and operator-specific settings should live in their respective workspaces rather than being dumped into a universal settings page.

---

# 22. Recipient Architecture

Recipient experience should intentionally have **no normal application navigation**.

The scoped link opens directly into:

```text
Delivery
│
├── Delivery information
├── Current status
├── Driver/operator information
├── Verify / receive
└── Report an issue
```

The recipient should not encounter:

* login
* signup
* dashboard
* marketplace
* unrelated Jobs
* platform settings

The link itself is the navigation mechanism.

---

# 23. Desktop vs Mobile

## Mobile

Prioritize:

* current work
* next action
* Jobs
* messages
* notifications
* profile/context

Use bottom navigation where appropriate.

---

## Desktop

Prioritize:

* persistent sidebar
* broader information visibility
* tables
* split views
* multi-column workflows
* operations tools

Desktop should **not simply be a stretched mobile interface**.

---

# 24. Navigation State

Navigation must account for:

* loading
* empty
* error
* offline
* unauthorized
* unavailable
* pending verification
* completed
* suspended
* deleted/inactive resources

Every major destination needs a meaningful state.

---

# 25. Navigation Anti-Patterns

Do not create:

* universal mega-navigation
* five-level nested menus
* separate navigation for every backend model
* dashboards full of meaningless statistics
* duplicated Job sections
* hidden critical actions
* role permissions enforced only by hiding links
* navigation that assumes constant connectivity
* a recipient account requirement
* desktop-first operator workflows

---

# 26. Proposed Primary Navigation Matrix

| Role               | Primary                        | Secondary                                                    |
| ------------------ | ------------------------------ | ------------------------------------------------------------ |
| Business           | Home, Jobs, Messages           | Staff, Locations, Statements, Account                        |
| Operator           | Home, Work, My Jobs            | Vehicles, Verification, Locations, Earnings, Account         |
| Driver             | Current Job, Jobs              | Profile, Help                                                |
| Group Manager      | Home, Jobs, Team               | Vehicles, Verification, Statements, Account                  |
| Operations Officer | Operations, Jobs, Verification | Incidents, Disputes, Businesses, Operators, Vehicles, Search |
| Platform Admin     | Control, Jobs, Verification    | Trust, Incidents, Users, Configuration, Commission, Audit    |

This is the **structural model**, not the final visual navigation.

> **Clarification (approval, 2026-09-09):** the "Driver" row is a **role-scoped
> view**, reached by role and context, not a separate account type or sign-up
> path (§4.3). Its "Work"-style discovery affordance exists only when the
> driver's group is in `DRIVER_ACCEPTS` mode, or the person is an individual
> operator acting as their own driver.

---

# 27. Design Decisions Preserved

This IA explicitly preserves approved product decisions:

* Job remains the central domain object.
* Roles remain distinct.
* Operator groups remain minimal.
* Stage/base/yard remains a first-class concept.
* Verification remains separate from trust.
* Verified facts are not represented as generic "trust."
* Recipient requires no account.
* WhatsApp remains a communication channel, not system of record.
* Mobile-first PWA remains the client.
* English and Swahili remain first-class.
* No native applications.
* No complex fleet-management system.
* No wallet/escrow.
* No AI dispatch.
* No route-optimization UI.
* No continuous GPS tracking UI.
* Server-side authorization remains authoritative; navigation scoping is a
  usability layer, never the enforcement mechanism.
* Driver is a role-scoped workspace over the existing identity/operator model,
  not a standalone account type (§4.3).
* The 14-state Job lifecycle remains authoritative and is not collapsed,
  renamed, or redefined by any presentation choice (§13.1).
* The authoritative verification state vocabulary is unchanged; the user-facing
  buckets are presentation only (§16.1).

---

# 28. What This Phase Does NOT Decide

This phase does not yet decide:

* final visual identity
* colors
* typography
* logo treatment
* exact components
* exact button styles
* animations
* final copy
* pixel-level layouts
* final dashboard cards
* final Job card appearance

Those belong to later design phases.

---

# 29. Next Phase

Once this IA is approved, the next deliverable is:

## Design Phase 2 — User Flows

We will map the actual journeys.

Priority flows:

### Business

1. Sign up
2. Create Job
3. Receive/counteroffer
4. Confirm transport
5. Monitor Job
6. Confirm delivery
7. Report incident

### Operator

1. Onboard
2. Add vehicle
3. Complete verification
4. Discover work
5. Negotiate
6. Accept Job
7. Assign driver/vehicle
8. Execute Job
9. Complete delivery
10. View earnings

### Driver

1. Receive assignment
2. Navigate to pickup
3. Confirm arrival
4. Complete pickup OTP
5. Record custody
6. Start transit
7. Arrive
8. Confirm delivery
9. Report incident if necessary

### Operations

1. Review verification
2. Monitor Jobs
3. Handle exceptions
4. Review incidents
5. Resolve disputes
6. Intervene/recover

### Recipient

1. Open scoped link
2. Review delivery
3. Verify receipt
4. Confirm delivery or raise incident

Design Phase 2 also inherits the clarifications recorded in §0.3:
Driver flows are role-scoped (no standalone driver sign-up; discovery gated by
`DRIVER_ACCEPTS`), Job flows must render `DRAFT` / `CANCELLED` / `FAILED` /
`DISPUTED`, and verification flows use the §16.2 grouping map over the
authoritative state vocabulary.

---

# 30. Approval Gate

**Design Phase 1 is complete only when the navigation model is approved.**

Approval should confirm:

* role workspaces are correct
* primary navigation is correct
* Job information architecture is correct
* recipient experience is appropriately minimal
* operator/driver mobile navigation is appropriate
* operations/admin separation is correct
* no product decisions were accidentally changed

**Status: APPROVED WITH CLARIFICATIONS (2026-09-09).** The review against
`docs/phase-0/`, `docs/phase-1/`, `docs/phase-2/`, and `docs/design-brief.md`
found no product contradictions. The five clarifications in §0.3 are folded in
and are additive / presentation-level only. Upon this approval, Design Phase 2
(User Flows) can begin.

---

# Appendix A. Open Design Questions

Recorded here rather than resolved, per the rule that documentation finalization
must not change a product rule:

1. **"Design Phase 0" naming.** This document treats `docs/design-brief.md` as
   the approved Design Phase 0 / context artifact (§0.1). If the design track
   later wants a separately named `docs/design-phase-0-*.md`, that is a
   restructuring decision for the design lead — the content of record is
   unchanged.
2. **Reputation surface wording.** §10 and §26 list "Trust & Reputation" as an
   admin area. The user-facing vocabulary for operator reputation (as distinct
   from verification) is deferred to the phase that builds Trust; this IA only
   reserves the navigation slot and keeps it separate from Verification.
3. **Recipient timeline exposure.** §22 gives the recipient a "Current status"
   view. How much of the §13 timeline (and which off-happy-path states) the
   recipient sees is a Design Phase 2 flow decision, constrained by the recipient
   minimal-scope rule.
