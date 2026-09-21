import { useWorkspaces } from '@/shell/useWorkspaces';

export type JobViewerRole = 'BUSINESS' | 'OPERATOR';

interface JobViewerRoleState {
  loading: boolean;
  role: JobViewerRole;
  /** The viewer's own operator profile id, when they have one — used to
   * tell "the assigned driver" apart from "an operator/group manager who
   * isn't personally driving" (`design-phase-3-wireframes.md` §7.4). */
  operatorId: string | null;
}

/**
 * `/jobs/:jobId`, `/jobs/:jobId/negotiation`, and My Jobs are shared routes a
 * Business owner and an Operator can both reach for the *same* job — unlike
 * `useActiveBusiness` (which picks a workspace with no job in view), this
 * resolves the viewer's role **for this specific job**: if one of the
 * viewer's own Business workspaces owns the job, they see the Business
 * rendering; otherwise, if they have an Operator workspace at all, they see
 * the Operator rendering. A person who is neither (shouldn't normally reach
 * this route — `job.read` authz already requires being a party) falls back
 * to `BUSINESS` rather than rendering nothing.
 */
export function useJobViewerRole(businessId: string | undefined): JobViewerRoleState {
  const { loading, workspaces } = useWorkspaces();
  if (loading) return { loading: true, role: 'BUSINESS', operatorId: null };

  const ownsThisBusiness = !!businessId && workspaces.some((w) => w.kind === 'BUSINESS' && w.id === businessId);
  const operatorWorkspace = workspaces.find((w) => w.kind === 'OPERATOR');

  if (!ownsThisBusiness && operatorWorkspace) {
    return { loading: false, role: 'OPERATOR', operatorId: operatorWorkspace.id };
  }
  return { loading: false, role: 'BUSINESS', operatorId: operatorWorkspace?.id ?? null };
}
