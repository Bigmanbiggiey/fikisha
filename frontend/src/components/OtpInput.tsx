import { useRef } from 'react';

import { cn } from './cn';

export interface OtpInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  /** The single accessible name for the whole group — `design-phase-3-
   * wireframes.md` §11.1's a11y note: one `aria-label` on the group, not
   * per-cell (e.g. "Pickup code"). */
  label: string;
  error?: string;
  disabled?: boolean;
}

/**
 * OtpInput — Design Phase 6 Increment 5. 6 single-character cells (one
 * `aria-label` on the group), `inputMode="numeric"`, paste-to-fill —
 * pasting a full code into any cell distributes it across all cells and
 * focuses the last filled one.
 */
export function OtpInput({
  length = 6,
  value,
  onChange,
  label,
  error,
  disabled = false,
}: OtpInputProps): JSX.Element {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length }, (_, i) => value[i] ?? '');

  function setDigit(index: number, digit: string): void {
    const next = digits.slice();
    next[index] = digit;
    onChange(next.join(''));
  }

  function handleChange(index: number, raw: string): void {
    const clean = raw.replace(/\D/g, '');
    if (!clean) {
      setDigit(index, '');
      return;
    }
    if (clean.length > 1) {
      // A paste landed in one cell — distribute across the rest.
      const next = digits.slice();
      for (let i = 0; i < clean.length && index + i < length; i++) {
        next[index + i] = clean.charAt(i);
      }
      onChange(next.join(''));
      const lastIndex = Math.min(index + clean.length, length) - 1;
      refs.current[lastIndex]?.focus();
      return;
    }
    setDigit(index, clean);
    if (index < length - 1) refs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>): void {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
  }

  return (
    <div className="space-y-1">
      <div role="group" aria-label={label} className="flex gap-2">
        {digits.map((digit, i) => (
          <input
            key={i}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="text"
            inputMode="numeric"
            autoComplete={i === 0 ? 'one-time-code' : 'off'}
            maxLength={length}
            value={digit}
            disabled={disabled}
            aria-invalid={!!error || undefined}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className={cn(
              'h-12 w-10 rounded-md border bg-surface-input text-center text-h3 text-fg',
              'focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
              error
                ? 'border-status-danger-border focus-visible:outline-status-danger-solid'
                : 'border-line-strong focus-visible:outline-line-focus',
              'disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-fg-disabled',
            )}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="text-body-sm text-status-danger-fg">
          {error}
        </p>
      )}
    </div>
  );
}
