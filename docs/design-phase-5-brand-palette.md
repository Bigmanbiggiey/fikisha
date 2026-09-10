# FIKISHA — Design Phase 5A — Brand Palette Proposal

**Status:** PALETTE PROPOSED — AWAITING FOUNDER APPROVAL
**Design track:** Phase 5A (Brand Palette Approval Gate — the first gate of Phase 5)
**Depends on / authoritative (in order):** `CLAUDE.md` · `docs/team-skills-policy.md`
· `docs/design-brief.md` (Design Phase 0) · `docs/design-phase-1-ia.md` ·
`docs/design-phase-2-user-flows.md` · `docs/design-phase-3-wireframes.md` ·
`docs/design-phase-4-visual-system.md` (approved visual-system baseline, commit
`4a5353e`).

> **This is the Brand Palette Approval Gate.** It contains **no** production
> tokens, no Tailwind config, no CSS, no React changes, no dependency changes, no
> component migration. It proposes **2–3 palette directions** with reasoning,
> behaviour-in-context, and an accessibility assessment, for the Founder to
> **select / modify / approve**. Every hex below remains a **proposal**. Nothing
> here changes any product or architecture decision. `RESUME_PRIOR` and
> rating/reputation remain open/deferred (§9).

---

# 1. Phase 5 purpose

Design Phase 4 was approved as the visual-system baseline **with the final brand
palette explicitly deferred to this gate** (`design-phase-4-visual-system.md §6,
§36`). Phase 5 proceeds in controlled gates:

- **Phase 5A (this document)** — propose the final palette; **STOP** for Founder
  approval.
- **Phase 5B (not started)** — after approval, translate the approved system into
  production design tokens (primitive → semantic → component), still
  documentation + a tokens spec, no unreviewed component restyle.
- **Later gates** — component implementation, only on explicit Founder
  instruction.

Phase 5A converts the approved Phase 4 *visual direction* into an
implementation-ready *brand foundation* **without making an unapproved brand
decision**. The output is a decision aid: the Founder should be able to
understand each palette as a whole system, not approve isolated hex values.

---

# 2. Approved Phase 4 foundation (carried forward, unchanged)

| Approved in Phase 4 | Carried into Phase 5 |
| --- | --- |
| **Colour direction** — warm stone / neutral ground · near-black text · a grounded teal action colour · a Kajiado-clay identity accent · strict, **brand-independent** semantic status colours | the starting point for every option below; **not automatically final** |
| **Two-tier token model** — primitive → semantic → component; components reference semantic (+ a few `component.*`) tokens, never raw values | unchanged; the 5B token spec must follow it |
| **Status = colour + icon/shape + text**, never colour alone | unchanged; every option is designed to remain legible with colour removed |
| **Semantic status independent of the brand colour** — "brand colour must not become the meaning of *success*" | a hard rule for every option; success is a leaf-green distinct in hue and lightness from the brand teal, and always carries `✓` |
| **WCAG 2.2 AA floor**, higher on operator-critical flows / recipient page | §4; every option assessed in §5 |
| **Job-state, verification, connectivity semantic mappings** (Phase 4 §13, §16, §6.5) | preserved verbatim; only the underlying hues are proposed here |
| **Responsive contextual adaptation** (Phase 4 §21.2–21.3, §25) — Driver stays focused/action-dominant at every width; Operator may expand into a workspace layout where it aids coordination; **no** hard 480 px cap; never density for its own sake | unchanged; see §10 |
| **Light theme authoritative; dark not precluded** | every option's semantic tokens are mode-ready; no dark values proposed here |

**Current technical baseline (for context only — not modified):**
`frontend/tailwind.config.ts` carries a placeholder `brand` teal scale
(`#0f766e` at `700`) and the system-font stack, no semantic colours, no stone
scale. The Phase 4 provisional palette was never committed to source. Phase 5B
will replace this config **after** this gate.

---

# 3. Palette design criteria

From `design-brief.md §4, §6.2` and Phase 4:

1. **Personality first.** Reliable · local · modern · practical · confident ·
   human · trustworthy. The single most important attribute is
   **trustworthy / accountable** — "a reliable witness: calm, clear,
   evidence-minded." Restraint reads as competence for this audience.
2. **Sunlight-legible on a cheap LCD.** High contrast; no reliance on subtle
   tonal differences that vanish on a $60 phone. Warm off-white ground (not stark
   white — glare) and near-black text.
