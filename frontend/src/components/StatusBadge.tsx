import { cn } from './cn';
import { Icon, type IconName } from '@/design/Icon';

/**
 * StatusBadge — Design Phase 5B. A chip that carries state.
 * Status is never colour-only: pass an `icon` (and the visible `label`).
 * Legacy tones `positive` / `negative` map to `success` / `danger`.
 */
export type BadgeTone =
  | 'neutral'
  | 'positive'
  | 'negative'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'brand';

type Resolved = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'brand';
type Variant = 'soft' | 'solid' | 'outline';

const RESOLVE: Record<BadgeTone, Resolved> = {
  neutral: 'neutral',
  positive: 'success',
  negative: 'danger',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  info: 'info',
  brand: 'brand',
};

const SOFT: Record<Resolved, string> = {
  neutral: 'bg-status-neutral-bg text-status-neutral-fg',
  success: 'bg-status-success-bg text-status-success-fg',
  warning: 'bg-status-warning-bg text-status-warning-fg',
  danger: 'bg-status-danger-bg text-status-danger-fg',
  info: 'bg-status-info-bg text-status-info-fg',
  brand: 'bg-surface-brand-tint text-action-primary-hover',
};

const SOLID: Record<Resolved, string> = {
  neutral: 'bg-status-neutral-solid text-fg-inverse',
  success: 'bg-status-success-solid text-fg-inverse',
  warning: 'bg-status-warning-solid text-fg-inverse',
  danger: 'bg-status-danger-solid text-fg-inverse',
  info: 'bg-status-info-solid text-fg-inverse',
  brand: 'bg-action-primary text-fg-inverse',
};

const OUTLINE: Record<Resolved, string> = {
  neutral: 'border border-status-neutral-fg text-status-neutral-fg',
  success: 'border border-status-success-fg text-status-success-fg',
  warning: 'border border-status-warning-fg text-status-warning-fg',
  danger: 'border border-status-danger-fg text-status-danger-fg',
  info: 'border border-status-info-fg text-status-info-fg',
  brand: 'border border-action-primary text-action-primary-hover',
};

export function StatusBadge({
  tone = 'neutral',
  variant = 'soft',
  label,
  icon,
}: {
  tone?: BadgeTone;
  variant?: Variant;
  label: string;
  icon?: IconName;
}): JSX.Element {
  const r = RESOLVE[tone];
  const styles = variant === 'solid' ? SOLID[r] : variant === 'outline' ? OUTLINE[r] : SOFT[r];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-label',
        styles,
      )}
    >
      {icon && <Icon name={icon} size={14} className="-ml-0.5 shrink-0" />}
      {label}
    </span>
  );
}
