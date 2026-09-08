# Operator Model

The operator model is built around **discovered practice**: operators work from
physical locations (stages, bases, yards, waiting areas), obtain work through
direct channels, and negotiate. The platform represents that reality rather than
imposing a fleet abstraction.

---

## 1. Operator

### 1.1 What an operator is (MVP)

Two shapes, both supported in the MVP:

**Individual operator** — a rider or driver, usually the owner of their vehicle,
sometimes an authorised driver of someone else's vehicle. One person, one
account.

**Operator group (CONFIRMED IN SCOPE — D-OPR-GRP-1)** — a yard/base owner, small
fleet, SACCO, or partnership controlling several vehicles and drivers. Minimal
but real:

- **Group profile**: name, type (`YARD_OWNER / FLEET / SACCO / PARTNERSHIP`),
  primary-contact user, operating base(s), payout details, status, aggregate
  standing.
- **Members**: `GroupMembership(user_id, role: OWNER / MANAGER / DRIVER)`. **Each
  member driver is individually identity- and licence-verified and needs their
  own Certificate of Good Conduct** — the group is not a shortcut.
- **Vehicles**: owned by the group; **each vehicle individually verified**
  (including the heavy-class NTSA requirements in §2.2).
- **Assignment**: a job assigned to a group **must name a specific driver +
  specific vehicle** at ASSIGNED. Value-band gating uses the **assigned driver's**
  trust level; the group's aggregate standing is a monitoring/suspension lever.
- **Commission**: statement goes to the group; internal driver settlement is
  off-platform for MVP.
- **Out of MVP scope**: internal payroll, shift scheduling, inter-group
  transfers.

See [users-and-roles.md](users-and-roles.md) §3.6 and
[domain-model.md](domain-model.md) for the full shape.

### 1.2 Operator profile fields
- Identity: full name, national ID / passport number + document image, date of
  birth, photo.
- Contact: phone (primary identifier), alternate phone, optional email.
- Licence: licence number, class(es), issue/expiry, document image. Commercial /
  PSV endorsements where applicable — **which are legally required per vehicle
  class REQUIRES KENYAN PROFESSIONAL VALIDATION**.
- **DCI Certificate of Good Conduct** — CONFIRMED 2026-09-08 (D-TRU-7): required
  for all operators; **mandatory before L2 / Elevated-band eligibility**.
- Operating base(s): one or more OperatingBase references (see §3).
- Service areas: the zones/routes the operator will accept work in (see §4).
- Availability: current status + optional schedule (see §5).
- Trust level + verification state (see [trust-and-safety.md](trust-and-safety.md)).
- Reputation summary (ratings, completed jobs, incident history).
- Payout details for commission settlement (mobile-money number) — access
  controlled.

---

## 2. Vehicles

### 2.1 Vehicle types (from the founder brief; extensible)
`MOTORCYCLE`, `PICKUP`, `CANTER`, `TIPPER`, `LORRY`, `SEMI_TRUCK`, `TRAILER`,
`OTHER` (free-text label required when OTHER).

The set is **configurable** by administrators so new classes can be added
without a code change.

### 2.2 Vehicle fields
- Type (from the set above) + optional sub-descriptor (e.g. "3-tonne canter",
  "flatbed trailer").
- Registration / number plate.
- Capacity:
  - Payload weight (kg / tonnes) — **required**.
  - Load volume or bed dimensions (L×W×H) — required for pickups/canters/lorries/
    trailers, optional for motorcycles.
  - Special features (tail-lift, refrigeration, covered/open, crane/HIAB, cattle
    body, etc.) as tags.
- Documents: registration/logbook, inspection certificate, insurance certificate
  — **mandatory set REQUIRES KENYAN PROFESSIONAL VALIDATION**.
- **Heavy classes (canter / tipper / lorry / semi-truck / trailer, tare
  > ~3,048 kg):** additionally require proof of **NTSA Commercial Service Vehicle
  Operator Licence + speed limiter + vehicular telematics + valid inspection +
  at least third-party insurance** as part of vehicle verification
  (see [legal-scope.md](legal-scope.md) §3.3 — exact list REQUIRES VALIDATION).
  A heavy vehicle without these is not surfaced for jobs.
- Ownership/association: owned by this operator, or operator is an authorised
  driver (with an association record + evidence).
- Verification state (per [trust-and-safety.md](trust-and-safety.md)).
- Status: active / inactive / under-repair.

### 2.3 Vehicle ↔ operator association
- An operator may register multiple vehicles.
- A vehicle may (later, via groups) be driven by more than one operator; **MVP
  WORKING ASSUMPTION:** one vehicle is associated with one operator account.
- Association where the operator is not the owner requires an
  association-verification record (owner consent evidence).

---

## 3. Operating base / stage / yard

A **first-class entity** — `OperatingBase`.