3. **Grounded, local, warm — not corporate, not neon.** Avoid over-formal
   blue-grey "freight forwarder" palettes and fintech/crypto neon. A saturated
   but *earthy* brand hue; a Kajiado-clay accent that belongs at a stage/yard.
4. **Brand ≠ status.** Brand colour = action/identity. Semantic colours = state.
   Success must **not** read as "the brand".
5. **Colour-blind-safe status.** Success / warning / danger / info / neutral must
   stay distinguishable in bright light and for CVD users — hue **plus** the
   mandatory icon/shape (Phase 4).
6. **Full status palettes.** Enough distinct, legible steps for: the 14 Job
   states, the 5 verification groups over 7 states, the trust-level ladder, and
   connectivity (online/offline/syncing/synced + sync-issue).
7. **Light theme flawless; structure not precluding a later dark theme.**
8. **Small, few-step scales** that map cleanly onto `tailwind.config`
   (`colors` 50–900) — decided at 5B, not here.

---

# 4. Accessibility criteria (hard constraint)

**WCAG 2.2 AA is the floor.** Every proposed palette is assessed against:

| Surface / element | Requirement |
| --- | --- |
| Normal body text | ≥ 4.5:1 |
| Large text (≥ 18.66 px bold / 24 px) | ≥ 3:1 |
| **Driver / Operator critical text**, **Recipient** body, **safety-critical action** labels | **target ≥ 7:1** where practical |
| Button text on its fill | ≥ 4.5:1 |
| Status chip: text+icon vs. its own bg | ≥ 4.5:1; chip bg vs. page ≥ 3:1 |
| Focus indicator | ≥ 3:1 against **both** adjacent colours |
| Borders that communicate a boundary | ≥ 3:1 |
| Light surfaces & tinted surfaces | text on them meets the row above |
| Disabled controls | exempt from contrast, but **always** carry a text reason (Phase 4) |

**Contrast figures below are computed (sRGB, WCAG formula) for the recommended
option and computed for the key pairs of the alternatives.** Per Phase 4, a full
per-pair check with **automated tooling on a low-cost device, in daylight** is a
**Phase 5B gate task** on whichever palette the Founder approves.

**Two adjustments apply to all three options** (surfaced by this assessment):

- **`success.solid` with white text:** a bright leaf-green (~`#1E8E3E`) yields
  ≈ 4.2:1 white — **below AA-normal**. All options use a **darker** green
  (~`#177A33`, ≈ 5.4:1 white) for `success.solid` and for `success.fg` on a
  tint. The bright green may be used only for a large `✓` glyph (large-text
  rule) or decoration.
- **`warning` chips:** white on mid-amber (~`#B5620B`) is ≈ 4.4:1 — marginal.
  All options render warning as **dark `.fg` + amber `.bg` tint + icon**; a
  **deep-amber `.solid` (~`#8A4A10`, ≈ 6.8:1 white)** is reserved for the one
  *strong* use — the `DISPUTED` header chip — so it stays prominent without a
  failing pair.

`danger.solid` (≈ 5.7:1 white) and `info.solid` (≈ 6.8:1 white) pass as-is in all
options.

---

# 5. Palette alternatives

Three directions. All keep **warm stone + Kajiado-clay + grounded teal** and the
approved personality. They differ in **character** — how warm, how bright, how
reserved — not in structure. Each lists: palette · rationale · strengths ·
weaknesses · accessibility · operational-UI implications · recommended use.

Scale roles (same for every option): `50` tint bg · `100` chip bg / hover ·
`200` tint border · `300` decorative / disabled-on-fill · `400–500` secondary
fills · `600` **primary action / accent** · `700` primary hover-pressed / links /
driver-critical primary / accent text · `800–900` max emphasis.

---

## 5.1 Option A — "Stage & Yard"  *(recommended)*

The most literal reading of the brief: a **sturdy field tool**. Deep grounded
teal, warm muted terracotta clay, low-chroma warm stone. Highest everyday
contrast; most robust in direct sun.

### Palette (proposal)

**Brand — teal (grounded, faint green lean)**

