import { forwardRef, type InputHTMLAttributes } from 'react';

import { cn } from './cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid = false, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm',
        'placeholder:text-slate-400 focus:outline focus:outline-2 focus:outline-offset-1',
        invalid
          ? 'border-red-400 focus:outline-red-500'
          : 'border-slate-300 focus:outline-brand-600',
        className,
      )}
      {...rest}
    />
  );
});
