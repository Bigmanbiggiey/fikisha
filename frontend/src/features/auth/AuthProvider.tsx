import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { onAuthLost, setAccessToken } from '@/services/apiClient';

import { authApi } from './authApi';
import { AuthContext, type AuthContextValue, type AuthStatus } from './AuthContext';
import type { AuthUser, VerifyResult } from './types';

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);

  const reloadMe = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
      setStatus('authenticated');
    } catch {
      setUser(null);
      setStatus('anonymous');
    }
  }, []);

  const completeLogin = useCallback((result: VerifyResult) => {
    setAccessToken(result.access_token);
    setUser(result.user);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Best effort — clear locally regardless.
    }
    setAccessToken(null);
    setUser(null);
    setStatus('anonymous');
  }, []);

  // On first load, try to silently resume a session from the refresh cookie.
  useEffect(() => {
    void reloadMe();
  }, [reloadMe]);

  // If the API client gives up on refreshing, drop to anonymous.
  useEffect(
    () =>
      onAuthLost(() => {
        setUser(null);
        setStatus('anonymous');
      }),
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, completeLogin, logout, reloadMe }),
    [status, user, completeLogin, logout, reloadMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
