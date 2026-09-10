import type { ButtonHTMLAttributes } from 'react';

import { cn } from './cn';
import { Spinner } from './Spinner';

/**
 * Button — Design Phase 5B foundation.
 * One filled `primary` per screen (Phase 3). `driver` size (56px) for
 * driver-critical / safety-critical actions. Consumes semantic tokens only.
 */
type Variant = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'destructive' | 'success';
type Size = 'default' | 'driver' | 'compact';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-action-primary text-action-on-primary hover:bg-action-primary-hover active:bg-action-primary-pressed',
  // driver-critical / safety-critical primary — see `size="driver"`
  success:
    'bg-status-success-solid text-fg-inverse hover:brightness-95 active:brightness-90',
  secondary:
    'border border-line-focus bg-surface-card text-action-secondary-text hover:bg-surface-brand-tint',
  tertiary: 'text-action-secondary-text hover:bg-surface-brand-tint',
  ghost: 'text-action-secondary-text hover:bg-surface-brand-tint',
  destructive:
    'border border-status-danger-border bg-surface-card text-status-danger-fg hover:bg-status-danger-bg',
};

const SIZES: Record<Size, string> = {
  compact: 'min-h-[36px] px-3 text-body-sm',
  default: 'min-h-target px-4 text-body',
  driver: 'min-h-target-driver px-5 text-[1.0625rem] font-bold',
};

export function Button({
  variant = 'primary',
  size = 'default',
  loading = false,
  fullWidth = false,
  disabled,
  className,
  children,
  type = 'button',
  ...rest
}: ButtonProps): JSX.Element {
  const strongPrimary = variant === 'primary' && size === 'driver';
  return (
    <button
      type={type}
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors duration-fast ease-standard',
        'disabled:cursor-not-allowed disabled:border-transparent disabled:bg-action-disabled-surface disabled:text-fg-disabled disabled:hover:bg-action-disabled-surface',
        SIZES[size],
        VARIANTS[variant],
        strongPrimary && 'bg-action-primary-strong hover:bg-action-primary-strong active:brightness-95',
        fullWidth && 'w-full',
        className,
      )}
    >
      {loading && <Spinner aria-hidden />}
      {children}
    </button>
  );
}