| Step | Hex | Step | Hex |
| --- | --- | --- | --- |
| `brand.50` | `#ECFBF7` | `brand.500` | `#0F9585` |
| `brand.100` | `#CDF3EA` | `brand.600` **primary** | `#0C7A6C` |
| `brand.200` | `#9CE6D5` | `brand.700` hover / driver-critical / link | `#0A6459` |
| `brand.300` | `#5FD0BC` | `brand.800` | `#0B5049` |
| `brand.400` | `#26B49F` | `brand.900` | `#0A3F3A` |

**Accent — Kajiado clay (warm muted terracotta; identity, trust pips, map/vehicle accents — not an action colour)**

| Step | Hex | Step | Hex |
| --- | --- | --- | --- |
| `accent.50` | `#FBF3EC` | `accent.500` | `#BC6C3A` |
| `accent.100` | `#F3E0CC` | `accent.600` accent text / trust label | `#9E561F` |
| `accent.300` | `#DDA475` (trust pip fill) | `accent.700` | `#7F4418` |

**Neutral — stone (warm, low chroma)**

`stone.0 #FFFFFF` · `50 #F7F5F1` · `100 #EEEBE4` · `200 #E0DBD1` · `300 #C9C3B6`
· `400 #A69F90` · `500 #7A7365` · `600 #59534A` · `700 #3E3931` · `800 #29251F`
· `900 #1A1712`

**Text** — `primary #1A1712` · `secondary #59534A` · `muted #7A7365` ·
`disabled #A69F90` · `inverse #FFFFFF` · `link #0A6459`

**Semantic** (`.solid` / `.fg` shown; `.bg` = a ~`50`-level tint of the same hue; `.border` = ~`200`-level)

| Token | `.solid` (white text) | `.fg` (text/icon on tint) | Icon |
| --- | --- | --- | --- |
| `status.success` | `#177A33` | `#177A33` | `✓` |
| `status.warning` | `#8A4A10` *(DISPUTED chip only)* | `#8A4A10` | `▲` / `!` / `⏸` |
| `status.danger` | `#C22B22` | `#B02017` | `✕` |
| `status.info` | `#2A5D93` | `#245285` | `●` / `…` |
| `status.neutral` | `#59534A` (`stone.600`) | `#59534A` | `•` / `⊘` |

### Rationale

Deep teal at `600` gives a confident, unmistakably-not-blue action colour that
survives glare; the clay is *muted* so it reads as "earth / vest / yard", never
"alert". The stone scale has the least chroma of the three options, keeping the
interface calm so the **status** colours do the meaning work. This is the palette
that most reads as a *reliable witness*.

### Strengths

- Highest routine contrast; best sunlight/cheap-LCD behaviour.
- Brand and success are far apart in both hue and lightness — least confusion
  risk.
- Calm neutrals → status chips and the primary `⌘` pop without shouting.
- Clay is restrained → no accidental "everything is important".

### Weaknesses

- The most "serious" option — least overtly warm/friendly; recruitment/marketing
  surfaces may want a warmer treatment (achievable with `accent` + illustration
  without changing the core).
- `brand.600` primary at ≈ 5.2:1 white is solid AA but not lavish — driver- and
  safety-critical primaries should use `brand.700` (≈ 7.0:1).

### Accessibility (computed, sRGB / WCAG)

| Pair | Ratio | Verdict |
| --- | --- | --- |
| `text.primary #1A1712` on `surface.page #F7F5F1` | ≈ **16.4:1** | AAA |
| `text.secondary #59534A` on page | ≈ **7.0:1** | AAA (large) / AA+ (normal) |
| `text.muted #7A7365` on page | ≈ **4.5:1** | AA normal (floor — captions/meta only) |
| white on `brand.600 #0C7A6C` (primary CTA) | ≈ **5.2:1** | AA normal |
| white on `brand.700 #0A6459` (driver-critical / safety CTA) | ≈ **7.0:1** | AAA-adjacent — meets the ≥ 7:1 target |
| `accent.600 #9E561F` on white (trust-level label) | ≈ **5.5:1** | AA normal |
| white on `status.danger.solid #C22B22` | ≈ **5.7:1** | AA normal |
| white on `status.info.solid #2A5D93` | ≈ **6.8:1** | AA+ |
| white on `status.success.solid #177A33` | ≈ **5.4:1** | AA normal |
| white on `status.warning.solid #8A4A10` (DISPUTED chip) | ≈ **6.8:1** | AA+ |
| `success.fg #177A33` on a light green tint `#E9F6EC` | ≈ **4.9:1** | AA normal |

