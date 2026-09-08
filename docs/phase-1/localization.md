# Localization (English + Swahili)

Implements Phase 0 `D-PIL-4`, `FR-A-10`, `NFR-ACC-1`, and Phase 1 brief §24.

**English and Swahili from day one.** Swahili is **prominent on operator-facing
screens**. Nothing user-visible is a hardcoded string.

---

## 1. Scope

Localized surfaces:

| Surface | How |
|---------|-----|
| PWA UI (all screens, both user and admin) | `react-i18next` + ICU MessageFormat; message **keys** only in components |
| API validation & domain errors | the API returns a stable `code` + `params`; **the client renders the localized string** (so the same error is correct in either language regardless of caller) |
| SMS / WhatsApp / in-app notification text | server-rendered from `notification_template(key, locale, channel)` using the recipient's `locale` (see [notification-architecture.md](notification-architecture.md) §4) |
| Recipient link page & short terms | server- or client-rendered in the recipient's `locale` (from the job / `Accept-Language`), switchable |
| Dates, times, numbers, currency | `Intl.*` with `Africa/Nairobi` / `KES` |
| PDF-ish artefacts (eTIMS invoice, statement) | rendered from templates; **English for the tax/legal artefact** (eTIMS/KRA), with a Swahili summary block — exact requirement is REQUIRES VALIDATION (tax advisor) |

Out of scope for the MVP: additional languages, a Sheng register (NFR-ACC-2 —
future), right-to-left (not applicable).

---

## 2. Catalog structure

```
web/src/locales/
  en/
    common.json      auth.json       jobs.json        negotiation.json
    custody.json     incidents.json  ratings.json     commission.json
    verification.json  trust.json    admin.json       errors.json
    notifications.json (client-rendered in-app copy)
  sw/
    (same files)
```

- **Namespaces** load per route (code-split) so a low-end device isn't parsing
  every string up front.
- **Keys** are dotted and descriptive: `jobs.create.cta`,
  `custody.pickup.otp_hint`, `errors.job.transition_not_allowed`.
- **ICU MessageFormat** for plurals / selects / interpolation:
  `"jobs.list.count": "{count, plural, =0 {No jobs} one {# job} other {# jobs}}"`.
- A **lint rule** (`i18next/no-literal-string` or an ESLint custom rule) fails CI
  on a user-visible literal in a component.
- Every `errors.*` key mirrors a server `code` (contract test: the set of server
  `code`s ⊆ the set of `errors.*` keys in **both** locales).

---

## 3. Server-side templates

- `notification_template(key, locale, channel, subject?, body, whatsapp_template_name?)`
  — one row per `(key, locale, channel)`. `body` uses the **same ICU
  placeholders** as the client catalogs so wording stays consistent across
  channels.
- WhatsApp: `whatsapp_template_name` points at a **BSP-approved** template in the
  matching language; the `body` is the reference copy.
- SMS: kept short and segment-aware; the resolver reports segment count for cost
  accounting.
- Validation error strings are **not** stored server-side as prose — the API
  returns `code` + `params`; the client localizes. (The exceptions are pure
  server-to-user channels — SMS/WhatsApp/email — which do render prose from
  templates.)

---

## 4. Locale resolution & default

```
user.locale  (persisted, per user; PATCH /me { locale })
   ⟶ else  Accept-Language header (first supported of en, sw)
   ⟶ else  'sw' for operator-facing entry points (D-PIL-4)
   ⟶ else  'en'
```

- A **language switcher** is always visible (app bar) and persists the choice.
- New operator accounts default to `sw`; new business accounts default from
  `Accept-Language` then `en`.
- The recipient link page offers a one-tap `EN | SW` toggle; default from the
  job's `recipient` locale hint or `Accept-Language`.

---

## 5. Formatting

| Thing | Rule |
|-------|------|
| Currency | `Intl.NumberFormat('sw-KE' | 'en-KE', { style: 'currency', currency: 'KES', maximumFractionDigits: 0 })` → `KSh 4,000`. Internally money is **integer minor units**; the display layer divides by 100 and formats. |
| Numbers | locale grouping via `Intl.NumberFormat`. |
| Dates / times | `Intl.DateTimeFormat` with `timeZone: 'Africa/Nairobi'`; the server sends UTC ISO-8601, the client renders EAT. Relative times ("2 h ago") localized via a small helper. |
| Phone numbers | displayed in a consistent Kenyan format; stored E.164. |
| Weekday / month names | from `Intl` per locale. |
| Distances / weights | metric (km, kg / tonnes); unit labels from the catalog. |

---

## 6. Content & translation quality

- Swahili is a **first-class catalog**, not machine-translated as a shortcut.
  **Professional translation + review** of all catalogs and notification
  templates is a Phase 2 task, with extra care on:
  - custody / OTP wording (must be unambiguous at the doorstep),
  - incident and dispute wording (evidentiary),
  - the recipient short terms and any consent text (**REQUIRES legal review** —
    legal-scope §4).
- Operator-facing critical flows (discovery, negotiate, custody steps, earnings)
  use **short, plain** phrasing that reads clearly on a small screen and
  translates cleanly (NFR-ACC-1).
- Keys are stable; copy changes don't churn keys.

---

## 7. Testing

- Snapshot/render tests run the key screens in **both** locales; a missing key
  fails the test (no silent fallback to the key name in CI).
- Contract test: server `code` set ⊆ `errors.*` keys in `en` **and** `sw`.
- A pseudo-localization mode (elongated strings) in dev to catch layout overflow
  on small screens.
- Notification template coverage test: every `template_key` used by a handler
  has rows for `en` and `sw` on each channel it targets.
