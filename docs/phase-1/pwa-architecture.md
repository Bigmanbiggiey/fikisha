# PWA Architecture

Implements Phase 0 `D-CLIENT-1`, `NFR-PERF-4/5`, `NFR-ACC-*`, and Phase 1 brief
§23.

Built specifically for: **Android, low-end devices, poor / intermittent
connectivity, camera use, mobile-first operator screens.** The MVP client is a
**responsive Progressive Web App** — installable, no app-store builds.

**The brief's rule (§23):** *do not pretend the app can safely perform every
operation offline.* This document draws a hard line between **offline-safe** and
**server-confirmed** actions.

---

## 1. Build & shell

| Aspect | Choice |
|--------|--------|
| Framework | React + TypeScript + Vite (see [technology-stack.md](technology-stack.md) §3); `preact/compat` as the first size lever |
| Bundler / SW | Vite + `vite-plugin-pwa` (Workbox) |
| Routing | Route-level **code splitting**; the operator custody flow is its own small chunk that can be cached aggressively |
| Styling | Tailwind (purged); large tap targets (≥ 44 px), high contrast, one-hand reach (NFR-ACC-3) |
| Server state | TanStack Query (cache + retry + background refetch) |
| Offline queue | `idb` (IndexedDB) — a mutation queue + a photo queue |
| i18n | `react-i18next` + ICU; `en` / `sw` catalogs (see [localization.md](localization.md)) |
| Maps | MapLibre GL **lazy-loaded** only on screens that need a map; a **static-map image + pin** fallback on the lowest-end devices (feature-detected / configurable) |
| Bundle budget | app shell (first load) target **< 200 KB gzipped** JS; each route chunk small; images as WebP; system fonts (no web-font download) |

The **app shell** (nav, auth gate, i18n runtime, offline indicator) is precached
and versioned by the service worker.

---

## 2. Service worker & caching

| Content | Strategy | Notes |
|---------|----------|-------|
| App shell (HTML/JS/CSS, versioned) | **Precache** (Workbox `precacheAndRoute`) | atomic swap on new version |
| Reference data: enums, config lookups, zone list, i18n catalogs (`GET /api/v1/reference`, `/locales/*`) | **StaleWhileRevalidate**, short max-age | invalidated by an app "config changed" signal |
| Read API GETs that tolerate slight staleness: my jobs list, job detail, profile, discovery list | **NetworkFirst** with a ~3 s timeout → cache fallback; every cached response is badged "as of HH:MM" in the UI | never used to make a decision the server must confirm |
| Map tiles | **CacheFirst**, bounded (LRU, size cap) | Kitengela is small; a modest tile cache covers it |
| Evidence thumbnails | **CacheFirst**, short cap | full/HIGH-PII media is never cached |
| Auth / mutations / transitions / OTP | **NetworkOnly** | never cached; see §3 |

- SW update: `skipWaiting` + a non-intrusive "New version — reload" toast.
  **Never auto-reloads while a custody flow is in progress** (a `beforeunload`
  guard + a "flow in progress" flag).
- Storage pressure: the SW respects a total quota; on `QuotaExceededError` it
  evicts tile + thumbnail caches first, never the mutation/photo queue.

---

## 3. Offline-safe vs server-confirmed actions (the hard line — brief §23)

### 3.1 Offline-safe (queued locally, replayed on reconnect)

A **small whitelist**. Each queued item carries a client-generated
`Idempotency-Key`, the payload, an `If-Match` version captured at queue time, and
a created timestamp (stored as `reported_time` server-side — NFR-AUD-4).

| Action | Why safe to defer | On replay |
|--------|-------------------|-----------|
| **Mark `AT_PICKUP` arrival** | Advisory; the gating proof is the pickup OTP which is done online | server records it with `reported_time`; if the job moved on, surfaces a sync issue |
| **Mark `IN_TRANSIT`** | Progress marker; no money, no custody handover | idempotent replay |
| **Mark `AT_DESTINATION` arrival** | Progress marker | idempotent replay |
| **Capture a custody / condition photo** | The photo is evidence, not a gate; better captured than lost | uploaded via the evidence endpoint with its idempotency key; attached to the relevant custody event |
| **Draft an incident** (type + text + photos) | Reporting; not state-changing until submitted | submitted online, or auto-submitted on reconnect with a confirmation prompt |
| **Save a job draft** (business) | `DRAFT` is not visible to anyone | synced |
| **Compose a negotiation note** (text only, not the offer) | just text | attaches when the online offer is placed |

The offline queue **caps** photos (e.g. 20 items / 50 MB); when near the cap the
UI **blocks new captures** with a clear "sync required" message and offers to
retry the upload.

### 3.2 Server-confirmed only (blocked when offline, with a clear message)

