import type { IconName } from './Icon';

/**
 * Fikisha production design tokens — Design Phase 5B.
 *
 * Source of truth for the visual foundation. Two tiers:
 *   PRIMITIVES  → raw approved scales (Stage & Yard palette, Phase 5A / commit 72b6a2e)
 *   SEMANTIC    → role-based tokens that reference primitives
 * Component-level tokens live with their components; components consume SEMANTIC
 * tokens (via the Tailwind theme in `tailwind.config.ts`, which mirrors this file)
 * and never invent raw colour values.
 *
 * Palette: Option A "Stage & Yard" — Founder-approved 2026-09-10.
 * See docs/design-phase-4-visual-system.md and docs/design-phase-5-brand-palette.md.
 * Light theme is authoritative; the structure does not preclude a later dark set.
 *
 * The two mandatory accessibility adjustments from Phase 5A are applied here:
 *  - success.solid is the darker green (#177A33), not the bright leaf green, so
 *    white text on it meets WCAG AA for normal text.
 *  - warning renders as dark foreground on an amber tint + an icon; a deep-amber
 *    solid (#8A4A10) is reserved for the strong "Under dispute" treatment.
 * Verified by src/design/contrast.test.ts.
 */

/* ─────────────────────────── PRIMITIVES ─────────────────────────── */

export const primitive = {
  brand: {
    50: '#ECFBF7',
    100: '#CDF3EA',
    200: '#9CE6D5',
    300: '#5FD0BC',
    400: '#26B49F',
    500: '#0F9585',
    600: '#0C7A6C',
    700: '#0A6459',
    800: '#0B5049',
    900: '#0A3F3A',
  },
  accent: {
    50: '#FBF3EC',
    100: '#F3E0CC',
    200: '#EACBA6',
    300: '#DDA475',
    400: '#CB8A56',
    500: '#BC6C3A',
    600: '#9E561F',
    700: '#7F4418',
    800: '#5F330F',
  },
  /** Warm, low-chroma neutral scale. Replaces Tailwind's built-in `stone`. */
  stone: {
    0: '#FFFFFF',
    50: '#F7F5F1',
    100: '#EEEBE4',
    200: '#E0DBD1',
    300: '#C9C3B6',
    400: '#A69F90',
    500: '#7A7365',
    600: '#59534A',
    700: '#3E3931',
    800: '#29251F',
    900: '#1A1712',
  },
  green: { fg: '#177A33', bg: '#E9F6EC', border: '#BEE3C6' },
  amber: { fg: '#8A4A10', bg: '#FBEFE2', border: '#EBD2B4' },
  red: { fg: '#B02017', solid: '#C22B22', bg: '#FCECEA', border: '#F1C6C1' },
  blue: { fg: '#245285', solid: '#2A5D93', bg: '#EAF1F8', border: '#C6D8EC' },
  white: '#FFFFFF',
  black: '#000000',
} as const;

/* ─────────────────────────── SEMANTIC ─────────────────────────── */

export const semantic = {
  /** action / identity — never the meaning of "success" */
  action: {
    primary: primitive.brand[600],
    primaryHover: primitive.brand[700],
    primaryPressed: primitive.brand[800],
    /** driver-critical & safety-critical primary — targets ≥ 7:1 with white */
    primaryStrong: primitive.brand[700],
    onPrimary: primitive.white,
    secondaryText: primitive.brand[700],
    link: primitive.brand[700],
    disabledSurface: primitive.stone[100],
  },
  accent: {
    /** trust-level label / identity emphasis (not an action colour) */
    text: primitive.accent[600],
    pipFilled: primitive.accent[300],
    pipEmpty: primitive.stone[300],
    tint: primitive.accent[50],
  },
  surface: {
    page: primitive.stone[50],
    card: primitive.stone[0],
    raised: primitive.stone[0],
    input: primitive.stone[0],
    nav: primitive.stone[0],
    navConsole: primitive.stone[50],
    sunken: primitive.stone[100],
    brandTint: primitive.brand[50],
    overlay: 'rgba(26, 23, 18, 0.55)',
  },
  text: {
    primary: primitive.stone[900],
    secondary: primitive.stone[600],
    // stone.500 (#7A7365) computes to ~4.3:1 on surface.page — just under AA.
    // Nudged darker to meet WCAG AA for normal text on the page ground.
    // Surfaced by src/design/contrast.test.ts; neutral-derived, not a brand change.
    muted: '#6B6458',
    disabled: primitive.stone[400],
    inverse: primitive.white,
    link: primitive.brand[700],
  },
  border: {
    subtle: primitive.stone[100],
    default: primitive.stone[200],
    // Boundary that identifies a component (input / selectable row) — WCAG 1.4.11
    // requires ≥ 3:1. stone.300 (#C9C3B6) is ~1.8:1 on white; use a stone.350-level
    // value so form fields are identifiable by their border. Dividers/cards keep
    // border.default (they are not the sole state indicator).
    strong: '#948C7D',
    focus: primitive.brand[600],
  },
  status: {
    success: { fg: primitive.green.fg, solid: primitive.green.fg, bg: primitive.green.bg, border: primitive.green.border },
    warning: { fg: primitive.amber.fg, solid: primitive.amber.fg, bg: primitive.amber.bg, border: primitive.amber.border },
    danger: { fg: primitive.red.fg, solid: primitive.red.solid, bg: primitive.red.bg, border: primitive.red.border },
    info: { fg: primitive.blue.fg, solid: primitive.blue.solid, bg: primitive.blue.bg, border: primitive.blue.border },
    neutral: { fg: primitive.stone[600], solid: primitive.stone[600], bg: primitive.stone[100], border: primitive.stone[200] },
  },
} as const;