- Type: `STAGE` (typical for riders), `BASE`, `YARD`, `WAITING_AREA` (typical for
  drivers/trucks).
- Fields: name (as known locally), type, geo-coordinates, area/zone, optional
  landmark description, optional photo.
- One or more operators associate with a base. A base may be shared by many
  operators (a stage).
- Bases are **verifiable** (does this stage/yard exist, is the operator actually
  known there) — see verification domains in
  [trust-and-safety.md](trust-and-safety.md). Base verification can be
  low-tech during the pilot (founder/administrator local knowledge).
- Bases are used in **discovery and matching**: proximity of an operator's base
  to a job's pickup is a primary ranking signal.

**Why this matters:** it mirrors how customers find operators today ("go to the
stage / call the yard"). It also gives the platform a real-world anchor point
for an operator, which supports trust and dispute resolution.

---

## 4. Service areas

- The geographic scope an operator is willing to work.
- **WORKING ASSUMPTION for MVP representation:** a list of named zones (the pilot
  area subdivided into a small number of zones by the founder) plus an optional
  maximum radius/distance from base. Polygon drawing is a FUTURE CONSIDERATION.
- A job is shown to an operator if its pickup (and optionally destination) falls
  within, or close to, a declared service area.
- Long-haul operators (semi-trucks, trailers) may declare inter-zone corridors
  rather than a local radius.

---

## 5. Availability

- States: `AVAILABLE`, `BUSY` (on a job), `UNAVAILABLE` (off).
- `BUSY` is set automatically when a job moves to ASSIGNED/AT_PICKUP and cleared
  on COMPLETED/CANCELLED/FAILED — **WORKING ASSUMPTION**; operators can still be
  shown jobs for later slots.
- Optional simple schedule (working days/hours) — **OPEN QUESTION** whether the
  pilot needs it or a manual toggle is enough. Recommend: manual toggle only for
  MVP.
- Availability is advisory for discovery; it does not hard-block an operator from
  seeing or accepting a job.

---

## 6. Job discovery for operators

An operator sees a job when **all** of the following hold:

1. The operator has at least one **verified** vehicle whose **type** satisfies
   the job's required vehicle type (or an accepted equivalent) **and** whose
   **capacity** meets the job's required capacity.
2. The job's pickup is within/near one of the operator's **service areas** or a
   configurable distance of one of their **bases**.
3. The operator's **trust level** meets the job's required level (driven by
   declared value / high-value threshold — see
   [trust-and-safety.md](trust-and-safety.md)).
4. The operator is not suspended/restricted, and identity + licence verification
   are valid (not expired).

Discovery is a **filtered list the operator browses and acts on** for MVP.
Ranking signals (not hard filters): base proximity, reputation, recent
responsiveness, availability. **Automated matching / auto-assign / auction
bidding are FUTURE CONSIDERATION.**

Direct off-platform contact after a match is expected and permitted; the job and
its records still live on the platform.

---

## 7. Operator lifecycle

```
REGISTERED  → documents submitted
            → PENDING_VERIFICATION  (admin queue)
            → VERIFIED              (identity + licence + ≥1 vehicle + base)
            → ACTIVE                (can discover & accept jobs, at trust level 1)
            → (progression)         trust level 2, 3, ...  via completed history + admin confirm
            → RESTRICTED / SUSPENDED (admin action, with reason + duration)
            → OFFBOARDED
```

Expiry of a licence, insurance, or inspection document moves the affected
capability back to a limited state until renewed (e.g. an expired vehicle
insurance makes that vehicle ineligible; an expired licence makes the operator
ineligible).

---

## 8. Status summary

| Item | Category |
|------|----------|
| Individual operators supported | CONFIRMED DECISION |
| Operator groups / sub-fleets (minimal: group + membership + group-owned vehicles + per-driver verification + driver-named assignment + statement to group) | CONFIRMED 2026-09-08 (D-OPR-GRP-1) |
| OperatingBase (stage/base/yard/waiting area) is first-class and used in matching | CONFIRMED DECISION (follows from discovered practice) |
| Vehicle type set is configurable, starts from the brief's list | CONFIRMED DECISION |
| Service areas = named zones + optional radius for MVP | WORKING ASSUMPTION (Kitengela zone list deferred — D-PIL-5; treat pilot area as one zone until supplied) |
| Availability = manual toggle for MVP | WORKING ASSUMPTION |
| Discovery = filtered browsable list, no auto-assign | CONFIRMED DECISION for MVP |
| DCI Certificate of Good Conduct required (mandatory before Elevated) | CONFIRMED 2026-09-08 (D-TRU-7) |
| Heavy vehicles must show NTSA operator licence + speed limiter + telematics + inspection + insurance | CONFIRMED the platform verifies these — exact list REQUIRES KENYAN PROFESSIONAL VALIDATION |
| Which licence classes / vehicle documents are legally mandatory | REQUIRES KENYAN PROFESSIONAL VALIDATION |
