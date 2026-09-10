import { VerificationPill } from './VerificationPill';
import { TrustLevel } from './TrustLevel';
import type { VerificationState } from '@/design/tokens';

/**
 * TrustFacts — Design Phase 4 §16/§30.9. A stacked list of verification pills
 * (evidence, not praise) with an optional trust-level ladder. Enforces
 * VERIFIED ≠ TRUSTED ≠ RECOMMENDED: no endorsement, no score. Absence of a fact
 * is neutral, never danger.
 */
export function TrustFacts({
  facts,
  level,
  className,
}: {
  facts: Array<{ domain: string; state: VerificationState }>;
  level?: { level: number; total?: number; name?: string; bandDescription?: string };
  className?: string;
}): JSX.Element {
  return (
    <div className={className}>
      <ul className="flex flex-wrap gap-1.5">
        {facts.map((f) => (
          <li key={f.domain}>
            <VerificationPill domain={f.domain} state={f.state} />
          </li>
        ))}
      </ul>
      {level && (
        <div className="mt-2">
          <TrustLevel {...level} />
        </div>
      )}
    </div>
  );
}
