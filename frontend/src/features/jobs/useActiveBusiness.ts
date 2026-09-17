import { useWorkspaces } from '@/shell/useWorkspaces';

interface ActiveBusinessState {
  loading: boolean;
  /** `null` once loaded if the user has no Business workspace at all. */
  businessId: string | null;
}

/**
 * The Business Jobs screens need one active business to scope Job creation
 * and lists to. A person can belong to more than one business (`useWorkspaces`
 * resolves all of them), but the wireframes' Business nav (`design-phase-3-
 * wireframes.md` §6) is flat, not per-business — there's no picker in the
 * approved design. For the pilot's realistic scale (typically one business
 * per owner), this simply uses the first Business workspace found. If more
 * than one turns out to matter in practice, add a picker here — a known,
 * documented simplification, not a silent one.
 */
export function useActiveBusiness(): ActiveBusinessState {
  const { loading, workspaces } = useWorkspaces();
  if (loading) return { loading: true, businessId: null };
  const business = workspaces.find((w) => w.kind === 'BUSINESS');
  return { loading: false, businessId: business?.id ?? null };
}
