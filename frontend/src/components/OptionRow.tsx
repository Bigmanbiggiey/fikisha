import { useId } from 'react';

import { Icon } from '@/design/Icon';

import { cn } from './cn';

export interface OptionRowItem<T extends string> {
  value: T;
  label: string;
  /** one plain-language line under the label */
  description: string;
}

/**
 * OptionRows — Design Phase 7 P-12 (F-12). A set of full-width, ≥64 px radio
 * rows for a driver-critical choice (e.g. the pickup / delivery proof
 * method), each with a one-line explanation. Native radios, so arrow keys
 * move the selection and screen readers announce "n of m". The selected row
 * shows a tick and a border, not colour alone.
 */
export function OptionRows<T extends string>({
  legend,
  options,
  value,
  onChange,
  className,
}: {
  /** the question the rows answer; announced as the group name */
  legend: string;
  options: OptionRowItem<T>[];
  value: T | null;
  onChange: (value: T) => void;
  className?: string;
}): JSX.Element {
  const name = useId();
  return (
    <fieldset className={cn('space-y-2', className)}>
      <legend className="mb-2 text-label text-fg-secondary">{legend}</legend>
      {options.map((option) => {
        const checked = value === option.value;
        const descId = `${name}-${option.value}-desc`;
        return (
          <label
            key={option.value}
            className={cn(
              'flex min-h-16 w-full cursor-pointer items-center gap-3 rounded-md border bg-surface-card px-4 py-3',
              'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-action-primary',
              // 2px selected edge without shifting layout: 1px border + 1px inset shadow
              checked
                ? 'border-action-primary bg-surface-brand-tint shadow-[inset_0_0_0_1px_var(--fk-action-primary)]'
                : 'border-line-strong',
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={checked}
              onChange={() => onChange(option.value)}
              aria-describedby={descId}
              className="h-5 w-5 shrink-0 accent-[var(--fk-action-primary)]"
            />
            <span className="min-w-0 flex-1">
              <span className="block text-body font-semibold text-fg">{option.label}</span>
              <span id={descId} className="block text-body-sm text-fg-secondary">
                {option.description}
              </span>
            </span>
            {checked && <Icon name="check" className="shrink-0 text-action-primary" />}
          </label>
        );
      })}
    </fieldset>
  );
}
