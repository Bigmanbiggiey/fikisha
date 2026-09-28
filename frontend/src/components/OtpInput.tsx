import { useId, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { cn } from './cn';

export interface OtpInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  /** The visible label, which also names the group (e.g. "Pickup code"). */
  label: string;
  /** Optional helper line under the label, e.g. where the code comes from. */
  hint?: string;
  error?: string;
  disabled?: boolean;
}

/**
 * OtpInput — Design Phase 6 Increment 5. 6 single-character cells,
 * `inputMode="numeric"`, paste-to-fill — pasting a full code into any cell
 * distributes it across all cells and focuses the last filled one.
 *
 * Labelling (Design Phase 7 P-10 / F-10): the label is **visible** and names
 * the group, as P3 §11.1 intends; each cell also carries a short name
 * ("Digit 1 of 6"), because every input needs its own accessible name
 * (WCAG 4.1.2 — axe flagged all six as unlabelled).
 */
export function OtpInput({
  length = 6,
  value,
  onChange,
  label,
  hint,
  error,
  disabled = false,
}: OtpInputProps): JSX.Element {
  const { t } = useTranslation('common');
  const id = useId();
  const labelId = `${id}-label`;
  const hintId = `${id}-hint`;
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
      <p id={labelId} className="text-label text-fg-secondary">
        {label}
      </p>
      {hint && (
        <p id={hintId} className="text-body-sm text-fg-muted">
          {hint}
        </p>
      )}
      <div
        role="group"
        aria-labelledby={labelId}
        aria-describedby={hint ? hintId : undefined}
        className="flex gap-2"
      >
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
            aria-label={t('otp.digit', { n: i + 1, total: length })}
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
