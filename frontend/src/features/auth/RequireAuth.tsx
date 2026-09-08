import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { PageLoader } from '@/components/PageLoader';

import { useAuth } from './useAuth';

export function RequireAuth({ children }: { children: ReactNode }): JSX.Element {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <PageLoader />;
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
