import { useQuery } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useState } from 'react';

import { useAuth } from '@/features/auth/useAuth';
import { vehiclesApi } from '@/features/vehicles/vehiclesApi';

import { NAV_ROLES, ROLE_PRIORITY, type NavRole } from './navConfig';
import { useWorkspaces } from './useWorkspaces';

interface NavRolesState {
  loading: boolean;
  /** the navigation roles this person can work as, in priority order */
  roles: NavRole[];
}

/**
 * Which navigation roles a person has (Design Phase 7 P-04). Mostly one per
 * workspace kind, with the driver rule the founder chose on 2026-09-28:
 * - a group DRIVER gets the Driver navigation (IA §4.3, §7);
 * - the Operator navigation needs an operator profile, and, for someone who
 *   is also a group driver, a vehicle they own personally (that is what
 *   makes them an individual operator as well); a solo operator without a
 *   group keeps it regardless;
 * - Platform Admin wins over Operations when a person has both.
 * UX only: the server authorises every action.
 */
export function useNavRoles(): NavRolesState {
  const { loading, workspaces } = useWorkspaces();
  const has = (kind: string): boolean => workspaces.some((w) => w.kind === kind);
  const operatorId = workspaces.find((w) => w.kind === 'OPERATOR')?.id ?? null;
  const isGroupDriver = has('DRIVER');

  const ownsVehicle = useQuery({
    queryKey: ['vehicles'],
    queryFn: vehiclesApi.list,
    enabled: !loading && isGroupDriver && !!operatorId,
    retry: false,
    select: (page) => page.data.some((v) => v.owner_operator_id === operatorId),
  });

  if (loading || (ownsVehicle.isPending && ownsVehicle.fetchStatus !== 'idle')) {
    return { loading: true, roles: [] };
  }

  const roles = new Set<NavRole>();
  if (has('BUSINESS')) roles.add('BUSINESS');
  if (operatorId && (!isGroupDriver || ownsVehicle.data)) roles.add('OPERATOR');
  if (isGroupDriver) roles.add('DRIVER');
  if (has('GROUP_MANAGER')) roles.add('GROUP_MANAGER');
  if (has('PLATFORM_ADMIN')) roles.add('PLATFORM_ADMIN');
  else if (has('OPERATIONS_OFFICER')) roles.add('OPERATIONS_OFFICER');

  return { loading: false, roles: ROLE_PRIORITY.filter((r) => roles.has(r)) };
}

export interface ActiveRoleState extends NavRolesState {
  /** the role whose navigation is showing; null when the person has none */
  role: NavRole | null;
  setRole: (role: NavRole) => void;
}

const storageKey = (userId: string): string => `fikisha.activeRole.${userId}`;

function readStored(userId: string | undefined): NavRole | null {
  if (!userId) return null;
  try {
    const value = window.localStorage.getItem(storageKey(userId));
    return (NAV_ROLES as readonly string[]).includes(value ?? '') ? (value as NavRole) : null;
  } catch {
    return null; // storage blocked (private window etc.): fall back to the default
  }
}

export function useActiveRoleState(): ActiveRoleState {
  const { user } = useAuth();
  const { loading, roles } = useNavRoles();
  const [picked, setPicked] = useState<{ userId: string; role: NavRole } | null>(null);

  const wanted = picked && picked.userId === user?.id ? picked.role : readStored(user?.id);
  const role = wanted && roles.includes(wanted) ? wanted : (roles[0] ?? null);

  const setRole = useCallback(
    (next: NavRole) => {
      if (!user) return;
      setPicked({ userId: user.id, role: next });
      try {
        window.localStorage.setItem(storageKey(user.id), next);
      } catch {
        // storage blocked: the choice still holds for this visit
      }
    },
    [user],
  );

  return { loading, roles, role, setRole };
}

/** Shared by ActiveRoleProvider (mounted in AppShell). */
export const ActiveRoleContext = createContext<ActiveRoleState | null>(null);

/** The active navigation role. Works outside the provider too (a page
 * rendered on its own, e.g. in a test), falling back to the default role. */
export function useActiveRole(): ActiveRoleState {
  const shared = useContext(ActiveRoleContext);
  const own = useActiveRoleState();
  return shared ?? own;
}
