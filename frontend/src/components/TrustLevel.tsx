import { cn } from './cn';

/**
 * TrustLevel — Design Phase 4 §16.2/§30.9. An "earned standing" ladder: N filled
 * clay pips of `total`. NOT a rating, NOT stars. The accessible name carries the
 * full meaning (level, name, and the value band it is cleared for).
 */
export function TrustLevel({
  level,
  total = 3,
  name,
  /** e.g. "cleared for deliveries up to KSh 250,000" */
  bandDescription,
  compact = false,
  className,
}: {
  level: number;
  total?: number;
  name?: string;
  bandDescription?: string;
  compact?: boolean;
  className?: string;
}): JSX.Element {
  const accessibleName = [
    `Level ${level} of ${total}`,
    name,
    bandDescription,
  ]
    .filter(Boolean)
    .join(' — ');
  return (
    <span
      className={cn('inline-flex items-center gap-2', className)}
      role="img"
      aria-label={accessibleName}
    >
      <span className="flex items-center gap-0.5" aria-hidden>
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              i < level ? 'bg-accent-token-pip-filled' : 'bg-accent-token-pip-empty',
            )}
          />
        ))}
      </span>
      <span aria-hidden className="text-label text-accent-token-text">
        {compact ? `L${level}` : name ? `Level ${level} · ${name}` : `Level ${level}`}
      </span>
    </span>
  );
}