All AA-or-better. Focus ring uses `brand.600` (≈ 5.2:1 vs white; ≥ 3:1 vs the
`50`-level tints); a dedicated darker `focus` token is set in 5B if any
dark-surface case needs it.

### Operational-UI implications

- Job-status chips: `info` for progress states, `brand` soft for
  confirmed/assigned/picked-up, `success` for delivered/completed, `neutral`
  outline for cancelled, `danger` outline for couldn't-complete, deep-amber solid
  for disputed — all clearly separable in sun.
- The driver `⌘` at `brand.700` is the single most prominent thing on screen.
- Admin console reads calm despite density because the neutrals are so low-chroma.
- Recipient card: near-black on warm white, one brand accent line — trustworthy,
  plain.

### Recommended use

**Primary recommendation for the whole product.** If the Founder wants more
warmth specifically in *recruitment/marketing* surfaces, lean on `accent` +
illustration there rather than changing the core.

---

## 5.2 Option B — "Kitengela Daylight"  *(warmer alternative)*

A friendlier, slightly brighter reading. The teal is a hair brighter, the clay
more present and saturated (usable as a light warm secondary, not only
identity), the neutrals creamier. Leans into **human** while staying practical.

### Palette (proposal)

**Brand — teal (brighter, faint blue lean)** — `50 #ECFCFA` · `100 #CBF4EF` ·
`200 #97E7DF` · `300 #5AD2C6` · `400 #22B5A8` · `500 #0E968B` ·
`600 #0A7C74` **primary** · `700 #0A655F` · `800 #0B514C` · `900 #093E3B`

**Accent — Kajiado clay (warmer, more saturated ochre-terracotta)** —
`50 #FCF4EA` · `100 #F6E1C7` · `300 #E6AE77` · `500 #CE7B3C` ·
`600 #AC5F20` accent text · `700 #8A4A18`

**Neutral — stone (creamier)** — `0 #FFFFFF` · `50 #F8F6F0` · `100 #F0ECE1` ·
`200 #E3DDCD` · `300 #CDC6B2` · `400 #A8A08C` · `500 #7C7462` · `600 #5B5447` ·
`700 #40392F` · `800 #2A251E` · `900 #1B1712`

**Text** — `primary #1B1712` · `secondary #5B5447` · `muted #7C7462` ·
`disabled #A8A08C` · `inverse #FFFFFF` · `link #0A655F`

**Semantic** — `success.solid #1F8A3C` (darkened variant `#177A33` for white
text) · `warning.fg/solid #8A4A10` (deep) · `danger.solid #C42E24` ·
`info.solid #2C5F96` · `neutral #5B5447`. Same rule as Option A: dark green for
white-text success; dark-fg + tint for warning chips.

### Rationale

The extra warmth in the neutrals and the more saturated clay make the product
feel more approachable in recruitment and business contexts, while the teal stays
grounded. It is still restrained — just a warmer restraint.

### Strengths

- Most "human / local" of the three; strongest for recruitment & business
  onboarding surfaces.
- Clay is versatile enough to double as a warm secondary emphasis.
- Body-text contrast on the creamier ground is still excellent (≈ 16.5:1).

### Weaknesses

- Brighter teal + warmer neutrals = slightly *less* extreme contrast for status
  chips than Option A; still AA but with less headroom outdoors.
- A more saturated clay risks "everything is warm/important" if used liberally —
  needs discipline in the component specs.
- The brighter `brand.500/400` steps drift toward "fresh" — must not be used for
  large fills or it edges toward the fintech-fresh anti-pattern.

### Accessibility (computed for the key pairs)

