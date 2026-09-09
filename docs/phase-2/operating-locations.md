# Operating Locations (Phase 2B)

Operators work from physical places — a **stage** (typical for riders), a
**base** or **yard** (typical for drivers and trucks), or a **waiting area**.
Phase 2B makes that place a first‑class entity (`OperatingBase`), as Phase 0
`operator-model.md` §3 requires, without building any GIS.

---

## 1. A place, not a possession

`OperatingBase` has **no owner column**. A stage is shared; a yard has a
keeper — but neither is "owned" in the data model. Presence is expressed
separately:

- **`OperatingBase`** — the place: `name`, `type` (`STAGE | BASE | YARD |
  WAITING_AREA`), optional `lat`/`lng`, optional `zone`, `landmark`,
  `created_by` (who added it).
- **`BaseMembership`** — a party's claim of operating presence at a base: an
  `operator` **or** a `group` (exactly one, enforced by a DB `CHECK`), a
  free‑text `role` (`"owner"`, `"member"`, …), and `status` (`ACTIVE` /
  `INACTIVE`).

## 2. Formal membership vs. physical presence (brief §20)

Phase 0 explicitly recognises that an operator's physical operating location can
be established **through means other than formal membership of a shared stage**.
The model keeps that distinction open:

| Way to establish an operating location | How |
| --- | --- |
| Join an existing shared stage | `POST /operators/{id}/bases {base_id, role}` → an `ACTIVE` `BaseMembership` |
| Declare your own base/yard | `POST /operating-locations {name, type, …}` — the base exists, created by you; you may (but need not) also add a `BaseMembership` |
| A group declares presence | `POST /groups/{id}/bases {base_id, role}` |

Creating an `OperatingBase` does **not** require any `BaseMembership`, and a
`BaseMembership` is **not** required for a base to exist. Ending a presence sets
the membership `INACTIVE` (the row is kept — history).

> **Deferred to a later phase:** `ServiceArea` (the zones/corridors an operator
> will accept work in) — that is a Jobs‑discovery input and is not needed until
> discovery exists. The `Zone` foundation (below) is what a `ServiceArea` will
> reference.

## 3. Authorization

| Action | Rule |
| --- | --- |
| read / list a base | any authenticated user — a stage is a public place |
| create a base | any authenticated user **with an `OperatorProfile`**, or a platform admin |
| edit a base | the base's `created_by` user, or a platform admin (a shared stage is not editable by every operator who works there) |
| associate an operator with a base | the operator's own user (or admin) — checked as `operator.update` on that profile |
| associate a group with a base | a group `OWNER`/`MANAGER` (or admin) — checked as `group.update` |

Full matrix: [`organization-authorization.md`](organization-authorization.md) §3.

## 4. Geography — `Zone`, not GIS

- Zones are part of Platform Configuration (Phase 1 domain‑architecture).
  `Zone` (`config_zone`) is a minimal admin‑extensible lookup: `code`,
  `name_en`, `name_sw`, `active`, `sort_order`.
- A migration seeds **one** zone, `KITENGELA` ("Kitengela and environs" /
  "Kitengela na maeneo jirani"). The founder's zone breakdown is deferred
  (D‑PIL‑5) — the pilot area is one zone until it is supplied. Adding zones is a
  data change, not a migration.
- `BusinessLocation.zone` and `OperatingBase.zone` are nullable FKs to `Zone`.
- Coordinates are **plain `lat`/`lng` decimals** (nullable). Phase 1
  *recommended* PostGIS `GEOGRAPHY` for proximity ranking in job discovery;
  Phase 2B uses the documented plain‑column fallback (database‑design §6),
  because (a) proximity ranking is a discovery concern that does not exist yet,
  and (b) the brief (§19) says **do not build a GIS, route optimisation, or
  geofencing**. Adopting PostGIS is a clean later change. Recorded as ADR‑2B‑04.

## 5. Kitengela is configuration, not code

`"Kitengela"` appears only as: the seeded `Zone.code`, a string in
`platform_config.defaults` (`pilot.area`, already there since 2A), and test
fixtures. No business logic branches on it. Serving a second area later is a
`Zone` row plus config, not a code change.

## 6. API summary

```
GET    /api/v1/operating-locations            ?type=STAGE&zone=KITENGELA   -> {data, page}
POST   /api/v1/operating-locations            {name, type, lat?, lng?, zone_code?, landmark?}
GET    /api/v1/operating-locations/{id}
PATCH  /api/v1/operating-locations/{id}       {name?, type?, lat?, lng?, zone_code?, landmark?}

GET    /api/v1/operators/{id}/bases
POST   /api/v1/operators/{id}/bases           {base_id, role?}
DELETE /api/v1/operators/{id}/bases/{membership_id}

GET    /api/v1/groups/{id}/bases
POST   /api/v1/groups/{id}/bases              {base_id, role?}
DELETE /api/v1/groups/{id}/bases/{membership_id}
```

All mutations write an audit row in the same transaction
(`operating_location.created` / `.updated` / `.operator_associated` /
`.group_associated` / `.association_ended`).
