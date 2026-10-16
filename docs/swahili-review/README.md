# Swahili review list

**Founder decision 20 (2026-10-14):** review every Swahili string before the
pilot launch. This folder is that list.

**File:** `swahili-review.csv`, compiled 2026-10-15. Open it in Excel, Google
Sheets or LibreOffice; it is UTF-8 with a byte-order mark, so Swahili and
symbols display correctly.

## What's in it

**1,096 strings**, one row each, covering everything built so far:
- `main`;
- the Commission & Statements stack (PRs #15 to #18);
- the open PRs #13 (follow-ups) and #14 (group driver pool). Their 10 new
  strings are marked in the `source` column.

| Area (namespace) | Strings | What it covers |
|---|---:|---|
| `jobs` | 280 | Creating, negotiating, assigning and delivering a job; driver screens |
| `admin` | 137 | Platform Admin console |
| `ops` | 123 | Operations Officer console, staff panel on a job |
| `statements` | 109 | Commission statements: payee and staff screens |
| `org` | 103 | Businesses, operator profile, groups, vehicles, verification |
| `common` | 72 | Navigation, buttons, language, offline |
| `incidents` | 71 | Reporting issues, disputes |
| `errors` | 50 | Error messages (can appear on any screen) |
| `recipient` | 46 | The recipient's no-account link page |
| `auth` | 38 | Sign-in, authenticator (MFA) |
| `negotiation` | 30 | Offer threads |
| `messages` | 25 | Messages inbox |
| `landing` | 12 | Public landing page |

## Columns

| Column | Meaning |
|---|---|
| `namespace`, `key` | Where the string lives in `frontend/src/i18n/locales/` |
| `screens` | The screen(s) or components that show it. "(dynamic)" means the key is chosen at run time, such as a status label. "Error message (any screen)" is an error that can appear wherever the action is tried. "not found in code (possibly unused)" means nothing references it; check before spending time on it |
| `english` | The English source |
| `swahili` | The current Swahili, written by Claude and not yet reviewed by a native speaker |
| `flags` | Automatic checks: `same as English` (possibly untranslated), `missing Swahili`, `placeholders differ` |
| `source` | `this branch`, or the open PR branch the string comes from |
| `reviewer_ok (Y/N)` | For the reviewer: is the Swahili right as it stands? |
| `suggested_swahili` | For the reviewer: a better wording when the answer is N |
| `reviewer_notes` | For the reviewer: anything else, such as tone, a term to use everywhere, or context needed |

**Keep `{{name}}` placeholders exactly as written.** The app fills them in, for
example `{{amount}}` becomes "KSh 250". Words around them can move.

## What the checks found

- **Missing Swahili:** 0.
- **Placeholders differ:** 0.
- **Same as English:** 5, all expected:
  - "07XX XXX XXX" (a phone format);
  - "Kiswahili" (the language's own name);
  - three "WhatsApp" labels.
- **Possibly unused:** 47: `org` 30 (older organisation screens), `common` 7,
  `jobs` 5, `auth` 2, `ops` 2, `negotiation` 1. They are still listed, but
  are a lower priority.

## Suggested review order

1. **Operator and driver screens first.** Swahili is the default language for
   operators (`locales.operator_default = sw`), so get these right before
   anything else: the `jobs` driver and work strings, `negotiation`,
   `statements` (payee part), and `common`.
2. **Recipient page** (`recipient`). The recipient may have no account and has
   never seen the app before.
3. **Errors** (`errors`). Short and seen at stressful moments.
4. **Business screens** (the rest of `jobs`, `incidents`, `messages`).
5. **Staff consoles** (`ops`, `admin`, `statements.admin`). These are used by
   Fikisha staff, so they matter less for the pilot.

Words worth agreeing once and using everywhere: kamisheni (commission),
taarifa ya malipo (statement), dereva (driver), mwendeshaji (operator),
kikundi (group), kazi (job), nauli (fare), paybill.

## Regenerating

Re-run before launch, once the open PRs are merged, so the list matches
`main` exactly:

```bash
cd frontend
node scripts/swahili-review.mjs                      # this branch only
node scripts/swahili-review.mjs --ref origin/<branch> # plus an open PR's new strings
```

A string added on a `--ref` branch is included. A string edited there, but
already present here, is not; regenerating on `main` after merging covers that.
Applying the reviewer's corrections is a separate small change to the `sw/*.json`
files.
