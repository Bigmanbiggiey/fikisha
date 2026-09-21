import { Icon } from '@/design/Icon';

import { cn } from './cn';

export interface EligibilityRowProps {
  name: string;
  value: string;
  label: string;
  meta?: string;
  eligible: boolean;
  reasons?: string[];
  selected: boolean;
  onSelect: (value: string) => void;
}

/**
 * EligibilityRow — Design Phase 6 Increment 4. A radio-group row for a
 * driver/vehicle candidate (or a Work-discovery job card's eligibility
 * marker) that is either selectable or explicitly blocked with a concrete
 * reason — never a bare "ineligible" (`design-phase-3-wireframes.md`
 * §9.2/§7.2). Eligibility is never colour-only: an icon and the reason text
 * carry the state, not colour alone (WCAG 2.2). Ineligible rows are shown,
 * not hidden, with `aria-disabled` and the reason folded into the radio's
 * accessible name.
 */
export function EligibilityRow({
  name,
  value,
  label,
  meta,
  eligible,
  reasons = [],
  selected,
  onSelect,
}: EligibilityRowProps): JSX.Element {
  const reasonText = reasons.join(' ');
  const accessibleLabel = eligible || !reasonText ? label : `${label} — ${reasonText}`;

  return (
    <label
      className={cn(
        'flex items-start gap-3 rounded-md border p-3',
        eligible
          ? cn(
              'cursor-pointer',
              selected
                ? 'border-action-primary bg-surface-brand-tint'
                : 'border-line bg-surface-card hover:bg-surface-brand-tint',
            )
          : 'cursor-not-allowed border-line bg-surface-sunken opacity-80',
      )}
      aria-disabled={!eligible}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={selected}
        disabled={!eligible}
        onChange={() => onSelect(value)}
        aria-label={accessibleLabel}
        className="mt-1 h-4 w-4"
      />
      <span className="flex-1">
        <span className="flex items-center gap-1.5 text-body font-medium text-fg">
          <Icon
            name={eligible ? 'check' : 'alertTriangle'}
            size={16}
            className={eligible ? 'text-status-success-fg' : 'text-status-danger-fg'}
          />
          {label}
        </span>
        {meta && <span className="block text-body-sm text-fg-secondary">{meta}</span>}
        {!eligible && reasonText && (
          <span className="mt-1 block text-body-sm text-status-danger-fg">{reasonText}</span>
        )}
      </span>
    </label>
  );
}
