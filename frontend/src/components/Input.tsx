import { forwardRef, type InputHTMLAttributes } from 'react';

import { cn } from './cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

/**
 * Input — Design Phase 5B. 44px min height, 16px text (no iOS auto-zoom),
 * token-driven border that meets WCAG 1.4.11 (line.strong), 2px focus ring.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid = false, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'block min-h-target w-full rounded-md border bg-surface-input px-3 text-body text-fg',
        'placeholder:text-fg-muted',
        'focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
        invalid
          ? 'border-status-danger-border focus-visible:outline-status-danger-solid'
          : 'border-line-strong focus-visible:outline-line-focus',
        'disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-fg-disabled',
        className,
      )}
      {...rest}
    />
  );
});
