import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { isStaff } from '@/features/auth/staff';

/**
 * UX-only gate for the Ops console routes — sends a non-staff user home
 * instead of showing a screen of 403s. The server's config-driven policies
 * (`job.monitor.view`, `audit.view.scoped`, …) are the enforcement.
 */
export function RequireStaff({ children }: { children: ReactNode }): JSX.Element {
  const { user } = useAuth();
  if (!isStaff(user)) return <Navigate to="/home" replace />;
  return <>{children}</>;
}
