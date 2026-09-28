import { Outlet, useLocation } from 'react-router-dom';

import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';

import { ActiveRoleProvider } from './ActiveRoleProvider';
import { RoleSidebar } from './RoleSidebar';
import { RoleTabBar } from './RoleTabBar';
import { TopBar } from './TopBar';

/**
 * AppShell (Design Phase 7 P-04, F-04 / F-16). Role navigation per P3
 * §24.2: a bottom tab bar on phones, the top bar's inline links on tablets,
 * a persistent sidebar from `lg`. The header and body share one width
 * container, so the header lines up with the content everywhere. Reading
 * pages keep a readable column; the Ops console (`/ops/*`) uses the full
 * width (P3 §18: a dense, desktop-first workspace). The "Phase 2A
 * foundation" footer is gone (F-16).
 */
export function AppShell(): JSX.Element {
  const { pathname } = useLocation();
  const { status } = useAuth();
  const signedIn = status === 'authenticated';
  const wide = pathname === '/ops' || pathname.startsWith('/ops/');

  return (
    <ActiveRoleProvider>
      <div className="flex min-h-full flex-col bg-surface-page">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-toast focus:rounded-md focus:bg-surface-card focus:px-3 focus:py-2 focus:text-label focus:text-action-primary focus:shadow-e2"
        >
          Skip to content
        </a>
        <TopBar />
        <div className="mx-auto flex w-full max-w-6xl flex-1 gap-6 px-4">
          {signedIn && <RoleSidebar />}
          {/* Bottom padding on phones keeps content clear of the tab bar. */}
          <main id="main" className={cn('min-w-0 flex-1 py-6', signedIn && 'pb-28 md:pb-6')}>
            <div className={cn('mx-auto w-full', !wide && 'max-w-3xl')}>
              <Outlet />
            </div>
          </main>
        </div>
        {signedIn && <RoleTabBar />}
      </div>
    </ActiveRoleProvider>
  );
}
