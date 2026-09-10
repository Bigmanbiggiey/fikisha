import { describe, expect, it } from 'vitest';

import { contrastRatio, round2 } from './contrast';
import { primitive, semantic, a11y } from './tokens';

/**
 * Automated WCAG 2.2 contrast validation for the Stage & Yard token pairs
 * (Design Phase 5B, §26 of the brief). AA is the floor; driver / safety-critical
 * pairs target ≥ 7:1. Run with `npm test`.
 *
 * A physical low-cost-display check is recorded in
 * docs/design-phase-5-implementation.md; this suite guards the token maths.
 */

const AA = a11y.contrastBodyMin; // 4.5
const AA_LARGE = a11y.contrastLargeMin; // 3
const TARGET = a11y.contrastBodyTarget; // 7
const UI = a11y.contrastUiMin; // 3

const page = semantic.surface.page;
const card = semantic.surface.card;
const white = primitive.white;

interface Row {
  name: string;
  fg: string;
  bg: string;
  min: number;
}

const NORMAL_TEXT: Row[] = [
  { name: 'text.primary on page', fg: semantic.text.primary, bg: page, min: AA },
  { name: 'text.primary on card', fg: semantic.text.primary, bg: card, min: AA },
  { name: 'text.secondary on page', fg: semantic.text.secondary, bg: page, min: AA },
  { name: 'text.muted on page (floor)', fg: semantic.text.muted, bg: page, min: AA },
  { name: 'link on card', fg: semantic.text.link, bg: card, min: AA },
  { name: 'white on action.primary (CTA)', fg: white, bg: semantic.action.primary, min: AA },
  { name: 'accent.text on card (trust label)', fg: semantic.accent.text, bg: card, min: AA },
  { name: 'white on status.danger.solid', fg: white, bg: semantic.status.danger.solid, min: AA },
  { name: 'white on status.info.solid', fg: white, bg: semantic.status.info.solid, min: AA },
  { name: 'white on status.success.solid (adjusted)', fg: white, bg: semantic.status.success.solid, min: AA },
  { name: 'white on status.warning.solid (DISPUTED, deep amber)', fg: white, bg: semantic.status.warning.solid, min: AA },
  { name: 'success.fg on success.bg (chip)', fg: semantic.status.success.fg, bg: semantic.status.success.bg, min: AA },
  { name: 'warning.fg on warning.bg (chip)', fg: semantic.status.warning.fg, bg: semantic.status.warning.bg, min: AA },
  { name: 'danger.fg on danger.bg (chip)', fg: semantic.status.danger.fg, bg: semantic.status.danger.bg, min: AA },
  { name: 'info.fg on info.bg (chip)', fg: semantic.status.info.fg, bg: semantic.status.info.bg, min: AA },
  { name: 'neutral.fg on neutral.bg (chip)', fg: semantic.status.neutral.fg, bg: semantic.status.neutral.bg, min: AA },
];

const LARGE_OR_UI: Row[] = [
  { name: 'focus ring vs card (UI)', fg: semantic.border.focus, bg: card, min: UI },
  { name: 'focus ring vs page (UI)', fg: semantic.border.focus, bg: page, min: UI },
  { name: 'focus ring vs brand-tint (UI)', fg: semantic.border.focus, bg: semantic.surface.brandTint, min: UI },
  { name: 'line.strong vs card (input border, WCAG 1.4.11)', fg: semantic.border.strong, bg: card, min: UI },
  { name: 'line.strong vs page (input border on page)', fg: semantic.border.strong, bg: page, min: 2.7 },
  { name: 'line.default vs card (divider — not a state indicator)', fg: semantic.border.default, bg: card, min: 1.2 },
  { name: 'numeric-lg price: primary on card (large)', fg: semantic.text.primary, bg: card, min: AA_LARGE },
];

const TARGETS: Row[] = [
  { name: 'white on action.primaryStrong (driver / safety CTA) ≥ 7:1', fg: white, bg: semantic.action.primaryStrong, min: TARGET },
  { name: 'text.primary on page ≥ 7:1 (operator-critical body)', fg: semantic.text.primary, bg: page, min: TARGET },
];

describe('Stage & Yard palette — WCAG contrast', () => {
  it.each(NORMAL_TEXT)('$name meets AA (≥ $min:1)', ({ fg, bg, min }) => {
    expect(round2(contrastRatio(fg, bg))).toBeGreaterThanOrEqual(min);
  });

  it.each(LARGE_OR_UI)('$name meets its floor (≥ $min:1)', ({ fg, bg, min }) => {
    expect(round2(contrastRatio(fg, bg))).toBeGreaterThanOrEqual(min);
  });

  it.each(TARGETS)('$name', ({ fg, bg, min }) => {
    expect(round2(contrastRatio(fg, bg))).toBeGreaterThanOrEqual(min);
  });

  it('status.success is a distinct hue from the brand colour (independent semantics)', () => {
    const success = semantic.status.success.solid;
    const brand = semantic.action.primary;
    expect(success.toLowerCase()).not.toBe(brand.toLowerCase());

    // Success is a yellow-green (G clearly above B); brand is a blue-green teal
    // (G and B close). Compare the green–blue channel spread.
    const spread = (hex: string): number => {
      const n = parseInt(hex.slice(1), 16);
      return ((n >> 8) & 0xff) - (n & 0xff); // G - B
    };
    expect(spread(success)).toBeGreaterThan(spread(brand) + 30);
  });

  it('prints the computed ratio table (visible with --reporter=verbose)', () => {
    const table = [...NORMAL_TEXT, ...LARGE_OR_UI, ...TARGETS].map((r) => ({
      pair: r.name,
      ratio: round2(contrastRatio(r.fg, r.bg)),
      min: r.min,
      pass: round2(contrastRatio(r.fg, r.bg)) >= r.min,
    }));
    console.table(table);
    expect(table.every((r) => r.pass)).toBe(true);
  });
});