/* ───────── Domain visual mappings (presentation only — the authoritative
 * Job / verification states are unchanged; see the design docs) ───────── */

/** UI status "tone" — resolves to a `semantic.status.*` entry. */
export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand';

/** All 14 authoritative Job states (Phase 3 §3 / Phase 4 §13). Labels are the
 *  approved working set; final EN/SW wording is a design-track detail. */
export type JobState =
  | 'DRAFT'
  | 'REQUESTED'
  | 'NEGOTIATING'
  | 'CONFIRMED'
  | 'ASSIGNED'
  | 'AT_PICKUP'
  | 'PICKED_UP'
  | 'IN_TRANSIT'
  | 'AT_DESTINATION'
  | 'DELIVERED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'FAILED'
  | 'DISPUTED';

export type JobStateCategory =
  | 'pre-active'
  | 'progress'
  | 'terminal-positive'
  | 'terminal-neutral'
  | 'terminal-negative'
  | 'exception-hold';

export interface JobStateVisual {
  /** i18n key under `job.state.*`; `labelEn` is the fallback / working label */
  labelEn: string;
  category: JobStateCategory;
  tone: StatusTone;
  /** chip fill style */
  chip: 'soft' | 'solid' | 'outline';
  /** icon name from src/design/Icon.tsx */
  icon: IconName;
}

export const JOB_STATE_VISUAL: Record<JobState, JobStateVisual> = {
  DRAFT: { labelEn: 'Draft', category: 'pre-active', tone: 'neutral', chip: 'outline', icon: 'pencil' },
  REQUESTED: { labelEn: 'Requested', category: 'progress', tone: 'info', chip: 'soft', icon: 'send' },
  NEGOTIATING: { labelEn: 'Negotiating', category: 'progress', tone: 'info', chip: 'soft', icon: 'chat' },
  CONFIRMED: { labelEn: 'Confirmed', category: 'progress', tone: 'brand', chip: 'soft', icon: 'handshake' },
  ASSIGNED: { labelEn: 'Assigned', category: 'progress', tone: 'brand', chip: 'soft', icon: 'badge' },
  AT_PICKUP: { labelEn: 'At pickup', category: 'progress', tone: 'info', chip: 'soft', icon: 'pin' },
  PICKED_UP: { labelEn: 'Picked up', category: 'progress', tone: 'brand', chip: 'soft', icon: 'box' },
  IN_TRANSIT: { labelEn: 'In transit', category: 'progress', tone: 'info', chip: 'soft', icon: 'truck' },
  AT_DESTINATION: { labelEn: 'At destination', category: 'progress', tone: 'info', chip: 'soft', icon: 'pinCheck' },
  DELIVERED: { labelEn: 'Delivered', category: 'progress', tone: 'success', chip: 'soft', icon: 'check' },
  COMPLETED: { labelEn: 'Completed', category: 'terminal-positive', tone: 'success', chip: 'solid', icon: 'flagCheck' },
  CANCELLED: { labelEn: 'Cancelled', category: 'terminal-neutral', tone: 'neutral', chip: 'outline', icon: 'slash' },
  FAILED: { labelEn: "Couldn't complete", category: 'terminal-negative', tone: 'danger', chip: 'outline', icon: 'alertTriangle' },
  DISPUTED: { labelEn: 'Under dispute', category: 'exception-hold', tone: 'warning', chip: 'solid', icon: 'pause' },
};

/** The 7 authoritative verification states (unchanged) mapped to the 5
 *  user-facing groups (Phase 3 §15 / Phase 4 §16). "Needs attention" =
 *  INFO_REQUESTED + REJECTED + effective EXPIRED. */