| Pair | Ratio | Verdict |
| --- | --- | --- |
| `text.primary #1B1712` on `surface.page #F8F6F0` | ≈ **16.5:1** | AAA |
| white on `brand.600 #0A7C74` (primary CTA) | ≈ **5.1:1** | AA normal |
| white on `brand.700 #0A655F` (driver-critical) | ≈ **6.8:1** | meets ≈ 7:1 target |
| `accent.600 #AC5F20` on white | ≈ **4.7:1** | AA normal (tighter than A's — verify at 5B) |
| Semantic solids | as Option A after the darkening rule | AA normal |

Secondary/muted-on-cream and status-on-tint pairs to be confirmed with tooling at
5B (the creamier ground slightly lowers every ratio vs. Option A).

### Operational-UI implications

- Works well where warmth helps (Business Home, onboarding, recruitment
  one-pagers) without hurting the operator flows.
- The operator/driver critical screens gain nothing from the extra warmth and
  lose a little contrast headroom vs. Option A — acceptable but not ideal for the
  highest-priority audience.

### Recommended use

A strong choice **if the Founder wants the brand to feel warmer overall**. Also a
good "marketing skin" companion to Option A if the Founder prefers Option A for
the product itself.

---

## 5.3 Option C — "Namanga Road"  *(most reserved alternative)*

The quietest, most authoritative reading. Deeper "pine-teal", a desaturated
dusty-brown clay used *very* sparingly, the lowest-chroma near-neutral stone.
Leans into **confident** and **modern**; the closest to an admin-console feel
that still scales down to the operator without going cold.

### Palette (proposal)

**Brand — teal (deep, quiet, green-leaning "pine-teal")** — `50 #EDF9F6` ·
`100 #D2F0E9` · `200 #A6E0D3` · `300 #6FC7B6` · `400 #38A996` · `500 #158A79` ·
`600 #0E6E60` **primary** · `700 #0C5A4F` · `800 #0C4841` · `900 #0A3833`

**Accent — clay (dusty, desaturated brown-clay; identity only, very sparing)** —
`50 #F9F4EF` · `100 #EDE0D2` · `300 #CFAD8C` · `500 #A9784F` ·
`600 #8C5E37` accent text · `700 #6F4A2C`

**Neutral — stone (near-neutral warm grey, lowest chroma)** — `0 #FFFFFF` ·
`50 #F6F5F3` · `100 #ECEAE6` · `200 #DDDAD3` · `300 #C6C2B8` · `400 #A39E92` ·
`500 #78726A` · `600 #565149` · `700 #3C3833` · `800 #28251F` · `900 #1A1815`

**Text** — `primary #1A1815` · `secondary #565149` · `muted #78726A` ·
`disabled #A39E92` · `inverse #FFFFFF` · `link #0C5A4F`

**Semantic** — `success.solid #217F3C` (→ `#177A33` for white text) ·
`warning #8A4A10` deep · `danger.solid #BE2C22` · `info.solid #2A5885` ·
`neutral #565149`. Same success/warning rules.

### Rationale

Maximum restraint. The deepest primary (highest contrast of the three) and the
most neutral stone make the product feel like a serious record-keeper. The clay
is almost a whisper — used only on the trust-level device and the occasional
identity accent.

### Strengths

- **Highest primary-CTA contrast** (≈ 6.1:1 white) — best for safety-critical
  legibility.
- The most "trustworthy witness / accountable record" feel — matches the brief's
  #1 attribute most directly.
- Least chroma anywhere → status colours are maximally distinct.
- Scales up to the admin console beautifully.

### Weaknesses

- **Risk of "over-formal corporate blue-grey"** (an explicit design-brief
  anti-pattern) if the desaturated clay is under-used or the neutrals read cold
  on a given screen — needs careful warmth checks in the illustration and the
  recipient page.
- Least "local / human / warm" — the desaturated clay gives up some of the
  Kajiado grounding.
- Could feel austere to a first-time business user.

### Accessibility (computed for the key pairs)

| Pair | Ratio | Verdict |
| --- | --- | --- |
| `text.primary #1A1815` on `surface.page #F6F5F3` | ≈ **16:1** | AAA |
| white on `brand.600 #0E6E60` (primary CTA) | ≈ **6.1:1** | AA+ — best of the three |
| white on `brand.700 #0C5A4F` (driver-critical) | ≈ **7.6:1** | exceeds the ≥ 7:1 target |
| `accent.600 #8C5E37` on white | ≈ **5.3:1** | AA normal |
| Semantic solids | as Option A after the darkening rule | AA normal |

The strongest contrast profile of the three.

### Operational-UI implications

- Best raw legibility for the driver `⌘` and safety actions.
- Admin/Operations console is its natural home.
- The recipient page must be warmth-checked — a desaturated palette on a doorstep
  can read "official/cold" rather than "trustworthy/human"; mitigate with the
  wordmark, one accent line, and a warm spot illustration.

### Recommended use

Choose **if the Founder prioritises maximum authority/legibility over warmth**,
or if Option A tests as slightly too intense outdoors (unlikely). Also the safest
base if the product will be heavily admin/operations-weighted early.

---

# 6. Visual examples — the recommended option (A) in context

Colour behaviour of **Option A** across the surfaces the Founder should see as a
whole. (Options B and C substitute their own hues into the same roles; the
*structure* is identical.)

| Surface / element | Colour role (Option A hex) |
| --- | --- |
| **App shell** | bg `surface.page #F7F5F1`; app bar `#FFFFFF` + bottom hairline `#E0DBD1`; title `#1A1712` |
| **Bottom nav** | inactive icon+label `#7A7365`; **active** `brand.600 #0C7A6C` + 3 px top indicator; "needs action" dot `danger #C22B22` |
| **Primary CTA** (standard) | fill `brand.600 #0C7A6C`, text `#FFFFFF`; pressed `brand.700 #0A6459` |
| **Primary CTA** (driver-critical / safety) | fill `brand.700 #0A6459`, text `#FFFFFF`, 56 px |
| **Secondary CTA** | white fill, text `brand.700 #0A6459`, 1.5 px `brand.600` border |
| **Tertiary / text button** | text `brand.700 #0A6459` |
| **Job card** | `#FFFFFF`, 1 px `#E0DBD1`, radius 8; ref `#7A7365`; route `#1A1712`; meta `#59534A`; price tabular `#1A1712` |
| **Job status chips** | Requested/At-pickup/In-transit → `info` (`fg #245285` on tint `#EAF1F8`); Confirmed/Assigned/Picked-up → `brand` soft (`#0A6459` on `#E7F6F2`); Delivered/Completed → `success` (`#177A33` on `#E9F6EC`, `✓`); Cancelled → `neutral` **outline** (`#59534A`); Couldn't-complete → `danger` outline (`#B02017`, `✕`); **Under dispute** → `warning.solid #8A4A10` + white + `⏸` |
| **Timeline** | done node `success #177A33` `✓`; current node `brand.600 #0C7A6C` `●`; upcoming `#C9C3B6` `○`; connector `#E0DBD1`, done-segment `brand.300 #5FD0BC`; operator-attested marker `warning.fg #8A4A10 !` |
| **Negotiation** | offer card `#FFFFFF` + `#E0DBD1`; **current proposal** 2 px `brand.600` left border + `brand` "Current" chip; **agreed** bar `brand.600` fill, white text, lock glyph; declined muted `#7A7365`; expired `warning` chip |
| **Verification pills** | Verified → `success` (`#177A33` on `#E9F6EC`, `✓`); Needs attention → `warning` (`#8A4A10` on `#FBEFE2`, `!`); Submitted/Under review → `info`; Not submitted → `neutral` |
| **Trust facts / level** | fact pills as above; **level device** = 3 pips `accent.300 #DDA475` filled / `#C9C3B6` empty + label `accent.600 #9E561F` "Level 2 · Established" |
| **Incidents** | Reported → `info` chip; Under review → `info`; Resolved → `success` or `neutral` per outcome; **no** "fault" colour |
| **Evidence** | verified tag `success`; operator-attested tag `warning`; restricted = lock icon `#7A7365` + text, no thumbnail; failed upload = `danger` inline + "Retry" |
| **Forms** | input border `#C9C3B6`; focus ring 2 px `brand.600 #0C7A6C`; error border/text `danger #B02017` + `✕`; hint `#7A7365`; `KSh` adornment `#7A7365` |
| **Alerts / banners** | info tint `#EAF1F8` / `#245285`; success `#E9F6EC` / `#177A33`; warning `#FBEFE2` / `#8A4A10`; danger `#FCECEA` / `#B02017` — each with its icon |
| **Offline state** | app-bar indicator `warning #8A4A10` dot + "Offline"; `as of HH:MM` badge `#7A7365`; blocked-`[server]` inline banner warning tint; sync-issues `⚑` `warning` |
| **Recipient card** | `#FFFFFF` card on `#F7F5F1`; near-black text; one `brand.600` accent line; primary = `Confirm I received the goods` on `success.solid #177A33`, white text, 56 px; "Report a problem" tertiary `brand.700` |
| **Operations / Admin console** | nav `surface.nav.console #F7F5F1` (cooler signal); dense rows on `#FFFFFF`, zebra `#F7F5F1`; sticky headers `shadow.1`; binding/destructive actions use `danger.solid #C22B22` + white in the confirm dialog |

**Two textual references (Option A colours):**

```
Driver Current Job                     Recipient card
┌──────────────────────────────┐       ┌────────────────────────────┐
│ FK-1042  ⌂ Njiani            │       │ fikisha        EN  [SW]     │  wordmark + toggle
│ Njiani (In transit)  info ●  │       │ ══ brand.600 accent line ══ │
│ ┌──────────────────────────┐ │       │ Delivery for John M.       │  #1A1712
│ │  ⌘ NIMEFIKA / I've       │ │       │ ● The driver has arrived   │  info
│ │    arrived               │ │       │ Coming: 8 cartons · Elec.  │
│ │  brand.700 · white · 56px│ │       │ Driver: Samuel             │
│ └──────────────────────────┘ │       │ Vehicle: Pickup · KDG 123A │
│ Pickup ●—— Transit ●—— …     │       │ Operator identity verified │  success ✓
│  brand.600 nodes · #E0DBD1   │       │ ┌────────────────────────┐ │
│ · Ripoti tatizo (tertiary)   │       │ │ ⌘ Confirm I received   │ │  success.solid
└──────────────────────────────┘       │ │   the goods            │ │  #177A33 · white · 56px
                                       │ └────────────────────────┘ │
                                       │ · Report a problem         │  tertiary brand.700
                                       └────────────────────────────┘
```

---

# 7. Recommendation

**Adopt Option A — "Stage & Yard".**

It is the most faithful expression of the brief's top attribute (a *reliable,
evidence-minded witness*), gives the best routine contrast for the highest-
priority audience (operator/driver, outdoors, cheap screens), keeps brand and
success clearly separate, and stays warm and local through the clay accent and
illustration without drifting toward either the fintech-fresh or the
corporate-blue-grey anti-patterns.

