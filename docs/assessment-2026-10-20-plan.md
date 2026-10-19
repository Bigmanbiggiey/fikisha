# Founder assessment — 2026-10-20: plan and decisions

**Source:** the founder's testing on 2026-10-20. **LD-1 to LD-5 approved as
recommended, 2026-10-20.** This record is the authoritative copy. Built on
the maps branch (PR #24).

## The assessment

1. Progress updates appear automatically for sender, operator and receiver;
   nobody refreshes.
2. The destination is filled from the map pin; the sender chooses between
   using the pin and naming the destination.
3. One Kenyan phone rule on every contact entry point: `07…`, `01…`, or
   `+254…` resolving to `0…`; 10 digits after conversion, otherwise refused
   (`+254100350768` → `0100350768` valid; `+25472345689` → `072345689`, 9
   digits, refused).
4. The operator side sees the recipient's contact only after pickup is
   confirmed, and no contact once the job is completed.
5. Pickup and delivery need both parties: the operator marks it, the other
   party confirms by code, signature or photo; high-value cargo needs all
   three.
6. Admin icons: Monitor eye, Verification tick, Commission coins, Operations
   settings wheel, Audit magnifier.

## Decisions (approved as recommended)

| # | Decision | Approved answer |
| --- | --- | --- |
| LD-1 | How updates arrive | Job screens re-check about every 10 s while open and visible, and at once on focus or reconnect. No server push infrastructure. |
| LD-2 | Phone storage | Stored `+254…` internally; accepted and shown as `07…` / `01…`; exactly 10 digits after conversion, otherwise refused. Existing non-conforming numbers are reported, not changed. |
| LD-3 | Contacts while disputed | Hidden from the operator side; the dispute runs through Fikisha staff. |
| LD-4 | Proof table | Below. Retires the operator-only STANDARD pickup fallback (a change to chain-of-custody §4 / user flows §38–44, by the founder). |
| LD-5 | Where signatures are taken | On the driver's phone, handed over; the sender can also confirm in their own app. |

### Proof table (LD-4)

| Band | Pickup: the sender confirms | Delivery: the recipient confirms, the operator photographs |
| --- | --- | --- |
| STANDARD (≤ 50,000) | one of: code, signature, photo | code **or** signature (photo optional) |
| ELEVATED (≤ 250,000) | code **or** in-app confirmation, **+** operator goods photo | code **+** photo |
| HIGH / VERY_HIGH | code **+** signature **+** photo | code **+** signature **+** photo |

### Contact visibility (assessment item 4, LD-3)

Business and staff always see every contact. The assigned operator, group
manager and driver:

| Job status | Sender (pickup) contact | Recipient contact |
| --- | --- | --- |
| before assignment | no | no |
| ASSIGNED, AT_PICKUP | yes | no |
| PICKED_UP, IN_TRANSIT, AT_DESTINATION, DELIVERED | yes | yes |
| COMPLETED, CANCELLED, FAILED, DISPUTED | no | no |

## Plan (one branch, one commit per part)

- **L-6 Admin icons** — new `settings`, `coins`, `search` icons; menu mapping.
- **L-1 Live progress** — shared refresh setting on job screens.
- **L-2 Destination: pin or name** — a choice on the destination step; the
  server needs a pin or a name.
- **L-3 Kenyan phone rule** — one validator on every entry point, a shared
  input and display helper, a `phones_report` command.
- **L-4 Contact timing** — the table above, with tests per status.
- **L-5 Two-party custody** — config `custody_proof_rules`, one pickup
  confirmation endpoint, the attested fallback retired (410), driver /
  business / recipient screens showing and enforcing what is required.
