import type { ReactNode } from 'react';

import { Button, type ButtonProps } from './Button';
import { cn } from './cn';

/**
 * NextActionCard — Design Phase 4 §30.4. The one thing the user can do now, or
 * an explicit "nothing needed". On driver-critical screens pass `driver` to get
 * the 56px dominant treatment.
 */
export function NextActionCard({
  action,
  emptyLabel = 'Nothing needed from you right now.',
  driver = false,
  note,
  className,
}: {
  /** the single primary action, or omit for the empty state */
  action?: { label: ReactNode } & Omit<ButtonProps, 'children' | 'size' | 'fullWidth' | 'variant'> & {
      variant?: ButtonProps['variant'];
    };
  emptyLabel?: ReactNode;
  driver?: boolean;
  /** optional supporting line (e.g. a disabled reason, or offline guidance) */
  note?: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={cn(
        'rounded-md border border-line bg-surface-card p-4',
        driver && 'p-5',
        className,
      )}
    >
      {action ? (
        (() => {
          const { label, variant, ...buttonRest } = action;
          return (
            <Button
              {...buttonRest}
              variant={variant ?? 'primary'}
              size={driver ? 'driver' : 'default'}
              fullWidth
            >
              {label}
            </Button>
          );
        })()
      ) : (
        <p className="text-body text-fg-secondary">{emptyLabel}</p>
      )}
      {note && <p className="mt-2 text-body-sm text-fg-muted">{note}</p>}
    </div>
  );
}
