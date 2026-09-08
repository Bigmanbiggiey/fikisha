import { Outlet } from 'react-router-dom';

import { TopBar } from './TopBar';

export function AppShell(): JSX.Element {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Fikisha · Phase 2A foundation
      </footer>
    </div>
  );
}
