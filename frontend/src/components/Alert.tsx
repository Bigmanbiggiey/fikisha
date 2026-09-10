import type { ReactNode } from 'react';

import { cn } from './cn';
import { Icon, type IconName } from '@/design/Icon';

/** `error` is kept as an alias of `danger` for existing call sites. */
type Tone = 'info' | 'success' | 'warning' | 'danger' | 'error';

const RESOLVED: Record<Tone, 'info' | 'success' | 'warning' | 'danger'> = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  error: 'danger',
};

const STYLES: Record<'info' | 'success' | 'warning' | 'danger', string> = {
  info: 'border-status-info-border bg-status-info-bg text-status-info-fg',
  success: 'border-status-success-border bg-status-success-bg text-status-success-fg',
  warning: 'border-status-warning-border bg-status-warning-bg text-status-warning-fg',
  danger: 'border-status-danger-border bg-status-danger-bg text-status-danger-fg',
};

const ICONS: Record<'info' | 'success' | 'warning' | 'danger', IconName> = {
  info: 'circle',
  success: 'check',
  warning: 'alertTriangle',
  danger: 'alert',
};

/**
 * Alert / banner — Design Phase 5B. Colour is always paired with an icon and
 * text. `danger` (and its `error` alias) is a live `role="alert"`; the rest are
 * polite `role="status"`.
 */
export function Alert({
  tone = 'info',
  title,
  children,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
}): JSX.Element {
  const resolved = RESOLVED[tone];
  return (
    <div
      role={resolved === 'danger' ? 'alert' : 'status'}
      className={cn('flex gap-2 rounded-md border px-4 py-3 text-body-sm', STYLES[resolved])}
    >
      <Icon name={ICONS[resolved]} size={18} className="mt-0.5 shrink-0" />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cn(title && 'mt-1')}>{children}</div>}
      </div>
    </div>
  );
}
