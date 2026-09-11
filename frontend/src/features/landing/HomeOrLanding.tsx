import { Navigate } from 'react-router-dom';

import { PageLoader } from '@/components/PageLoader';
import { useAuth } from '@/features/auth/useAuth';

import { LandingPage } from './LandingPage';

/**
 * The `/` route. A first-time or signed-out visitor sees the public
 * `LandingPage` — no account/session required. A signed-in visitor is sent
 * straight to their dashboard (`/home`); `/` itself is never a protected
 * route, so it never bounces a new user to `/login`.
 */
export function HomeOrLanding(): JSX.Element {
  const { status } = useAuth();

  if (status === 'loading') return <PageLoader />;
  if (status === 'authenticated') return <Navigate to="/home" replace />;
  return <LandingPage />;
}
