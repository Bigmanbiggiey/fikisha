import { Outlet } from 'react-router-dom';

import { TopBar } from './TopBar';

/**
 * AppShell — Design Phase 5B retone. Structure (navigation, IA) is unchanged
 * from Phase 2A; only colours/spacing move to the token system. The content
 * column stays readable-width; role-specific layouts (Operator workspace
 * expansion, Driver focus) are Phase 5C.
 */
export function AppShell(): JSX.Element {
  return (
    <div className="flex min-h-full flex-col bg-surface-page">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-toast focus:rounded-md focus:bg-surface-card focus:px-3 focus:py-2 focus:text-label focus:text-action-primary focus:shadow-e2"
      >
        Skip to content
      </a>
      <TopBar />
      <main id="main" className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-line py-4 text-center text-caption text-fg-muted">
        Fikisha · Phase 2A foundation
      </footer>
    </div>
  );
}
