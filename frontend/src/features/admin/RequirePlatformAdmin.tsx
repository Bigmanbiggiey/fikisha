import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { isPlatformAdmin } from '@/features/auth/staff';
import { useAuth } from '@/features/auth/useAuth';

/**
 * UX-only gate for Platform Admin console routes (Increment 9): anyone else,
 * an Operations Officer included, goes Home instead of a screen of 403s.
 * The server's policies are the enforcement.
 */
export function RequirePlatformAdmin({ children }: { children: ReactNode }): JSX.Element {
  const { user } = useAuth();
  if (!isPlatformAdmin(user)) return <Navigate to="/home" replace />;
  return <>{children}</>;
}
