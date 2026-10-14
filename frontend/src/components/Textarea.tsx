import { forwardRef, type TextareaHTMLAttributes } from 'react';

import { cn } from './cn';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

/**
 * Textarea — Design Phase 7 P-13, to the P4 input spec (same as `Input`):
 * 16px text, `line.strong` border (WCAG 1.4.11), 2px focus ring, a danger
 * border when invalid, a sunken look when disabled. Works inside `Field`
 * (pass its `id` / `aria-describedby`).
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid = false, className, rows = 3, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(
        'block min-h-[88px] w-full rounded-md border bg-surface-input px-3 py-2 text-body text-fg',
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
