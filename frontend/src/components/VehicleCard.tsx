import { Card } from './Card';
import { Icon } from '@/design/Icon';
import { StatusBadge } from './StatusBadge';
import { VerificationPill } from './VerificationPill';
import { vehicleStatusBadge } from './vehicleStatus';
import type { VerificationState } from '@/design/tokens';

/**
 * VehicleCard — Design Phase 4 §30.10. Class + plate + status + verification
 * marker. `SUSPENDED` is admin-only and read-only to an operator (the caller
 * controls whether any action is offered).
 */
export function VehicleCard({
  vehicleClass,
  registration,
  capacity,
  status,
  statusLabel,
  verification,
  className,
}: {
  vehicleClass: string;
  registration: string;
  capacity?: string;
  status: 'ACTIVE' | 'UNDER_REPAIR' | 'SUSPENDED' | 'INACTIVE';
  statusLabel?: string;
  verification?: { domain: string; state: VerificationState };
  className?: string;
}): JSX.Element {
  return (
    <Card className={className}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon name="truck" size={20} className="text-fg-secondary" />
          <div>
            <p className="text-h3 text-fg">{vehicleClass}</p>
            <p className="fk-numeric text-body-sm text-fg-secondary">{registration}</p>
          </div>
        </div>
        <StatusBadge
          {...vehicleStatusBadge(status)}
          label={statusLabel ?? vehicleStatusBadge(status).label}
        />
      </div>
      {capacity && <p className="mt-2 text-body-sm text-fg-secondary">{capacity}</p>}
      {verification && (
        <div className="mt-2">
          <VerificationPill domain={verification.domain} state={verification.state} />
        </div>
      )}
    </Card>
  );
}