- If the Founder wants a **warmer overall brand**, choose **Option B**, or keep
  **A for the product** and use **B's warmth for recruitment/marketing surfaces**.
- If the Founder prioritises **maximum authority/legibility** (or the product is
  admin/operations-weighted early), choose **Option C**, with an explicit warmth
  check on the recipient page and illustration.

**All three require the same two accessibility adjustments** at 5B (darkened
`success.solid`; dark-fg + deep-amber `warning`), and the same
**automated per-pair contrast verification on a low-cost device in daylight**
before any value is committed to source.

---

# 8. Founder approval section

Please record a decision on each line (approve / modify / reject). Nothing
proceeds to Phase 5B until this section is completed.

| # | Decision needed | Options | Founder decision |
| --- | --- | --- | --- |
| D-1 | **Palette direction** | A "Stage & Yard" (recommended) · B "Kitengela Daylight" · C "Namanga Road" · a modification of one | ☐ __________ |
| D-2 | **Primary brand colour** (`brand.600`) | as proposed for the chosen option · adjust to: __________ | ☐ __________ |
| D-3 | **Accent / Kajiado-clay** (`accent.600`, pip `accent.300`) | as proposed · adjust · use more sparingly / more liberally | ☐ __________ |
| D-4 | **Neutral / stone scale** | as proposed · warmer · cooler · lower/higher chroma | ☐ __________ |
| D-5 | **Near-black text** (`text.primary`) | as proposed (`~#1A17xx`) · pure `#000` (not recommended — harsh on cheap panels) · other | ☐ __________ |
| D-6 | **Semantic status palette** (success / warning / danger / info / neutral) | as proposed + the two AA adjustments · adjust specific hues: __________ | ☐ __________ |
| D-7 | **Success stays independent of brand** (leaf-green, always `✓`, never the brand teal) | confirm · discuss | ☐ __________ |
| D-8 | **Light-theme surface hierarchy** (`page` warm off-white, `card` white, `console` cooler tint) | as proposed · adjust | ☐ __________ |
| D-9 | **Driver / safety-critical primary uses `brand.700`** (≥ 7:1) while standard primary uses `brand.600` (AA) | confirm · require `brand.700` everywhere · other | ☐ __________ |
| D-10 | **Marketing/recruitment surfaces** may use a warmer treatment (e.g. Option B warmth) while the product uses the chosen option | yes · no · decide later | ☐ __________ |
| D-11 | **Wordmark / app-icon system, illustration style, photography direction** | still pending the brand/KIPI process — track separately (design-brief §2, §6.1, §6.5, §12) | ☐ acknowledged |
| D-12 | **Anything to change before 5B token production** | free text | __________ |

