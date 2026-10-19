# Maps — plan and decisions (2026-10-19)

**Source:** the founder's request on 2026-10-19: businesses pick their
locations on a map when registering them (and name them), pick each job's
destination on a map, keep pickup as the saved-location dropdown, and
operators use the pins to navigate. **MD-1 to MD-6 approved as recommended,
2026-10-19.** This record is the authoritative copy.

## What already exists

- `BusinessLocation`, and a job's pickup and destination `JobLocation`, have
  `lat`/`lng`; the API accepts them. Nothing sets them yet.
- A saved location's coordinates are copied into the job's pickup
  (assessment part 2), so pinned branches give jobs a pinned pickup.
- Job detail and Work discovery currently send `lat`/`lng` to every operator
  who can see the job. `JobLocation.geo_state` has `CAPTURED`,
  `NOT_CAPTURED` and `COARSENED`.
- Maps are a provider-agnostic seam (Phase 1 OD-6, technology-stack §
  "Map tiles"); none is wired. The design allows navigation only: no live
  tracking, no route optimisation, nothing implying continuous GPS.

## Decisions (approved as recommended)

| # | Decision | Approved answer |
| --- | --- | --- |
| MD-1 | Map provider | **MapTiler** (OpenStreetMap data) for the pilot, behind config so it can move to Google Maps if coverage on the Kitengela outskirts is thin. OpenStreetMap's public tiles in local dev only. The privacy notice must name the provider, and the cross-border transfer needs legal sign-off (legal-scope §3; REQUIRES VALIDATION). |
| MD-2 | Exact pins before assignment | **Approximate until assigned**: an operator who is not the assigned operator (or a driver of the assigned group) gets coordinates rounded to ~1 km and `geo_state = COARSENED`; the business, the assigned side and staff get exact ones. Same principle as decision 7 (phones). |
| MD-3 | Pin required | **Required when the map is available**; a typed address is the fallback only when the map cannot load (offline, provider down: NFR-AVAIL-4). |
| MD-4 | Place-name search (geocoding) | **Later** (a separate provider choice, OD-6). Pan, zoom and "Use my location" for the pilot. |
| MD-5 | Pins outside the pilot area | **Warn, not block.** |
| MD-6 | Navigation hand-off | **Yes**: an "Open in Google Maps" button, only when the operator taps it, carrying just the destination (or pickup) coordinates. |

## Plan (one branch, one PR to `main`)

- **M-1 — Map picker.** Leaflet, loaded only on screens with a map. Tile URL
  and attribution from config (`VITE_MAP_TILE_URL`,
  `VITE_MAP_ATTRIBUTION`). Pan/zoom to place a pin; "Use my location" asks
  the browser's permission each time. If tiles cannot load, the screen says
  so and the typed address still works.
- **M-2 — Business locations.** Adding (and editing) a location: pin on the
  map, a name, the type, an optional landmark or address. Existing
  locations without a pin get an "Add the pin" prompt, as does the pickup
  dropdown when the chosen location has none.
- **M-3 — Destination.** The create-job destination step gets the picker and
  a landmark/address field. The backend sets `geo_state = CAPTURED` when a
  location has coordinates. Out-of-area pins warn.
- **M-4 — Navigation.** Job detail and the driver's Current job show the
  pins and an "Open in Google Maps" button. Exact coordinates only for the
  parties in MD-2; everyone else gets the coarse area, with tests that a
  non-assigned operator never receives exact coordinates.
