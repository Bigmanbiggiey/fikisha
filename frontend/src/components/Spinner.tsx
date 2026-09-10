import type { HTMLAttributes } from 'react';

import { cn } from './cn';

/**
 * Spinner — a single pending indicator. Decorative by default (`aria-hidden`);
 * pass a `label` to announce it, or wrap the pending region with `aria-busy`.
 * The spin animation is disabled under `prefers-reduced-motion` (see index.css).
 */
export function Spinner({
  className,
  label,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { label?: string }): JSX.Element {
  return (
    <span
      {...rest}
      role={label ? 'status' : undefined}
      aria-hidden={label ? undefined : true}
      className={cn(
        'inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent',
        className,
      )}
    >
      {label ? <span className="sr-only">{label}</span> : null}
    </span>
  );
}
