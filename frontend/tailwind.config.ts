import type { Config } from 'tailwindcss';

import {
  primitive,
  semantic,
  typography,
  radius,
  elevation,
  motion,
  breakpoint,
  target,
  zIndex,
} from './src/design/tokens';

/**
 * Fikisha Tailwind theme — Design Phase 5B.
 *
 * This mirrors `src/design/tokens.ts` (the source of truth). Components use
 * SEMANTIC utility classes (`bg-surface-card`, `text-fg-secondary`,
 * `border-line`, `bg-status-success-bg`, `text-action-primary`, …) rather than
 * raw palette steps. The raw `brand` / `accent` / `stone` scales are exposed for
 * the few cases that need a specific step.
 *
 * `theme.extend` is used so Tailwind's built-in palettes (slate / green / amber /
 * red …) remain available to screens not yet migrated to the token system —
 * see docs/design-phase-5-implementation.md "Known legacy styling".
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    screens: {
      sm: breakpoint.sm,
      md: breakpoint.md,
      lg: breakpoint.lg,
      xl: breakpoint.xl,
      '2xl': breakpoint['2xl'],
    },
    extend: {
      colors: {
        // ── primitive scales ──
        brand: primitive.brand,
        accent: primitive.accent,
        // Deliberately replaces Tailwind's built-in `stone` with the warm,
        // low-chroma Stage & Yard neutral scale.
        stone: primitive.stone,

        // ── semantic: text / foreground ──
        fg: {
          DEFAULT: semantic.text.primary,
          secondary: semantic.text.secondary,
          muted: semantic.text.muted,
          disabled: semantic.text.disabled,
          inverse: semantic.text.inverse,
          link: semantic.text.link,
        },
        // ── semantic: surfaces ──
        surface: {
          page: semantic.surface.page,
          card: semantic.surface.card,
          raised: semantic.surface.raised,
          input: semantic.surface.input,
          nav: semantic.surface.nav,
          'nav-console': semantic.surface.navConsole,
          sunken: semantic.surface.sunken,
          'brand-tint': semantic.surface.brandTint,
          overlay: semantic.surface.overlay,
        },
        // ── semantic: borders / lines ──
        line: {
          subtle: semantic.border.subtle,
          DEFAULT: semantic.border.default,
          strong: semantic.border.strong,
          focus: semantic.border.focus,
        },
        // ── semantic: action / identity ──
        action: {
          primary: semantic.action.primary,
          'primary-hover': semantic.action.primaryHover,
          'primary-pressed': semantic.action.primaryPressed,
          'primary-strong': semantic.action.primaryStrong,
          'on-primary': semantic.action.onPrimary,
          'secondary-text': semantic.action.secondaryText,
          link: semantic.action.link,
          'disabled-surface': semantic.action.disabledSurface,
        },
        'accent-token': {
          text: semantic.accent.text,
          'pip-filled': semantic.accent.pipFilled,
          'pip-empty': semantic.accent.pipEmpty,
          tint: semantic.accent.tint,
        },
        // ── semantic: status (each: fg / bg / border / solid) ──
        status: {
          'success-fg': semantic.status.success.fg,
          'success-bg': semantic.status.success.bg,
          'success-border': semantic.status.success.border,
          'success-solid': semantic.status.success.solid,
          'warning-fg': semantic.status.warning.fg,
          'warning-bg': semantic.status.warning.bg,
          'warning-border': semantic.status.warning.border,
          'warning-solid': semantic.status.warning.solid,
          'danger-fg': semantic.status.danger.fg,
          'danger-bg': semantic.status.danger.bg,
          'danger-border': semantic.status.danger.border,
          'danger-solid': semantic.status.danger.solid,
          'info-fg': semantic.status.info.fg,
          'info-bg': semantic.status.info.bg,
          'info-border': semantic.status.info.border,
          'info-solid': semantic.status.info.solid,
          'neutral-fg': semantic.status.neutral.fg,
          'neutral-bg': semantic.status.neutral.bg,
          'neutral-border': semantic.status.neutral.border,
          'neutral-solid': semantic.status.neutral.solid,
        },
      },
      fontFamily: {
        sans: typography.fontFamily.sans.split(', '),
        numeric: typography.fontFamily.numeric.split(', '),
      },
      fontSize: {
        display: [typography.scale.display[0], { lineHeight: typography.scale.display[1] as string }],
        h1: [typography.scale.h1[0], { lineHeight: typography.scale.h1[1] as string }],
        h2: [typography.scale.h2[0], { lineHeight: typography.scale.h2[1] as string }],
        h3: [typography.scale.h3[0], { lineHeight: typography.scale.h3[1] as string }],
        body: [typography.scale.body[0], { lineHeight: typography.scale.body[1] as string }],
        'body-sm': [typography.scale.bodySm[0], { lineHeight: typography.scale.bodySm[1] as string }],
        label: [typography.scale.label[0], { lineHeight: typography.scale.label[1] as string }],
        caption: [typography.scale.caption[0], { lineHeight: typography.scale.caption[1] as string }],
        'numeric-lg': [
          typography.scale.numericLg[0],
          { lineHeight: typography.scale.numericLg[1] as string },
        ],
      },
      borderRadius: {
        sm: radius.sm,
        md: radius.md,
        lg: radius.lg,
      },
      boxShadow: {
        e1: elevation[1],
        e2: elevation[2],
        e3: elevation[3],
      },
      minHeight: {
        target: target.min,
        'target-driver': target.driver,
      },
      minWidth: {
        target: target.min,
        'target-driver': target.driver,
      },
      transitionDuration: {
        fast: motion.duration.fast.replace('ms', ''),
        base: motion.duration.base.replace('ms', ''),
        slow: motion.duration.slow.replace('ms', ''),
      },
      transitionTimingFunction: {
        standard: motion.easing.standard,
        exit: motion.easing.exit,
      },
      zIndex: {
        sticky: String(zIndex.sticky),
        nav: String(zIndex.nav),
        dropdown: String(zIndex.dropdown),
        overlay: String(zIndex.overlay),
        modal: String(zIndex.modal),
        toast: String(zIndex.toast),
      },
    },
  },
  plugins: [],
} satisfies Config;
