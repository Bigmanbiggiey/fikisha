import { Icon } from '@/design/Icon';
import { TrustFacts } from './TrustFacts';
import { cn } from './cn';
import type { VerificationState } from '@/design/tokens';

/**
 * IdentityCard — Design Phase 4 §30.11. Operator / driver identity for an
 * evaluating audience. `minimal` (recipient) shows only the name, vehicle, and a
 * single "identity verified" line — no phone, no staff detail, no documents,
 * no trust internals (Phase 3 §20.0 minimum-necessary-disclosure).
 */
export function IdentityCard({
  name,
  role,
  vehicle,
  identityVerified = false,
  facts,
  level,
  minimal = false,
  className,
}: {
  name: string;
  role?: string;
  vehicle?: string;
  identityVerified?: boolean;
  facts?: Array<{ domain: string; state: VerificationState }>;
  level?: { level: number; total?: number; name?: string; bandDescription?: string };
  minimal?: boolean;
  className?: string;
}): JSX.Element {
  return (
    <div className={cn('space-y-1', className)}>
      <p className="text-h3 text-fg">{name}</p>
      {role && !minimal && <p className="text-body-sm text-fg-secondary">{role}</p>}
      {vehicle && <p className="text-body-sm text-fg-secondary">{vehicle}</p>}
      {minimal ? (
        identityVerified && (
          <p className="inline-flex items-center gap-1 text-body-sm text-status-success-fg">
            <Icon name="check" size={14} />
            Operator identity verified
          </p>
        )
      ) : (
        facts && facts.length > 0 && <TrustFacts facts={facts} level={level} className="pt-1" />
      )}
    </div>
  );
}