| Action | Why it must be online |
|--------|----------------------|
| **Login / OTP request + verify** | Security; needs the live challenge |
| **Any negotiation action** — propose, counter, **accept**, reject | Race-sensitive (the confirm race); money terms; must reflect authoritative state |
| **`CONFIRMED`, `ASSIGNED`** transitions | Eligibility + high-value approval re-checked server-side at that instant |
| **`PICKED_UP`** (pickup OTP confirmation) | The OTP is issued and verified server-side; custody-liability moment |
| **`DELIVERED`** (recipient verification / POD) | Recipient OTP verified server-side; custody handover moment |
| **`COMPLETED` acceptance**, ratings | Triggers the commission ledger |
| **Any commission / statement action** | Financial |
| **Verification submission decisions**, trust confirmations, admin actions | Authoritative, audited |
| **Evidence *view*** of HIGH-PII | Authorization + access logging server-side |

When offline and a blocked action is attempted, the UI shows a specific message
(localized): *"You need a connection to confirm pickup"* / *"Ungependa muunganisho
kuthibitisha kupokea mzigo"* — not a generic error — and, where applicable, keeps
the safe part (e.g. it still lets the driver capture the goods photo into the
queue).

---

## 4. Sync engine

```
On reconnect (navigator.onLine + a successful health ping):
  1. Drain the mutation queue in FIFO order:
       POST/PATCH with the stored Idempotency-Key and If-Match.
       - 2xx  -> remove from queue; refresh affected queries
       - 409 / 412 (job moved on) -> move the item to the "Sync issues" tray
         with a human explanation and a "review" action (never silently drop)
       - 5xx / network -> leave in queue, backoff, retry
  2. Drain the photo queue (evidence uploads), same idempotency handling.
  3. Re-run background query refetch so the UI reflects server truth.
```

- **Conflicts are surfaced, never auto-merged** (brief §23). The "Sync issues"
  tray tells the driver e.g. *"This job was cancelled by the business while you
  were offline — your arrival note was not applied."*
- The queue is per-device; it survives app restarts (IndexedDB); it is cleared
  on logout.
- A visible **offline / syncing / synced** indicator in the app bar at all
  times.

---

## 5. Camera & image handling (brief §23)

- Capture: `<input type="file" accept="image/*" capture="environment">`
  (universally supported on Android; iOS Safari too). No custom camera stack.
- Client-side processing before upload: draw to a `<canvas>`, **downscale** to
  ≤ 1600 px on the long edge, **compress** to JPEG/WebP ~200–500 KB, show a
  preview. This keeps uploads small on 3G and cheap for the user's data bundle
  (NFR-PERF-5). EXIF is dropped by the canvas re-encode (privacy — the server
  also strips it).
- Upload: chunked/resumable is **not** built for the MVP (files are already
  small); a failed upload retries from the photo queue.
- Multiple photos per custody step allowed (condition documentation).

---

## 6. Geolocation (privacy — [chain-of-custody.md](chain-of-custody.md) §5)

- Requested **lazily**, only when the driver taps a custody action, via a single
  `navigator.geolocation.getCurrentPosition` with a timeout.
- Denied / unavailable → the step proceeds; `geo_state = NOT_CAPTURED`.
- **Never** requested on load; **never** watched (`watchPosition` is not used);
  **no** background location.

---

## 7. Install, updates, notifications

- **Web App Manifest**: name, short_name, icons (maskable), `display:
  standalone`, theme colour, `start_url` with a source tag.
- Install prompt: capture `beforeinstallprompt`, show a contextual "Add Fikisha
  to your home screen" after a successful first job; iOS gets an "Add to Home
  Screen" instruction card (no `beforeinstallprompt` on iOS).
- **Notifications**: the primary channels are **SMS + WhatsApp + an in-app inbox
  polled on foreground** (see [notification-architecture.md](notification-architecture.md)).
  **Web Push** is **SHOULD, not MUST** — supported on Android Chrome, **absent or
  limited on iOS** and older Android WebViews. Nothing time-critical depends on
  Web Push; it is an enhancement for Android users.

---

## 8. Performance targets on low-end Android (NFR-PERF-2/3/4)

| Metric | Target | Lever |
|--------|--------|-------|
| First load (cold, 3G) | interactive < ~5 s | small shell, code-splitting, system fonts, no map on first screen |
| Repeat load (SW cached) | < 1.5 s | precache |
| Interactive action p95 (create job, place offer, mark a custody step) | < 2 s on a typical connection | small payloads, optimistic UI for the *safe* actions only |
| Discovery list p95 | < 3 s | cursor pagination, server-side filtering, cached reference data |
| JS on the custody route | minimal chunk | isolate from the map/admin bundles |

A **device-lab test on representative Kitengela-tier phones** in early Phase 2 is
a tracked risk ([technical-risks.md](technical-risks.md)); if the React bundle is
a problem, the Svelte spike (technology-stack §3) is the contingency.

---

## 9. Admin in the PWA

The admin area is a lazily-loaded route group, behind an admin session
(phone-OTP + TOTP). It is **not** offline-capable (NetworkOnly) — admins work
from stable connections. Heavy admin tooling (config, audit browsing) can also be
done in Django Admin (see [admin-architecture.md](admin-architecture.md)).
