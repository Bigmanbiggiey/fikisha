import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/features/auth/useAuth';
import { orgApi } from '@/features/org/orgApi';
import { ApiError } from '@/services/problem';

import type { Workspace } from './workspaces';

const GROUP_MANAGER_ROLES = new Set(['OWNER', 'MANAGER']);

interface WorkspacesState {
  loading: boolean;
  workspaces: Workspace[];
}

/**
 * Resolves every workspace this signed-in user actually has, by calling the
 * same org endpoints the existing Businesses/Operator/Groups screens already
 * use (`orgApi`), via the codebase's established `@tanstack/react-query`
 * pattern (see `OperatorProfilePage.tsx` for the same
 * no-operator-yet-is-a-404-not-an-error handling this mirrors) — no new
 * backend endpoint. A person can hold more than one workspace (e.g. a
 * business owner who is also an operator); the caller decides how to
 * present that (Q3, `design-phase-6-jobs-frontend-plan.md` §9).
 */
export function useWorkspaces(): WorkspacesState {
  const { status, user } = useAuth();
  const enabled = status === 'authenticated' && !!user;

  const businesses = useQuery({
    queryKey: ['businesses'],
    queryFn: orgApi.listBusinesses,
    enabled,
    retry: false,
  });
  const operator = useQuery({
    queryKey: ['operator', 'me'],
    queryFn: orgApi.getMyOperator,
    enabled,
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 1,
  });
  const groups = useQuery({ queryKey: ['groups'], queryFn: orgApi.listGroups, enabled, retry: false });

  if (!enabled) {
    return { loading: status === 'loading', workspaces: [] };
  }
  if (businesses.isPending || groups.isPending || (operator.isPending && operator.fetchStatus !== 'idle')) {
    return { loading: true, workspaces: [] };
  }

  const workspaces: Workspace[] = [];
  for (const business of businesses.data?.data ?? []) {
    if (business.my_role) {
      workspaces.push({ kind: 'BUSINESS', id: business.id, label: business.trading_name });
    }
  }
  if (operator.data) {
    workspaces.push({
      kind: 'OPERATOR',
      id: operator.data.id,
      label: operator.data.display_name || operator.data.full_name,
    });
  }
  for (const group of groups.data?.data ?? []) {
    if (group.my_role && GROUP_MANAGER_ROLES.has(group.my_role)) {
      workspaces.push({ kind: 'GROUP_MANAGER', id: group.id, label: group.name });
    }
  }
  if (user.roles.includes('OPERATIONS_OFFICER')) {
    workspaces.push({ kind: 'OPERATIONS_OFFICER', id: null, label: 'Operations' });
  }
  // By role only — `is_admin` is true for Ops Officers too (any active
  // AdminProfile), so it must not grant a Platform Admin workspace.
  if (user.roles.includes('PLATFORM_ADMIN')) {
    workspaces.push({ kind: 'PLATFORM_ADMIN', id: null, label: 'Platform Admin' });
  }

  return { loading: false, workspaces };
}
