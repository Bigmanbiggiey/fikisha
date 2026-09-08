import { useId, type ReactNode } from 'react';

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  children: (props: { id: string; invalid: boolean }) => ReactNode;
}

export function Field({ label, hint, error, children }: FieldProps): JSX.Element {
  const id = useId();
  const invalid = Boolean(error);
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children({ id, invalid })}
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  );
}
