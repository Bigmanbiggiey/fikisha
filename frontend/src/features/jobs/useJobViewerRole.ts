import { useAuth } from '@/features/auth/useAuth';
import { isPlatformAdmin, isStaff } from '@/features/auth/staff';
import { useWorkspaces } from '@/shell/useWorkspaces';

export type JobViewerRole = 'BUSINESS' | 'OPERATOR' | 'STAFF';

interface JobViewerRoleState {
  loading: boolean;
  role: JobViewerRole;
  /** The viewer's own operator profile id, when they have one — used to
   * tell "the assigned driver" apart from "an operator/group manager who
   * isn't personally driving" (`design-phase-3-wireframes.md` §7.4). */
  operatorId: string | null;
  /** True when the OPERATOR viewer is this job's assigned driver
   * (`job.assigned_driver_id` is an operator profile id — group drivers
   * have one too). Picks the driver's "Current job" rendering (P3 §10.1,
   * Design Phase 7 P-03). */
  isAssignedDriver: boolean;
  /** Staff tier, for the Platform-Admin-only controls on the STAFF view. */
  isPlatformAdmin: boolean;
}

/**
 * `/jobs/:jobId`, `/jobs/:jobId/negotiation`, and My Jobs are shared routes a
 * Business owner and an Operator can both reach for the *same* job — unlike
 * `useActiveBusiness` (which picks a workspace with no job in view), this
 * resolves the viewer's role **for this specific job**: if one of the
 * viewer's own Business workspaces owns the job, they see the Business
 * rendering; otherwise Fikisha staff (Ops Officer / Platform Admin, Design
 * Phase 6 Increment 8) see the STAFF rendering; otherwise, if they have an
 * Operator workspace at all, they see the Operator rendering. A person who
 * is none of these (shouldn't normally reach this route — `job.read` authz
 * already requires being a party) falls back to `BUSINESS` rather than
 * rendering nothing.
 */
export function useJobViewerRole(
  businessId: string | undefined,
  assignedDriverId?: string | null,
): JobViewerRoleState {
  const { user } = useAuth();
  const { loading, workspaces } = useWorkspaces();
  const platformAdmin = isPlatformAdmin(user);
  const base = { operatorId: null, isAssignedDriver: false, isPlatformAdmin: platformAdmin };
  if (loading) return { ...base, loading: true, role: 'BUSINESS' };

  const ownsThisBusiness = !!businessId && workspaces.some((w) => w.kind === 'BUSINESS' && w.id === businessId);
  const operatorWorkspace = workspaces.find((w) => w.kind === 'OPERATOR');
  const operatorId = operatorWorkspace?.id ?? null;

  if (!ownsThisBusiness && isStaff(user)) {
    return { ...base, loading: false, role: 'STAFF', operatorId };
  }
  if (!ownsThisBusiness && operatorWorkspace) {
    const isAssignedDriver = !!assignedDriverId && assignedDriverId === operatorId;
    return { ...base, loading: false, role: 'OPERATOR', operatorId, isAssignedDriver };
  }
  return { ...base, loading: false, role: 'BUSINESS', operatorId };
}
