import { Select } from '@/components/Select';

/** A labelled `<Select>` for list filters (Ops monitor, Platform Admin
 * directory). */
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
      <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, text]) => (
          <option key={v || 'any'} value={v}>
            {text}
          </option>
        ))}
      </Select>
    </div>
  );
}
