import type { IconName } from '@/design/Icon';
import type { BadgeTone } from './StatusBadge';

/**
 * Vehicle operational status → chip presentation (Design Phase 4 §15 / §30.10).
 * `SUSPENDED` is admin-only; `ACTIVE` is the only "operational" state.
 * The authoritative status values are unchanged.
 */
export type VehicleStatus = 'ACTIVE' | 'UNDER_REPAIR' | 'SUSPENDED' | 'INACTIVE';

const TONE: Record<VehicleStatus, BadgeTone> = {
  ACTIVE: 'success',
  UNDER_REPAIR: 'warning',
  SUSPENDED: 'danger',
  INACTIVE: 'neutral',
};

const ICON: Record<VehicleStatus, IconName | undefined> = {
  ACTIVE: 'check',
  UNDER_REPAIR: 'alertTriangle',
  SUSPENDED: 'alert',
  INACTIVE: undefined,
};

/** StatusBadge props for a vehicle's operational status. */
export function vehicleStatusBadge(status: string): {
  tone: BadgeTone;
  icon?: IconName;
  label: string;
} {
  const s = (status as VehicleStatus) in TONE ? (status as VehicleStatus) : 'INACTIVE';
  return { tone: TONE[s], icon: ICON[s], label: status.replace(/_/g, ' ') };
}
