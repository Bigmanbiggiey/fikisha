import { useId, type ReactNode } from 'react';

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  /** Show a "Required" marker in text (never colour-only). */
  required?: boolean;
  requiredText?: string;
  children: (props: {
    id: string;
    invalid: boolean;
    'aria-describedby'?: string;
    'aria-required'?: boolean;
  }) => ReactNode;
}

/**
 * Field — label + control + hint/error, Design Phase 5B.
 * The label is always visible (never placeholder-as-label). The error/hint is
 * wired to the control via `aria-describedby`; the error also has `role="alert"`.
 * Required is communicated as text, not a colour-only asterisk.
 */
export function Field({
  label,
  hint,
  error,
  required = false,
  requiredText = 'Required',
  children,
}: FieldProps): JSX.Element {
  const id = useId();
  const describedById = `${id}-desc`;
  const invalid = Boolean(error);
  const described = error || hint ? describedById : undefined;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-label text-fg-secondary">
        {label}
        {required && <span className="ml-1 font-normal text-fg-muted">({requiredText})</span>}
      </label>
      {children({
        id,
        invalid,
        'aria-describedby': described,
        'aria-required': required || undefined,
      })}
      {error ? (
        <p id={describedById} className="text-body-sm text-status-danger-fg" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={describedById} className="text-caption text-fg-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