---

# 9. Decision status

| Item | Status |
| --- | --- |
| Phase 5A palette proposal | **PROPOSED — AWAITING FOUNDER APPROVAL** |
| Final brand palette | **NOT APPROVED** — every hex is a proposal |
| Production design tokens (5B) | **NOT CREATED** |
| Tailwind config / CSS / component restyle | **NOT TOUCHED** |
| Responsive rule (Phase 4 §21.2–21.3, §25) | **carried forward unchanged** — Driver focused/action-dominant at every width; Operator may expand where it aids coordination; **no** hard 480 px cap; never density for its own sake |
| Product invariants (Job lifecycle & states, negotiation & agreed-price freeze, pickup/delivery proof, custody, recipient access, verification, trust, value bands, operator groups, authorization, incidents, disputes, commission, payment architecture, cancellation reputation, notification rules, legal positioning, MVP exclusions) | **UNCHANGED** — this document represents the approved product, it does not redefine it |
| `RESUME_PRIOR` preconditions (Q7) | **OPEN** — product/architecture decision; only the approved admin shell is styled |
| Rating / reputation (Q8) | **DEFERRED** — no star ratings, public scores, ranking, or recommendation scoring introduced |
| Other Phase 4 open questions | untouched; revisited only if the approved palette decision requires it |

