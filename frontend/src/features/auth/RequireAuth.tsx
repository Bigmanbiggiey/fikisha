import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { PageLoader } from '@/components/PageLoader';

import { MfaPage } from './MfaPage';
import { useAuth } from './useAuth';

export function RequireAuth({ children }: { children: ReactNode }): JSX.Element {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <PageLoader />;
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  // An admin's roles apply only after MFA (Increment 9a): until this session
  // has passed it, they set up or enter a code before anything else.
  if (user?.mfa?.required && !user.mfa.verified) return <MfaPage />;
  return <>{children}</>;
}
