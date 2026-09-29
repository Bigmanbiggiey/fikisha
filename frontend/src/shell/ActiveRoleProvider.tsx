import type { ReactNode } from 'react';

import { ActiveRoleContext, useActiveRoleState } from './activeRole';

/** Shares one active role across the shell (top bar, tab bar, sidebar,
 * More) and the pages under it. Mounted by AppShell. */
export function ActiveRoleProvider({ children }: { children: ReactNode }): JSX.Element {
  const state = useActiveRoleState();
  return <ActiveRoleContext.Provider value={state}>{children}</ActiveRoleContext.Provider>;
}
