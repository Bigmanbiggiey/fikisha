import { cn } from './cn';

type Tone = 'neutral' | 'positive' | 'negative';

const TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700',
  positive: 'bg-green-100 text-green-800',
  negative: 'bg-red-100 text-red-800',
};

export function StatusBadge({ tone = 'neutral', label }: { tone?: Tone; label: string }): JSX.Element {
  return (
    <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium', TONES[tone])}>
      {label}
    </span>
  );
}
