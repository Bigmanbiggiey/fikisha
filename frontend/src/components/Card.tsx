import type { HTMLAttributes, ReactNode } from 'react';

import { cn } from './cn';

/**
 * Card — Design Phase 5B. A surface in normal flow: hairline border, no shadow,
 * radius `md` (8px). `interactive` gives the whole card a pointer + focusable
 * treatment for card-as-link patterns (Phase 3).
 */
export function Card({
  children,
  className,
  interactive = false,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode; interactive?: boolean }): JSX.Element {
  return (
    <div
      {...rest}
      className={cn(
        'rounded-md border border-line bg-surface-card p-4 sm:p-5',
        interactive &&
          'cursor-pointer transition-colors duration-fast hover:bg-surface-brand-tint focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-line-focus',
        className,
      )}
    >
      {children}
    </div>
  );
}
