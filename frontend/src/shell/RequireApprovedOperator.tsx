import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { PageLoader } from '@/components/PageLoader';

import { useActiveRole } from './activeRole';
import { OPERATOR_SIDE_ROLES } from './navConfig';

/**
 * Keeps an operator Fikisha has not approved yet (status `PENDING`) on the
 * screens that get them approved: work, jobs, messages, groups and
 * statements send them Home, where their checklist is (assessment 2026-10-19
 * D-2 / D-3). Only while they are working as an operator-side role: the same
 * person working as a Business keeps those screens. UX only; the server
 * refuses a pending operator's work on its own.
 */
export function RequireApprovedOperator({ children }: { children: ReactNode }): JSX.Element {
  const { loading, role, operatorPending } = useActiveRole();
  if (loading) return <PageLoader />;
  if (operatorPending && role && OPERATOR_SIDE_ROLES.has(role)) {
    return <Navigate to="/home" replace />;
  }
  return <>{children}</>;
}
