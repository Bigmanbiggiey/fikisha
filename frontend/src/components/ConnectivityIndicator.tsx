import { Icon } from '@/design/Icon';
import { CONNECTIVITY_VISUAL, type ConnectivityState } from '@/design/tokens';
import { cn } from './cn';

const TONE_TEXT: Record<string, string> = {
  success: 'text-status-success-fg',
  info: 'text-status-info-fg',
  warning: 'text-status-warning-fg',
  neutral: 'text-fg-muted',
  danger: 'text-status-danger-fg',
  brand: 'text-action-primary',
};

/**
 * ConnectivityIndicator — Design Phase 4 §6.5/§30.26. Always in the app bar.
 * Never colour-only: icon + word. `count` is shown for the sync-issue state.
 */
export function ConnectivityIndicator({
  state,
  count,
  label,
  className,
}: {
  state: ConnectivityState;
  count?: number;
  label?: string;
  className?: string;
}): JSX.Element {
  const v = CONNECTIVITY_VISUAL[state];
  return (
    <span
      role="status"
      aria-live="polite"
      className={cn('inline-flex items-center gap-1 text-caption', TONE_TEXT[v.tone], className)}
    >
      <Icon name={v.icon} size={14} className={state === 'syncing' ? 'motion-safe:animate-spin' : undefined} />
      <span>
        {label ?? v.labelEn}
        {state === 'sync_issue' && typeof count === 'number' ? ` (${count})` : ''}
      </span>
    </span>
  );
}