export type VerificationState =
  | 'NOT_SUBMITTED'
  | 'SUBMITTED'
  | 'IN_REVIEW'
  | 'INFO_REQUESTED'
  | 'VERIFIED'
  | 'REJECTED'
  | 'EXPIRED';

export type VerificationGroup =
  | 'required'
  | 'submitted'
  | 'under_review'
  | 'verified'
  | 'needs_attention';

export const VERIFICATION_GROUP_OF: Record<VerificationState, VerificationGroup> = {
  NOT_SUBMITTED: 'required',
  SUBMITTED: 'submitted',
  IN_REVIEW: 'under_review',
  VERIFIED: 'verified',
  INFO_REQUESTED: 'needs_attention',
  REJECTED: 'needs_attention',
  EXPIRED: 'needs_attention',
};

export interface VerificationGroupVisual {
  labelEn: string;
  tone: StatusTone;
  icon: IconName;
}

export const VERIFICATION_GROUP_VISUAL: Record<VerificationGroup, VerificationGroupVisual> = {
  required: { labelEn: 'Required', tone: 'neutral', icon: 'dot' },
  submitted: { labelEn: 'Submitted', tone: 'info', icon: 'ellipsis' },
  under_review: { labelEn: 'Under review', tone: 'info', icon: 'eye' },
  verified: { labelEn: 'Verified', tone: 'success', icon: 'check' },
  needs_attention: { labelEn: 'Needs attention', tone: 'warning', icon: 'alert' },
};

export type ConnectivityState = 'online' | 'syncing' | 'offline' | 'sync_issue';

export interface ConnectivityVisual {
  labelEn: string;
  tone: StatusTone;
  icon: IconName;
}

export const CONNECTIVITY_VISUAL: Record<ConnectivityState, ConnectivityVisual> = {
  online: { labelEn: 'Synced', tone: 'success', icon: 'dot' },
  syncing: { labelEn: 'Syncing…', tone: 'info', icon: 'sync' },
  offline: { labelEn: 'Offline', tone: 'warning', icon: 'dot' },
  sync_issue: { labelEn: 'Sync issues', tone: 'warning', icon: 'flag' },
};

/* ─────────────────────────── NON-COLOUR TOKENS ─────────────────────────── */

export const typography = {
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
    numeric: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
  },
  /** [size, lineHeight, weight] */
  scale: {
    display: ['1.75rem', '2rem', 700],
    h1: ['1.375rem', '1.75rem', 700],
    h2: ['1.125rem', '1.5rem', 700],
    h3: ['1rem', '1.375rem', 600],
    body: ['1rem', '1.5rem', 400],
    bodySm: ['0.875rem', '1.25rem', 400],
    label: ['0.875rem', '1.25rem', 600],
    caption: ['0.75rem', '1rem', 400],
    button: ['1rem', '1', 600],
    buttonDriver: ['1.0625rem', '1', 700],
    numericLg: ['1.5rem', '1.75rem', 700],
  },
} as const;

export const space = {
  0: '0px', 1: '4px', 2: '8px', 3: '12px', 4: '16px', 5: '20px',
  6: '24px', 8: '32px', 10: '40px', 12: '48px', 16: '64px',
} as const;

export const radius = { none: '0px', sm: '4px', md: '8px', lg: '12px', full: '9999px' } as const;

export const border = { hairline: '1px', control: '1px', emphasis: '2px' } as const;

export const elevation = {
  0: 'none',
  1: '0 1px 2px rgba(26, 23, 18, 0.08)',
  2: '0 1px 2px rgba(26, 23, 18, 0.08), 0 4px 12px rgba(26, 23, 18, 0.08)',
  3: '0 8px 24px rgba(26, 23, 18, 0.16)',
} as const;

export const motion = {
  duration: { fast: '120ms', base: '200ms', slow: '280ms' },
  easing: { standard: 'cubic-bezier(0.2, 0, 0, 1)', exit: 'cubic-bezier(0.4, 0, 1, 1)' },
} as const;

export const breakpoint = { sm: '360px', md: '600px', lg: '900px', xl: '1200px', '2xl': '1600px' } as const;

export const target = { min: '44px', driver: '56px', compact: '36px' } as const;

export const zIndex = {
  base: 0, sticky: 10, nav: 20, dropdown: 30, overlay: 40, modal: 50, toast: 60,
} as const;

export const a11y = {
  focusRingWidth: '2px',
  focusRingOffset: '2px',
  contrastBodyMin: 4.5,
  contrastBodyTarget: 7,
  contrastLargeMin: 3,
  contrastUiMin: 3,
} as const;