---

# 10. Explicit implementation gate

**Phase 5B (production design tokens) and any component work may begin only after
the Founder completes §8.** On approval, Phase 5B will:

1. Fix the primitive scales (50–900) for the approved brand, accent, and stone
   hues, plus the near-black text scale.
2. Define semantic tokens referencing them (`color.action.*`, `surface.*`,
   `text.*`, `status.*` incl. `status.job.<STATE>`, `status.verification.<group>`,
   `status.connectivity.*`), applying the two AA adjustments.
3. Define component tokens (`component.button.*` incl. `driver`, `component.chip.*`,
   `component.timeline.*`, `component.otp.*`, `component.trustPips.*`, …).
4. Add the non-colour token families already fixed in Phase 4 (typography,
   spacing, radius, border, elevation, motion, breakpoints, target sizes,
   `a11y.*`).
5. **Run automated contrast verification on every semantic/component pair, on a
   low-cost device in daylight**, and record the results.
6. Keep the **two-tier discipline** — components reference semantic (+
   `component.*`) tokens, never raw hex.
7. Produce this as a **tokens specification document**; committing actual
   `tailwind.config.ts` / CSS variables / component changes is a **later gate**
   with its own Founder go-ahead.

Until then: **no production tokens, no config change, no CSS, no React changes,
no dependency changes, no component migration.**

---

# 11. Phase 5A exit criteria

- [x] palette direction researched / designed (§3, §5)
- [x] 2–3 viable options documented, each with palette · rationale · strengths ·
      weaknesses · accessibility · operational-UI implications · recommended use
      (§5.1–5.3)
- [x] accessibility implications assessed, with computed contrast for the key
      pairs and the two required adjustments identified (§4, §5)
- [x] operational-UI implications demonstrated across the full surface set
      (§5 per option + §6 walkthrough for the recommendation)
- [x] recommendation provided, with when-to-choose guidance for the alternatives
      (§7)
- [x] provisional vs. final clearly distinguished — every hex marked a proposal;
      final palette explicitly **NOT APPROVED** (§9)
- [x] Founder approval gate explicit (§8, §10)
- [x] no production tokens committed
- [x] no application UI restyled; no `tailwind.config` / CSS / component change
- [x] no architecture or product decision changed; Q7 open, Q8 deferred (§9)
- [x] no Phase 5B implementation began

---

# 12. Changelog

| Date | Change | By |
| --- | --- | --- |
| 2026-09-10 | Phase 5A brand-palette proposal — 3 options (A recommended), accessibility assessment, Founder approval gate. No production tokens; no code. | (brief: "Design Phase 5: Brand Palette & Implementation Foundation — Phase 5A") |
