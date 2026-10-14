import { forwardRef, type SelectHTMLAttributes } from 'react';

import { cn } from './cn';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
  /** size to its content instead of filling the row (a role picker in a
   * member row, the language switcher) */
  inline?: boolean;
}

/**
 * Select — Design Phase 7 P-13, to the P4 input spec (same as `Input`):
 * 44px minimum height, `line.strong` border, 2px focus ring, a danger border
 * when invalid. It needs an accessible name: a `<label htmlFor>`, `Field`, or
 * `aria-label` (axe `select-name`).
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid = false, inline = false, className, children, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'block min-h-target rounded-md border bg-surface-input px-3 text-body text-fg',
        inline ? 'w-auto' : 'w-full',
        'focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
        invalid
          ? 'border-status-danger-border focus-visible:outline-status-danger-solid'
          : 'border-line-strong focus-visible:outline-line-focus',
        'disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-fg-disabled',
        className,
      )}
      {...rest}
    >
      {children}
    </select>
  );
});
