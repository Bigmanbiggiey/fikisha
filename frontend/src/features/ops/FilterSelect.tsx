/** A labelled `<select>` for list filters (Ops monitor, Platform Admin
 * directory). */
export const selectClass =
  'block min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg';

export function FilterSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
}): JSX.Element {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-label text-fg-secondary">
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={selectClass}>
        {options.map(([v, text]) => (
          <option key={v || 'any'} value={v}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}
